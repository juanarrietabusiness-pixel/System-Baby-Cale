"""El enlace de un solo uso para que la clienta marque su punto de entrega desde el chat (``/u/<secreto>``).

Lo crea Juan (herramienta ``enlace_de_ubicacion``) o alguien del equipo (Brian). Está amarrado a una ficha (y, si
viene del chat, a su conversación): la clienta solo marca el punto en el mapa y, al confirmar, Juan le escribe con la
zona y el precio del envío. **No copia ni pega nada.**

* El secreto (128 bits al azar) se manda una vez y se guarda como huella SHA-256: ni la base lo tiene en texto.
* Vence a las ``HORAS_VIGENCIA`` horas y sirve una sola vez (después dice «ya recibimos su ubicación»).
"""
import logging
from datetime import timedelta

from markupsafe import Markup, escape

from odoo import api, fields, models

from ..motor import geo

_logger = logging.getLogger(__name__)

HORAS_VIGENCIA = 24
RUTA = '/u/'


class UbicacionEnlace(models.Model):
    _name = 'dcasa.ubicacion.enlace'
    _description = 'Enlace para marcar la ubicación de entrega'
    _order = 'id desc'

    huella = fields.Char(required=True, readonly=True, copy=False, index=True, groups='base.group_system')
    partner_id = fields.Many2one('res.partner', 'Clienta', required=True, readonly=True, ondelete='cascade',
                                 index=True)
    conversacion_id = fields.Many2one('dcasa.conversacion', 'Conversación', readonly=True, ondelete='cascade',
                                      index=True)
    orden_id = fields.Many2one('sale.order', 'Pedido', readonly=True, ondelete='cascade', index='btree_not_null',
                               help='Si vino del link de pago (la página del pedido): al confirmar se recalcula su '
                                    'envío y la clienta vuelve a su pedido.')
    creado_por = fields.Selection([('juan', 'Juan (el asistente)'), ('equipo', 'El equipo'),
                                   ('aviso', 'El aviso de la venta')], readonly=True, required=True, default='equipo',
                                  help='«El aviso de la venta»: se lo pidió el sistema al confirmar una venta a '
                                       'domicilio sin su casa en el mapa, o con «🚚 Sale hoy» (models/avisos.py).')
    usuario_id = fields.Many2one('res.users', 'Lo pidió', readonly=True, default=lambda self: self.env.user)
    vence = fields.Datetime(required=True, readonly=True)
    usado_el = fields.Datetime('Usado el', readonly=True)
    zona = fields.Char('Zona marcada', readonly=True)
    estado = fields.Selection([('vigente', 'Esperando a la clienta'), ('usado', 'Ya marcó su punto'),
                               ('vencido', 'Venció')], compute='_compute_estado')

    _huella_unica = models.Constraint('UNIQUE(huella)', 'Ese enlace ya existe.')

    @api.depends('vence', 'usado_el')
    def _compute_estado(self):
        ahora = fields.Datetime.now()
        for enlace in self:
            # Vencido manda (aunque se haya usado): pasadas las 24 horas la página ya no dice ni la zona.
            enlace.estado = 'vencido' if enlace.vence < ahora else 'usado' if enlace.usado_el else 'vigente'

    @api.model
    def _crear(self, partner, conversacion=None, creado_por='equipo', orden=None):
        """``(enlace, url)`` nuevo para esa ficha. El secreto solo vive en la URL que se devuelve."""
        token = geo.token_nuevo()
        enlace = self.sudo().create({
            'huella': geo.huella(token), 'partner_id': partner.id,
            'conversacion_id': conversacion.id if conversacion else False,
            'orden_id': orden.id if orden else False,
            'creado_por': creado_por if creado_por in ('juan', 'aviso') else 'equipo',
            'vence': fields.Datetime.now() + timedelta(hours=HORAS_VIGENCIA),
        })
        return enlace, enlace._url(token)

    def _url(self, token):
        base = (self.env['ir.config_parameter'].sudo().get_param('web.base.url') or '').rstrip('/')
        website = self.env['website'].sudo().search([], limit=1)
        if website and website.domain:
            dominio = website.domain if '://' in website.domain else 'https://' + website.domain
            base = dominio.rstrip('/')
        return f'{base}{RUTA}{token}'

    @api.model
    def _del_secreto(self, token):
        """El enlace de ese secreto (vigente, usado o vencido) o un registro vacío. Busca por la huella."""
        if not isinstance(token, str) or not 16 <= len(token) <= 64:
            return self.sudo().browse()
        return self.sudo().search([('huella', '=', geo.huella(token))], limit=1)

    def _confirmar(self, lat, lon, origen, precision=None, referencia=None):
        """La clienta confirmó su punto en la página del enlace. Guarda el punto en su ficha, marca el enlace usado y
        le escribe por el chat (si vino de una conversación). Devuelve la zona; ``UbicacionInvalida`` si el punto no
        sirve (el enlace sigue vigente para que lo intente otra vez)."""
        self.ensure_one()
        enlace = self.sudo()
        zona = enlace.partner_id._dcasa_poner_ubicacion(lat, lon, origen, precision=precision,
                                                        referencia=referencia, confirmada=True)
        enlace.write({'usado_el': fields.Datetime.now(), 'zona': zona['texto'] or False})
        enlace.partner_id.message_post(
            body=Markup('<p>%s</p>') % escape(self.env._(
                'La clienta marcó su punto de entrega con el enlace del chat: %(zona)s (%(origen)s).',
                zona=zona['texto'] or self.env._('sin zona en la tabla'), origen=geo.etiqueta(origen))),
            subtype_xmlid='mail.mt_note')
        orden = enlace.orden_id.sudo()
        if orden and orden.state in ('draft', 'sent') and orden.carrier_id.dcasa_por_cotizar:
            orden._set_delivery_method(orden.carrier_id)   # el envío del pedido sale del punto nuevo
        if orden:
            orden.message_post(body=Markup('<p>%s</p>') % escape(self.env._(
                'La clienta marcó su punto de entrega desde la página del pedido: %s.', zona['texto'] or '—')),
                subtype_xmlid='mail.mt_note')
        if enlace.conversacion_id:
            enlace._avisar_por_el_chat(zona)
            enlace.conversacion_id.sudo()._aviso(enlace.partner_id._dcasa_ubic_aviso_para_el_equipo())
        return zona

    def _avisar_por_el_chat(self, zona):
        """Juan le escribe a la clienta con la zona y el precio del envío (como el asistente: no toma la
        conversación). Un fallo aquí no deshace el punto: queda guardado y Juan cotiza cuando ella escriba."""
        self.ensure_one()
        conv = self.conversacion_id.sudo()
        try:
            texto = self._texto_para_la_clienta(zona)
            Mensaje = self.env['dcasa.mensaje']
            mensaje, _creado = Mensaje._crear_si_no_existe({
                'conversacion_id': conv.id, 'id_mensaje': Mensaje._id_local(), 'direccion': 'saliente',
                'autor': 'bot', 'texto': texto, 'ts': fields.Datetime.now(), 'origen': 'odoo',
                'estado_envio': 'por_enviar'})
            mensaje._enviar()
        except Exception:   # noqa: BLE001 — el punto ya quedó; el aviso es un extra
            _logger.exception('Ubicación: no se pudo avisar por el chat a la conversación %s', conv.id)

    def _texto_para_la_clienta(self, zona):
        """«✅ ¡Listo! Recibimos su ubicación: Brisas del Golf, San Miguelito. 🚚 Envío $5.00. ¿Se lo sumamos a su
        pedido?» Corto y con íconos (el dueño, 2026-11-25: la gente no lee párrafos), de usted y sin coordenadas. Sin
        precio: se lo confirma la tienda.

        Con la venta ya confirmada (el enlace del aviso al comprar o de «🚚 Sale hoy», models/avisos.py), nada de precio
        ni de «¿se lo sumamos?»: lo cobrado no se cambia. «✅ ¡Listo! Ya tenemos su casa: Villa Lucre, San Miguelito.
        🏠 Casa 24. 🛵 Su pedido S00042 va para allá.» Si el envío de la tabla es otro, el equipo lo ve en la venta."""
        donde = ', '.join(p for p in (zona.get('barriada') or zona.get('corregimiento'), zona.get('distrito')) if p)
        # La casa que escribió en la página (el paso 3): así Juan no se la vuelve a preguntar.
        casa = geo.texto_corto(self.partner_id.sudo().dcasa_referencia, 80)
        orden = self.orden_id.sudo()
        if orden and orden.state not in ('draft', 'sent'):
            listo = (self.env._('✅ ¡Listo! Ya tenemos su casa: %s.', donde) if donde
                     else self.env._('✅ ¡Listo! Ya tenemos su casa.'))
            if casa:
                listo += ' ' + self.env._('🏠 %s.', casa.rstrip('.'))
            if orden.state == 'sale':
                listo += ' ' + self.env._('🛵 Su pedido %s va para allá.', orden.name)
            return listo
        recibido = (self.env._('✅ ¡Listo! Recibimos su ubicación: %s.', donde) if donde
                    else self.env._('✅ ¡Listo! Recibimos su ubicación.'))
        if casa:
            recibido += ' ' + self.env._('🏠 %s.', casa.rstrip('.'))
        precio = self.env['dcasa.ubicacion']._precio(zona.get('lugar'))
        if precio['con_precio']:
            return recibido + ' ' + self.env._('🚚 Envío %s. ¿Se lo sumamos a su pedido?', precio['total_txt'])
        return recibido + ' ' + self.env._('🚚 El costo del envío se lo confirmamos en un momento.')

    @api.autovacuum
    def _gc_enlaces_viejos(self):
        """Los enlaces vencidos hace más de 30 días no sirven para nada: se borran."""
        limite = fields.Datetime.now() - timedelta(days=30)
        self.sudo().search([('vence', '<', limite)]).unlink()
