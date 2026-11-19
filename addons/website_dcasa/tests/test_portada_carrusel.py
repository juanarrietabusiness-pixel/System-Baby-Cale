# ruff: noqa: E501  (JavaScript del navegador embebido en texto)
"""Portada: el hero con los productos que elige Gerencia (models/portada.py, views/homepage_templates.xml,
static/src/js/portada.js), con la marca de Baby Caleb (docs/MARCA_BABY_CALEB.md, 2026-11-19). Lo que se fija aquí:

* El ajuste: «Sitio web › Carrusel de la portada», una lista que se ordena arrastrando; solo Gerencia y los
  administradores la ven y la cambian.
* Vacío = el hero de siempre, con la foto del bebé (también si nada de la lista se puede mostrar: sin publicar o sin
  foto). Con productos: el mismo hero crema, y en el marco redondeado de la derecha sus fotos se funden unas en otras,
  en orden al azar, con un zoom lento que no para. Ni nombres de producto, ni enlaces, ni flechas, ni barras, ni
  pausa: el visitante no maneja nada, así que las fotos son decorativas (aria-hidden, alt vacío). La primera es la
  imagen LCP (precargada, «eager», prioridad alta).
* Sin velo ni degradado sobre las fotos: el texto va sobre el crema, al lado (encima en el celular).
* El carrusel nace UNA vez con los productos aprobados (por su código público); lo que no existe se salta.
* Con el editor del sitio abierto (quien tiene el grupo de diseñador recibe las plantillas con sus marcas) la portada
  abre, y un hero guardado con el editor sigue dentro de su condición.
* La sección «de cine» (dos cintas de fotos de las categorías de muebles) ya no sale: se quitó con la marca.
* En Chrome: la foto llena su marco, el zoom corre, la foto cambia sola (y quieta con movimiento reducido), no hay
  NADA que tocar y nada ensancha la página.
"""
import base64
import contextlib
import io

from lxml import html as lhtml
from PIL import Image
from psycopg2 import IntegrityError

from odoo import Command
from odoo.addons.website_dcasa.models import portada as modulo_portada
from odoo.addons.website_dcasa.models.portada import CARRUSEL_INICIAL, PARAM_SEMBRADO
from odoo.exceptions import AccessError
from odoo.tests import HttpCase, tagged
from odoo.tests import common as comun
from odoo.tests.common import ChromeBrowser
from odoo.tools import mute_logger


def _foto(color, ancho=600, alto=800):
    salida = io.BytesIO()
    Image.new('RGB', (ancho, alto), color).save(salida, 'JPEG')
    return base64.b64encode(salida.getvalue())


def _usuario(env, login, *grupos):
    return env['res.users'].with_context(no_reset_password=True).create({
        'name': login.replace('_', ' ').title(), 'login': login, 'password': login,
        'group_ids': [Command.set([env.ref('base.group_user').id, *(env.ref(g).id for g in grupos)])],
    })


def _clases(nodo):
    return set((nodo.get('class') or '').split())


def _id_del_src(src):
    """El id del producto dentro de la URL de su foto (/web/image/product.template/<id>/image_1024/...)."""
    return int(src.split('/image_')[0].rsplit('/', 1)[-1])


@tagged('post_install', '-at_install')
class TestCarruselPortada(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env.ref('website.default_website')
        cls.Diapositiva = cls.env['dcasa.portada.diapositiva']
        cls.Diapositiva.search([]).unlink()
        base = {'type': 'consu', 'is_storable': False, 'sale_ok': True, 'is_published': True, 'list_price': 45.0}
        Plantilla = cls.env['product.template']
        cls.camas = Plantilla.browse()   # (el nombre viene de la copia de origen: aquí son cajas de pañales)
        for nombre, color in (('CAJA NATEEN TALLA M', (20, 20, 20)),
                              ('CAJA NATEEN TALLA L', (230, 150, 170)),
                              ('CAJA WIPES DE AGUA', (220, 205, 180))):
            cls.camas |= Plantilla.create({**base, 'name': f'ZZCARRUSEL {nombre}', 'image_1920': _foto(color)})
        cls.sin_publicar = Plantilla.create({**base, 'name': 'ZZCARRUSEL CAJA SIN PUBLICAR', 'is_published': False,
                                             'image_1920': _foto((90, 90, 90))})
        cls.sin_foto = Plantilla.create({**base, 'name': 'ZZCARRUSEL CAJA SIN FOTO'})
        cls.gerente = _usuario(cls.env, 'gerente_carrusel', 'dcasa_base.group_gerencia')
        cls.vendedora = _usuario(cls.env, 'vendedora_carrusel', 'dcasa_base.group_vendedora')
        cls.interno = _usuario(cls.env, 'interno_carrusel')

    def _elegir(self, *productos):
        self.Diapositiva.search([]).unlink()
        for orden, producto in enumerate(productos, start=1):
            self.Diapositiva.create({'website_id': self.website.id, 'product_tmpl_id': producto.id, 'sequence': orden})

    def _portada(self, ruta='/'):
        respuesta = self.url_open(ruta)
        self.assertEqual(respuesta.status_code, 200, respuesta.text[:2000])
        return respuesta.text, lhtml.fromstring(respuesta.text)

    def _vitrina(self, arbol):
        secciones = arbol.xpath('//section[contains(@class, "o_dcasa_hero_vitrina")]')
        return secciones[0] if secciones else None

    # ------------------------------------------------------------------ el ajuste

    def test_solo_gerencia_y_administradores_eligen_el_carrusel(self):
        Diapositiva = self.Diapositiva.with_user(self.gerente)
        diapositiva = Diapositiva.create({'product_tmpl_id': self.camas[0].id})
        self.assertEqual(diapositiva.website_id, self.website, 'por defecto, el sitio de siempre')
        diapositiva.sequence = 5
        diapositiva.product_tmpl_id = self.camas[1]
        self.assertTrue(diapositiva.en_portada)
        diapositiva.unlink()
        admin = self.env.ref('base.user_admin')
        self.Diapositiva.with_user(admin).create({'product_tmpl_id': self.camas[0].id}).unlink()
        for usuario in (self.vendedora, self.interno):
            with self.subTest(usuario=usuario.login):
                with self.assertRaises(AccessError):
                    self.Diapositiva.with_user(usuario).create({'product_tmpl_id': self.camas[0].id})
                with self.assertRaises(AccessError):
                    self.Diapositiva.with_user(usuario).search([])
        menu = 'website_dcasa.menu_dcasa_portada_diapositiva'
        def menus(usuario):
            datos = self.env['ir.ui.menu'].with_user(usuario).load_menus(False)
            return {m['xmlid'] for m in datos.values() if isinstance(m, dict) and m.get('xmlid')}
        self.assertIn(menu, menus(self.gerente), 'Gerencia lo encuentra en Sitio web')
        self.assertNotIn(menu, menus(self.vendedora))

    @mute_logger('odoo.sql_db')
    def test_un_producto_va_una_sola_vez_y_la_lista_dice_cual_no_sale(self):
        self._elegir(self.camas[0], self.sin_publicar, self.sin_foto)
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self.Diapositiva.create({'website_id': self.website.id, 'product_tmpl_id': self.camas[0].id})
        por_producto = {d.product_tmpl_id: d.en_portada for d in self.Diapositiva.search([])}
        self.assertEqual(por_producto, {self.camas[0]: True, self.sin_publicar: False, self.sin_foto: False})

    # ------------------------------------------------------------------ la portada

    def test_vacio_queda_el_hero_de_siempre(self):
        self.Diapositiva.search([]).unlink()
        texto, arbol = self._portada()
        self.assertIsNone(self._vitrina(arbol))
        self.assertTrue(arbol.xpath('//div[@id="oe_structure_dcasa_hero"]//section[contains(@class, "o_dcasa_hero")]'))
        self.assertIn('/website_dcasa/static/src/img/hero-bebe-1200.webp', texto, 'la foto del bebé de babycaleb.com')
        precarga = arbol.xpath('//head/link[@rel="preload"][@as="image"]')
        self.assertEqual([p.get('href') for p in precarga], ['/website_dcasa/static/src/img/hero-bebe-1200.webp'])
        self.assertIn('hero-bebe-800.webp 800w', precarga[0].get('imagesrcset'))

    def test_con_productos_el_fondo_son_las_fotos_y_encima_solo_el_texto(self):
        """El hero es un fondo: una foto por producto, en el orden del panel, y encima el texto de siempre.

        Nada que el visitante pueda tocar (la dueña, 2026-11-17: «no quiero ni siquiera que el usuario tenga control
        de este carrusel», «ni siquiera tiene que tener el nombre del producto»): ni enlaces, ni nombres, ni flechas,
        ni barras, ni pausa. Por eso la pila de fotos es decorativa y el lector de pantalla no la lee.
        """
        orden = [self.camas[2], self.camas[0], self.camas[1]]
        self._elegir(orden[0], self.sin_publicar, orden[1], self.sin_foto, orden[2])
        texto, arbol = self._portada()
        vitrina = self._vitrina(arbol)
        self.assertIsNotNone(vitrina, 'con productos elegidos, el hero es el fondo en movimiento')
        self.assertFalse(arbol.xpath('//div[@id="oe_structure_dcasa_hero"]'), 'y no el de siempre')
        self.assertNotIn('hero-bebe', texto, 'y no la foto del bebé')
        self.assertEqual(len(arbol.xpath('//h1')), 1, 'un solo titular en la página')
        self.assertEqual(' '.join(vitrina.xpath('.//h1')[0].text_content().split()),
                         'Cuidado hipoalergénico para la piel de tu bebé')
        self.assertEqual(vitrina.xpath('.//a[contains(@class, "btn-primary")]/@href'), ['/shop'])

        pila = vitrina.xpath('.//div[contains(@class, "o_dcasa_vitrina_fotos")]')[0]
        self.assertEqual(pila.get('aria-hidden'), 'true', 'el fondo es decorativo: no se lee')
        fotos = pila.xpath('./div[contains(@class, "o_dcasa_vitrina_foto")]')
        self.assertEqual(len(fotos), len(orden),
                         'una foto por producto que se puede mostrar, sin el sin publicar ni el que no tiene foto')
        self.assertEqual([f.get('style') for f in fotos], ['--i: 0;', '--i: 1;', '--i: 2;'],
                         'cada foto arranca en un punto distinto del zoom')
        imagenes = [f.xpath('.//img')[0] for f in fotos]
        self.assertEqual([img.get('alt') for img in imagenes], [''] * len(orden),
                         'alt vacío: el nombre del producto no sale ni para el lector de pantalla')
        primera, *demas = imagenes
        self.assertEqual((primera.get('loading'), primera.get('fetchpriority')), ('eager', 'high'), 'la imagen LCP')
        self.assertTrue(all(img.get('loading') == 'lazy' for img in demas))
        self.assertIn('is-activa', _clases(fotos[0]))
        self.assertFalse(any('is-activa' in _clases(f) for f in fotos[1:]), 'sin JavaScript se ve la primera')
        # La foto grande: WebP del ancho justo (hasta 1600 px) y, de respaldo, la de Odoo a 1920.
        fuente = fotos[0].xpath('.//source[@type="image/webp"]')[0].get('srcset')
        self.assertIn(f'/dcasa/img/product.template/{orden[0].id}/image_1920/1600.webp', fuente)
        self.assertIn('image_1920', primera.get('srcset'))

        # Nada que manejar: ni mandos, ni enlaces, ni nombres, ni el papel de «carrusel».
        self.assertFalse(vitrina.xpath('.//*[contains(@class, "o_dcasa_vitrina_barra")]'), 'sin barras')
        self.assertFalse(vitrina.xpath('.//*[contains(@class, "o_dcasa_vitrina_boton")]'), 'sin flechas ni pausa')
        self.assertFalse(vitrina.xpath('.//*[contains(@class, "o_dcasa_vitrina_nombre")]'), 'sin nombres')
        self.assertFalse(vitrina.xpath('.//*[contains(@class, "o_dcasa_vitrina_ver")]'), 'sin «Ver detalles»')
        self.assertFalse(pila.xpath('.//a'), 'el fondo no lleva a ninguna ficha')
        self.assertFalse(pila.xpath('.//button'))
        self.assertFalse(vitrina.xpath('.//*[@role="group"] | .//*[@aria-roledescription] | .//*[@aria-live]'),
                         'no es un carrusel que se recorra: no se anuncia como tal')
        en_el_hero = lhtml.tostring(vitrina, encoding='unicode')
        for producto in orden:
            self.assertNotIn(producto._dcasa_nombre_cliente(), en_el_hero,
                             'el nombre del producto no sale en el hero (en los carriles de abajo sí: son tarjetas)')

        # El texto va aparte de la pila de fotos, en su propio bloque.
        panel = vitrina.xpath('.//div[contains(@class, "o_dcasa_vitrina_panel")]')[0]
        self.assertTrue(panel.xpath('.//h1'), 'el titular va en su bloque')
        self.assertFalse(panel.xpath('.//img'), 'y ninguna foto dentro del bloque del texto')

        precarga = arbol.xpath('//head/link[@rel="preload"][@as="image"]')
        self.assertEqual(len(precarga), 1, 'se precarga solo la primera foto del fondo')
        self.assertEqual(precarga[0].get('imagesrcset'), fuente)
        self.assertEqual(precarga[0].get('fetchpriority'), 'high')

    def test_el_mismo_hero_crema_con_su_boton_naranja(self):
        """Con productos, el hero es el de babycaleb.com: el antetítulo en píldora, el titular, el subtítulo y el único
        botón («Ver el catálogo», el principal: naranja con letra navy). Sin la clase del hero de siempre ni la de la
        foto oscura, y sin el botón de WhatsApp de la copia de origen."""
        self._elegir(*self.camas)
        _texto, arbol = self._portada()
        vitrina = self._vitrina(arbol)
        panel = vitrina.xpath('.//div[contains(@class, "o_dcasa_vitrina_panel")]')[0]
        self.assertTrue(panel.xpath('.//p[contains(@class, "o_dcasa_kicker_pildora")]'))
        self.assertEqual(panel.xpath('.//a[contains(@class, "btn")]/@href'), ['/shop'], 'un solo botón, al catálogo')
        self.assertFalse(vitrina.xpath('.//*[contains(@class, "o_dcasa_btn_linea") or contains(@class, "o_dcasa_kicker_light")]'))
        self.assertNotIn('o_dcasa_hero ', (vitrina.get('class') or '') + ' ')
        self.assertEqual(len(vitrina.xpath('.//span[contains(@class, "o_dcasa_hero_mancha")]')), 2, 'las manchas suaves')

    def test_la_seccion_de_cine_ya_no_sale(self):
        """La sección «de cine» (dos cintas de fotos por categoría de muebles) se quitó con la marca de Baby Caleb: no está
        en la portada de su web y sus categorías eran las de la mueblería de origen."""
        _texto, arbol = self._portada()
        self.assertFalse(arbol.xpath('//section[contains(@class, "o_dcasa_cine")]'))
        self.assertFalse(hasattr(type(self.website), '_dcasa_cine'))
        self.assertFalse(hasattr(modulo_portada, 'CATEGORIAS_CINE'))

    def test_si_nada_se_puede_mostrar_vuelve_el_hero_de_siempre(self):
        self._elegir(self.sin_publicar, self.sin_foto)
        _texto, arbol = self._portada()
        self.assertIsNone(self._vitrina(arbol))
        self.assertTrue(arbol.xpath('//div[@id="oe_structure_dcasa_hero"]'))

    def test_un_solo_producto_una_foto_quieta(self):
        """Con un solo producto el fondo es esa foto, con su zoom lento; no hay nada más que enseñar."""
        self._elegir(self.camas[1])
        _texto, arbol = self._portada()
        vitrina = self._vitrina(arbol)
        self.assertEqual(len(vitrina.xpath('.//div[contains(@class, "o_dcasa_vitrina_fotos")]/div')), 1)
        self.assertFalse(vitrina.xpath('.//div[contains(@class, "o_dcasa_vitrina_barras")]'))
        self.assertFalse(vitrina.xpath('.//div[contains(@class, "o_dcasa_vitrina_botones")]'))

    def test_el_cambio_se_ve_al_momento(self):
        """Odoo guarda la portada de los visitantes hasta una hora: el carrusel va en la clave de esa memoria."""
        self.Diapositiva.search([]).unlink()
        self.assertIsNone(self._vitrina(self._portada()[1]))
        self._elegir(self.camas[0], self.camas[1])
        self.assertIsNotNone(self._vitrina(self._portada()[1]), 'elegir productos se ve sin esperar')
        self._elegir(self.camas[1], self.camas[0])
        fotos = self._vitrina(self._portada()[1]).xpath(
            './/div[contains(@class, "o_dcasa_vitrina_fotos")]/div//img/@src')
        self.assertEqual([_id_del_src(f) for f in fotos], [self.camas[1].id, self.camas[0].id], 'reordenar, también')
        self.Diapositiva.search([]).unlink()
        self.assertIsNone(self._vitrina(self._portada()[1]), 'y vaciar la lista vuelve al hero de siempre')

    def test_con_el_editor_del_sitio_abierto_la_portada_abre(self):
        """Quien tiene el grupo de diseñador recibe las plantillas con las marcas del editor (inherit_branding): ni
        con el carrusel ni sin él la portada puede dar error. Un hero guardado con el editor (una vista que reemplaza
        el bloque por su id) sigue dentro de la condición: sale sin carrusel y no se mezcla con él."""
        # Como lo guarda Odoo: una vista del sitio que hereda la portada que ese sitio dibuja (su copia, si la tiene).
        portada = self.env['website'].with_context(website_id=self.website.id).viewref('website_dcasa.homepage_dcasa')
        self.env['ir.ui.view'].create({
            'name': 'Hero guardado con el editor (prueba)', 'type': 'qweb', 'key': 'prueba_carrusel.hero_guardado',
            'website_id': self.website.id, 'inherit_id': portada.id,
            'arch': """<data><xpath expr="//*[hasclass('oe_structure')][@id='oe_structure_dcasa_hero']" position="replace">
                <div class="oe_structure" id="oe_structure_dcasa_hero"><section class="o_dcasa_hero">
                <h1 class="o_dcasa_display">HERO GUARDADO EN EL EDITOR</h1></section></div></xpath></data>""",
        })
        disenador = _usuario(self.env, 'disenador_carrusel', 'website.group_website_designer')
        self.authenticate(disenador.login, disenador.login)
        for ruta in ('/', '/?enable_editor=1'):
            with self.subTest(ruta=ruta, carrusel=False):
                self.Diapositiva.search([]).unlink()
                texto, arbol = self._portada(ruta)
                self.assertIn('data-oe-model', texto, 'la página trae las marcas del editor')
                self.assertIn('HERO GUARDADO EN EL EDITOR', texto)
                self.assertIsNone(self._vitrina(arbol))
            with self.subTest(ruta=ruta, carrusel=True):
                self._elegir(*self.camas)
                texto, arbol = self._portada(ruta)
                self.assertIsNotNone(self._vitrina(arbol))
                self.assertNotIn('HERO GUARDADO EN EL EDITOR', texto)
                self.assertEqual(len(arbol.xpath('//div[contains(@class, "o_dcasa_vitrina_fotos")]/div')), 3)

    # ------------------------------------------------------------------ nace con las camas aprobadas

    def _cama_con_codigo(self, codigo):
        """Una cama publicada, con foto, con el código público ``codigo`` (el código solo se da al crear)."""
        return self.env['product.template'].create({
            'name': f'ZZCARRUSEL CAMA {codigo}', 'sale_ok': True, 'is_published': True, 'list_price': 199.99,
            'image_1920': _foto((120, 110, 100)), 'dcasa_codigo_publico': codigo})

    def test_nace_una_vez_con_las_camas_aprobadas_y_se_salta_lo_que_no_existe(self):
        Param = self.env['ir.config_parameter'].sudo()
        self.assertTrue(Param.get_param(PARAM_SEMBRADO), 'al instalar ya se intentó (en esta base no hay esas camas)')
        # Tres de las ocho existen, creadas en otro orden; las demás no: se saltan sin error.
        ivory, black, beige = (self._cama_con_codigo(CARRUSEL_INICIAL[i]) for i in (5, 0, 3))
        self.Diapositiva.search([]).unlink()
        Param.set_param(PARAM_SEMBRADO, False)
        self.assertEqual(self.Diapositiva._dcasa_sembrar(), 3)
        diapositivas = self.Diapositiva.search([('website_id', '=', self.website.id)])
        self.assertEqual(list(diapositivas.mapped('product_tmpl_id')), [black, beige, ivory],
                         'en el orden que aprobó la dueña')
        self.assertTrue(Param.get_param(PARAM_SEMBRADO))
        fotos = self._vitrina(self._portada()[1]).xpath(
            './/div[contains(@class, "o_dcasa_vitrina_fotos")]/div//img/@src')
        self.assertEqual([_id_del_src(f) for f in fotos], [black.id, beige.id, ivory.id])
        # Desde ahí la lista es de Gerencia: si la vacía (o la cambia), una actualización no la vuelve a llenar.
        diapositivas.unlink()
        self.assertEqual(self.Diapositiva._dcasa_sembrar(), 0)
        self.assertFalse(self.Diapositiva.search_count([]))
        self.assertIsNone(self._vitrina(self._portada()[1]), 'vacía: el hero de siempre')

    def test_no_pisa_una_lista_que_ya_tiene_productos(self):
        self._cama_con_codigo(CARRUSEL_INICIAL[0])
        self._elegir(self.camas[2])
        self.env['ir.config_parameter'].sudo().set_param(PARAM_SEMBRADO, False)
        self.assertEqual(self.Diapositiva._dcasa_sembrar(), 0)
        self.assertEqual(self.Diapositiva.search([]).product_tmpl_id, self.camas[2])

    def test_sin_ninguna_cama_aprobada_queda_el_hero_de_siempre(self):
        self.Diapositiva.search([]).unlink()
        self.env['ir.config_parameter'].sudo().set_param(PARAM_SEMBRADO, False)
        self.assertEqual(self.Diapositiva._dcasa_sembrar(), 0)
        self.assertIsNone(self._vitrina(self._portada()[1]))

    # ------------------------------------------------------------------ en Chrome

    @contextlib.contextmanager
    def _chrome(self, ancho, alto, movil=False, reducido=False):
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
            browser._websocket_request('Emulation.setEmulatedMedia', params={
                'features': [{'name': 'prefers-reduced-motion', 'value': 'reduce' if reducido else 'no-preference'}]})
            yield browser

    def _en_chrome(self, codigo, ancho=1440, alto=900, movil=False, reducido=False):
        with self._chrome(ancho, alto, movil, reducido) as browser:
            browser.navigate_to(self.base_url() + '/', wait_stop=True)
            res = browser._websocket_request('Runtime.evaluate', params={
                'expression': PRUEBA_JS % codigo, 'awaitPromise': True, 'returnByValue': True}, timeout=120)
            self.assertFalse(browser.had_failure, 'console.error en la página')
        self.assertFalse(res.get('exceptionDetails'), f'JavaScript falló: {res}')
        return res['result']['value']

    def test_en_la_computadora_las_fotos_llenan_su_marco_y_cambian_solas(self):
        self._elegir(*self.camas)
        r = self._en_chrome(PASOS_COMPUTADORA)
        self.assertTrue(r['fotoEnSuMarco'], 'la foto llena el marco redondeado')
        self.assertEqual(r['radioMarco'], '24px')
        self.assertTrue(r['textoAlLado'], 'el texto va a la izquierda de las fotos, sobre el crema')
        self.assertEqual(r['zoom'], 'dcasa-vitrina-zoom', 'el zoom lento corre')
        self.assertEqual(r['zoomEstado'], 'running', 'y no para nunca')
        self.assertEqual(r['alEmpezar'], 0, 'se ve la primera, la que el navegador precargó')
        self.assertNotEqual(r['trasEsperar'], 0, 'la foto cambia sola')
        self.assertEqual(r['visibles'], 1, 'se ve una sola foto a la vez')
        self.assertTrue(r['sinCapa'], 'sin velo ni degradado sobre las fotos')
        self.assertEqual(r['nadaQueTocar'], 0, 'no hay flechas, barras, pausa ni enlaces')
        self.assertFalse(r['whatsappEscondido'], 'el WhatsApp flotante no se esconde (la burbuja de su web siempre está)')
        self.assertTrue(r['nadaEnsancha'], 'nada ensancha la página')

    def test_con_movimiento_reducido_nada_se_mueve_solo(self):
        self._elegir(*self.camas)
        r = self._en_chrome(PASOS_REDUCIDO, reducido=True)
        self.assertEqual(r['trasEsperar'], 0, 'la foto no cambia sola')
        self.assertEqual(r['zoom'], 'none', 'y el zoom tampoco se mueve')
        self.assertTrue(r['fotoEnSuMarco'], 'pero la foto sigue llenando su marco')
        self.assertEqual(r['nadaQueTocar'], 0, 'sigue sin nada que manejar')
        self.assertTrue(r['nadaEnsancha'])

    def test_en_el_telefono_el_texto_va_arriba_y_las_fotos_debajo(self):
        self._elegir(*self.camas)
        r = self._en_chrome(PASOS_TELEFONO, ancho=390, alto=844, movil=True)
        self.assertTrue(r['fotoEnSuMarco'], 'la foto llena su marco')
        self.assertTrue(r['textoArriba'], 'en el celular el texto va arriba y las fotos debajo, como en su web')
        self.assertTrue(r['sinCapa'], 'sin velo ni degradado')
        self.assertTrue(r['botonVisible'], 'el botón naranja se ve sin bajar')
        self.assertEqual(r['nadaQueTocar'], 0, 'tampoco en el celular hay nada que manejar')
        self.assertFalse(r['deslizarCambia'], 'deslizar no cambia la foto: no es un carrusel')
        self.assertFalse(r['abrioFicha'], 'ni abre ninguna ficha')
        self.assertTrue(r['nadaEnsancha'])


# El esqueleto de cada prueba en Chrome: espera a que la página esté lista y corre los pasos (%s).
PRUEBA_JS = r"""(async () => {
    const esperar = (ms) => new Promise((ok) => setTimeout(ok, ms));
    for (let i = 0; i < 300 && document.body.getAttribute('is-ready') !== 'true'; i++) { await esperar(50); }
    await esperar(400);
    const vitrina = document.querySelector('.o_dcasa_vitrina');
    const fotos = () => [...vitrina.querySelectorAll('.o_dcasa_vitrina_foto')];
    const actual = () => fotos().findIndex((f) => f.classList.contains('is-activa'));
    const pila = vitrina.querySelector('.o_dcasa_vitrina_fotos');
    const foto = pila.getBoundingClientRect();
    const panel = vitrina.querySelector('.o_dcasa_vitrina_panel .o_dcasa_hero_texto').getBoundingClientRect();
    const primera = fotos()[0].querySelector('img');
    const i = primera.getBoundingClientRect();
    const sinContenido = (el, p) => ['none', 'normal'].includes(getComputedStyle(el, p).content);
    const r = {
        // La foto llena su marco (el zoom solo la agranda: nunca deja un hueco).
        fotoEnSuMarco: i.left <= foto.left + 1 && i.right >= foto.right - 1 && i.top <= foto.top + 1 && i.bottom >= foto.bottom - 1,
        radioMarco: getComputedStyle(pila).borderTopLeftRadius,
        textoAlLado: panel.right <= foto.left + 1,
        textoArriba: panel.bottom <= foto.top + 1,
        zoom: getComputedStyle(primera).animationName,
        zoomEstado: getComputedStyle(primera).animationPlayState,
        // Ni velo ni degradado: ninguna capa sobre el hero, sobre el marco ni sobre las fotos.
        sinCapa: ['::before', '::after'].every((p) => sinContenido(vitrina, p) && sinContenido(pila, p))
            && getComputedStyle(pila).backgroundImage === 'none' && getComputedStyle(primera).filter === 'none',
        // Ni un solo mando ni enlace dentro del hero, salvo el botón del texto: no se maneja.
        nadaQueTocar: vitrina.querySelectorAll('a, button, [role="group"], [aria-live], .o_dcasa_vitrina_barra,'
            + ' .o_dcasa_vitrina_boton, .o_dcasa_vitrina_nombre').length
            - vitrina.querySelectorAll('.o_dcasa_vitrina_panel a, .o_dcasa_vitrina_panel button').length,
        whatsappEscondido: document.documentElement.classList.contains('o_dcasa_vitrina_a_la_vista'),
        nadaEnsancha: document.documentElement.scrollWidth <= window.innerWidth,
    };
    %s
    return r;
})()"""

# El primer cambio ya está programado desde que carga la página, con el tiempo de verdad ($dcasa-vitrina-tiempo,
# 6,5 s): acortar --vitrina-tiempo aquí solo vale de la segunda vez en adelante. Por eso se espera hasta ESPERA_FONDO.
PASOS_COMPUTADORA = """
    r.alEmpezar = actual();
    vitrina.style.setProperty('--vitrina-tiempo', '0.4s');
    for (let i = 0; i < 240 && actual() === r.alEmpezar; i++) { await esperar(50); }
    r.trasEsperar = actual();
    // Para contar cuántas se ven hay que dejar de cambiar: con 0,4 s entre fotos y 1,8 s de fundido siempre
    // habría dos a medio camino. Se alarga el tiempo, se deja terminar el fundido y recién ahí se cuenta.
    vitrina.style.setProperty('--vitrina-tiempo', '600s');
    await esperar(2500);
    r.visibles = fotos().filter((f) => parseFloat(getComputedStyle(f).opacity) > 0.01).length;
"""

# Se espera MÁS que el tiempo de verdad de una diapositiva (6,5 s): si con movimiento reducido se hubiera
# programado el cambio, aquí ya habría pasado.
PASOS_REDUCIDO = """
    await esperar(9000);
    r.trasEsperar = actual();
"""

PASOS_TELEFONO = """
    const boton = document.querySelector('.o_dcasa_hero_vitrina .btn-primary').getBoundingClientRect();
    r.botonVisible = boton.bottom < window.innerHeight;
    // Que nadie se quede «arrastrando» el fondo esperando que pase algo: deslizar no cambia la foto ni abre nada.
    vitrina.style.setProperty('--vitrina-tiempo', '600s');
    const antes = actual();
    const caja = pila.getBoundingClientRect();
    const y = caja.top + caja.height / 2;
    const deslizar = (desde, hasta) => {
        const comun = { bubbles: true, cancelable: true, pointerType: 'touch', isPrimary: true, pointerId: 7 };
        const objetivo = document.elementFromPoint(desde, y);
        objetivo.dispatchEvent(new PointerEvent('pointerdown', { ...comun, clientX: desde, clientY: y }));
        objetivo.dispatchEvent(new PointerEvent('pointerup', { ...comun, clientX: hasta, clientY: y + 4 }));
        return objetivo.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, clientX: hasta, clientY: y }));
    };
    const inicio = location.href;
    deslizar(caja.left + caja.width * 0.8, caja.left + caja.width * 0.2);
    await esperar(300);
    r.deslizarCambia = actual() !== antes;
    r.abrioFicha = location.href !== inicio;
"""
