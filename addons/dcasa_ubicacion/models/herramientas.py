"""La ubicación de entrega para Juan (el asistente de clientes) y para Brian (el del equipo, también por MCP).

Juan:
* ``enlace_de_ubicacion``: el enlace de un solo uso para que la clienta marque su punto (Instagram, Messenger, o si no
  puede compartir su ubicación). Cuando lo confirma, Juan le escribe con la zona y el precio.
* ``cotizar_envio`` sin lugar: si la clienta ya tiene un punto de entrega confirmado, cotiza con ese punto.

Brian (todo el equipo; por MCP también):
* ``ubicacion_de_entrega``: el punto de entrega de una venta (zona, referencia, de dónde salió, Waze y Google Maps).
* ``enlace_de_ubicacion_para_cliente``: el mismo enlace de un solo uso, para mandarlo a mano.
* ``poner_ubicacion_de_entrega``: guarda el punto de un enlace de Google Maps o Waze (o coordenadas) que la clienta
  mandó por otro lado.

Las coordenadas nunca salen en lo que ve el modelo de IA: solo la zona y los botones.
"""
from odoo import api, models
from odoo.addons.dcasa_brian.models.registro import BrianError, herramienta
from odoo.addons.dcasa_conversaciones.models.herramientas_juan import GRUPOS, PREFIJO

from ..motor import enlaces_mapa, geo
from .zona import UbicacionInvalida

INTERNO = ('base.group_user',)


class BrianHerramientasUbicacion(models.AbstractModel):
    _inherit = 'brian.herramientas'

    # ------------------------------------------------------------------
    # Juan: cotizar_envio sin lugar (con el punto guardado)
    # ------------------------------------------------------------------

    @api.model
    def _j_cotizar_envio(self, lugar=None, lugar_id=None):
        sin_lugar = lugar_id is None and not (isinstance(lugar, str) and lugar.strip())
        conv = self._j_conversacion_opcional() if sin_lugar else None
        destino = conv.partner_id.sudo() if conv else None
        if not destino or not destino._dcasa_ubic_punto():
            return super()._j_cotizar_envio(lugar=lugar, lugar_id=lugar_id)
        apagado = self._j_envios_encendidos()
        if apagado:
            return dict(apagado, por_ubicacion=True)
        if not destino.dcasa_ubic_lugar_id:
            return self._j_envio_sin_lugar_cerca()
        datos = super()._j_cotizar_envio(lugar_id=destino.dcasa_ubic_lugar_id.id)
        datos['por_ubicacion'] = True
        datos['ubicacion_guardada'] = destino.dcasa_ubic_zona or ''
        return datos

    # ------------------------------------------------------------------
    # Juan: enlace_de_ubicacion
    # ------------------------------------------------------------------

    @herramienta(
        nombre=PREFIJO + 'enlace_de_ubicacion',
        descripcion='Un enlace de un solo uso para que el cliente marque su punto de entrega en un mapa (vence en 24 '
                    'horas). Úsalo en Instagram o Messenger, o si no puede compartir su ubicación por el chat. '
                    'Cuando lo confirme, la tienda le escribe sola con la zona y el precio del envío: no le pidas '
                    'que copie ni pegue nada.',
        nivel='construccion', categoria='ventas', grupos=GRUPOS,
        ejemplos=['«¿cómo le paso mi dirección?» en Instagram → enlace_de_ubicacion()'],
    )
    def _juan_enlace_de_ubicacion(self):
        conv = self._j_conversacion()
        partner = conv.partner_id.sudo()
        if not partner:
            raise BrianError('Esta conversación todavía no tiene ficha de cliente.')
        _enlace, url = self.env['dcasa.ubicacion.enlace']._crear(partner, conversacion=conv, creado_por='juan')
        return {
            'enlace': url,
            'vence_en_horas': 24,
            'frase_para_el_cliente': 'Para llevárselo exacto, marque su ubicación de entrega en este enlace (se abre '
                                     f'un mapa; no tiene que copiar nada): {url}',
            'instruccion': 'Mándale el enlace con la frase (puedes acortarla, sin cambiar el enlace). Cuando marque su '
                           'punto, la tienda le escribe con la zona y el precio del envío.',
        }

    # ------------------------------------------------------------------
    # Brian (equipo y MCP)
    # ------------------------------------------------------------------

    @api.model
    def _ubic_venta(self, venta):
        texto = str(venta or '').strip()
        if not texto:
            raise BrianError('Dime el número de la venta (p. ej. S00042).')
        orden = self.env['sale.order'].search([('name', '=ilike', texto)], limit=1)
        if not orden:
            raise BrianError(f'No encuentro la venta «{texto[:40]}».')
        return orden

    @api.model
    def _ubic_cliente(self, cliente):
        texto = str(cliente or '').strip()
        if not texto:
            raise BrianError('Dime el cliente (nombre, celular o correo).')
        Partner = self.env['res.partner']
        encontrados = Partner.search(['|', '|', ('name', 'ilike', texto), ('phone', 'ilike', texto),
                                      ('email', '=ilike', texto)], limit=6)
        if not encontrados:
            raise BrianError(f'No encuentro a «{texto[:40]}».')
        if len(encontrados) > 1:
            nombres = '; '.join(f'{p.name} ({p.phone or p.email or "sin contacto"})' for p in encontrados[:5])
            raise BrianError(f'Hay varios: {nombres}. Dime el celular para saber cuál.')
        return encontrados

    @herramienta(
        nombre='ubicacion_de_entrega',
        descripcion='El punto de entrega de una venta: la zona, la dirección, la referencia, de dónde salió el punto '
                    '(GPS, mapa, chat, enlace o escrita) y los botones de Waze y Google Maps para el motorizado.',
        parametros={'venta': {'type': 'string', 'description': 'El número de la venta (p. ej. S00042).'}},
        requeridos=['venta'], nivel='lectura', categoria='ventas', grupos=INTERNO,
        ejemplos=['«¿a dónde va el pedido S00042?» → ubicacion_de_entrega(venta=S00042)'],
    )
    def _brian_ubicacion_de_entrega(self, venta):
        orden = self._ubic_venta(venta)
        destino = orden.partner_shipping_id or orden.partner_id
        resumen = destino._dcasa_ubic_resumen()
        resumen['venta'] = orden.name
        resumen['va_a_domicilio'] = orden._dcasa_va_a_domicilio()
        entrega = self.env['dcasa.ubicacion.entrega']._de_la_venta(orden, crear=False)
        if entrega and self.env.user.has_group('sales_team.group_sale_salesman'):
            resumen['pagina_del_motorizado'] = entrega._url()
        if not resumen['tiene_punto']:
            resumen['aviso'] = 'Sin punto en el mapa: el motorizado tiene que llamar antes de salir.'
        elif not resumen['confiable']:
            resumen['aviso'] = 'El punto es aproximado: conviene confirmarlo con la clienta.'
        return resumen

    @herramienta(
        nombre='enlace_de_ubicacion_para_cliente',
        descripcion='Crea un enlace de un solo uso (vence en 24 horas) para que el cliente marque su punto de entrega '
                    'en un mapa. Es para mandarlo a mano (por WhatsApp, correo…); cuando lo marque, queda en su ficha.',
        parametros={'cliente': {'type': 'string', 'description': 'Nombre, celular o correo del cliente.'}},
        requeridos=['cliente'], nivel='construccion', categoria='ventas', grupos=INTERNO,
        ejemplos=['«mándale a Ana el enlace para que ponga su ubicación» → '
                  'enlace_de_ubicacion_para_cliente(cliente=Ana)'],
    )
    def _brian_enlace_de_ubicacion_para_cliente(self, cliente):
        partner = self._ubic_cliente(cliente)
        partner.check_access('write')
        _enlace, url = self.env['dcasa.ubicacion.enlace']._crear(partner.sudo(), creado_por='equipo')
        return {'cliente': partner.name, 'enlace': url, 'vence_en_horas': 24,
                'texto_para_mandar': f'Para llevárselo exacto, marque su ubicación de entrega aquí: {url}'}

    @herramienta(
        nombre='poner_ubicacion_de_entrega',
        descripcion='Guarda el punto de entrega de un cliente a partir de un enlace de Google Maps o Waze que mandó (o '
                    'de coordenadas). Deduce la zona con la tabla de envíos.',
        parametros={
            'cliente': {'type': 'string', 'description': 'Nombre, celular o correo del cliente.'},
            'enlace_mapa': {'type': 'string', 'description': 'El enlace de Google Maps, Waze o Apple Maps.'},
            'latitud': {'type': 'number', 'description': 'Solo si no hay enlace.'},
            'longitud': {'type': 'number', 'description': 'Solo si no hay enlace.'},
            'referencia': {'type': 'string', 'description': 'Cómo reconocer el sitio (opcional).'},
        },
        requeridos=['cliente'], nivel='construccion', categoria='ventas', grupos=INTERNO,
        ejemplos=['«guarda esta ubicación de Ana: https://maps.app.goo.gl/…» → poner_ubicacion_de_entrega(cliente=Ana, '
                  'enlace_mapa=…)'],
    )
    def _brian_poner_ubicacion_de_entrega(self, cliente, enlace_mapa=None, latitud=None, longitud=None,
                                          referencia=None):
        partner = self._ubic_cliente(cliente)
        partner.check_access('write')
        if enlace_mapa:
            punto = enlaces_mapa.coordenadas(enlace_mapa, resolver_cortos=True)
            if not punto:
                raise BrianError('Ese enlace no trae el punto (puede ser una búsqueda por nombre). Pídele al cliente '
                                 'que comparta su ubicación o mándale el enlace de un solo uso.')
            origen = 'enlace'
        elif latitud is not None and longitud is not None:
            punto, origen = (latitud, longitud), 'pin'
        else:
            raise BrianError('Necesito el enlace del mapa o la latitud y la longitud.')
        try:
            zona = partner._dcasa_poner_ubicacion(*punto, origen, referencia=referencia, confirmada=True)
        except UbicacionInvalida as error:
            raise BrianError(str(error.args[0])) from None
        precio = self.env['dcasa.ubicacion']._precio(zona['lugar'])
        return {'cliente': partner.name, 'zona': zona['texto'] or 'sin lugar de la tabla cerca',
                'origen': geo.etiqueta(origen),
                'envio': precio['total_txt'] if precio['con_precio'] else 'por cotizar'}
