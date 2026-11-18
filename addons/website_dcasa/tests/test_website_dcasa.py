import base64
import json
import re

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
        salas = self.env.ref('website_dcasa.public_category_salas')
        # Con algo publicado, la tarjeta lleva a su categoría (sin nada, abre WhatsApp: TestPortadaDinamica).
        self.env['product.template'].create({'name': 'SOFÁ PUBLICADO', 'list_price': 10.0, 'is_published': True,
                                             'public_categ_ids': [(6, 0, salas.ids)]})
        # Con «Brian de la tienda» (dcasa_brian_tienda) encendido, la burbuja flotante es la suya: aquí se prueba la de
        # WhatsApp, la que sale con Brian apagado o sin ese módulo.
        self.env['ir.config_parameter'].sudo().set_param('dcasa_brian_tienda.activo', 'False')
        response = self.url_open('/')
        self.assertEqual(response.status_code, 200)
        html = response.text
        self.assertIn('Cuidado hipoalergénico para la piel de tu bebé', html)
        self.assertIn('https://wa.me/50767575065', html)
        self.assertIn('o_dcasa_wa_float', html)
        self.assertIn(f"/shop/category/{self.env['ir.http']._slug(salas)}", html)
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
        html = self.url_open('/').text
        css_links = re.findall(r'href="([^"]*web\.assets_frontend[^"]*\.css)"', html)
        self.assertTrue(css_links, 'La página debe enlazar el bundle CSS del sitio')
        css = self.url_open(css_links[0]).text
        self.assertIn('o_dcasa_pcard', css)
        self.assertIn('o_dcasa_hero_texto', css)
        self.assertIn('o_dcasa_wa_float', css)
        self.assertRegex(css.lower(), r'#1340b1|rgb\(19,\s*64,\s*177\)')


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
        los colchones. Sin nada publicado, la tarjeta abre WhatsApp; con algo publicado, su página de la tienda."""
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
        portada = self.url_open('/').text
        self.assertIn('Colchones: pregúntanos por WhatsApp', portada)
        self.assertIn('Pregúntanos por WhatsApp', portada)   # v3: la nota debajo del nombre (antes «· por WhatsApp»)
        self.colchon.is_published = True
        self.assertFalse(tarjeta('Colchones')['whatsapp'], 'al publicar, vuelve sola a la tienda')

    def test_sin_nada_publicado_en_ninguna_categoria_no_sale_compra_por_espacio(self):
        """Baby Caleb (2026-11-18): las categorías de la portada son las de muebles de la copia de origen y su catálogo
        no tiene nada en ellas. Seis tarjetas que solo llevan a WhatsApp no ayudan a comprar: la sección no sale. Con
        una sola categoría con algo, vuelve entera (las vacías, a WhatsApp, como antes)."""
        claves = [f'website_dcasa.public_category_{clave}' for clave in
                  ('salas', 'recamaras', 'colchones', 'zapateras', 'organizacion', 'oficina')]
        categorias = self.env['product.public.category'].browse([self.env.ref(x).id for x in claves])
        publicados = self.env['product.template'].sudo().search([
            ('public_categ_ids', 'child_of', categorias.ids), ('is_published', '=', True)])
        publicados.is_published = False
        self.assertEqual(self.website._dcasa_categorias_con_productos(), [])
        portada = self.url_open('/').text
        self.assertNotIn('dcasa-cat-titulo', portada)
        self.assertNotIn('pregúntanos por WhatsApp', portada)
        self.sofa.is_published = True
        # (La portada ya quedó guardada en la memoria de páginas de Odoo para el visitante: se mira el dato.)
        self.assertEqual(len(self.website._dcasa_categorias_con_productos()), 6)

    def test_portada_muestra_productos_con_precio_y_agregar(self):
        html = self.url_open('/').text
        self.assertIn('Sofá de Prueba', html)
        self.assertRegex(html, r'123[.,]45')
        self.assertIn('action="/dcasa/carrito/agregar"', html)
        self.assertNotIn('MUEBLE SIN PUBLICAR', html)
        self.assertIn('Lo más buscado', html)
        self.assertIn('Para dormir mejor', html)

    def test_cifras_de_socios_salen_de_puntos_json(self):
        reglas = self.website._dcasa_reglas_socios()
        html = self.url_open('/').text
        self.assertIn('{:,}'.format(reglas['referido']['puntosAlPadrino']), html)
        self.assertIn('{:,}'.format(reglas['referido']['puntosAlAhijado']), html)

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

    def test_hero_sin_placa_con_texto_blanco(self):
        html = self.url_open('/').text
        self.assertIn('o_dcasa_hero_texto', html)
        self.assertNotIn('o_dcasa_placa', html)
        socios = self.url_open('/socios').text
        self.assertIn('o_dcasa_hero_compacto', socios, 'Las páginas interiores usan el mismo hero')

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
        # En la portada solo una franja corta, sin mapa, que lleva a la página.
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

    def test_whatsapp_sin_boton_en_el_menu_y_con_la_seccion_de_contacto(self):
        """Decisión de la dueña (2026-11-15): «Escríbenos» sale del menú; la portada lleva una sección pequeña que
        invita a escribir por WhatsApp o por correo, antes de Visítanos."""
        self.assertNotIn('btn_cta', self.url_open('/shop').text, 'el menú ya no lleva «Escríbenos»')
        portada = self.url_open('/').text
        seccion = re.search(r'<section class="o_dcasa_contacto_cta".*?</section>', portada, re.S)
        self.assertTrue(seccion, 'la portada trae la sección de contacto')
        self.assertIn('href="/whatsapp"', seccion.group(0))
        self.assertRegex(seccion.group(0), r'href="mailto:[^"]+@[^"]+"')
        self.assertLess(portada.index('o_dcasa_contacto_cta'), portada.index('id="visitanos"'), 'antes de Visítanos')

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
