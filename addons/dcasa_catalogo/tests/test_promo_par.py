"""La promoción por pares «2 cajas por $35.00» (decisión del dueño de Baby Caleb, 2026-11-24): cada par de cajas va al
precio del par y una caja suelta, a su precio normal. 1 = $20.00; 2 = $35.00; 3 = $55.00; 4 = $70.00; 5 = $90.00.

Con productos inventados (precio de lista $20.00, par $35.00, sin ITBMS, como Baby Caleb) y con el DANY-AW600 del
catálogo: el total exacto en una venta del panel, cambiar y quitar cajas en la cotización, quién cambia el precio por
par, el tope de la vendedora, la tarifa (la campaña) que no se suma, lo puesto a mano, la factura, el PDF y la ficha de
la tienda. El carrito de la web va en ``test_promo_par_carrito.py``.
"""
from odoo import Command
from odoo.addons.dcasa_catalogo.catalogo import poner_precios_par
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import Form, HttpCase, TransactionCase, new_test_user, tagged

PAR = 'Promoción: 2 cajas por $35.00'
SUELTA = 'Caja suelta: precio normal'
# cajas → (líneas como (cantidad, precio por caja), total)
ESPERADO = {
    1: ([(1.0, 20.0)], 20.0),
    2: ([(2.0, 17.5)], 35.0),
    3: ([(1.0, 20.0), (2.0, 17.5)], 55.0),
    4: ([(4.0, 17.5)], 70.0),
    5: ([(1.0, 20.0), (4.0, 17.5)], 90.0),
}


class PromoParCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ubicacion = cls.env['stock.warehouse'].search(
            [('company_id', '=', cls.env.company.id)], limit=1).lot_stock_id
        Plantilla = cls.env['product.template']
        base = {'type': 'consu', 'is_storable': True, 'sale_ok': True, 'is_published': True,
                'taxes_id': [Command.clear()]}
        cls.toallitas = Plantilla.create({**base, 'name': 'ZZTOALLITAS DE PRUEBA', 'default_code': 'ZZ-TOA',
                                          'list_price': 20.0}).product_variant_id
        cls.toallitas.write({'dcasa_presentacion': 'Toallitas de prueba — caja de 600 toallitas (6 paquetes de 100)',
                             'dcasa_precio_par': 35.0})
        cls.panal = Plantilla.create({**base, 'name': 'ZZPAÑAL DE PRUEBA', 'default_code': 'ZZ-PAN',
                                      'list_price': 50.0}).product_variant_id
        for variante in (cls.toallitas, cls.panal):
            cls.env['stock.quant'].with_context(inventory_mode=True).create({
                'product_id': variante.id, 'location_id': cls.ubicacion.id,
                'inventory_quantity': 100})._apply_inventory()
        cls.vendedora = new_test_user(cls.env, login='par_vendedora', groups='dcasa_base.group_vendedora')
        cls.gerencia = new_test_user(cls.env, login='par_gerencia', groups='dcasa_base.group_gerencia')
        cls.cliente = cls.env['res.partner'].create({
            'name': 'CLIENTA DE PRUEBA PROMO PAR', 'phone': '6000-0301', 'email': 'clienta.par@example.com'})

    def orden(self, *cantidades, usuario=None, producto=None, **valores):
        producto = producto or self.toallitas
        return self.env['sale.order'].with_user(usuario or self.vendedora).create({
            'partner_id': self.cliente.id, **valores,
            'order_line': [Command.create({'product_id': producto.id, 'product_uom_qty': c}) for c in cantidades]})

    def cajas(self, orden, producto=None):
        producto = producto or self.toallitas
        return sorted((ln.product_uom_qty, ln.price_unit) for ln in orden.order_line if ln.product_id == producto)

    def assertCajas(self, orden, cajas, mensaje=None):
        lineas, total = ESPERADO[cajas]
        self.assertEqual(self.cajas(orden), lineas, mensaje)
        self.assertEqual(sum(orden.order_line.mapped('product_uom_qty')), cajas, 'ni se pierden ni se duplican cajas')
        self.assertAlmostEqual(orden.amount_untaxed, total, places=2, msg=mensaje)
        self.assertAlmostEqual(orden.amount_total, total, places=2, msg='Baby Caleb no cobra ITBMS')


@tagged('post_install', '-at_install')
class TestPromoParEnElPanel(PromoParCommon):

    def test_de_una_a_cinco_cajas_el_total_es_exacto(self):
        for cajas in ESPERADO:
            with self.subTest(cajas=cajas):
                orden = self.orden(cajas)
                self.assertCajas(orden, cajas)
                etiquetas = sorted(ln._dcasa_etiqueta() for ln in orden.order_line)
                if cajas == 1:
                    self.assertEqual(etiquetas, [''], 'una sola caja: precio normal, sin rótulo')
                elif cajas % 2:
                    self.assertEqual(etiquetas, [SUELTA, PAR])
                else:
                    self.assertEqual(etiquetas, [PAR])

    def test_sin_precio_por_par_todo_sigue_igual(self):
        orden = self.orden(3, producto=self.panal)
        self.assertEqual(self.cajas(orden, self.panal), [(3.0, 50.0)])
        self.assertEqual(orden.order_line._dcasa_etiqueta(), '')

    def test_cambiar_y_quitar_cajas_en_la_cotizacion(self):
        orden = self.orden(1)
        linea = orden.order_line
        linea.with_user(self.vendedora).product_uom_qty = 3
        self.assertCajas(orden, 3, 'de 1 a 3: se parte en el par y la caja suelta')
        self.assertIn(linea, orden.order_line, 'la línea que tocó la vendedora no se borra')
        self.assertEqual(linea.product_uom_qty, 2.0)
        linea.with_user(self.vendedora).product_uom_qty = 1
        self.assertCajas(orden, 2, 'el par baja a 1 y se junta con la suelta: 2 cajas, $35.00')
        self.env['sale.order.line'].with_user(self.vendedora).create(
            {'order_id': orden.id, 'product_id': self.toallitas.id, 'product_uom_qty': 3})
        self.assertCajas(orden, 5, 'una línea nueva de 3 se junta: 5 cajas')
        suelta = orden.order_line.filtered(lambda ln: ln.product_uom_qty == 1)
        suelta.with_user(self.vendedora).unlink()
        self.assertCajas(orden, 4, 'quitar la caja suelta')
        orden.order_line.with_user(self.vendedora).product_uom_qty = 1
        self.assertCajas(orden, 1)
        orden.order_line.with_user(self.vendedora).unlink()
        self.assertFalse(orden.order_line)

    def test_dos_lineas_nuevas_del_mismo_producto_en_un_guardado(self):
        orden = self.orden()
        orden.with_user(self.vendedora).write({'order_line': [
            Command.create({'product_id': self.toallitas.id, 'product_uom_qty': 1}),
            Command.create({'product_id': self.toallitas.id, 'product_uom_qty': 1})]})
        self.assertCajas(orden, 2, 'dos sueltas en el mismo guardado se vuelven el par')
        orden = self.orden(1, 1, 1)
        self.assertCajas(orden, 3)

    def test_en_el_formulario_de_la_cotizacion(self):
        formulario = Form(self.env['sale.order'].with_user(self.vendedora))
        formulario.partner_id = self.cliente
        with formulario.order_line.new() as linea:
            linea.product_id = self.toallitas
            linea.product_uom_qty = 2
            self.assertEqual(linea.price_unit, 17.5, 'la pantalla ya enseña el precio del par')
        with formulario.order_line.new() as linea:
            linea.product_id = self.toallitas
            linea.product_uom_qty = 1
        orden = formulario.save()
        self.assertCajas(orden, 3)
        formulario = Form(orden.with_user(self.vendedora))
        with formulario.order_line.edit(0) as linea:
            linea.product_uom_qty = 4
        formulario.save()
        self.assertCajas(orden, 5)

    def test_otro_producto_en_la_venta_no_se_mezcla(self):
        orden = self.orden(3)
        self.env['sale.order.line'].with_user(self.vendedora).create(
            {'order_id': orden.id, 'product_id': self.panal.id, 'product_uom_qty': 2})
        self.assertEqual(self.cajas(orden), ESPERADO[3][0])
        self.assertEqual(self.cajas(orden, self.panal), [(2.0, 50.0)])
        self.assertAlmostEqual(orden.amount_untaxed, 55.0 + 100.0)

    def test_lo_puesto_a_mano_no_se_reparte(self):
        orden = self.orden(usuario=self.gerencia)
        # Como lo manda la pantalla: el precio tecleado y, aparte, el que había calculado el sistema.
        self.env['sale.order.line'].with_user(self.gerencia).create({
            'order_id': orden.id, 'product_id': self.toallitas.id, 'product_uom_qty': 3, 'price_unit': 19.0,
            'technical_price_unit': 20.0})
        self.assertEqual(self.cajas(orden), [(3.0, 19.0)], 'un precio a mano no se reparte (como en los combos)')
        self.assertEqual(orden.order_line._dcasa_etiqueta(), '')

    def test_una_venta_confirmada_no_se_parte(self):
        orden = self.orden(2, usuario=self.gerencia)
        orden.action_confirm()
        orden.order_line.with_user(self.gerencia).product_uom_qty = 3
        self.assertEqual(len(orden.order_line), 1, 'confirmada: la línea no se parte (lo decide una persona)')

    def test_el_tope_de_la_vendedora_se_mide_sobre_el_precio_de_la_promocion(self):
        orden = self.orden(3)
        par = orden.order_line.filtered(lambda ln: ln.product_uom_qty == 2)
        suelta = orden.order_line - par
        self.assertEqual(par._dcasa_precio_autorizado(), 17.5)
        self.assertEqual(suelta._dcasa_precio_autorizado(), 20.0)
        par.with_user(self.vendedora).price_unit = 15.75   # 10 % sobre 17.50: su tope
        with self.assertRaisesRegex(ValidationError, 'puedes rebajar hasta 10'):
            par.with_user(self.vendedora).price_unit = 15.7
        suelta.with_user(self.vendedora).price_unit = 18.0   # 10 % sobre 20.00
        with self.assertRaisesRegex(ValidationError, 'puedes rebajar hasta 10'):
            suelta.with_user(self.vendedora).price_unit = 17.9

    def test_la_promocion_no_se_suma_a_otra_rebaja_de_la_tarifa(self):
        self.env.ref('base.group_user').write({
            'implied_ids': [Command.link(self.env.ref('sale.group_discount_per_so_line').id)]})
        tarifa = self.env['product.pricelist'].create({'name': 'ZZ tarifa de prueba'})
        regla = self.env['product.pricelist.item'].create({
            'pricelist_id': tarifa.id, 'applied_on': '0_product_variant', 'product_id': self.toallitas.id,
            'compute_price': 'fixed', 'fixed_price': 16.0})
        orden = self.orden(3, usuario=self.gerencia, pricelist_id=tarifa.id)
        self.assertEqual(self.cajas(orden), [(1.0, 16.0), (2.0, 16.0)], 'la tarifa deja la caja más barata: va ella')
        self.assertFalse(any(orden.order_line.mapped(lambda ln: ln._dcasa_etiqueta())))
        regla.fixed_price = 19.0
        orden = self.orden(3, usuario=self.gerencia, pricelist_id=tarifa.id)
        self.assertEqual(self.cajas(orden), [(1.0, 19.0), (2.0, 17.5)], 'la promoción es mejor: va la promoción')
        regla.write({'compute_price': 'percentage', 'percent_price': 10.0})
        orden = self.orden(3, usuario=self.gerencia, pricelist_id=tarifa.id)
        par = orden.order_line.filtered(lambda ln: ln.product_uom_qty == 2)
        suelta = orden.order_line - par
        self.assertEqual((par.price_unit, par.discount), (17.5, 0.0), 'nunca las dos rebajas juntas')
        self.assertEqual((suelta.price_unit, suelta.discount), (20.0, 10.0), 'la suelta, con la de la tarifa')
        self.assertAlmostEqual(orden.amount_untaxed, 35.0 + 18.0)

    def test_la_factura_y_el_papel_dicen_la_promocion(self):
        orden = self.orden(3, usuario=self.gerencia)
        html = self.env['ir.actions.report']._render_qweb_html('sale.action_report_saleorder', orden.ids)[0].decode()
        self.assertIn(PAR, html)
        self.assertIn(SUELTA, html)
        self.assertIn('55.00', html)
        orden.action_confirm()
        factura = orden._create_invoices()
        self.assertAlmostEqual(factura.amount_total, 55.0)
        etiquetas = sorted(ln._dcasa_etiqueta() for ln in factura.invoice_line_ids)
        self.assertEqual(etiquetas, [SUELTA, PAR])
        factura.action_post()
        html = self.env['ir.actions.report']._render_qweb_html('account.account_invoices', factura.ids)[0].decode()
        self.assertIn(PAR, html)

    def test_el_aviso_del_carrito_dice_lo_que_de_verdad_subio(self):
        """El «agregaste…» del carrito: con la promoción no es el precio de la línea por la cantidad."""
        orden = self.env['sale.order'].create({
            'partner_id': self.cliente.id, 'website_id': self.env.ref('website.default_website').id})
        # 1 → 2 → 3 → 5 cajas: el carrito pasa por 20, 35, 55 y 90. Con 1 caja no hay par: el aviso de Odoo ya cuadra.
        for agregadas, importe in ((1, None), (1, 15.0), (1, 20.0), (2, 35.0)):
            with self.subTest(agregadas=agregadas):
                datos = orden._cart_add(self.toallitas.id, agregadas)
                linea = orden.order_line.filtered(lambda ln, i=datos['line_id']: ln.id == i)
                self.assertEqual(orden._dcasa_par_importe_agregado(linea, agregadas, False), importe)
        self.assertAlmostEqual(orden.amount_total, 90.0)


@tagged('post_install', '-at_install')
class TestPrecioPorPar(PromoParCommon):

    def test_solo_gerencia_cambia_el_precio_por_par(self):
        with self.assertRaises(AccessError):
            self.toallitas.with_user(self.vendedora).dcasa_precio_par = 30.0
        with self.assertRaises(AccessError):
            self.toallitas.product_tmpl_id.with_user(self.vendedora).dcasa_precio_par = 30.0
        with self.assertRaises(AccessError):
            self.env['product.product'].with_user(self.vendedora).with_context(default_dcasa_precio_par=30.0).create(
                {'name': 'ZZ PRODUCTO DE LA VENDEDORA', 'list_price': 20.0})
        self.toallitas.product_tmpl_id.with_user(self.vendedora).name = 'ZZTOALLITAS DE PRUEBA (RENOMBRADAS)'
        self.toallitas.product_tmpl_id.with_user(self.gerencia).dcasa_precio_par = 36.0
        self.assertEqual(self.toallitas.dcasa_precio_par, 36.0, 'desde la ficha del producto (una sola variante)')
        self.assertEqual(self.orden(2).order_line.price_unit, 18.0)

    def test_tiene_que_ser_una_promocion_que_se_cobre_exacta(self):
        Gerencia = self.toallitas.with_user(self.gerencia)
        for precio, aviso in ((40.0, 'menor que el de 2 sueltas'), (45.0, 'menor que el de 2 sueltas'),
                              (35.01, 'partirse en dos al centavo'), (-1.0, 'mayor que 0')):
            with self.subTest(precio=precio), self.assertRaisesRegex(ValidationError, aviso), \
                    self.env.cr.savepoint():
                Gerencia.dcasa_precio_par = precio
        Gerencia.dcasa_precio_par = 0.0
        self.assertEqual(self.cajas(self.orden(2)), [(2.0, 20.0)], 'vacío: sin promoción')

    def test_los_textos_salen_del_dato(self):
        self.assertEqual(self.toallitas._dcasa_par_texto(), '2 cajas por $35.00')
        self.assertEqual(self.toallitas._dcasa_par_nota(), 'Va por pares: una caja suelta va a su precio normal.')
        self.assertEqual(self.toallitas.product_tmpl_id._dcasa_promos_par(),
                         ['2 cajas por $35.00. Va por pares: una caja suelta va a su precio normal.'])
        self.assertEqual(self.panal.product_tmpl_id._dcasa_promos_par(), [])

    def test_el_dany_baby_del_catalogo_trae_su_promocion(self):
        dany = self.env['product.product'].search([('default_code', '=', 'DANY-AW600')])
        self.assertEqual((dany.lst_price, dany.dcasa_precio_par), (20.0, 35.0))
        self.assertEqual(poner_precios_par(self.env), {'DANY-AW600': 'ya_tenia'}, 'el que ya está no se pisa')
        for cajas, (_lineas, total) in ESPERADO.items():
            with self.subTest(cajas=cajas):
                orden = self.orden(cajas, producto=dany)
                self.assertAlmostEqual(orden.amount_untaxed, total)
        dany.dcasa_precio_par = 0.0
        self.assertEqual(poner_precios_par(self.env), {'DANY-AW600': 'cargado'}, 'vacío: entra el del catálogo')
        self.assertEqual(dany.dcasa_precio_par, 35.0)
        dany.write({'dcasa_precio_par': 0.0})
        dany.product_tmpl_id.list_price = 17.0   # dos sueltas valen 34: 35 ya no es promoción
        self.assertEqual(poner_precios_par(self.env), {'DANY-AW600': 'no_vale'}, 'no se adivina otra cifra')
        self.assertEqual(dany.dcasa_precio_par, 0.0)


@tagged('post_install', '-at_install')
class TestPromoParEnLaFicha(HttpCase):

    def test_la_ficha_dice_la_promocion_aparte_del_precio(self):
        plantilla = self.env['product.template'].create({
            'name': 'ZZTOALLITAS DE LA FICHA', 'type': 'consu', 'list_price': 20.0, 'is_published': True,
            'sale_ok': True, 'taxes_id': [Command.clear()]})
        plantilla.product_variant_id.write({'dcasa_presentacion': 'Caja de 600 toallitas', 'dcasa_precio_par': 35.0})
        self.env.flush_all()
        respuesta = self.url_open(plantilla.website_url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('<dt>Promoción</dt>', respuesta.text)
        self.assertIn('2 cajas por $35.00. Va por pares: una caja suelta va a su precio normal.', respuesta.text)
