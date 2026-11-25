"""El punto de entrega de una clienta (su dirección de entrega en Odoo: ``res.partner``).

Se guarda solo aquí y en la entrega de cada venta (``dcasa.ubicacion.entrega``): nunca en el texto de una
conversación, en la auditoría de Brian ni en el registro del servidor (docs/UBICACION.md › «Privacidad»)."""
from odoo import api, fields, models

from ..motor import geo


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # partner_latitude / partner_longitude vienen de Odoo (base): son las coordenadas del punto.
    dcasa_ubic_origen = fields.Selection(geo.ORIGENES, string='De dónde salió el punto', readonly=True)
    dcasa_ubic_precision_m = fields.Integer('Precisión del GPS (m)', readonly=True)
    dcasa_ubic_fecha = fields.Datetime('Punto puesto el', readonly=True)
    dcasa_ubic_confirmada = fields.Boolean(
        'La clienta confirmó el punto', readonly=True,
        help='Tocó «Sí, aquí es» en el mapa, o compartió su ubicación por el chat.')
    dcasa_ubic_lugar_id = fields.Many2one(
        'dcasa.envio.lugar', 'Lugar de la calculadora', readonly=True, ondelete='set null',
        help='El lugar de la tabla de envíos más cercano al punto (a no más de 3 km): pone el precio del envío.')
    dcasa_ubic_zona = fields.Char('Zona de entrega', readonly=True,
                                  help='Barriada · corregimiento · distrito · provincia, deducidos del punto.')
    dcasa_barriada = fields.Char('Barriada')
    dcasa_corregimiento = fields.Char('Corregimiento')
    dcasa_distrito = fields.Char('Distrito')
    dcasa_provincia = fields.Char('Provincia')
    dcasa_referencia = fields.Char('Cómo reconocer el sitio', size=geo.MAX_REFERENCIA,
                                   help='Casa verde de portón negro, frente al chino… Lo lee el motorizado.')
    dcasa_ubic_direccion_mapa = fields.Char('Dirección según el mapa', readonly=True,
                                            help='La que da Google para el punto (una ayuda; lo escrito manda).')
    dcasa_ubic_etiqueta = fields.Char('Origen del punto', compute='_compute_dcasa_ubic_etiqueta')
    dcasa_ubic_tiene_punto = fields.Boolean('Tiene punto de entrega', compute='_compute_dcasa_ubic_etiqueta')

    @api.depends('dcasa_ubic_origen', 'dcasa_ubic_precision_m', 'partner_latitude', 'partner_longitude')
    def _compute_dcasa_ubic_etiqueta(self):
        for partner in self:
            partner.dcasa_ubic_tiene_punto = partner._dcasa_ubic_punto() is not None
            partner.dcasa_ubic_etiqueta = geo.etiqueta(
                partner.dcasa_ubic_origen, partner.dcasa_ubic_precision_m or None) if partner.dcasa_ubic_origen else ''

    def _dcasa_ubic_punto(self):
        """``(lat, lon)`` del punto de entrega, o ``None`` (sin punto, o escrito a mano)."""
        self.ensure_one()
        if self.dcasa_ubic_origen in (False, 'escrita'):
            return None
        return geo.punto(self.partner_latitude, self.partner_longitude)

    def _dcasa_poner_ubicacion(self, lat, lon, origen, precision=None, referencia=None, confirmada=True,
                               nombre_lugar=None, direccion=None):
        """Guarda el punto de entrega (con ``sudo``: lo llaman el checkout, la página del enlace, la API de Juan y
        Brian después de comprobar quién es). ``UbicacionInvalida`` si el punto no sirve.

        Devuelve la zona (``dcasa.ubicacion._zona``) con ``aviso`` vacío: el que compara lo escrito lo arma quien
        tiene el texto."""
        self.ensure_one()
        if origen not in geo.ETIQUETAS or origen == 'escrita':
            raise ValueError(f'Origen de ubicación desconocido: {origen!r}')
        Ubicacion = self.env['dcasa.ubicacion']
        lat, lon, zona = Ubicacion._validar(lat, lon)
        calle = Ubicacion._calle_de_google(lat, lon)
        if not calle:
            # WhatsApp manda el nombre y la dirección cuando la clienta elige un lugar en vez de su ubicación.
            calle = ', '.join(p for p in (geo.texto_corto(nombre_lugar, 120), geo.texto_corto(direccion, 200)) if p)
        valores = {
            'partner_latitude': lat, 'partner_longitude': lon,
            'dcasa_ubic_origen': origen,
            'dcasa_ubic_precision_m': geo.precision_m(precision) if origen == 'gps' else False,
            'dcasa_ubic_fecha': fields.Datetime.now(),
            'dcasa_ubic_confirmada': bool(confirmada),
            'dcasa_ubic_lugar_id': zona['lugar'].id or False,
            'dcasa_ubic_zona': zona['texto'] or False,
            'dcasa_barriada': zona['barriada'] or False,
            'dcasa_corregimiento': zona['corregimiento'] or False,
            'dcasa_distrito': zona['distrito'] or False,
            'dcasa_provincia': zona['provincia'] or False,
            'dcasa_ubic_direccion_mapa': calle or False,
        }
        if referencia is not None:
            valores['dcasa_referencia'] = geo.texto_corto(referencia, geo.MAX_REFERENCIA) or False
        if zona['distrito'] and not self.city:
            valores['city'] = zona['distrito']
        self.sudo().write(valores)
        self._dcasa_ubic_al_dia_en_ventas()
        return zona

    def _dcasa_ubic_al_dia_en_ventas(self):
        """Las ventas confirmadas que van a esta dirección quedan con su entrega armada (para el QR)."""
        ordenes = self.env['sale.order'].sudo().search([('partner_shipping_id', '=', self.id), ('state', '=', 'sale')],
                                                       limit=20, order='id desc')
        for orden in ordenes:
            orden._dcasa_entrega_motorizado()

    def _dcasa_poner_escrita(self, referencia=None):
        """La clienta prefirió escribir la dirección: sin punto (el motorizado llama antes)."""
        self.ensure_one()
        valores = {'dcasa_ubic_origen': 'escrita', 'dcasa_ubic_confirmada': False, 'dcasa_ubic_lugar_id': False,
                   'dcasa_ubic_precision_m': False, 'dcasa_ubic_fecha': fields.Datetime.now(),
                   'dcasa_ubic_direccion_mapa': False, 'dcasa_ubic_zona': False,
                   'partner_latitude': 0.0, 'partner_longitude': 0.0}
        if referencia is not None:
            valores['dcasa_referencia'] = geo.texto_corto(referencia, geo.MAX_REFERENCIA) or False
        self.sudo().write(valores)
        self._dcasa_ubic_al_dia_en_ventas()

    def action_dcasa_enlace_ubicacion(self):
        """Panel: crea el enlace de un solo uso y lo muestra para copiarlo y mandárselo a la clienta."""
        self.ensure_one()
        self.check_access('write')
        _enlace, url = self.env['dcasa.ubicacion.enlace']._crear(self.sudo(), creado_por='equipo')
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {
            'type': 'info', 'sticky': True, 'title': self.env._('Enlace para marcar la ubicación (vence en 24 horas)'),
            'message': url}}

    def _dcasa_ubic_resumen(self):
        """Lo que se muestra de la entrega (panel, Brian, la página del motorizado): sin ids internos."""
        self.ensure_one()
        partner = self.sudo()
        punto = partner._dcasa_ubic_punto()
        direccion = ', '.join(p for p in (partner.street, partner.street2, partner.city) if p)
        resumen = {
            'tiene_punto': punto is not None,
            'origen': partner.dcasa_ubic_etiqueta or '',
            'confiable': bool(punto) and geo.es_confiable(partner.dcasa_ubic_origen,
                                                          partner.dcasa_ubic_precision_m or None),
            'confirmada': bool(partner.dcasa_ubic_confirmada),
            'zona': partner.dcasa_ubic_zona or geo.zona_texto({
                'barriada': partner.dcasa_barriada, 'corregimiento': partner.dcasa_corregimiento,
                'distrito': partner.dcasa_distrito, 'provincia': partner.dcasa_provincia}),
            'direccion': direccion,
            'direccion_mapa': partner.dcasa_ubic_direccion_mapa or '',
            'referencia': partner.dcasa_referencia or '',
        }
        if punto:
            resumen['enlaces'] = geo.enlaces(*punto)
        return resumen
