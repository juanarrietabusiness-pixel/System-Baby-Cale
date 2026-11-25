"""Checkout: guarda el punto de entrega con la dirección (views/checkout_templates.xml, docs/UBICACION.md).

Los campos ``dcasa_ubic_*`` y ``dcasa_referencia`` se sacan del formulario antes de que Odoo lo procese (no son de su
dirección) y, si Odoo aceptó la dirección, se guardan en la dirección de entrega del carrito:

* «Marcar en el mapa»: hace falta un punto de Panamá **confirmado** («Sí, aquí es») y la referencia; si no, el
  formulario vuelve con el aviso, sin guardar nada.
* «Escribirla»: queda como escrita a mano (el motorizado llama antes) y el envío se cotiza como siempre.
* Opcionales, debajo del número de casa: **quién recibe** y **otro teléfono** de Panamá (``dcasa_recibe`` y
  ``dcasa_tel_respaldo``). Vienen llenos con lo de la ficha: vacíos, se borran. Un teléfono que no es de Panamá
  devuelve el formulario con el aviso, sin guardar nada.

Después se vuelve a poner el método de entrega del carrito: así el precio del envío sale del punto nuevo.

La página «¡Gracias por su compra!» (``/shop/confirmation``) muestra la tarjeta «📍 Marcar mi casa en el mapa» si el
pedido va a domicilio y la casa no tiene un punto confiable (views/pedido_templates.xml).
"""
import json

from odoo.addons.website_dcasa.controllers.main import DcasaCheckout
from odoo.http import request, route

from ..models.zona import UbicacionInvalida
from ..motor import casa, geo

CAMPOS = ('dcasa_ubic_modo', 'dcasa_ubic_lat', 'dcasa_ubic_lon', 'dcasa_ubic_origen', 'dcasa_ubic_precision',
          'dcasa_ubic_confirmada', 'dcasa_referencia')
ORIGENES_WEB = ('gps', 'pin', 'busqueda')
FALTA_EL_PUNTO = 'Marque su casa en el mapa y toque «Sí, aquí es» (o elija «Escribir»).'
FALTAN_INDICACIONES = 'Escriba el número de casa y las indicaciones para el motorizado.'
CAMPOS_CASA = ('dcasa_recibe', 'dcasa_tel_respaldo')


def _numero(valor):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def quien_recibe_del_formulario(formulario):
    """``(recibe, telefono, error)`` de los campos opcionales del bloque: ``None`` si el campo no vino (un formulario
    viejo: no se toca la ficha), ``''`` si vino vacío (se borra) y el teléfono ya bien escrito («+507 6123-4567»).
    ``error``: el aviso si el teléfono no es de Panamá."""
    recibe = formulario.get('dcasa_recibe')
    texto = formulario.get('dcasa_tel_respaldo')
    recibe = None if recibe is None else casa.recibe_limpio(recibe)
    if texto is None:
        return recibe, None, None
    texto = geo.texto_corto(texto, casa.MAX_TELEFONO)
    if not texto:
        return recibe, '', None
    numero = casa.telefono_de_respaldo(texto)
    if not numero:
        return recibe, None, casa.MENSAJE_TELEFONO
    return recibe, numero['guardar'], None


def _lo_que_falta(referencia, error_del_telefono):
    """La respuesta del formulario con lo que falta o está mal (sin guardar nada), o ``None``."""
    if not referencia:
        # Siempre, en el mapa o escrita (el dueño, 2026-11-25, como en PedidosYa).
        return json.dumps({'invalid_fields': ['dcasa_referencia'], 'messages': [FALTAN_INDICACIONES]})
    if error_del_telefono:
        return json.dumps({'invalid_fields': ['dcasa_tel_respaldo'], 'messages': [error_del_telefono]})
    return None


class UbicacionCheckout(DcasaCheckout):

    @route()
    def shop_address_submit(self, partner_id=None, address_type='billing', use_delivery_as_billing=None,
                            callback=None, **form_data):
        ubicacion = {campo: form_data.pop(campo, None) for campo in CAMPOS}
        de_la_casa = {campo: form_data.pop(campo) for campo in CAMPOS_CASA if campo in form_data}
        modo = ubicacion['dcasa_ubic_modo']
        if modo not in ('mapa', 'escrita'):
            # Sin el bloque (un formulario viejo o sin productos que entregar): como siempre.
            return super().shop_address_submit(partner_id=partner_id, address_type=address_type,
                                               use_delivery_as_billing=use_delivery_as_billing, callback=callback,
                                               **form_data)
        referencia = geo.texto_corto(ubicacion['dcasa_referencia'] or '', geo.MAX_REFERENCIA)
        recibe, telefono, error = quien_recibe_del_formulario(de_la_casa)
        problema = _lo_que_falta(referencia, error)
        if problema:
            return problema
        punto = None
        if modo == 'mapa':
            punto = geo.punto(_numero(ubicacion['dcasa_ubic_lat']), _numero(ubicacion['dcasa_ubic_lon']))
            origen = ubicacion['dcasa_ubic_origen']
            if not punto or origen not in ORIGENES_WEB or ubicacion['dcasa_ubic_confirmada'] != '1':
                return json.dumps({'invalid_fields': [], 'messages': [FALTA_EL_PUNTO]})
        respuesta = super().shop_address_submit(partner_id=partner_id, address_type=address_type,
                                                use_delivery_as_billing=use_delivery_as_billing, callback=callback,
                                                **form_data)
        # Llamada con super(), la ruta de Odoo devuelve un Response (``route_wrapper``: ``Response.load``), no texto.
        texto = respuesta.get_data(as_text=True) if hasattr(respuesta, 'get_data') else respuesta
        try:
            resultado = json.loads(texto) if isinstance(texto, str) else None
        except ValueError:
            resultado = None
        if not isinstance(resultado, dict) or resultado.get('invalid_fields') or resultado.get('redirectUrl') \
                and '/shop/cart' in str(resultado.get('redirectUrl')):
            return respuesta
        orden = request.cart
        if not orden or not orden.partner_shipping_id:
            return respuesta
        es_entrega = address_type == 'delivery' or use_delivery_as_billing or orden._is_anonymous_cart() \
            or orden.partner_shipping_id == orden.partner_invoice_id
        if not es_entrega:
            return respuesta
        destino = orden.partner_shipping_id.sudo()
        destino._dcasa_poner_quien_recibe(recibe=recibe, telefono=telefono, al_dia=False)
        if modo == 'mapa':
            try:
                destino._dcasa_poner_ubicacion(punto[0], punto[1], ubicacion['dcasa_ubic_origen'],
                                               precision=_numero(ubicacion['dcasa_ubic_precision']),
                                               referencia=referencia, confirmada=True)
            except UbicacionInvalida as error:
                return json.dumps({'invalid_fields': [], 'messages': [str(error.args[0])]})
        else:
            destino._dcasa_poner_escrita(referencia=referencia)
        if orden.carrier_id and orden.carrier_id.dcasa_por_cotizar:
            orden._set_delivery_method(orden.carrier_id)
        return respuesta
