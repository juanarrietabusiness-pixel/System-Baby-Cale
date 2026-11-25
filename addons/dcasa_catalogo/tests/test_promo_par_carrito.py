"""La promoción por pares en el carrito de la tienda en línea, como lo usa una clienta: las rutas de verdad
(``/shop/cart/add`` y ``/shop/cart/update``) y la página ``/shop/cart`` en un navegador, con sus botones «+», «−»,
«Quitar» y la cantidad escrita. Las cajas de un mismo producto pueden ir en dos líneas (el par y la caja suelta): el
total tiene que salir exacto y ninguna caja se pierde ni se duplica al sumar, restar o quitar."""
from odoo import Command
from odoo.tests import HttpCase, tagged

CORREO = 'clienta.promo.par@example.com'
CLAVE = CORREO   # browser_js entra con la clave igual al usuario
PAR = 'Promoción: 2 cajas por $35.00'
SUELTA = 'Caja suelta: precio normal'

EN_EL_CARRITO = """
(async () => {
    const PRODUCTO = %(producto)s;
    const esperar = async (fn, que, ms = 20000) => {
        const inicio = Date.now();
        while (Date.now() - inicio < ms) {
            const r = fn();
            if (r) { return r; }
            await new Promise((ok) => setTimeout(ok, 100));
        }
        throw new Error("Carrito por pares: no se llegó a " + que);
    };
    const falla = (texto) => { throw new Error("Carrito por pares: " + texto); };
    const visible = (el) => el && el.offsetParent !== null;
    const filas = () => [...document.querySelectorAll(`.o_cart_product[data-product-id="${PRODUCTO}"]`)];
    const cantidad = (fila) => parseInt([...fila.querySelectorAll("input.js_quantity")].find(visible).value);
    const cantidades = () => filas().map(cantidad).sort((a, b) => a - b).join(",");
    const total = () => (document.querySelector("tr[name=o_order_total]")?.textContent || "").replace(/\\s/g, "");
    const llegar = (quiero, monto, paso) => esperar(
        () => cantidades() === quiero && total().endsWith(monto),
        `${paso}: líneas ${quiero} y total ${monto} (hay ${cantidades()} y ${total()})`);
    const boton = (fila, icono) => [...fila.querySelectorAll(".css_quantity > a")]
        .find((a) => visible(a) && a.querySelector("i")?.classList.contains(icono));
    const conCantidad = (n) => filas().find((fila) => cantidad(fila) === n);

    // Las interacciones del carrito tardan en arrancar después de cargar la página.
    await esperar(() => odoo.loader.modules.get("@website_sale/interactions/cart_line"), "el JS del carrito");
    await new Promise((ok) => setTimeout(ok, 1500));

    // 3 cajas: el par a $17.50 y la caja suelta a $20.00, con su rótulo.
    await llegar("1,2", "55.00", "al abrir");
    const texto = document.querySelector("#cart_products").textContent;
    if (!texto.includes("%(par)s") || !texto.includes("%(suelta)s")) { falla("faltan los rótulos: " + texto); }

    boton(conCantidad(1), "oi-plus").click();               // + en la caja suelta: 4 cajas, una sola línea
    await llegar("4", "70.00", "«+» en la caja suelta");
    boton(conCantidad(4), "oi-minus").click();              // − : 3 cajas, otra vez el par y la suelta
    await llegar("1,2", "55.00", "«−» con 4");
    boton(conCantidad(2), "oi-plus").click();               // + en el par: 4 cajas
    await llegar("4", "70.00", "«+» en el par");
    boton(conCantidad(4), "oi-plus").click();               // 5 cajas
    await llegar("1,4", "90.00", "«+» con 4");
    [...conCantidad(1).querySelectorAll(".js_delete_product")].find(visible).click();   // quitar la caja suelta
    await llegar("4", "70.00", "quitar la caja suelta");
    boton(conCantidad(4), "oi-minus").click();
    await llegar("1,2", "55.00", "«−» con 4 (otra vez)");
    boton(conCantidad(2), "oi-minus").click();              // − en el par: quedan 2 cajas en una línea
    await llegar("2", "35.00", "«−» en el par");
    boton(conCantidad(2), "oi-minus").click();
    await llegar("1", "20.00", "«−» con 2");
    const campo = [...filas()[0].querySelectorAll("input.js_quantity")].find(visible);
    campo.value = "5";                                      // escribir la cantidad
    campo.dispatchEvent(new Event("change", { bubbles: true }));
    await llegar("1,4", "90.00", "escribir 5");
    if (document.documentElement.scrollWidth > window.innerWidth + 1) { falla("scroll de lado en el carrito"); }
    console.log("test successful");
})().catch((e) => console.error(e.message || e));
"""


@tagged('post_install', '-at_install')
class TestPromoParEnElCarrito(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env.ref('website.default_website')
        cls.toallitas = cls.env['product.template'].create({
            'name': 'ZZTOALLITAS DEL CARRITO', 'type': 'consu', 'is_storable': True, 'sale_ok': True,
            'is_published': True, 'list_price': 20.0, 'taxes_id': [Command.clear()],
        }).product_variant_id
        cls.toallitas.write({'dcasa_presentacion': 'Caja de 600 toallitas', 'dcasa_precio_par': 35.0})
        ubicacion = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.company.id)], limit=1).lot_stock_id
        cls.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': cls.toallitas.id, 'location_id': ubicacion.id, 'inventory_quantity': 50})._apply_inventory()
        cls.usuario = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Clienta Prueba Promo Par', 'login': CORREO, 'email': CORREO, 'password': CLAVE,
            'group_ids': [Command.set([cls.env.ref('base.group_portal').id])]})
        cls.cliente = cls.usuario.partner_id
        cls.cliente.write({'phone': '+507 6000-0302', 'street': 'Calle de prueba 3', 'city': 'Panamá',
                           'country_id': cls.env.ref('base.pa').id})

    def carrito(self):
        return self.env['sale.order'].search(
            [('partner_id', '=', self.cliente.id), ('website_id', '=', self.website.id), ('state', '=', 'draft')],
            order='id desc', limit=1)

    def agregar(self, cajas):
        return self.make_jsonrpc_request('/shop/cart/add', {
            'product_template_id': self.toallitas.product_tmpl_id.id, 'product_id': self.toallitas.id,
            'quantity': cajas})

    def cambiar(self, linea, cajas):
        return self.make_jsonrpc_request('/shop/cart/update', {'line_id': linea.id, 'quantity': cajas})

    def estado(self):
        orden = self.carrito()
        orden.invalidate_recordset()
        orden.order_line.invalidate_recordset()
        return sorted((ln.product_uom_qty, ln.price_unit) for ln in orden.order_line), orden.amount_total

    def test_agregar_de_una_a_cinco_cajas_desde_la_ficha(self):
        self.authenticate(CORREO, CLAVE)
        esperado = {1: ([(1.0, 20.0)], 20.0), 2: ([(2.0, 17.5)], 35.0), 3: ([(1.0, 20.0), (2.0, 17.5)], 55.0),
                    4: ([(4.0, 17.5)], 70.0), 5: ([(1.0, 20.0), (4.0, 17.5)], 90.0)}
        for cajas, (lineas, total) in esperado.items():
            with self.subTest(cajas=cajas):
                respuesta = self.agregar(cajas)
                self.assertEqual(respuesta['cart_quantity'], cajas)
                self.assertEqual(self.estado(), (lineas, total))
                aviso, = respuesta['notification_info']['lines']
                self.assertAlmostEqual(aviso['price_total'], total, msg='el aviso dice lo que de verdad cuesta')
                self.make_jsonrpc_request('/shop/cart/clear', {})

    def test_sumar_restar_y_quitar_cajas_sin_perder_ni_duplicar(self):
        self.authenticate(CORREO, CLAVE)
        for cajas, importe in ((1, 20.0), (1, 15.0), (1, 20.0)):
            aviso, = self.agregar(cajas)['notification_info']['lines']
            self.assertAlmostEqual(aviso['price_total'], importe)
        self.assertEqual(self.estado(), ([(1.0, 20.0), (2.0, 17.5)], 55.0))
        orden = self.carrito()
        suelta = orden.order_line.filtered(lambda ln: ln.product_uom_qty == 1)
        respuesta = self.cambiar(suelta, 2)                   # «+» en la caja suelta
        self.assertEqual(self.estado(), ([(4.0, 17.5)], 70.0))
        self.assertEqual((respuesta['cart_quantity'], respuesta['amount']), (4, 70.0))
        self.assertEqual(respuesta['minor_amount'], 7000, 'lo que se manda a cobrar')
        self.assertNotIn(SUELTA, respuesta['website_sale.cart_lines'])
        self.assertIn(PAR, respuesta['website_sale.cart_lines'])
        par = self.carrito().order_line
        respuesta = self.cambiar(par, 3)                      # «−»
        self.assertEqual(self.estado(), ([(1.0, 20.0), (2.0, 17.5)], 55.0))
        self.assertIn(PAR, respuesta['website_sale.cart_lines'])
        self.assertIn(SUELTA, respuesta['website_sale.cart_lines'])
        self.assertIn('55.00', respuesta['website_sale.total'])
        par = self.carrito().order_line.filtered(lambda ln: ln.product_uom_qty == 2)
        self.cambiar(par, 1)                                  # «−» en el par: 2 cajas, el par otra vez
        self.assertEqual(self.estado(), ([(2.0, 17.5)], 35.0))
        self.cambiar(self.carrito().order_line, 5)            # escribir 5
        self.assertEqual(self.estado(), ([(1.0, 20.0), (4.0, 17.5)], 90.0))
        suelta = self.carrito().order_line.filtered(lambda ln: ln.product_uom_qty == 1)
        self.cambiar(suelta, 0)                               # «Quitar» la caja suelta
        self.assertEqual(self.estado(), ([(4.0, 17.5)], 70.0))
        respuesta = self.cambiar(self.carrito().order_line, 0)   # «Quitar» todo
        self.assertEqual(respuesta['cart_quantity'], 0)
        self.assertFalse(self.carrito().order_line)

    def test_al_pagar_el_total_sigue_exacto(self):
        """Lo que corre antes de cobrar (la campaña al día y «Actualizar precios») no cambia el total."""
        self.authenticate(CORREO, CLAVE)
        self.agregar(3)
        orden = self.carrito()
        orden._dcasa_campana_al_dia_si_hay()
        orden._recompute_prices()
        self.assertEqual(self.estado(), ([(1.0, 20.0), (2.0, 17.5)], 55.0))
        respuesta = self.url_open('/shop/cart')
        self.assertIn(PAR, respuesta.text)
        self.assertIn(SUELTA, respuesta.text)

    def test_en_la_pagina_del_carrito_con_los_botones(self):
        for tamano in ('1440x900', '390x844'):
            with self.subTest(tamano=tamano):
                orden = self.carrito() or self.env['sale.order'].create({
                    'partner_id': self.cliente.id, 'website_id': self.website.id})
                orden.order_line.unlink()
                orden._cart_add(self.toallitas.id, 3)
                self.assertEqual(self.estado(), ([(1.0, 20.0), (2.0, 17.5)], 55.0))
                self.browser_size = tamano
                self.browser_js('/shop/cart', EN_EL_CARRITO % {
                    'producto': self.toallitas.id, 'par': PAR, 'suelta': SUELTA}, login=CORREO, timeout=180)
                self.assertEqual(self.estado(), ([(1.0, 20.0), (4.0, 17.5)], 90.0))
