import base64
import json
import re

from markupsafe import Markup

from odoo.tests import HttpCase, TransactionCase, tagged
from odoo.tools.misc import file_open


@tagged('post_install', '-at_install')
class TestWhatsappLink(TransactionCase):

    def setUp(self):
        super().setUp()
        self.website = self.env.ref('website.default_website')

    def test_whatsapp_url_uses_configured_number(self):
        self.website.dcasa_whatsapp_number = '+507 6757-5065'
        url = self.website._dcasa_whatsapp_url('Hola Baby Caleb')
        self.assertTrue(url.startswith('https://wa.me/50767575065?text='))
        self.assertIn('Hola%20Baby%20Caleb', url)

    def test_whatsapp_de_fabrica_es_el_de_baby_caleb(self):
        """El número de ventas y el saludo que trae el sitio al instalarse (decisión del dueño, 2026-11-18)."""
        self.assertEqual(self.website.dcasa_whatsapp_number, '+507 6757-5065')
        url = self.website._dcasa_whatsapp_url()
        self.assertTrue(url.startswith('https://wa.me/50767575065?text='), url)
        self.assertIn('Hola%20Baby%20Caleb', url)
        self.assertEqual(self.website.name, 'Baby Caleb')
        self.assertEqual(self.website.social_instagram, 'https://www.instagram.com/babycalebpanama')
        self.assertFalse(self.website.social_tiktok, 'Baby Caleb no tiene TikTok en su web: no se inventa')

    def test_whatsapp_url_falls_back_to_company_phone(self):
        self.website.dcasa_whatsapp_number = False
        self.website.company_id.phone = '+507 6000-1111'
        self.assertTrue(self.website._dcasa_whatsapp_url().startswith('https://wa.me/50760001111'))

    def test_whatsapp_url_without_number_goes_to_contact(self):
        self.website.dcasa_whatsapp_number = False
        self.website.company_id.phone = False
        self.assertEqual(self.website._dcasa_whatsapp_url(), '/contactus')


@tagged('post_install', '-at_install')
class TestWebsitePages(HttpCase):

    def test_homepage(self):
        # Con «Brian de la tienda» (dcasa_brian_tienda) encendido, la burbuja flotante es la suya: aquí se prueba la de
        # WhatsApp, la que sale con Brian apagado o sin ese módulo.
        self.env['ir.config_parameter'].sudo().set_param('dcasa_brian_tienda.activo', 'False')
        response = self.url_open('/')
        self.assertEqual(response.status_code, 200)
        html = response.text
        self.assertIn('Cuidado hipoalergénico para la piel de tu bebé', html)
        self.assertIn('https://wa.me/50767575065', html)
        self.assertIn('o_dcasa_wa_float', html)
        self.assertIn('babycalebpanama@gmail.com', html, 'El pie de página muestra los datos reales')
        for de_la_tienda_de_origen in ("D'CASA", 'D&#39;CASA', 'dcasapty', 'La Chorrera', 'Libertadores', '6026',
                                       'amueblada'):
            self.assertNotIn(de_la_tienda_de_origen, html)
        self.assertNotIn('555-555-5556', html, 'No debe quedar el teléfono de ejemplo de Odoo')
        self.assertNotIn('Company name', html, 'No debe quedar el copyright de ejemplo de Odoo')

    def test_socios_linked_from_site(self):
        home = self.url_open('/').text
        self.assertIn('href="/socios"', home)
        self.assertIn('Suma puntos y gana invitando', home)
        response = self.url_open('/socios')
        self.assertEqual(response.status_code, 200)
        self.assertIn('https://wa.me/50767575065', response.text, 'La app del socio usa el mismo sitio y pie')

    def test_terminos_de_odoo_llevan_a_los_reales(self):
        """La factura y el portal enlazan /terms: la plantilla de Odoo trae términos inventados en inglés."""
        self.env['ir.config_parameter'].sudo().set_param('account.use_invoice_terms', True)
        self.env.company.terms_type = 'html'
        respuesta = self.url_open('/terms', allow_redirects=False)
        self.assertEqual(respuesta.status_code, 301)
        self.assertTrue(respuesta.headers['Location'].endswith('/terminos'))
        self.assertNotIn('Odoo S.A.', self.url_open('/terms').text)

    def test_shop(self):
        self.assertEqual(self.url_open('/shop').status_code, 200)

    def test_frontend_css_compiles_with_brand(self):
        """La hoja del sitio compila con la marca de Baby Caleb (docs/MARCA_BABY_CALEB.md): crema, navy, naranja y
        verde, y ya no queda nada del azul, el amarillo ni el navy de D'CASA."""
        html = self.url_open('/').text
        css_links = re.findall(r'href="([^"]*web\.assets_frontend[^"]*\.css)"', html)
        self.assertTrue(css_links, 'La página debe enlazar el bundle CSS del sitio')
        css = self.url_open(css_links[0]).text
        self.assertIn('o_dcasa_pcard', css)
        self.assertIn('o_dcasa_hero_texto', css)
        self.assertIn('o_dcasa_wa_float', css)
        bajo = css.lower()
        for color in ('#f9f6ed', '#f2efe5', '#1b3246', '#ee924a', '#91c9a2', '#985d2f', '#53735c'):
            self.assertIn(color, bajo, f'falta el {color} de la marca')
        # La paleta del sitio (de la que Odoo saca los botones, los enlaces y las combinaciones de color) es la de Baby
        # Caleb: el «primary» es el naranja y el texto, el navy.
        self.assertRegex(bajo, r'--o-color-1:\s*#ee924a')
        self.assertRegex(bajo, r'--o-color-5:\s*#1b3246')
        # Y en las hojas de este módulo no queda nada del azul, el amarillo ni el navy de D'CASA, ni su letra.
        for hoja in ('primary_variables.scss', 'fuentes.scss', 'dcasa.scss'):
            with file_open(f'website_dcasa/static/src/scss/{hoja}') as archivo:
                fuente = archivo.read().lower()
            for de_dcasa in ('#1340b1', '#fed00f', '#0e2a6b', '#0f3591', "'anton'", "'oswald'", "'inter'"):
                self.assertNotIn(de_dcasa, fuente, f'{hoja}: quedó {de_dcasa} de D\'CASA')


@tagged('post_install', '-at_install')
class TestPortadaDinamica(HttpCase):
    """Carriles de productos, compra en 1 clic y SEO de la portada."""

    def setUp(self):
        super().setUp()
        self.website = self.env.ref('website.default_website')
        self.salas = self.env.ref('website_dcasa.public_category_salas')
        self.colchones = self.env.ref('website_dcasa.public_category_colchones')
        Product = self.env['product.template']
        self.sofa = Product.create({
            'name': 'SOFÁ DE PRUEBA', 'list_price': 123.45, 'is_published': True,
            'taxes_id': [(5, 0, 0)],  # sin impuesto: la cifra mostrada es la del precio
            'website_sequence': -100, 'public_categ_ids': [(6, 0, self.salas.ids)],
        })
        self.colchon = Product.create({
            'name': 'COLCHÓN DE PRUEBA', 'list_price': 99.0, 'is_published': True,
            'website_sequence': -99, 'public_categ_ids': [(6, 0, self.colchones.ids)],
        })
        self.oculto = Product.create({
            'name': 'MUEBLE SIN PUBLICAR', 'list_price': 10.0, 'is_published': False,
            'website_sequence': -101,
        })

    def test_productos_de_la_portada(self):
        todos = [i['producto'] for i in self.website._dcasa_productos(limit=50)]
        self.assertIn(self.sofa, todos)
        self.assertNotIn(self.oculto, todos, 'La portada solo muestra lo publicado')
        descanso = [i['producto'] for i in self.website._dcasa_productos(limit=50, categorias=['colchones'])]
        self.assertIn(self.colchon, descanso)
        self.assertNotIn(self.sofa, descanso)

    def test_una_categoria_sin_nada_publicado_abre_whatsapp_y_vuelve_sola_al_publicar(self):
        """Pedido de la dueña (2026-11-09): «Colchones» llevaba a una página de error porque Gerencia no ha publicado
        los colchones. Sin nada publicado, la tarjeta abre WhatsApp; con algo publicado, su página de la tienda. (La
        portada ya no enseña las categorías; las ofrece la búsqueda sin resultados: TestBuscador.)"""
        self.website.dcasa_whatsapp_number = '+507 6757-5065'

        def tarjeta(nombre):
            return next(t for t in self.website._dcasa_categorias() if t['nombre'] == nombre)

        con = tarjeta('Colchones')
        self.assertFalse(con['whatsapp'])
        self.assertTrue(con['url'].startswith('/shop/category/'), con['url'])
        # Todo lo publicado en Colchones, no solo el de esta prueba: con el catálogo instalado (dcasa_catalogo, como en
        # el CI) ya hay colchones publicados.
        publicados = self.env['product.template'].sudo().search([
            ('public_categ_ids', 'child_of', self.colchones.id), ('is_published', '=', True)])
        self.assertIn(self.colchon, publicados)
        publicados.is_published = False
        sin = tarjeta('Colchones')
        self.assertTrue(sin['whatsapp'])
        self.assertTrue(sin['url'].startswith('https://wa.me/50767575065?text='), sin['url'])
        self.assertIn('colchones', sin['url'])
        self.assertFalse(tarjeta('Salas')['whatsapp'], 'las que tienen productos siguen a su página')
        self.assertNotIn('imagen', tarjeta('Salas'), 'sin fotos de muebles')
        self.colchon.is_published = True
        self.assertFalse(tarjeta('Colchones')['whatsapp'], 'al publicar, vuelve sola a la tienda')

    def test_la_portada_ya_no_tiene_nada_de_muebles(self):
        """Marca de Baby Caleb (2026-11-19, docs/MARCA_BABY_CALEB.md › La web pública): fuera «Compra por espacio» con
        sus fotos, «Para dormir mejor», la sección «de cine» y toda foto de muebles, aunque haya algo publicado en las
        categorías de muebles de la copia de origen."""
        self.sofa.is_published = True
        portada = self.url_open('/').text
        for de_muebles in ('dcasa-cat-titulo', 'Compra por espacio', '¿Qué le hace falta a tu casa?',
                           'Para dormir mejor', 'o_dcasa_cine', 'o_dcasa_categorias', 'o_dcasa_galeria', 'img/cat-',
                           'img/insp-', 'img/split-', 'img/hero.webp', 'Recámaras y colchones'):
            self.assertNotIn(de_muebles, portada)
        for archivo in ('cat-salas.webp', 'cat-salas-400.webp', 'hero.webp', 'hero-800.webp', 'insp-3.webp',
                        'split-socios.webp', 'split-hoy.webp'):
            self.assertEqual(self.url_open(f'/website_dcasa/static/src/img/{archivo}').status_code, 404,
                             f'{archivo} (de muebles) ya no está en el módulo')

    def test_la_portada_en_el_orden_de_babycaleb(self):
        """El orden de Baby-caleb/src/pages/Home.tsx (docs/MARCA_BABY_CALEB.md): hero, sellos, educación, productos,
        las mamás, la cobertura, la banda final y las preguntas, con los textos de su web (content.json) tal cual."""
        portada = self.url_open('/').text
        piezas = [
            'Cuidado hipoalergénico para la piel de tu bebé',            # 1. hero
            'Piel sensible',                                              # 2. los sellos
            '¿Sabías que no es lo mismo',                                 # 3. educación
            'Lo más buscado',                                             # 4. productos
            'Lo que dicen nuestras mamás.',                               # 5. testimonios
            'Vendemos online y te lo llevamos.',                          # 6. cobertura
            'Dale a tu bebé el cuidado que su piel merece.',              # 7. banda final
            'Lo que más nos preguntan',                                   # 8. preguntas
        ]
        posiciones = [portada.index(pieza) for pieza in piezas]
        self.assertEqual(posiciones, sorted(posiciones), 'las secciones en el orden de su web')
        for texto in ('Pensamos en cada etapa de tu bebé', 'Pañales y wipes hipoalergénicos: sin químicos agresivos, '
                      'sin perfumes, sin alcohol, sin cloro.', 'Hipoalergénico', 'Sin cloro', 'Biodegradable',
                      '#QUENOTENEGAÑEN', 'Elizabeth M.', 'Mamá de 2', 'Cero alergias', 'Ana C.', 'Mamá primeriza',
                      'Talla correcta', 'Carla R.', 'Mamá de prematuro', 'Piel calmada',
                      'Desde que usamos Nateen, las irritaciones desaparecieron por completo. La talla XL fue un '
                      'salvavidas.', 'Ciudad de Panamá', 'Según zona', 'Interior / otras zonas', 'Cotizar por WhatsApp',
                      'Sin cloro · Sin perfumes'):
            self.assertIn(texto, portada)
        # «Cómo pedir» no promete lo que este sistema no hace: allá se paga con Yappy en la misma página; aquí el pago
        # y el envío se coordinan por WhatsApp.
        como_pedir = re.search(r'Cómo pedir</h3>\s*<p>(.*?)</p>', portada, re.S).group(1)
        self.assertIn('WhatsApp para coordinar el pago', ' '.join(como_pedir.split()))
        self.assertNotIn('en la misma página', como_pedir)
        # El CI (paso «El sitio responde con la marca Baby Caleb») pide esto mismo en producción.
        self.assertIn('Cuidado hipoalerg', portada)
        self.assertIn('babycalebpanama@gmail.com', portada)
        for de_dcasa in ("D'CASA", 'D&#39;CASA', 'dcasapty', '6026-1919', '60261919'):
            self.assertNotIn(de_dcasa, portada)

    def test_portada_muestra_productos_con_precio_y_agregar(self):
        html = self.url_open('/').text
        self.assertIn('Sofá de Prueba', html)
        self.assertRegex(html, r'123[.,]45')
        self.assertIn('action="/dcasa/carrito/agregar"', html)
        self.assertNotIn('MUEBLE SIN PUBLICAR', html)
        self.assertIn('Lo más buscado', html)

    def test_cifras_de_socios_salen_de_puntos_json(self):
        # Cifras de PRUEBA encima de puntos.json (dcasa_socios/tests/common.py): la banda las lee de ahí.
        from odoo.addons.dcasa_socios.tests.common import parche_de_reglas_de_prueba  # noqa: PLC0415
        with parche_de_reglas_de_prueba():
            reglas = self.website._dcasa_reglas_socios()
            html = self.url_open('/').text
        self.assertIn('{:,}'.format(reglas['referido']['puntosAlPadrino']), html)
        self.assertIn('{:,}'.format(reglas['referido']['puntosAlAhijado']), html)

    def test_con_puntos_json_de_fabrica_la_banda_no_dice_cifras(self):
        """Todo en PENDIENTE (2026-11-18): la banda de Socios no enseña ninguna cifra."""
        html = self.url_open('/').text
        banda = re.search(r'<section class="o_dcasa_socios_band".*?</section>', html, re.S)
        texto = re.sub(r'<[^>]+>', ' ', banda.group(0)) if banda else ''
        self.assertNotRegex(texto, r'\d', 'ninguna cifra en la banda')
        self.assertNotIn('por cada dólar', texto)

    def test_json_ld_tienda(self):
        html = self.url_open('/').text
        bloques = [json.loads(b) for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]
        datos = next((b for b in bloques if b.get('@type') == 'OnlineStore'), None)
        self.assertTrue(datos, 'La portada publica los datos de la tienda (en línea: Baby Caleb no tiene local)')
        self.assertEqual(datos['name'], 'Baby Caleb')
        self.assertEqual(datos['telephone'], '+507 6757-5065')
        self.assertEqual(datos['email'], 'babycalebpanama@gmail.com')
        self.assertEqual(datos['address'], {'@type': 'PostalAddress', 'addressCountry': 'PA'},
                         'Solo lo que la empresa tiene escrito: sin calle, ciudad ni provincia inventadas')
        for sin_local in ('geo', 'hasMap', 'image'):
            self.assertNotIn(sin_local, datos)
        self.assertNotIn('FurnitureStore', html)
        self.assertNotIn('OnlineStore', self.url_open('/shop').text, 'Solo en la portada')

    def test_seo_de_la_portada(self):
        html = self.url_open('/').text
        self.assertIn('Baby Caleb Panamá | Pañales y Wipes Nateen hipoalergénicos', html)
        self.assertIn('Tallas RN a XXL en caja para todo el mes', html)
        self.assertIn('name="description"', html)

    def test_agregar_al_carrito_en_un_clic(self):
        self.authenticate(None, None)
        home = self.url_open('/').text
        token = re.search(r'name="csrf_token" value=[\'"]([^\'"]+)', home).group(1)
        respuesta = self.url_open('/dcasa/carrito/agregar', data={
            'csrf_token': token, 'product_template_id': self.sofa.id,
        }, allow_redirects=False)
        self.assertIn(respuesta.status_code, (302, 303))
        self.assertTrue(respuesta.headers['Location'].endswith('/shop/cart'))
        carrito = self.url_open('/shop/cart').text
        self.assertIn('Sofá de Prueba', carrito)

    def test_agregar_producto_no_publicado_no_entra(self):
        self.authenticate(None, None)
        home = self.url_open('/').text
        token = re.search(r'name="csrf_token" value=[\'"]([^\'"]+)', home).group(1)
        respuesta = self.url_open('/dcasa/carrito/agregar', data={
            'csrf_token': token, 'product_template_id': self.oculto.id,
        }, allow_redirects=False)
        self.assertTrue(respuesta.headers['Location'].endswith('/shop'))
        self.assertNotIn('MUEBLE SIN PUBLICAR', self.url_open('/shop/cart').text)

    def test_ficha_de_producto_con_whatsapp_y_sellos(self):
        html = self.url_open(self.sofa.website_url).text
        self.assertIn('o_dcasa_sellos', html)
        # Formato título (F5).
        self.assertIn('Hola%20Baby%20Caleb%2C%20me%20interesa%3A%20Sof%C3%A1%20de%20Prueba', html)
        self.assertIn('Entrega a domicilio en Ciudad de Panamá.', html)
        self.assertIn('Asesoría directa y humana por WhatsApp', html)
        for sin_tienda in ('Míralo en tienda', 'Te lo llevas hoy', 'Libertadores', 'este mueble'):
            self.assertNotIn(sin_tienda, html)

    def test_ficha_sin_promesas_inventadas(self):
        html = self.url_open(self.sofa.website_url).text
        self.assertNotIn('30-day', html)
        self.assertNotIn('30 días', html)

    def test_tienda_con_descripcion_para_google(self):
        html = self.url_open('/shop').text
        self.assertIn('<meta name="description" content="Catálogo de Baby Caleb: pañales Nateen', html)

    def _token(self):
        self.authenticate(None, None)
        home = self.url_open('/').text
        return re.search(r'name="csrf_token" value=[\'"]([^\'"]+)', home).group(1)

    def _agregar(self, product_template_id, token=None):
        return self.url_open('/dcasa/carrito/agregar', data={
            'csrf_token': token or self._token(), 'product_template_id': product_template_id,
        }, allow_redirects=False)

    def test_agregar_sin_csrf_se_rechaza(self):
        self.authenticate(None, None)
        respuesta = self.url_open('/dcasa/carrito/agregar', data={'product_template_id': self.sofa.id},
                                  allow_redirects=False)
        self.assertEqual(respuesta.status_code, 400)

    def test_agregar_id_invalido_va_a_la_tienda(self):
        respuesta = self._agregar('abc')
        self.assertTrue(respuesta.headers['Location'].endswith('/shop'))

    def test_producto_con_variantes_va_a_la_ficha(self):
        color = self.env['product.attribute'].create({
            'name': 'Color prueba',
            'value_ids': [(0, 0, {'name': 'Gris'}), (0, 0, {'name': 'Azul'})],
        })
        self.sofa.attribute_line_ids = [(0, 0, {
            'attribute_id': color.id, 'value_ids': [(6, 0, color.value_ids.ids)],
        })]
        respuesta = self._agregar(self.sofa.id)
        self.assertIn(self.sofa.website_url, respuesta.headers['Location'])
        # v3 (2026-11-15): el mismo ícono del carrito, que lleva a la ficha y lo dice a los lectores de pantalla.
        self.assertIn('Elegir medida o color de', self.url_open('/').text, 'Con variantes la tarjeta lleva a la ficha')

    def test_precio_cero_bloqueado_no_se_agrega(self):
        self.website.prevent_zero_price_sale = True
        gratis = self.env['product.template'].create({
            'name': 'MUEBLE A CONSULTAR', 'list_price': 0.0, 'is_published': True, 'website_sequence': -102,
        })
        respuesta = self._agregar(gratis.id)
        self.assertIn(gratis.website_url, respuesta.headers['Location'])
        self.assertNotIn('MUEBLE A CONSULTAR', self.url_open('/shop/cart').text)

    def test_whatsapp_redirige_al_numero_configurado(self):
        self.website.dcasa_whatsapp_number = '+507 6757-5065'
        respuesta = self.url_open('/whatsapp?texto=Hola', allow_redirects=False)
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta.headers['Location'].startswith('https://wa.me/50767575065?text=Hola'))
        self.website.dcasa_whatsapp_number = False
        self.website.company_id.phone = False
        respuesta = self.url_open('/whatsapp', allow_redirects=False)
        self.assertTrue(respuesta.headers['Location'].endswith('/contactus'))

    def test_json_ld_no_cierra_el_script(self):
        self.website.company_id.name = 'D\'CASA </script><script>alert(1)</script>'
        texto = str(self.website._dcasa_json_ld().__html__())  # lo que QWeb imprime en <script>
        self.assertNotIn('<', texto)
        self.assertEqual(json.loads(texto)['name'], self.website.company_id.name)
        self.assertNotIn('priceRange', texto, 'Sin cifras inventadas')


@tagged('post_install', '-at_install')
class TestMarcaYMovimiento(HttpCase):
    """Sin marca de Odoo, hero sin placa, reseñas reales y animaciones."""

    def test_sin_credito_de_odoo(self):
        for ruta in ('/', '/shop', '/socios'):
            html = self.url_open(ruta).text
            self.assertNotIn('o_brand_promotion', html, ruta)
            self.assertNotIn('utm_source=db', html, ruta)
            self.assertNotIn('Con la tecnología de', html, ruta)

    def test_favicon_de_dcasa(self):
        website = self.env.ref('website.default_website')
        # Odoo lo guarda convertido a .ico: basta con que ya no sea el de Odoo.
        with file_open('web/static/img/favicon.ico', 'rb') as archivo:
            self.assertNotEqual(base64.b64decode(website.favicon), archivo.read())
        self.assertTrue(website.favicon)

    def test_hero_crema_y_cabeceras_de_pagina_sin_foto(self):
        """El hero de babycaleb.com: crema, con el antetítulo en píldora; las páginas interiores, la misma cabecera
        crema, sin foto (la de antes era de muebles)."""
        html = self.url_open('/').text
        self.assertIn('o_dcasa_hero_texto', html)
        self.assertIn('o_dcasa_kicker_pildora', html)
        self.assertNotIn('o_dcasa_placa', html)
        self.assertNotIn('o_dcasa_kicker_light', html)
        for ruta in ('/socios', '/privacidad', '/web/login', '/visitanos', '/contactus'):
            pagina = self.url_open(ruta).text
            cabecera = re.search(r'<section class="o_dcasa_hero o_dcasa_hero_compacto[^"]*".*?</section>', pagina, re.S)
            self.assertTrue(cabecera, f'{ruta}: la cabecera de página de siempre')
            self.assertNotIn('<img', cabecera.group(0), f'{ruta}: la cabecera ya no lleva foto')
            self.assertIn('o_dcasa_kicker_pildora', cabecera.group(0))

    def test_sin_resenas_de_otra_empresa(self):
        """Baby Caleb (2026-11-18): todavía no hay ficha de Google suya en data/resenas.json; las de la tienda de origen
        se quitaron. Sin opiniones, la cinta de la portada no sale (y no se inventa ninguna)."""
        resenas = self.env.ref('website.default_website')._dcasa_resenas()
        self.assertEqual(resenas['opiniones'], [])
        html = self.url_open('/').text
        self.assertNotIn('Déjanos tu opinión en Google', html)
        self.assertNotIn('o_dcasa_resenas_pausa', html)

    def test_resenas_reales_de_google(self):
        """Con la copia de las reseñas de la ficha de Google (la que pegue la dueña en data/resenas.json), la cinta."""
        from odoo.addons.website_dcasa.models import website as modulo
        original = modulo._leer_resenas
        modulo._leer_resenas = lambda: {
            'ficha': 'https://share.google/ficha-de-prueba', 'puntuacion': 5.0, 'total': 4,
            'opiniones': [{'autor': f'Clienta {n}', 'estrellas': 5, 'cuando': 'Hace un mes', 'texto': 'Muy bien.'}
                          for n in range(1, 5)]}
        self.addCleanup(setattr, modulo, '_leer_resenas', original)
        resenas = self.env.ref('website.default_website')._dcasa_resenas()
        html = self.url_open('/').text
        self.assertIn(resenas['ficha'], html)
        self.assertIn('Déjanos tu opinión en Google', html)
        self.assertIn('o_dcasa_resenas_pausa', html, 'La cinta se puede pausar (WCAG 2.2.2)')
        for opinion in resenas['opiniones']:
            self.assertIn(opinion['autor'], html)
        self.assertGreater(resenas['copias'], 1)
        self.assertEqual(resenas['copias'] % 2, 0, 'El bucle sin salto necesita un número par de copias')
        self.assertGreaterEqual(len(resenas['opiniones']) * resenas['copias'] / 2, 8)

    def test_animaciones_cargan(self):
        html = self.url_open('/').text
        self.assertIn('data-anim-entrada', html)
        self.assertIn('data-titular', html)
        scripts = re.findall(r'src="([^"]*web\.assets_frontend[^"]*\.js)"', html)
        self.assertTrue(scripts)
        js = ''.join(self.url_open(src).text for src in scripts)
        self.assertIn('website_dcasa.revelar', js, 'Las animaciones son Interactions de Odoo')

    def test_menu_corto_con_catalogo(self):
        website = self.env.ref('website.default_website')
        nombres = website.menu_id.child_id.sorted('sequence').mapped('name')
        self.assertEqual(nombres, ['Catálogo', 'Socios Baby Caleb', 'Contacto'])
        self.assertEqual(website.menu_id.child_id[0].url, '/shop')
        catalogo = website.menu_id.child_id.filtered(lambda m: m.url == '/shop')
        self.assertEqual(catalogo.with_context(lang='es_419').name, 'Catálogo', 'No «Tienda» en español')
        contacto = website.menu_id.child_id.filtered(lambda m: m.name == 'Contacto')
        self.assertEqual(contacto.url, '/visitanos', 'El contacto (sin tienda que visitar) tiene su propia página')

    def test_navbar_liquido_y_franja_visitanos(self):
        html = self.url_open('/').text
        self.assertIn('o_no_autohide_menu', html, 'Las tres opciones del menú nunca se esconden en el «+»')
        self.assertIn('id="dcasa-liquido"', html)
        self.assertNotIn('o_dcasa_anuncios', html, 'sin la barra de anuncios encima de la pastilla')
        # En la portada, la cobertura (sin mapa), que lleva a la página de contacto.
        self.assertIn('id="visitanos"', html)
        self.assertIn('href="/visitanos"', html)
        self.assertNotIn('https://www.google.com/maps/embed?pb=', html)

    def test_pagina_visitanos(self):
        """Baby Caleb vende 100% en línea (decisión del dueño, 2026-11-18): en lugar de la dirección y el mapa, su
        cobertura, su horario y sus canales."""
        respuesta = self.url_open('/visitanos')
        self.assertEqual(respuesta.status_code, 200)
        html = respuesta.text
        self.assertIn('Venta 100% online con entrega a domicilio — Ciudad de Panamá', html)
        self.assertIn('Vendemos online y te lo llevamos.', html)
        self.assertRegex(html, r'<a [^>]*href="https://wa\.me/50767575065\?text=[^"]*"[^>]*>\+507 6757-5065 ')
        self.assertIn('href="mailto:babycalebpanama@gmail.com"', html)
        self.assertIn('href="https://www.instagram.com/babycalebpanama"', html)
        self.assertIn('Escríbenos por WhatsApp', html)
        self.assertIn('<meta property="og:title" content="Contacto | Baby Caleb"/>', html)
        for sin_tienda in ('data-dcasa-mapa', 'google.com/maps', '<iframe', 'destination=', 'Libertadores',
                           'La Chorrera', 'Local 4550', "D'CASA", 'D&#39;CASA', 'dcasapty', '6026'):
            self.assertNotIn(sin_tienda, html)
        datos = json.loads(self.env.ref('website.default_website')._dcasa_json_ld())
        self.assertNotIn('geo', datos, 'Sin local: sin coordenadas')

    def test_menu_visitanos_viejo_se_actualiza(self):
        """Un sitio con el menú viejo (ancla /#visitanos) queda con uno solo, a la página."""
        website = self.env.ref('website.default_website')
        website.menu_id.child_id.filtered(lambda m: m.url == '/visitanos').url = '/#visitanos'
        self.env['website']._dcasa_armar_menu_principal()
        urls = website.menu_id.child_id.mapped('url')
        self.assertIn('/visitanos', urls)
        self.assertNotIn('/#visitanos', urls)

    def test_armar_menu_respeta_lo_agregado(self):
        website = self.env.ref('website.default_website')
        propio = self.env['website.menu'].create({
            'name': 'Ofertas', 'url': '/ofertas', 'parent_id': website.menu_id.id, 'website_id': website.id,
        })
        self.env['website']._dcasa_armar_menu_principal()
        self.env['website']._dcasa_armar_menu_principal()
        urls = website.menu_id.child_id.mapped('url')
        self.assertIn('/ofertas', urls, 'El menú que agregó la dueña se queda')
        self.assertEqual(urls.count('/shop'), 1, 'Sin duplicados al volver a correr')
        self.assertTrue(propio.exists())

    def test_cabecera_sobre_el_hero(self):
        self.assertIn('o_header_overlay', self.url_open('/').text)
        self.assertIn('o_header_overlay', self.url_open('/socios').text)
        self.assertIn('o_header_overlay', self.url_open('/contactus').text)
        self.assertNotIn('o_header_overlay', self.url_open('/shop').text)

    def test_contacto_con_datos_reales(self):
        html = self.url_open('/contactus').text
        self.assertNotIn('Fake Buena Vista', html)
        self.assertNotIn('555-555-5556', html)
        self.assertIn('babycalebpanama@gmail.com', html)
        self.assertIn('Venta 100% online con entrega a domicilio — Ciudad de Panamá', html)
        self.assertNotIn('Libertadores', html)
        self.assertIn('href="/whatsapp"', html)

    def test_whatsapp_sin_boton_en_el_menu_y_con_la_cobertura(self):
        """Decisión de la dueña (2026-11-15): «Escríbenos» sale del menú. Con la marca de Baby Caleb (2026-11-19) la
        portada lleva su cobertura (S18Coverage.tsx): el WhatsApp de ventas, el horario y la zona; el correo, en el
        pie."""
        self.assertNotIn('btn_cta', self.url_open('/shop').text, 'el menú ya no lleva «Escríbenos»')
        portada = self.url_open('/').text
        seccion = re.search(r'<section id="visitanos".*?</section>', portada, re.S)
        self.assertTrue(seccion, 'la portada trae la cobertura')
        self.assertIn('https://wa.me/50767575065', seccion.group(0))
        self.assertIn('+507 6757-5065', seccion.group(0))
        self.assertIn('Venta 100% online con entrega a domicilio — Ciudad de Panamá', seccion.group(0))
        pie = re.search(r'<footer.*?</footer>', portada, re.S).group(0)
        self.assertRegex(pie, r'href="mailto:babycalebpanama@gmail\.com"')

    def test_cache_de_pagina_separa_tarifas(self):
        pagina = self.env.ref('website.homepage_page')
        pedido = type('Pedido', (), {})()
        pedido.website = self.env.ref('website.default_website')
        pedido.lang = self.env['res.lang']._lang_get('en_US')
        pedido.httprequest = type('H', (), {'path': '/'})()
        pedido.session = type('S', (), {'debug': ''})()
        tarifas = self.env['product.pricelist'].create([{'name': 'A'}, {'name': 'B'}])
        claves = []
        for tarifa in tarifas:
            pedido.pricelist = tarifa
            pedido.fiscal_position = self.env['account.fiscal.position']
            claves.append(pagina._get_cache_key(pedido))
        self.assertNotEqual(*claves)


@tagged('post_install', '-at_install')
class TestCarritoReglas(HttpCase):
    """«Agregar» de un clic con la tienda solo para usuarios registrados."""

    def test_tienda_solo_registrados_no_agrega(self):
        website = self.env.ref('website.default_website')
        website.ecommerce_access = 'logged_in'
        producto = self.env['product.template'].create({
            'name': 'MESA DE PRUEBA', 'list_price': 50.0, 'is_published': True,
        })
        self.authenticate(None, None)
        # Sin acceso a la tienda la portada no ofrece «Agregar»: el token sale de otro formulario.
        self.assertNotIn('action="/dcasa/carrito/agregar"', self.url_open('/').text)
        socios = self.url_open('/socios').text
        token = re.search(r'name="csrf_token" value=[\'"]([^\'"]+)', socios).group(1)
        respuesta = self.url_open('/dcasa/carrito/agregar', data={
            'csrf_token': token, 'product_template_id': producto.id,
        }, allow_redirects=False)
        self.assertNotIn('/shop/cart', respuesta.headers.get('Location', ''))


@tagged('post_install', '-at_install')
class TestResenasRobustas(TransactionCase):

    def test_json_incompleto_no_tumba_la_portada(self):
        from odoo.addons.website_dcasa.models import website as modulo
        website = self.env.ref('website.default_website')
        original = modulo._leer_resenas
        try:
            modulo._leer_resenas = lambda: {'ficha': 'https://x', 'puntuacion': None,
                                            'opiniones': [{'autor': 'A', 'texto': 'Bien', 'estrellas': 5}]}
            self.assertEqual(website._dcasa_resenas()['copias'], 1)
            modulo._leer_resenas = lambda: {'opiniones': [{'texto': 'sin autor'}]}
            self.assertEqual(website._dcasa_resenas()['opiniones'], [])
        finally:
            modulo._leer_resenas = original


# Lo que ningún visitante debe leer en las páginas de este módulo (encargo del 2026-11-19): ni la marca de la tienda de
# origen ni nada de muebles. Se mira el texto visible y lo que también se lee o se oye: alt, title, aria-label,
# placeholder y las etiquetas <meta> (Google y las redes).
RESTOS_DE_DCASA = re.compile(r"D'CASA|D&#39;CASA|D&apos;CASA|D’CASA|dcasapty|mueble|colch[oó]n|La Chorrera", re.I)


def _lo_que_se_ve(html):
    sin_codigo = re.sub(r'<script.*?</script>|<style.*?</style>|<!--.*?-->', ' ', html, flags=re.S)
    textos = re.sub(r'<[^>]+>', ' ', sin_codigo)
    atributos = re.findall(r'\b(?:alt|title|aria-label|placeholder)="([^"]*)"', sin_codigo)
    metas = re.findall(r'<meta[^>]*\bcontent="([^"]*)"', sin_codigo)
    return ' '.join([textos, *atributos, *metas])


@tagged('post_install', '-at_install')
class TestSinRestosDeDcasa(HttpCase):
    """Ni «D'CASA» ni nada de muebles en lo que se ve del sitio (los textos legales van palabra por palabra y los dicta
    el dueño: no se miran aquí; /socios es de dcasa_socios)."""

    def setUp(self):
        super().setUp()
        self.website = self.env.ref('website.default_website')
        self.producto = self.env['product.template'].create({
            'name': 'Pañal de la prueba de restos', 'list_price': 45.0, 'is_published': True,
            'dcasa_black_weekend': True})

    def test_ninguna_pagina_dice_dcasa_ni_muebles(self):
        from odoo.addons.website_dcasa.models.black_weekend import PARAM_ACTIVO, PARAM_FIN, PARAM_INICIO
        param = self.env['ir.config_parameter'].sudo()
        param.set_param(PARAM_ACTIVO, '1')
        param.set_param(PARAM_INICIO, '')
        param.set_param(PARAM_FIN, '')
        for ruta in ('/', '/shop', self.producto.website_url, '/visitanos', '/contactus', '/web/login',
                     '/promociones', '/shop/cart', '/shop?search=zzzz', '/esta-pagina-no-existe'):
            with self.subTest(ruta=ruta):
                respuesta = self.url_open(ruta)
                self.assertIn(respuesta.status_code, (200, 404))
                encontrado = RESTOS_DE_DCASA.findall(_lo_que_se_ve(respuesta.text))
                self.assertEqual(encontrado, [], ruta)

    def test_el_checkout_no_dice_el_lugar_ni_muebles(self):
        """Las entregas y el mensaje del pago en la tienda: lo que el cliente lee al pagar."""
        entregas = self.env['delivery.carrier'].sudo().search([('is_published', '=', True)])
        for nombre in entregas.mapped('name'):
            self.assertNotRegex(nombre, RESTOS_DE_DCASA)
        self.assertIn('Retiro en tienda', entregas.mapped('name'))
        cod = self.env.ref('delivery.payment_provider_cod').sudo()
        self.assertNotRegex(str(cod.with_context(lang='es_419').pending_msg), RESTOS_DE_DCASA)
        mensaje = str(cod.with_context(lang='es_419').pending_msg)
        self.assertIn('El pedido se entrega cuando está pagado completo', mensaje)

    def test_una_base_ya_instalada_queda_al_dia_al_actualizar(self):
        """El menú se arma una vez al instalar y las entregas y los pagos también: en una base que ya existía (staging)
        la migración 19.0.1.19.0 los pone al día. Aquí se simula esa base vieja y se corre lo que corre la migración."""
        idiomas = [codigo for codigo, _n in self.env['res.lang'].get_installed()]
        socios = self.website.menu_id.child_id.filtered(lambda m: m.url == '/socios')
        socios.update_field_translations('name', dict.fromkeys(idiomas, "Socios D'CASA"))
        Carrier = self.env['delivery.carrier'].sudo().with_context(active_test=False)
        retiro = Carrier.search([('name', '=', 'Retiro en tienda')])
        retiro.update_field_translations('name', dict.fromkeys(idiomas, 'Retiro en tienda (La Chorrera)'))
        cod = self.env.ref('delivery.payment_provider_cod').sudo()
        for idioma in idiomas:
            cod.with_context(lang=idioma).pending_msg = Markup(
                '<p>Te lo apartamos por la página web. El mueble se entrega cuando está pagado completo.</p>')
        self.assertIn("Socios D&#39;CASA", self.url_open('/shop').text, 'la base vieja')

        self.env['website']._dcasa_sin_restos_de_dcasa()
        self.env['website']._dcasa_sin_restos_de_dcasa()   # se puede volver a correr

        for idioma in idiomas:
            with self.subTest(idioma=idioma):
                self.assertEqual(socios.with_context(lang=idioma).name, 'Socios Baby Caleb')
                self.assertEqual(retiro.with_context(lang=idioma).name, 'Retiro en tienda')
                self.assertIn('El pedido se entrega', str(cod.with_context(lang=idioma).pending_msg))
        self.assertEqual(Carrier.search_count([('name', 'ilike', 'Retiro en tienda')]), 1, 'sin duplicar la entrega')
        cabecera = re.search(r'<header id="top".*?</header>', self.url_open('/shop').text, re.S).group(0)
        self.assertNotRegex(cabecera, RESTOS_DE_DCASA)
        self.assertIn('<span>Socios Baby Caleb</span>', cabecera)
        # La migración llama justo a esto.
        with file_open('website_dcasa/migrations/19.0.1.19.0/post-migrate.py') as archivo:
            self.assertIn('_dcasa_sin_restos_de_dcasa()', archivo.read())
