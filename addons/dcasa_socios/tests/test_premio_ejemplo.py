"""El premio de ejemplo «Dos almohadas» (de la empresa de la que se copió el sistema, 03/10/2026).

Desde el 2026-11-18 una instalación nueva NO lo crea (ni ningún otro premio con cifras): el catálogo arranca vacío y los
premios los pone el dueño. La función que lo creaba sigue y se prueba aquí con sus cifras de PRUEBA, llamándola a mano.
"""
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from .test_socios_web import CarritoCommon


@tagged('post_install', '-at_install')
class TestPremioEjemploAlmohadas(CarritoCommon):

    def setUp(self):
        super().setUp()
        self.recrear()

    def ejemplo(self):
        return self.env.ref('dcasa_socios.premio_ejemplo_almohadas')

    def recrear(self):
        """Corre la función como lo hacía una base nueva."""
        anterior = self.env.ref('dcasa_socios.premio_ejemplo_almohadas', raise_if_not_found=False)
        if anterior:
            anterior.unlink()
        self.env['ir.config_parameter'].sudo().set_param('dcasa_socios.ejemplo_almohadas_creado', False)
        return self.env['dcasa.premio']._crear_ejemplo_almohadas('Dos almohadas', 400, 'ALMOHADA001', 2)

    def test_se_crea_editable_y_en_el_catalogo(self):
        premio = self.ejemplo()
        self.assertEqual((premio.name, premio.puntos, premio.tipo, premio.cantidad),
                         ('Dos almohadas', 400, 'producto', 2))
        self.assertTrue(premio.active)
        self.assertIn(premio, self.env['dcasa.premio']._catalogo())
        datos = self.env['ir.model.data'].search([('module', '=', 'dcasa_socios'),
                                                  ('name', '=', 'premio_ejemplo_almohadas')])
        self.assertTrue(datos.noupdate, 'Gerencia lo edita sin que una actualización se lo pise')

    def test_ligado_al_producto_si_existe(self):
        producto = self.env['product.product'].search([('default_code', '=', 'ALMOHADA001')], limit=1) \
            or self.env['product.product'].create({
                'name': 'ALMOHADA MICRO GEL (prueba)', 'default_code': 'ALMOHADA001',
                'list_price': 3.99, 'standard_price': 1.89})
        premio = self.recrear()
        self.assertEqual(premio.product_id, producto)
        self.assertAlmostEqual(premio.valor, producto.lst_price * 2, places=2)
        self.assertAlmostEqual(premio.costo, producto.standard_price * 2, places=2)
        self.assertEqual(self.ejemplo(), premio, 'el xmlid apunta al premio nuevo')

    def test_sin_el_producto_se_crea_igual_y_no_falla(self):
        self.env['product.product'].search([('default_code', '=', 'ALMOHADA001')]).action_archive()
        premio = self.recrear()
        self.assertTrue(premio)
        self.assertFalse(premio.product_id)
        self.assertFalse(premio.descripcion, 'el socio no ve notas internas en el catálogo')
        self.assertEqual((premio.valor, premio.costo, premio.puntos, premio.cantidad), (0, 0, 400, 2))

    def test_se_crea_una_sola_vez(self):
        self.ejemplo().action_archive()
        otra = self.env['dcasa.premio']._crear_ejemplo_almohadas('Dos almohadas', 400, 'ALMOHADA001', 2)
        self.assertFalse(otra, 'si Gerencia lo archivó o borró, una actualización no lo resucita')
        self.assertEqual(self.env['dcasa.premio'].with_context(active_test=False).search_count(
            [('name', '=', 'Dos almohadas')]), 1)

    def test_el_minimo_no_frena_premios_de_producto(self):
        """Las almohadas (400) se piden aunque el mínimo de puntos.json sea mayor: los premios de
        producto los define Gerencia; el mínimo solo aplica a descuentos en dólares."""
        premio = self.ejemplo()
        self.assertEqual(premio.tipo, 'producto')
        with self.reglas_con(canje__saldoMinimoParaCanjear=premio.puntos + 100):
            canje = self.env['dcasa.canje']._pedir(self.socia, premio)
        self.assertEqual(canje.puntos, premio.puntos)
        self.assertEqual(self.socia.dcasa_saldo, 1500 - premio.puntos)

    def test_premio_de_producto_no_entra_en_el_carrito(self):
        orden = self.carrito()
        with self.assertRaisesRegex(UserError, 'no se puede usar en la tienda web'):
            orden._dcasa_usar_puntos_web(premio=self.ejemplo())


@tagged('post_install', '-at_install')
class TestCatalogoDeFabricaVacio(TransactionCase):
    """Una instalación nueva no trae premios con cifras (decisión del dueño, 2026-11-18)."""

    def test_no_trae_el_ejemplo_ni_la_escalera_de_descuentos(self):
        Premio = self.env['dcasa.premio'].sudo().with_context(active_test=False)
        self.assertFalse(Premio.search([('libre', '=', False)]), 'el catálogo arranca vacío')
        self.assertFalse(self.env['ir.config_parameter'].sudo().get_param('dcasa_socios.ejemplo_almohadas_creado'))
        for xmlid in ('premio_ejemplo_almohadas', 'premio_desc_5', 'premio_desc_10', 'premio_desc_25',
                      'premio_desc_50', 'premio_desc_100'):
            self.assertFalse(self.env.ref(f'dcasa_socios.{xmlid}', raise_if_not_found=False), xmlid)
        # Solo queda el premio técnico del canje libre, que no sale en el catálogo.
        libre = self.env.ref('dcasa_socios.premio_libre_web')
        self.assertTrue(libre.libre)
        self.assertNotIn(libre, Premio._catalogo())
