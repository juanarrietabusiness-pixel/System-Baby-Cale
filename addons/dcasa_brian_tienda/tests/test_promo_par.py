"""El carrito del chat de la tienda (Andrés) con la promoción por pares (dcasa_catalogo, ``precio_par.py``): un mismo
producto puede ir en dos líneas (el par y la caja suelta), pero el chat lo enseña y lo cambia como UN producto con su
cantidad total. Sumar, cambiar y quitar cajas no pierde ni duplica ninguna, y el total sale exacto."""
from odoo import Command
from odoo.tests import tagged

from .common import RAIZ, TiendaCase


@tagged('post_install', '-at_install')
class TestCarritoDelChatConPromoPar(TiendaCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.toallitas = cls.env['product.template'].create({
            'name': 'ZZBT TOALLITAS', 'type': 'consu', 'sale_ok': True, 'is_published': True, 'list_price': 20.0,
            'taxes_id': [Command.clear()]}).product_variant_id
        cls.toallitas.write({'dcasa_presentacion': 'Caja de 600 toallitas', 'dcasa_precio_par': 35.0})

    def poner(self, ruta, cantidad):
        datos = self.post(f'carrito/{ruta}', {'producto_id': self.toallitas.id, 'cantidad': cantidad}).json()
        self.assertTrue(datos['ok'], datos)
        return datos['carrito']

    def test_una_fila_por_producto_con_el_total_exacto(self):
        casos = [('agregar', 1, 1, '$20.00'), ('agregar', 1, 2, '$35.00'), ('agregar', 1, 3, '$55.00'),
                 ('cantidad', 5, 5, '$90.00'), ('cantidad', 4, 4, '$70.00'), ('agregar', 1, 5, '$90.00'),
                 ('cantidad', 2, 2, '$35.00'), ('cantidad', 3, 3, '$55.00')]
        for ruta, cantidad, cajas, total in casos:
            with self.subTest(ruta=ruta, cantidad=cantidad):
                carrito = self.poner(ruta, cantidad)
                (fila,) = carrito['lineas']
                self.assertEqual((fila['producto_id'], fila['cantidad'], fila['subtotal_texto']),
                                 (self.toallitas.id, cajas, total))
                self.assertEqual((carrito['cantidad_total'], carrito['total_texto']), (cajas, total))
        self.env.invalidate_all()
        orden = self.env['sale.order'].search([('website_id', '=', self.website.id),
                                               ('order_line.product_id', '=', self.toallitas.id)])
        self.assertEqual(sorted(orden.order_line.mapped('product_uom_qty')), [1.0, 2.0], 'el par y la caja suelta')
        carrito = self.poner('cantidad', 0)
        self.assertEqual(carrito['lineas'], [], '0 quita las dos líneas del producto')
        self.env.invalidate_all()
        self.assertFalse(orden.order_line)
        self.assertEqual(self.url_open(f'{RAIZ}/carrito').json()['carrito']['lineas'], [])
