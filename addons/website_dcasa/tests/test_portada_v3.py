# ruff: noqa: E501  (JavaScript del navegador embebido en texto)
"""Portada v3 (pedido y aprobación de la dueña, 2026-11-15: las secciones «se salen una página entera», el carrito se
entiende sin la palabra, una paleta más profesional). Lo que se fija aquí:

* La tarjeta de producto: el carrito es un ícono con su nombre para lectores de pantalla («Agregar … al carrito») y
  WhatsApp va al lado; con medidas o colores para elegir, el mismo carrito lleva a la ficha.
* Los carriles traen las flechas y la línea de avance escondidas: carril.js las enciende si hay algo que deslizar.
* En Chrome, en la computadora (1440 × 900) y en un teléfono (390 px): «Lo más buscado» cabe en una pantalla con cinco
  tarjetas a la vista, las flechas mueven el carril, el carrito es redondo de 48 px (una barra ancha en el teléfono), la
  tarjeta es la de babycaleb.com (TarjetaDeArticulo.tsx: crema con filo fino y radio de 16 px, la foto entera en un
  plato cuadrado) y nada ensancha la página.
* (Las categorías «Compra por espacio» y el carril «Para dormir mejor» eran de muebles: se quitaron con la marca de Baby
  Caleb, 2026-11-19.)
"""
import contextlib

from lxml import html as lhtml

from odoo import Command
from odoo.tests import HttpCase, tagged
from odoo.tests import common as comun
from odoo.tests.common import ChromeBrowser

NOMBRES = [f'ZZPORTADA V3 MUEBLE {i}' for i in range(1, 8)]

MEDIR = """(async () => {
    const esperar = (ms) => new Promise((ok) => setTimeout(ok, ms));
    for (let i = 0; i < 200 && document.body.getAttribute('is-ready') !== 'true'; i++) { await esperar(50); }
    await esperar(800);
    const r = {};
    r.categorias = document.querySelectorAll('.o_dcasa_categorias, .o_dcasa_cat').length;
    const carril = document.querySelector('.o_dcasa_rail');
    carril.scrollIntoView();
    await esperar(400);
    r.carrilAlto = carril.getBoundingClientRect().height;
    const pista = carril.querySelector('.o_dcasa_rail_track');
    const caja = pista.getBoundingClientRect();
    const items = [...pista.querySelectorAll('.o_dcasa_rail_item')];
    r.items = items.length;
    r.filasCarril = new Set(items.map((i) => Math.round(i.getBoundingClientRect().top))).size;
    r.enteras = items.filter((i) => { const b = i.getBoundingClientRect(); return b.left >= caja.left - 1 && b.right <= caja.right + 1; }).length;
    r.anchoTarjeta = items[0].getBoundingClientRect().width;
    const flechas = carril.querySelector('.o_dcasa_carril_flechas');
    r.flechasVisibles = !flechas.hidden && getComputedStyle(flechas).display !== 'none';
    const [atras, adelante] = carril.querySelectorAll('.o_dcasa_carril_flecha');
    r.controla = !!pista.id && atras.getAttribute('aria-controls') === pista.id && adelante.getAttribute('aria-controls') === pista.id;
    r.atrasAlEmpezar = atras.disabled;
    r.adelanteAlEmpezar = adelante.disabled;
    r.avanceVisible = !carril.querySelector('.o_dcasa_carril_avance').hidden;
    if (r.flechasVisibles) {
        adelante.click();
        await esperar(900);
        r.desplazado = pista.scrollLeft;
        r.atrasDespues = atras.disabled;
    }
    const boton = carril.querySelector('.o_dcasa_pcard_add');
    const b = boton.getBoundingClientRect();
    r.carrito = { ancho: b.width, alto: b.height, texto: boton.textContent.trim(), etiqueta: boton.getAttribute('aria-label'), svg: !!boton.querySelector('svg') };
    r.paginaAncho = document.documentElement.scrollWidth;
    r.pantalla = window.innerWidth;
    r.fondo = getComputedStyle(document.querySelector('.o_dcasa_home')).backgroundColor;
    const tarjeta = carril.querySelector('.o_dcasa_pcard');
    const plato = tarjeta.querySelector('.o_dcasa_pcard_media');
    const foto = plato.querySelector('img');
    const t = getComputedStyle(tarjeta);
    r.tarjeta = { fondo: t.backgroundColor, borde: t.borderTopColor, radio: t.borderTopLeftRadius,
                  plato: getComputedStyle(plato).backgroundColor,
                  cuadrado: Math.abs(plato.getBoundingClientRect().width - plato.getBoundingClientRect().height) < 2,
                  foto: getComputedStyle(foto).objectFit,
                  carritoFondo: getComputedStyle(boton).backgroundColor, carritoColor: getComputedStyle(boton).color,
                  precio: getComputedStyle(carril.querySelector('.o_dcasa_pcard_price')).fontWeight };
    return r;
})()"""


@tagged('post_install', '-at_install')
class TestPortadaV3(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env.ref('website.default_website')
        Plantilla = cls.env['product.template']
        base = {'type': 'consu', 'is_storable': False, 'sale_ok': True, 'is_published': True, 'list_price': 149.99}
        # Siete muebles y un sofá con colores salen primero en «Lo más buscado» (son los 8 del carril): el carril tiene
        # más de lo que cabe a la vista y la primera tarjeta se agrega de un clic.
        cls.muebles = Plantilla.browse()
        for i, nombre in enumerate(NOMBRES):
            cls.muebles |= Plantilla.create({**base, 'name': nombre, 'website_sequence': -5000 + i})
        color = cls.env['product.attribute'].create({
            'name': 'Zzcolor portada v3', 'create_variant': 'always',
            'value_ids': [Command.create({'name': 'Zzgris'}), Command.create({'name': 'Zzbeige'})]})
        cls.con_colores = Plantilla.create({
            **base, 'name': 'ZZPORTADA V3 SOFÁ CON COLORES', 'website_sequence': -4990,
            'attribute_line_ids': [Command.create({'attribute_id': color.id, 'value_ids': [Command.set(color.value_ids.ids)]})]})
        # Con algo publicado en Recámaras, la portada igual NO trae «Para dormir mejor» (era de muebles).
        Plantilla.create({**base, 'name': 'ZZPORTADA V3 CAMA', 'website_sequence': -4980,
                          'public_categ_ids': [Command.set(cls.env.ref('website_dcasa.public_category_recamaras').ids)]})

    def _portada(self):
        return lhtml.fromstring(self.url_open('/').text)

    def _tarjeta(self, arbol, producto):
        tarjetas = arbol.xpath(f'//article[contains(@class, "o_dcasa_pcard")][.//h3/a[@href="{producto.website_url}"]]')
        self.assertTrue(tarjetas, f'la portada no trae la tarjeta de {producto.name}')
        return tarjetas[0]

    # ------------------------------------------------------------------ en el HTML

    def test_las_categorias_cuentan_lo_publicado_y_se_ponen_al_dia_solas(self):
        """Cada categoría dice cuántos productos hay publicados: un dato real del catálogo (lo usa la búsqueda sin
        resultados; la portada ya no enseña categorías)."""
        def cantidad(clave):
            return next(t for t in self.website._dcasa_categorias() if t['clave'] == clave)['cantidad']

        antes = cantidad('oficina')
        oficina = self.env.ref('website_dcasa.public_category_oficina')
        self.env['product.template'].create({
            'name': 'ZZPORTADA V3 ESCRITORIO', 'is_published': True, 'sale_ok': True, 'list_price': 99.0,
            'public_categ_ids': [(6, 0, oficina.ids)]})
        self.env['product.template'].create({
            'name': 'ZZPORTADA V3 ESCRITORIO SIN PUBLICAR', 'is_published': False, 'sale_ok': True, 'list_price': 99.0,
            'public_categ_ids': [(6, 0, oficina.ids)]})
        self.assertEqual(cantidad('oficina'), antes + 1, 'cuenta lo publicado, y solo lo publicado')
        self.assertFalse(self._portada().xpath('//span[@class="o_dcasa_cat_nota"]'), 'la portada no las enseña')

    def test_la_tarjeta_lleva_el_carrito_como_icono_con_su_nombre(self):
        arbol = self._portada()
        mueble = self.muebles[0]
        tarjeta = self._tarjeta(arbol, mueble)
        nombre = mueble._dcasa_nombre_cliente()
        boton = tarjeta.xpath('.//form[@action="/dcasa/carrito/agregar"]//button[contains(@class, "o_dcasa_pcard_add")]')
        self.assertTrue(boton, 'la tarjeta trae el formulario de un clic')
        boton = boton[0]
        self.assertEqual(boton.text_content().strip(), '', 'solo el ícono: sin la palabra «Agregar»')
        self.assertTrue(boton.xpath('.//svg'), 'el ícono del carrito')
        self.assertEqual(boton.get('aria-label'), f'Agregar {nombre} al carrito', 'los lectores de pantalla oyen qué hace')
        self.assertEqual(boton.get('title'), 'Agregar al carrito', 'y con el mouse, la ayuda')
        whatsapp = tarjeta.xpath('.//a[contains(@class, "o_dcasa_pcard_wa")]')[0]
        self.assertTrue(whatsapp.get('aria-label').startswith(f'Preguntar por {nombre} por WhatsApp'))
        # Ni «Agregar» ni «Elegir» como texto en la tarjeta (el nombre y el precio sí).
        texto = ' '.join(tarjeta.text_content().split())
        self.assertNotIn('Agregar', texto)
        self.assertNotIn('Elegir', texto)
        self.assertIn('149.99', texto)

    def test_con_colores_para_elegir_el_carrito_lleva_a_la_ficha(self):
        tarjeta = self._tarjeta(self._portada(), self.con_colores)
        self.assertFalse(tarjeta.xpath('.//form'), 'con colores no se agrega de un clic')
        enlace = tarjeta.xpath('.//a[contains(@class, "o_dcasa_pcard_add")]')[0]
        self.assertEqual(enlace.get('href'), self.con_colores.website_url)
        self.assertEqual(enlace.get('aria-label'), f'Elegir medida o color de {self.con_colores._dcasa_nombre_cliente()}')
        self.assertEqual(enlace.text_content().strip(), '')
        self.assertTrue(enlace.xpath('.//svg'))

    def test_los_carriles_traen_flechas_y_avance_escondidos_hasta_medir(self):
        carriles = self._portada().xpath('//section[contains(@class, "o_dcasa_rail")]')
        self.assertEqual(len(carriles), 1, 'solo «Lo más buscado»: «Para dormir mejor» era de muebles')
        flechas = carriles[0].xpath('.//div[contains(@class, "o_dcasa_carril_flechas")]')[0]
        self.assertIsNotNone(flechas.get('hidden'), 'sin JavaScript las flechas no se ven')
        atras, adelante = flechas.xpath('.//button[contains(@class, "o_dcasa_carril_flecha")]')
        self.assertEqual(atras.get('aria-label'), 'Anteriores de Lo más buscado')
        self.assertEqual(adelante.get('aria-label'), 'Más de Lo más buscado')
        self.assertIsNotNone(atras.get('disabled'), 'al empezar no hay nada atrás')
        self.assertIsNotNone(carriles[0].xpath('.//div[contains(@class, "o_dcasa_carril_avance")]')[0].get('hidden'))

    # ------------------------------------------------------------------ en Chrome

    @contextlib.contextmanager
    def _chrome(self, ancho, alto, movil):
        if comun.websocket is None:
            self.skipTest('websocket-client module is not installed')
        self.browser_size = f'{ancho}x{alto}'
        browser = ChromeBrowser(self, headless=True)
        with self.allow_requests(browser=browser), contextlib.ExitStack() as atexit:
            atexit.callback(self._wait_remaining_requests)
            atexit.enter_context(browser.cleanup)
            self.authenticate(None, None, browser=browser)
            self.cr.flush()
            self.cr.clear()
            browser._websocket_request('Emulation.setDeviceMetricsOverride', params={
                'width': ancho, 'height': alto, 'deviceScaleFactor': 2 if movil else 1, 'mobile': movil})
            if movil:
                browser._websocket_request('Emulation.setTouchEmulationEnabled', params={'enabled': True})
            # Sin animaciones de entrada: las posiciones se miden quietas.
            browser._websocket_request('Emulation.setEmulatedMedia', params={
                'features': [{'name': 'prefers-reduced-motion', 'value': 'reduce'}]})
            yield browser

    def _medir(self, ancho, alto, movil):
        with self._chrome(ancho, alto, movil) as browser:
            browser.navigate_to(self.base_url() + '/', wait_stop=True)
            res = browser._websocket_request('Runtime.evaluate', params={
                'expression': MEDIR, 'awaitPromise': True, 'returnByValue': True}, timeout=120)
        self.assertFalse(res.get('exceptionDetails'), f'JavaScript falló: {res}')
        return res['result']['value']

    def test_en_la_computadora_todo_cabe_y_el_carril_se_mueve(self):
        r = self._medir(1440, 900, movil=False)
        self.assertEqual(r['categorias'], 0, 'sin «Compra por espacio»')
        self.assertLess(r['carrilAlto'], 900, '«Lo más buscado» cabe en una pantalla')
        self.assertEqual(r['filasCarril'], 1, 'una sola fila')
        self.assertEqual(r['enteras'], 5, 'cinco tarjetas enteras a la vista')
        self.assertGreater(r['items'], 5)
        self.assertTrue(r['flechasVisibles'], 'hay más de lo que se ve: salen las flechas')
        self.assertTrue(r['controla'], 'cada flecha dice qué carril mueve')
        self.assertTrue(r['atrasAlEmpezar'])
        self.assertFalse(r['adelanteAlEmpezar'])
        self.assertTrue(r['avanceVisible'])
        self.assertGreater(r['desplazado'], 0, 'la flecha mueve el carril')
        self.assertFalse(r['atrasDespues'], 'después de avanzar se puede volver')
        self.assertAlmostEqual(r['carrito']['ancho'], 48, delta=1, msg='redondo de 48 px: el mínimo de los botones')
        self.assertAlmostEqual(r['carrito']['alto'], 48, delta=1, msg='redondo, no ovalado')
        self.assertEqual(r['carrito']['texto'], '')
        self.assertTrue(r['carrito']['svg'])
        self.assertTrue(r['carrito']['etiqueta'].startswith('Agregar '))
        self.assertLessEqual(r['paginaAncho'], r['pantalla'], 'nada ensancha la página')
        self.assertEqual(r['fondo'], 'rgb(249, 246, 237)', 'el crema de Baby Caleb')
        self._revisar_tarjeta(r)

    def test_en_el_telefono_dos_tarjetas_y_media(self):
        r = self._medir(390, 844, movil=True)
        self.assertEqual(r['categorias'], 0, 'sin «Compra por espacio»')
        self.assertEqual(r['filasCarril'], 1)
        self.assertEqual(r['enteras'], 2, 'dos tarjetas enteras y asoma la tercera')
        self.assertGreater(r['anchoTarjeta'], 140)
        self.assertLess(r['anchoTarjeta'], 180)
        self.assertFalse(r['flechasVisibles'], 'en el teléfono se desliza con el dedo')
        # Una barra (más ancha que alta) junto a WhatsApp, con el relleno de 12 px de la tarjeta de su web (p-3).
        self.assertGreater(r['carrito']['ancho'], r['carrito']['alto'] * 1.4,
                           'en la tarjeta angosta el carrito es una barra ancha')
        self.assertAlmostEqual(r['carrito']['alto'], 48, delta=1)
        self.assertEqual(r['carrito']['texto'], '')
        self.assertLessEqual(r['paginaAncho'], r['pantalla'], 'nada ensancha la página')
        self._revisar_tarjeta(r)

    def _revisar_tarjeta(self, r):
        """TarjetaDeArticulo.tsx: `surface` con el filo `line`, radio de 16 px, la foto entera en un plato cuadrado
        crema, el precio en 700 y el carrito naranja con el ícono navy."""
        self.assertEqual(r['tarjeta'], {
            'fondo': 'rgb(242, 239, 229)', 'borde': 'rgba(27, 50, 70, 0.12)', 'radio': '16px',
            'plato': 'rgb(249, 246, 237)', 'cuadrado': True, 'foto': 'contain',
            'carritoFondo': 'rgb(238, 146, 74)', 'carritoColor': 'rgb(27, 50, 70)', 'precio': '700'})
