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
    creado_por = fields.Selection([('juan', 'Juan (el asistente)'), ('equipo', 'El equipo')], readonly=True,
                                  required=True, default='equipo')
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
            enlace.estado = 'usado' if enlace.usado_el else 'vencido' if enlace.vence < ahora else 'vigente'

    @api.model
    def _crear(self, partner, conversacion=None, creado_por='equipo'):
        """``(enlace, url)`` nuevo para esa ficha. El secreto solo vive en la URL que se devuelve."""
        token = geo.token_nuevo()
        enlace = self.sudo().create({
            'huella': geo.huella(token), 'partner_id': partner.id,
            'conversacion_id': conversacion.id if conversacion else False,
            'creado_por': 'juan' if creado_por == 'juan' else 'equipo',
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
        if enlace.conversacion_id:
            enlace._avisar_por_el_chat(zona)
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
        """«Recibimos su ubicación de entrega: Brisas del Golf, San Miguelito. El envío hasta ahí cuesta $5.00. ¿Desea
        que se lo sumemos a su pedido?» (de usted, sin coordenadas). Sin precio: se lo confirma la tienda."""
        donde = zona['texto'].replace(' · ', ', ') if zona.get('texto') else ''
        recibido = (self.env._('Recibimos su ubicación de entrega: %s.', donde) if donde
                    else self.env._('Recibimos su ubicación de entrega.'))
        precio = self.env['dcasa.ubicacion']._precio(zona.get('lugar'))
        if precio['con_precio']:
            return recibido + ' ' + self.env._('El envío hasta ahí cuesta %s. ¿Desea que se lo sumemos a su pedido?',
                                               precio['total_txt'])
        return recibido + ' ' + self.env._('En un momento le confirmamos el costo del envío.')

    @api.autovacuum
    def _gc_enlaces_viejos(self):
        """Los enlaces vencidos hace más de 30 días no sirven para nada: se borran."""
        limite = fields.Datetime.now() - timedelta(days=30)
        self.sudo().search([('vence', '<', limite)]).unlink()
