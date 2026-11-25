"""La entrega de una venta para el motorizado: el QR del comprobante y de la nota de entrega abre ``/entrega/<secreto>``
con «Abrir en Waze», «Abrir en Google Maps», la dirección, la referencia y «Llamar».

A diferencia de Nébula, la página **vence** (``DIAS_VIGENCIA`` días desde que se armó o se puso al día) y **no cambia
nada** (no marca «entregado»): quien encuentre el papel no puede tocar el pedido. El secreto va en el QR, así que se
guarda en un campo que solo lee el equipo de ventas.
"""
import base64
from datetime import timedelta

from odoo import api, fields, models

from ..motor import geo

DIAS_VIGENCIA = 30
RUTA = '/entrega/'
QR_PIXELES = 240


class UbicacionEntrega(models.Model):
    _name = 'dcasa.ubicacion.entrega'
    _description = 'Entrega para el motorizado (QR)'
    _order = 'id desc'

    token = fields.Char(required=True, readonly=True, copy=False, index=True,
                        groups='sales_team.group_sale_salesman,account.group_account_invoice')
    order_id = fields.Many2one('sale.order', 'Venta', required=True, readonly=True, ondelete='cascade', index=True)
    vence = fields.Datetime(required=True, readonly=True)

    _venta_unica = models.Constraint('UNIQUE(order_id)', 'Cada venta tiene una sola entrega.')

    @api.model
    def _de_la_venta(self, orden, crear=True):
        """La entrega de esa venta. Con ``crear`` la arma si no existe y le pone la vigencia al día; sin ``crear``
        solo la busca y no escribe nada (el PDF se arma en una transacción de solo lectura: ``/report`` de Odoo 19)."""
        orden = orden.sudo()
        entrega = self.sudo().search([('order_id', '=', orden.id)], limit=1)
        if not crear:
            return entrega
        vence = fields.Datetime.now() + timedelta(days=DIAS_VIGENCIA)
        if entrega:
            if entrega.vence < vence - timedelta(days=1):
                entrega.write({'vence': vence})
            return entrega
        return self.sudo().create({'order_id': orden.id, 'token': geo.token_nuevo(18), 'vence': vence})

    @api.model
    def _del_secreto(self, token):
        """La entrega vigente de ese secreto, o un registro vacío (vencida o inexistente: lo mismo)."""
        if not isinstance(token, str) or not 16 <= len(token) <= 64:
            return self.sudo().browse()
        return self.sudo().search([('token', '=', token), ('vence', '>', fields.Datetime.now())], limit=1)

    def _url(self):
        self.ensure_one()
        base = (self.env['ir.config_parameter'].sudo().get_param('web.base.url') or '').rstrip('/')
        website = self.order_id.sudo().website_id or self.env['website'].sudo().search([], limit=1)
        if website and website.domain:
            dominio = website.domain if '://' in website.domain else 'https://' + website.domain
            base = dominio.rstrip('/')
        return f'{base}{RUTA}{self.sudo().token}'

    def _para_el_motorizado(self):
        """Lo que ve el motorizado: nombre de pila, teléfono, la dirección y el punto (con sus dos botones)."""
        self.ensure_one()
        orden = self.order_id.sudo()
        destino = orden.partner_shipping_id or orden.partner_id
        resumen = destino._dcasa_ubic_resumen()
        nombre = (destino.name or orden.partner_id.name or '').strip()
        telefono = destino.phone or orden.partner_id.phone or ''
        resumen.update({
            'pedido': orden.name,
            'nombre': nombre.split()[0] if nombre else '',
            'telefono': telefono,
            'telefono_tel': ''.join(c for c in telefono if c.isdigit() or c == '+'),
            'nota': geo.texto_corto(orden.client_order_ref or '', 120),
        })
        return resumen

    def _qr_src(self):
        """El QR (``data:image/png;base64,…``) con la dirección de la página, incrustado en el PDF."""
        self.ensure_one()
        png = self.env['ir.actions.report'].barcode('QR', self._url(), width=QR_PIXELES, height=QR_PIXELES,
                                                    quiet=0, barLevel='M')
        return 'data:image/png;base64,' + base64.b64encode(png).decode()

    @api.autovacuum
    def _gc_entregas_vencidas(self):
        """Las entregas vencidas hace más de 90 días se borran (la venta sigue; al confirmar o publicar otra vez, se
        arma otra)."""
        self.sudo().search([('vence', '<', fields.Datetime.now() - timedelta(days=90))]).unlink()


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    dcasa_zona_entrega = fields.Char('Zona de entrega', related='partner_shipping_id.dcasa_ubic_zona')

    def _dcasa_va_a_domicilio(self):
        """¿Esta venta se lleva a domicilio? (El método de entrega «a domicilio» o una línea de envío del sistema.)"""
        self.ensure_one()
        orden = self.sudo()
        if orden.carrier_id and orden.carrier_id.dcasa_por_cotizar:
            return True
        return any(linea.dcasa_envio_lugar_id for linea in orden.order_line)

    def _dcasa_entrega_motorizado(self, crear=True):
        """La entrega de esta venta para el QR, o un registro vacío si no va a domicilio o no tiene a dónde. Sin
        ``crear`` no escribe nada (para el PDF)."""
        self.ensure_one()
        if self.state == 'cancel' or not self._dcasa_va_a_domicilio():
            return self.env['dcasa.ubicacion.entrega']
        destino = (self.partner_shipping_id or self.partner_id).sudo()
        if not destino._dcasa_ubic_punto() and not (destino.street or destino.dcasa_referencia):
            return self.env['dcasa.ubicacion.entrega']
        return self.env['dcasa.ubicacion.entrega']._de_la_venta(self, crear=crear)

    def action_confirm(self):
        resultado = super().action_confirm()
        for orden in self:
            orden._dcasa_entrega_motorizado()
        return resultado

    def action_dcasa_abrir_entrega(self):
        """Panel: abre la página del motorizado (la misma del QR) en otra pestaña."""
        self.ensure_one()
        self.check_access('read')
        entrega = self._dcasa_entrega_motorizado()
        if not entrega:
            return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {
                'type': 'warning', 'title': self.env._('Sin entrega a domicilio'),
                'message': self.env._('Esta venta no va a domicilio o la clienta todavía no tiene dirección.')}}
        return {'type': 'ir.actions.act_url', 'url': entrega._url(), 'target': 'new'}


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _dcasa_entrega_para_el_qr(self):
        """La entrega (para el QR del motorizado) de la venta de este comprobante, o un registro vacío. No escribe."""
        self.ensure_one()
        if self.move_type != 'out_invoice' or self.state != 'posted':
            return self.env['dcasa.ubicacion.entrega']
        for orden in self.sudo().invoice_line_ids.sale_line_ids.order_id:
            entrega = orden._dcasa_entrega_motorizado(crear=False)
            if entrega:
                return entrega
        return self.env['dcasa.ubicacion.entrega']

    def _post(self, soft=True):
        publicados = super()._post(soft=soft)
        for factura in publicados.filtered(lambda m: m.move_type == 'out_invoice'):
            for orden in factura.sudo().invoice_line_ids.sale_line_ids.order_id:
                orden._dcasa_entrega_motorizado()
        return publicados


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _dcasa_entrega_para_el_qr(self):
        """La entrega (para el QR del motorizado) de la venta de esta salida, o un registro vacío."""
        self.ensure_one()
        if self.picking_type_code != 'outgoing' or not self.sale_id:
            return self.env['dcasa.ubicacion.entrega']
        return self.sale_id._dcasa_entrega_motorizado(crear=False)
