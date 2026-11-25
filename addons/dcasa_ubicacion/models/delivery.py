"""El precio del envío en el checkout sale del punto de entrega (docs/UBICACION.md).

La entrega «a domicilio» (la que se cotizaba por WhatsApp, ``dcasa_por_cotizar``) da precio cuando la dirección de
entrega tiene un punto confirmado y el lugar de la tabla más cercano tiene precio con las reglas de siempre (tarifa
aprobada, lugar revisado, no «se cotiza aparte»). Si no, sigue como hoy: «por cotizar». La línea del envío queda como
la que pone Juan (``dcasa_envio_lugar_id``) y, si la promoción de envío de hoy aplica, con su línea.
"""
from odoo import models
from odoo.addons.dcasa_envios.motor import tarjeta as motor_tarjeta


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    def fixed_rate_shipment(self, order):
        resultado = super().fixed_rate_shipment(order)
        if resultado.get('success') and self.dcasa_por_cotizar:
            envio = order._dcasa_envio_por_ubicacion()
            if envio:
                resultado = dict(resultado, price=envio['total'])
        return resultado


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _dcasa_envio_por_ubicacion(self):
        """``{'lugar', 'total', 'total_txt'}`` si la dirección de entrega tiene un punto confirmado con precio; si no,
        ``None`` (sin punto, escrita a mano, sin lugar a 3 km, tarifa en revisión, lugar sin revisar o aparte)."""
        self.ensure_one()
        destino = (self.partner_shipping_id or self.partner_id).sudo()
        if not destino or not destino.dcasa_ubic_confirmada or not destino._dcasa_ubic_punto():
            return None
        precio = self.env['dcasa.ubicacion']._precio(destino.dcasa_ubic_lugar_id)
        return precio if precio['con_precio'] else None

    def _set_delivery_method(self, delivery_method, rate=None):
        resultado = super()._set_delivery_method(delivery_method, rate=rate)
        if delivery_method and delivery_method.dcasa_por_cotizar:
            for orden in self:
                orden._dcasa_marcar_envio_por_ubicacion()
        return resultado

    def _dcasa_marcar_envio_por_ubicacion(self):
        """La línea del envío que acaba de poner Odoo (con el precio del punto) queda como la del sistema: con su
        lugar y su nombre, y con la promoción de envío si aplica hoy. Solo en el carrito (borrador o enviada)."""
        self.ensure_one()
        if self.state not in ('draft', 'sent') or self.locked:
            return
        envio = self._dcasa_envio_por_ubicacion()
        if not envio:
            return
        orden = self.sudo()
        linea = orden.order_line.filtered(lambda ln: ln.is_delivery and not ln.dcasa_promocion_envio_id)[-1:]
        if not linea or linea.dcasa_envio_lugar_id == envio['lugar']:
            return
        lugar = envio['lugar']
        linea.write({'name': self.env._('Envío a domicilio: %s', motor_tarjeta.lugar_con_zona(lugar._como_motor())),
                     'dcasa_envio_lugar_id': lugar.id})
        resultado, terminos = orden._dcasa_promocion_calcular(linea)
        if terminos:
            orden._dcasa_promocion_crear(linea, resultado, terminos)
