"""Checkout: guarda el punto de entrega con la dirección (views/checkout_templates.xml, docs/UBICACION.md).

Los campos ``dcasa_ubic_*`` y ``dcasa_referencia`` se sacan del formulario antes de que Odoo lo procese (no son de su
dirección) y, si Odoo aceptó la dirección, se guardan en la dirección de entrega del carrito:

* «Marcar en el mapa»: hace falta un punto de Panamá **confirmado** («Sí, aquí es») y la referencia; si no, el
  formulario vuelve con el aviso, sin guardar nada.
* «Escribirla»: queda como escrita a mano (el motorizado llama antes) y el envío se cotiza como siempre.

Después se vuelve a poner el método de entrega del carrito: así el precio del envío sale del punto nuevo.
"""
import json

from odoo.addons.website_dcasa.controllers.main import DcasaCheckout
from odoo.http import request, route

from ..models.zona import UbicacionInvalida
from ..motor import geo

CAMPOS = ('dcasa_ubic_modo', 'dcasa_ubic_lat', 'dcasa_ubic_lon', 'dcasa_ubic_origen', 'dcasa_ubic_precision',
          'dcasa_ubic_confirmada', 'dcasa_referencia')
ORIGENES_WEB = ('gps', 'pin', 'busqueda')
FALTA_EL_PUNTO = 'Marque su casa en el mapa y toque «Sí, aquí es» (o elija «Escribir»).'
FALTAN_INDICACIONES = 'Escriba el número de casa y las indicaciones para el motorizado.'


def _numero(valor):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


class UbicacionCheckout(DcasaCheckout):

    @route()
    def shop_address_submit(self, partner_id=None, address_type='billing', use_delivery_as_billing=None,
                            callback=None, **form_data):
        ubicacion = {campo: form_data.pop(campo, None) for campo in CAMPOS}
        modo = ubicacion['dcasa_ubic_modo']
        if modo not in ('mapa', 'escrita'):
            # Sin el bloque (un formulario viejo o sin productos que entregar): como siempre.
            return super().shop_address_submit(partner_id=partner_id, address_type=address_type,
                                               use_delivery_as_billing=use_delivery_as_billing, callback=callback,
                                               **form_data)
        referencia = geo.texto_corto(ubicacion['dcasa_referencia'] or '', geo.MAX_REFERENCIA)
        if not referencia:
            # Siempre, en el mapa o escrita (el dueño, 2026-11-25, como en PedidosYa).
            return json.dumps({'invalid_fields': ['dcasa_referencia'], 'messages': [FALTAN_INDICACIONES]})
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
