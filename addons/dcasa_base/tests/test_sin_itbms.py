"""Un negocio que no cobra ITBMS (Baby Caleb, decisión del dueño del 2026-11-24): ``aplicar_sin_itbms``.

En staging y producción de Baby Caleb lo corre el arranque con ``DCASA_COBRA_ITBMS=0``; sin la variable el sistema
sigue sumando el 7 % como D'CASA (y así corren las demás pruebas)."""
from odoo.addons.dcasa_base import (
    PARAMETRO_SIN_ITBMS,
    _configurar_ventas_panama,
    aplicar_sin_itbms,
    itbms_de_venta,
    sin_itbms,
)
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestSinItbms(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref('base.main_company')
        cls.venta = itbms_de_venta(cls.env, cls.company)
        cls.compra = cls.env['account.tax'].search([('company_id', '=', cls.company.id),
                                                    ('type_tax_use', '=', 'purchase')], limit=1)
        cls.producto = cls.env['product.template'].create({
            'name': 'Pañales de prueba ITBMS', 'list_price': 50.0,
            'taxes_id': [(6, 0, cls.venta.ids)], 'supplier_taxes_id': [(6, 0, cls.compra.ids)]})
        cls.cliente = cls.env['res.partner'].create({'name': 'Clienta de prueba ITBMS'})

    def test_de_fabrica_se_cobra(self):
        """Sin la variable el sistema es el de D'CASA: el 7 % se suma."""
        self.assertFalse(sin_itbms(self.env))
        self.assertTrue(self.venta, 'el ITBMS de venta de l10n_pa')
        self.assertEqual(self.company.account_sale_tax_id, self.venta)

    def test_la_empresa_y_los_productos_quedan_sin_itbms(self):
        self.assertGreaterEqual(aplicar_sin_itbms(self.env), 1)
        self.assertTrue(sin_itbms(self.env))
        self.assertEqual(self.env['ir.config_parameter'].sudo().get_param(PARAMETRO_SIN_ITBMS), '1')
        self.assertFalse(self.company.account_sale_tax_id, 'un producto nuevo nace sin impuesto')
        self.assertFalse(self.producto.taxes_id, 'el ITBMS de venta se quita')
        self.assertEqual(self.producto.supplier_taxes_id, self.compra, 'el de compra se queda')
        nuevo = self.env['product.template'].create({'name': 'Toallitas nuevas de prueba', 'list_price': 20.0})
        self.assertFalse(nuevo.taxes_id)
        # La venta: el precio de la lista es el final.
        orden = self.env['sale.order'].create({'partner_id': self.cliente.id, 'order_line': [(0, 0, {
            'product_id': self.producto.product_variant_id.id, 'product_uom_qty': 2})]})
        self.assertEqual((orden.amount_untaxed, orden.amount_tax, orden.amount_total), (100.0, 0.0, 100.0))

    def test_se_puede_repetir_y_la_configuracion_no_lo_devuelve(self):
        aplicar_sin_itbms(self.env)
        self.assertEqual(aplicar_sin_itbms(self.env), 0, 'la segunda vez no hay nada que quitar')
        _configurar_ventas_panama(self.env)
        self.assertFalse(self.company.account_sale_tax_id, 'la configuración de Panamá no vuelve a poner el ITBMS')

    def test_un_impuesto_de_venta_en_cero_se_queda(self):
        exento = self.venta.copy({'name': 'Exento de prueba', 'amount': 0.0})
        self.producto.taxes_id = [(6, 0, (self.venta | exento).ids)]
        aplicar_sin_itbms(self.env)
        self.assertEqual(self.producto.taxes_id, exento)
