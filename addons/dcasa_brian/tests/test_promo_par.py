"""Brian y la promoción por pares (dcasa_catalogo, ``precio_par.py``): la ficha del producto la dice y Gerencia la pone
o la quita con ``poner_precio_por_par`` (también por MCP); la vendedora no. Una cotización que arma Brian cobra igual
que el panel y la tienda."""
from odoo import Command
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestBrianPromoPar(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.toallitas = cls.env['product.product'].create({
            'name': 'BRIANZETA TOALLITAS', 'default_code': 'BRZ-TOA', 'type': 'consu', 'list_price': 20.0,
            'taxes_id': [Command.clear()], 'dcasa_presentacion': 'Caja de 600 toallitas'})
        cls.vendedora = new_test_user(cls.env, login='brian_par_vendedora', groups='dcasa_base.group_vendedora')
        cls.gerencia = new_test_user(cls.env, login='brian_par_gerencia', groups='dcasa_base.group_gerencia')
        cls.cliente = cls.env['res.partner'].create({'name': 'BRIANZETA CLIENTA PAR', 'phone': '6123-4511'})

    def ejecutar(self, usuario, nombre, argumentos):
        return self.env['brian.herramientas'].with_user(usuario).ejecutar(nombre, argumentos)

    def test_gerencia_pone_y_quita_la_promocion(self):
        respuesta = self.ejecutar(self.vendedora, 'poner_precio_por_par', {'producto': 'BRZ-TOA', 'precio': 35})
        self.assertFalse(respuesta['ok'], 'la vendedora no la pone')
        self.assertEqual(self.toallitas.dcasa_precio_par, 0.0)
        respuesta = self.ejecutar(self.gerencia, 'poner_precio_por_par', {'producto': 'BRZ-TOA', 'precio': 40})
        self.assertFalse(respuesta['ok'])
        self.assertIn('menor que el de 2 sueltas', respuesta['error'])
        respuesta = self.ejecutar(self.gerencia, 'poner_precio_por_par', {'producto': 'BRZ-TOA', 'precio': 35})
        self.assertTrue(respuesta['ok'], respuesta)
        self.assertEqual(self.toallitas.dcasa_precio_par, 35.0)
        self.assertEqual(respuesta['datos']['promocion'], {
            'precio_por_par': '$35.00',
            'texto': '2 cajas por $35.00. Va por pares: una caja suelta va a su precio normal.'})
        ficha = self.ejecutar(self.vendedora, 'ver_producto', {'producto': 'BRZ-TOA'})['datos']
        self.assertEqual(ficha['promocion']['precio_por_par'], '$35.00')
        respuesta = self.ejecutar(self.gerencia, 'poner_precio_por_par', {'producto': 'BRZ-TOA', 'precio': 0})
        self.assertTrue(respuesta['ok'], respuesta)
        self.assertEqual(self.toallitas.dcasa_precio_par, 0.0)
        self.assertNotIn('promocion', self.ejecutar(self.vendedora, 'ver_producto', {'producto': 'BRZ-TOA'})['datos'])

    def test_la_cotizacion_de_brian_cobra_la_promocion(self):
        self.toallitas.dcasa_precio_par = 35.0
        orden = self.env['sale.order'].with_user(self.vendedora).create({'partner_id': self.cliente.id})
        for _vez in range(3):
            orden.with_user(self.vendedora)._dcasa_agregar_producto(self.toallitas, 1)
        self.assertEqual(sorted((ln.product_uom_qty, ln.price_unit) for ln in orden.order_line),
                         [(1.0, 20.0), (2.0, 17.5)])
        self.assertAlmostEqual(orden.amount_total, 55.0)
