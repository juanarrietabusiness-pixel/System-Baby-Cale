"""Juan y la promoción por pares (dcasa_catalogo, ``precio_par.py``): la ficha del producto le trae el precio del par
ya escrito (no calcula nada) y su cotización cobra igual que la tienda y el panel: 1 caja $20.00, 2 $35.00, 3 $55.00,
4 $70.00 y 5 $90.00, con el par y la caja suelta rotulados como en el PDF."""
from odoo import Command
from odoo.tests import tagged

from .test_cotizacion_automatica import CotizarCase

PAR = 'Promoción: 2 cajas por $35.00'
SUELTA = 'Caja suelta: precio normal'


@tagged('post_install', '-at_install')
class TestPromoParDeJuan(CotizarCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.toallitas = cls.env['product.template'].create({
            'name': 'ZZTOALLITAS DANY DE PRUEBA', 'default_code': 'ZZ-TOA', 'type': 'consu', 'is_storable': True,
            'sale_ok': True, 'is_published': True, 'list_price': 20.0, 'taxes_id': [Command.clear()],
            'public_categ_ids': [Command.set(cls.categoria.ids)]})
        cls.toallitas.product_variant_id.write({
            'dcasa_presentacion': 'Toallitas de prueba — caja de 600 toallitas', 'dcasa_precio_par': 35.0})
        almacen = cls.env['stock.warehouse'].search([], limit=1)
        cls.stock._update_available_quantity(cls.toallitas.product_variant_id, almacen.lot_stock_id, 50)

    def test_la_ficha_trae_la_promocion_ya_escrita(self):
        datos = self.salida('buscar_productos', {'consulta': 'zztoallitas'})
        (ficha,) = datos['productos']
        self.assertEqual(ficha['precio_texto'], '$20.00')
        self.assertEqual(ficha['promocion'], {
            'texto': '2 cajas por $35.00', 'precio_par': 35.0, 'precio_par_texto': '$35.00',
            'nota': 'Va por pares: una caja suelta va a su precio normal. En el carrito y en la cotización ya sale '
                    'así.'})
        completa = self.salida('ver_producto', {'codigo': self.toallitas.dcasa_codigo_publico})
        self.assertEqual(completa['promocion']['texto'], '2 cajas por $35.00')
        sin = self.salida('buscar_productos', {'consulta': 'zzsofa'})['productos'][0]
        self.assertIsNone(sin['promocion'], 'sin precio por par, sin promoción')

    def test_la_cotizacion_cobra_la_promocion_de_1_a_5_cajas(self):
        codigo = self.toallitas.dcasa_codigo_publico
        esperado = {
            1: ([(1, '$20.00', '$20.00', None)], '$20.00'),
            2: ([(2, '$17.50', '$35.00', PAR)], '$35.00'),
            3: ([(2, '$17.50', '$35.00', PAR), (1, '$20.00', '$20.00', SUELTA)], '$55.00'),
            4: ([(4, '$17.50', '$70.00', PAR)], '$70.00'),
            5: ([(4, '$17.50', '$70.00', PAR), (1, '$20.00', '$20.00', SUELTA)], '$90.00'),
        }
        for cajas, (lineas, total) in esperado.items():
            with self.subTest(cajas=cajas):
                datos = self.cotizar({'codigo': codigo, 'cantidad': cajas})
                cotizacion = datos['cotizacion']
                self.assertEqual(
                    [(x['cantidad'], x['precio_unitario_texto'], x['subtotal_texto'], x.get('promocion'))
                     for x in cotizacion['lineas']], lineas)
                self.assertEqual((cotizacion['subtotal_texto'], cotizacion['total_texto']), (total, total))
                orden = self.ordenes().filtered(lambda o, n=cotizacion['numero']: o.name == n)
                self.assertEqual(sum(orden.order_line.mapped('product_uom_qty')), cajas)

    def test_la_misma_cotizacion_pedida_otra_vez_se_reutiliza(self):
        """Con 3 cajas la cotización lleva dos líneas (2 + 1): sigue siendo la misma compra de 3 cajas."""
        codigo = self.toallitas.dcasa_codigo_publico
        primera = self.cotizar({'codigo': codigo, 'cantidad': 3})
        otra = self.cotizar({'codigo': codigo, 'cantidad': 3})
        self.assertTrue(otra['reutilizada'])
        self.assertEqual(otra['cotizacion']['numero'], primera['cotizacion']['numero'])
        self.assertEqual(len(self.ordenes()), 1)
