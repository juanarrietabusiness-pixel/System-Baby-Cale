# ruff: noqa: E501  (JavaScript del navegador embebido en texto)
"""Portada: el hero con los productos que elige Gerencia (models/portada.py, views/homepage_templates.xml,
static/src/js/portada.js), con la marca de Baby Caleb (docs/MARCA_BABY_CALEB.md, 2026-11-19). Lo que se fija aquí:

* El ajuste: «Sitio web › Carrusel de la portada», una pantalla con los segundos que dura cada foto (3 de fábrica,
  de 2 a 15) y la lista de productos, que se ordena arrastrando; solo Gerencia y los administradores la ven y la cambian
  (viene de D'CASA, 2026-11-19: «demoran… 5 a 6 segundos… de unos 2 a 3, o poderlo definir yo mismo»).
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
* En Chrome: la foto llena su marco, el zoom corre, la foto cambia sola dentro del tiempo elegido (y quieta con
  movimiento reducido), el fundido y el zoom van a escala con ese tiempo, no hay NADA que tocar y nada ensancha la
  página.
"""
import base64
import contextlib
import io
from types import SimpleNamespace

from lxml import html as lhtml
from PIL import Image
from psycopg2 import IntegrityError

from odoo import Command
from odoo.addons.website_dcasa.models import portada as modulo_portada
from odoo.addons.website_dcasa.models.portada import CARRUSEL_INICIAL, PARAM_SEMBRADO
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import Form, HttpCase, tagged
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

    # ------------------------------------------------------------------ los segundos de cada foto

    def _ajustes(self, sitio=None):
        """Los ajustes del carrusel del sitio (se crean con el valor de fábrica si faltan)."""
        return self.env['dcasa.portada.ajustes']._dcasa_del_sitio(sitio or self.website, crear=True)

    def _segundos(self, valor, sitio=None):
        self._ajustes(sitio).segundos = valor

    def _tiempo_de_la_portada(self):
        """Lo que la portada le dice al navegador: el estilo del fondo (``--vitrina-tiempo``)."""
        _texto, arbol = self._portada()
        fondo = self._vitrina(arbol).xpath('.//div[contains(concat(" ", @class, " "), " o_dcasa_vitrina ")]')[0]
        return fondo.get('style')

    def test_de_fabrica_cada_foto_dura_3_segundos_y_la_plantilla_lo_dice(self):
        self.env['dcasa.portada.ajustes'].sudo().search([]).unlink()
        self.assertEqual(self.website._dcasa_hero_segundos(), 3.0, 'sin ajustes, 3 segundos por foto')
        self.assertEqual(self.website._dcasa_hero_tiempo(), '3s')
        self.assertEqual(self._ajustes().segundos, 3.0, 'y los ajustes nuevos nacen con 3')
        self._elegir(*self.camas)
        self.assertEqual(self._tiempo_de_la_portada(), '--vitrina-tiempo: 3s;', 'la plantilla lo escribe en el fondo')

    def test_un_sitio_nuevo_trae_los_3_segundos_de_fabrica_y_los_sitios_no_se_mezclan(self):
        otro = self.env['website'].create({'name': 'Sitio de prueba del carrusel'})
        self.assertFalse(self.env['dcasa.portada.ajustes'].sudo().search([('website_id', '=', otro.id)]))
        self.assertEqual(otro._dcasa_hero_tiempo(), '3s', 'un sitio nuevo, sin ajustes, trae el 3 de fábrica')
        self._segundos(6)
        self._segundos(9, otro)
        self.assertEqual((self.website._dcasa_hero_tiempo(), otro._dcasa_hero_tiempo()), ('6s', '9s'))
        self.assertNotEqual(self.website._dcasa_hero_firma(), otro._dcasa_hero_firma(), 'cada sitio, su firma')
        self._segundos(2.5)
        self.assertEqual((self.website._dcasa_hero_tiempo(), otro._dcasa_hero_tiempo()), ('2.5s', '9s'))
        with self.assertRaises(IntegrityError), self.cr.savepoint(), mute_logger('odoo.sql_db'):
            self.env['dcasa.portada.ajustes'].sudo().create({'website_id': otro.id})

    def test_la_portada_usa_los_segundos_que_se_eligen(self):
        self._elegir(*self.camas)
        for valor, texto in ((2, '2s'), (2.5, '2.5s'), (7.5, '7.5s'), (15, '15s')):
            with self.subTest(segundos=valor):
                self._segundos(valor)
                self.assertEqual(self.website._dcasa_hero_tiempo(), texto)
                self.assertEqual(self._tiempo_de_la_portada(), f'--vitrina-tiempo: {texto};')

    def test_los_segundos_van_de_2_a_15(self):
        ajustes = self._ajustes()
        for bueno in (2, 3, 2.5, 15):
            with self.subTest(bueno=bueno):
                ajustes.segundos = bueno
                self.assertEqual(ajustes.segundos, bueno)
        for malo in (0, 1, 1.9, 15.1, 16, 60, -3):
            with self.subTest(malo=malo), self.assertRaises(ValidationError) as error, self.cr.savepoint():
                ajustes.segundos = malo
            self.assertIn('de 2 a 15', str(error.exception), 'el mensaje dice los límites en palabras sencillas')
        self.assertEqual(ajustes.segundos, 15.0, 'un valor fuera de rango no se guarda')
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.env['dcasa.portada.ajustes'].sudo().create({'website_id': self.website.id, 'segundos': 99})

    def test_valores_raros_por_rpc_dan_un_error_claro(self):
        """Por RPC llega de todo: NaN, infinito, texto, ``None``, listas. Siempre ``ValidationError`` en español."""
        ajustes = self._ajustes()
        ajustes.segundos = 4
        # Con ``write`` y ``create`` (lo que llega por RPC): asignar con ``ajustes.segundos = …`` ya revienta en el ORM
        # antes de llegar al modelo, y por RPC no se puede.
        for raro in (float('nan'), float('inf'), float('-inf'), 1e400, 'abc', '', '3,5', None, False, True, [3],
                     {'a': 1}, '3; background:red', '3s}</style>'):
            with self.subTest(raro=repr(raro)), self.assertRaises(ValidationError) as error, self.cr.savepoint():
                ajustes.write({'segundos': raro})
            self.assertIn('de 2 a 15', str(error.exception))
            with self.subTest(raro=repr(raro), via='create'), self.assertRaises(ValidationError), self.cr.savepoint():
                self.env['dcasa.portada.ajustes'].sudo().create({'website_id': self.website.id, 'segundos': raro})
        self.assertEqual(ajustes.segundos, 4.0, 'ninguno se guardó')
        for texto, esperado in (('2.5', 2.5), (' 3 ', 3.0), ('1e1', 10.0)):
            ajustes.write({'segundos': texto})
            self.assertEqual(ajustes.segundos, esperado, f'el texto numérico {texto!r} se acepta como número')

    def test_un_valor_suelto_en_la_base_no_rompe_la_portada(self):
        """Si alguien dejara en la base un valor que no sirve (SQL a mano: fuera de rango o NaN), la portada sigue y usa
        los 3 segundos de fábrica."""
        self._elegir(*self.camas)
        ajustes = self._ajustes()
        for suelto in ('0', '0.2', '99', '1000000', "'NaN'"):
            with self.subTest(suelto=suelto):
                self.cr.execute(f'UPDATE dcasa_portada_ajustes SET segundos = {suelto} WHERE id = %s', (ajustes.id,))
                ajustes.invalidate_recordset()
                self.assertEqual(self.website._dcasa_hero_tiempo(), '3s')
                self.assertEqual(self._tiempo_de_la_portada(), '--vitrina-tiempo: 3s;')

    def test_cambiar_los_segundos_cambia_la_firma_y_la_portada_guardada(self):
        """Odoo guarda la portada de los visitantes hasta una hora: los segundos van en la clave de esa memoria."""
        self._elegir(*self.camas)
        self._segundos(3)
        pedido = SimpleNamespace(website=self.website, lang=SimpleNamespace(code='es_419'),
                                 httprequest=SimpleNamespace(path='/'), session=SimpleNamespace(debug=''))
        Pagina = self.env['website.page']
        firma, clave = self.website._dcasa_hero_firma(), Pagina._get_cache_key(pedido)
        self.assertEqual(self._tiempo_de_la_portada(), '--vitrina-tiempo: 3s;', 'la portada ya quedó guardada')
        self._segundos(6)
        self.assertNotEqual(self.website._dcasa_hero_firma(), firma, 'los segundos entran en la firma')
        self.assertNotEqual(Pagina._get_cache_key(pedido), clave, 'y en la clave de la portada guardada')
        self.assertEqual(self._tiempo_de_la_portada(), '--vitrina-tiempo: 6s;', 'el cambio se ve sin esperar la hora')
        self._segundos(3)
        self.assertEqual(self.website._dcasa_hero_firma(), firma, 'y volver al valor de antes, a la misma firma')

    def test_las_diapositivas_quedan_con_los_ajustes_de_su_sitio(self):
        """La lista de la pantalla cuelga de los ajustes del sitio: quien crea una diapositiva solo con el sitio (la
        siembra, las pruebas) la deja igual de bien puesta, y la lista de un sitio no trae las del otro."""
        otro = self.env['website'].create({'name': 'Sitio de prueba del carrusel'})
        self._elegir(self.camas[0], self.camas[1])
        propia = self.Diapositiva.create({'website_id': otro.id, 'product_tmpl_id': self.camas[2].id})
        self.assertEqual(propia.ajustes_id, self._ajustes(otro))
        self.assertEqual(self._ajustes().diapositiva_ids.product_tmpl_id, self.camas[0] | self.camas[1])
        self.assertEqual(self._ajustes(otro).diapositiva_ids, propia)
        # Desde la lista del padre llega el padre y no el sitio: el sitio es el del padre, no el «actual».
        nueva = self.Diapositiva.create({'ajustes_id': self._ajustes(otro).id, 'product_tmpl_id': self.sin_publicar.id})
        self.assertEqual(nueva.website_id, otro)

    def test_gerencia_cambia_los_segundos_y_la_lista_desde_su_pantalla_y_nada_mas_del_sitio(self):
        accion = self.env['dcasa.portada.ajustes'].with_user(self.gerente).action_abrir()
        ajustes = self._ajustes()
        self.assertEqual((accion['res_model'], accion['res_id'], accion['view_mode']),
                         ('dcasa.portada.ajustes', ajustes.id, 'form'), 'abre los ajustes del sitio actual')
        # La pantalla: el campo de los segundos arriba y la lista de productos, como la ve Gerencia.
        with Form(ajustes.with_user(self.gerente), view='website_dcasa.view_dcasa_portada_ajustes_form') as pantalla:
            self.assertEqual(pantalla.segundos, 3.0)
            pantalla.segundos = 2.5
            with pantalla.diapositiva_ids.new() as linea:
                linea.product_tmpl_id = self.camas[0]
        self.assertEqual(ajustes.segundos, 2.5)
        self.assertEqual(ajustes.diapositiva_ids.product_tmpl_id, self.camas[0])
        self.assertEqual(ajustes.diapositiva_ids.website_id, self.website)
        self.assertEqual(self.website._dcasa_hero_tiempo(), '2.5s')
        # Nada del sitio mismo: Gerencia ya no escribe en `website` (ni siquiera para esto).
        sitio = self.website.with_user(self.gerente)
        self.assertEqual([sitio.has_access(op) for op in ('read', 'write', 'create', 'unlink')],
                         [True, False, False, False])
        for campo, valor in (('name', 'Otro nombre'), ('domain', 'https://otro.example'), ('social_facebook', 'x')):
            with self.subTest(campo=campo), self.assertRaises(AccessError):
                sitio.write({campo: valor})
        with self.assertRaises(AccessError):
            self.env['website'].with_user(self.gerente).create({'name': 'Sitio nuevo'})
        with self.assertRaises(AccessError):
            sitio.unlink()
        # Los ajustes no se borran ni se crean de más: uno por sitio.
        with self.assertRaises(AccessError):
            ajustes.with_user(self.gerente).unlink()
        # Los administradores también cambian los ajustes.
        ajustes.with_user(self.env.ref('base.user_admin')).segundos = 4
        self.assertEqual(ajustes.segundos, 4.0)

    def test_quien_no_es_gerencia_no_cambia_los_segundos(self):
        ajustes = self._ajustes()
        for usuario in (self.vendedora, self.interno):
            with self.subTest(usuario=usuario.login):
                with self.assertRaises(AccessError):
                    ajustes.with_user(usuario).write({'segundos': 2})
                with self.assertRaises(AccessError):
                    ajustes.with_user(usuario).write({'diapositiva_ids': [Command.create(
                        {'product_tmpl_id': self.camas[0].id})]})
                with self.assertRaises(AccessError):
                    self.env['dcasa.portada.ajustes'].with_user(usuario).search([])
        self.assertEqual(ajustes.segundos, 3.0)
        menu = 'website_dcasa.menu_dcasa_portada_diapositiva'
        accion = self.env.ref('website_dcasa.action_dcasa_portada_carrusel')
        self.assertEqual(self.env.ref(menu).action, accion, 'el menú abre la pantalla con los segundos y la lista')

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

    def _ritmo_en_chrome(self, segundos, espera_ms):
        """Pone los segundos en el sitio, abre la portada en Chrome y mide el ritmo del fondo (PASOS_RITMO)."""
        self._segundos(segundos)
        self._elegir(*self.camas)
        return self._en_chrome(PASOS_RITMO.replace('ESPERA_MAX', str(espera_ms)))['ritmo']

    def _comprobar_escala(self, r, segundos):
        """El fundido y el zoom escalan con lo que dura cada foto (SCSS: clamp y calc sobre --vitrina-tiempo)."""
        self.assertEqual(r['tiempo'], f'{segundos:g}s', 'el fondo lleva los segundos que eligió Gerencia')
        fundido = min(max(0.35 * segundos, 0.5), 2.4)
        self.assertAlmostEqual(r['fundido'], fundido, delta=0.02, msg='el fundido es una parte del tiempo de la foto')
        self.assertLessEqual(r['fundido'], 0.4 * segundos, 'y nunca pasa del 40 % de lo que dura la foto')
        self.assertAlmostEqual(r['zoom'], 6 * segundos, delta=0.05, msg='el zoom va al mismo ritmo por foto')
        for i, desfase in enumerate(r['desfase']):
            self.assertAlmostEqual(desfase, -i * segundos, delta=0.05, msg='cada foto arranca en un punto distinto')

    def test_con_2_segundos_la_foto_cambia_dentro_del_tiempo(self):
        r = self._ritmo_en_chrome(2, 3500)
        self.assertTrue(r['cambio'], 'con 2 segundos por foto, la foto cambió antes de los 3,5 s (antes tardaba 6,5)')
        self._comprobar_escala(r, 2)

    def test_con_3_segundos_de_fabrica_la_foto_cambia_dentro_del_tiempo(self):
        r = self._ritmo_en_chrome(3, 4500)
        self.assertTrue(r['cambio'], 'con los 3 segundos de fábrica, la foto cambió antes de los 4,5 s')
        self._comprobar_escala(r, 3)

    def test_con_15_segundos_la_foto_no_cambia_antes_y_sigue_elegante(self):
        r = self._ritmo_en_chrome(15, 7000)
        self.assertFalse(r['cambio'], 'con 15 segundos por foto no cambió en 7 s: el valor se respeta hacia los dos lados')
        self._comprobar_escala(r, 15)

    def test_con_2_segundos_hay_fundido_y_se_ve_una_sola_foto_al_asentarse(self):
        """A 2 s el fundido (0,7 s) deja pasar a la siguiente foto sin dejar dos a medias para siempre."""
        self._segundos(2)
        self._elegir(*self.camas)
        r = self._en_chrome(PASOS_ASENTARSE)
        self.assertEqual(r['visiblesAlAsentarse'], 1, 'tras el fundido queda una sola foto a la vista')
        self.assertGreaterEqual(r['cambios'], 2, 'y siguió cambiando de foto a foto, sin quedarse trabada')

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

# El primer cambio ya está programado desde que carga la página, con el tiempo de verdad (los 3 s de fábrica de
# dcasa.portada.ajustes.segundos): acortar --vitrina-tiempo aquí solo vale de la segunda vez en adelante. Por eso se espera
# hasta 12 s (240 × 50 ms), más que ese primer tiempo.
PASOS_COMPUTADORA = """
    r.alEmpezar = actual();
    vitrina.style.setProperty('--vitrina-tiempo', '0.4s');
    for (let i = 0; i < 240 && actual() === r.alEmpezar; i++) { await esperar(50); }
    r.trasEsperar = actual();
    // Para contar cuántas se ven hay que dejar de cambiar: con 0,4 s entre fotos y varios segundos de fundido siempre
    // habría dos a medio camino. Se alarga el tiempo (el último cambio ya programado ocurre en menos de 0,4 s y su
    // fundido, ahora de 2,4 s, tarda lo suyo) y se espera a que se asiente: se cuenta cuando queda una sola, hasta 8 s.
    vitrina.style.setProperty('--vitrina-tiempo', '600s');
    const cuantas = () => fotos().filter((f) => parseFloat(getComputedStyle(f).opacity) > 0.01).length;
    const t1 = performance.now();
    while (cuantas() !== 1 && performance.now() - t1 < 8000) { await esperar(100); }
    r.visibles = cuantas();
"""

# Se espera MÁS que el triple del tiempo de verdad de una foto (3 s de fábrica): si con movimiento reducido se hubiera
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

# El ritmo del fondo con los segundos que puso Gerencia (el sitio ya trae el valor; no se toca --vitrina-tiempo): lo que
# el CSS calcula con él (fundido, zoom, desfase de cada foto) y si la foto cambia dentro del tiempo (ESPERA_MAX, en ms).
PASOS_RITMO = """
    const una = fotos()[0];
    const ritmo = {
        tiempo: getComputedStyle(vitrina).getPropertyValue('--vitrina-tiempo').trim(),
        fundido: parseFloat(getComputedStyle(una).transitionDuration),
        zoom: parseFloat(getComputedStyle(una.querySelector('img')).animationDuration),
        desfase: fotos().map((f) => parseFloat(getComputedStyle(f.querySelector('img')).animationDelay)),
    };
    const inicial = actual();
    const t0 = performance.now();
    while (actual() === inicial && performance.now() - t0 < ESPERA_MAX) { await esperar(25); }
    ritmo.cambio = actual() !== inicial;
    r.ritmo = ritmo;
"""

# Con 2 s por foto y 0,7 s de fundido: se deja pasar varias fotos y, parando el cambio, se cuenta cuántas quedan a la vista.
PASOS_ASENTARSE = """
    let cambios = 0;
    let previa = actual();
    const t0 = performance.now();
    while (cambios < 2 && performance.now() - t0 < 12000) {
        await esperar(50);
        if (actual() !== previa) { cambios++; previa = actual(); }
    }
    r.cambios = cambios;
    vitrina.style.setProperty('--vitrina-tiempo', '600s');
    // El último cambio ya programado ocurre en menos de 2 s y su fundido (ahora de 2,4 s) tarda lo suyo: se cuenta cuando
    // queda una sola, hasta 8 s.
    const cuantas = () => fotos().filter((f) => parseFloat(getComputedStyle(f).opacity) > 0.01).length;
    const t1 = performance.now();
    while (cuantas() !== 1 && performance.now() - t1 < 8000) { await esperar(100); }
    r.visiblesAlAsentarse = cuantas();
"""
