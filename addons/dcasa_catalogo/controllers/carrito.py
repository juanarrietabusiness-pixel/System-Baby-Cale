"""El aviso «agregaste…» del carrito con la promoción por pares (models/precio_par.py).

Odoo lo arma con el precio de la línea por las cajas agregadas. Con la promoción no cuadra: dos cajas sueltas que se
vuelven par bajan las dos, y 3 cajas van en dos líneas (2 a $17.50 + 1 a $20.00). El importe del aviso es lo que de
verdad subió el carrito por esas cajas (``sale.order._dcasa_par_importe_agregado``).
"""
from odoo.addons.website_sale.controllers.cart import Cart


class CartPromoPar(Cart):

    def _get_cart_notification_information(self, order, added_qty_per_line):
        informacion = super()._get_cart_notification_information(order, added_qty_per_line)
        con_itbms = order.website_id.show_line_subtotals_tax_selection == 'tax_included'
        for fila in informacion.get('lines') or []:
            linea = order.order_line.filtered(lambda ln, i=fila['id']: ln.id == i)
            if not linea or linea.product_id.dcasa_precio_par <= 0:
                continue
            importe = order._dcasa_par_importe_agregado(linea, fila['quantity'], con_itbms)
            if importe is not None:
                fila['price_total'] = importe
        return informacion
