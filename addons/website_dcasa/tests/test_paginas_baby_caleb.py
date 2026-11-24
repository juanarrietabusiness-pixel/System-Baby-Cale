"""Las páginas de babycaleb.com en el sitio de Odoo (pedido del dueño, 2026-11-24: «tal cual»): Beneficios, Historia,
Tips, Cómo comprar y FAQ, con sus textos (content.json) y sus títulos (src/seo/rutas.ts), y la tarjetita del hero con el
precio leído de Odoo. Lo que este sistema hace distinto (el pago se elige al pedir; el envío se cotiza por WhatsApp) no
se promete como en su web."""
import json
import re

from odoo.tests import HttpCase, tagged

PAGINAS = {
    '/beneficios': ('Beneficios | Pañales hipoalergénicos Nateen — Baby Caleb Panamá',
                    'Beneficios de los pañales hipoalergénicos Nateen',
                    ('Más allá de un pañal, un servicio pensado para ti.', 'Cajas para todo el mes',
                     'De recién nacido a XXL', 'Atención personal', 'Delivery a domicilio',
                     'Lo que dicen nuestras mamás.')),
    '/historia': ('Nuestra historia | Baby Caleb Panamá', 'Nuestra historia',
                  ('Cuidamos a los que más amas', 'Baby Caleb nació en 2024 en Panamá',
                   '«En Baby Caleb Panamá pensamos en cada etapa de tu bebé.»', 'tallas, de RN a XXL',
                   'Piel sensible', '¿Sabías que no es lo mismo')),
    '/tips': ('Tips y cuidado de la piel del bebé | Baby Caleb Panamá', 'Tips para cuidar la piel de tu bebé',
              ('Cuidar la piel de tu bebé, mejor informada.', 'Tips para evitar la pañalitis',
               'La piel avisa antes de quejarse', 'Cuándo consultar al pediatra', 'Tip 06')),
    '/como-comprar': ('Cómo comprar | Baby Caleb Panamá', 'Cómo comprar en Baby Caleb',
                      ('Simple, directo y sin complicaciones.', 'Paso 01', 'Paso 02', 'Paso 03',
                       'Vendemos online y te lo llevamos.')),
    '/faq': ('Preguntas frecuentes | Baby Caleb Panamá', 'Preguntas frecuentes',
             ('Resolvemos tus dudas.', '¿Cómo sé qué talla necesita mi bebé?', '¿Tienen talla XXL?',
              '¿Los pañales son biodegradables?')),
}
TIPS = ('tip-panalitis', 'tip-cloro', 'tip-senales-piel', 'tip-quien-se-beneficia', 'tip-wipes-caja', 'tip-pediatra')
DE_DCASA = ("D'CASA", 'D&#39;CASA', 'dcasapty', '6026-1919', 'La Chorrera', 'mueble')


@tagged('post_install', '-at_install')
class TestPaginasBabyCaleb(HttpCase):

    def test_cada_pagina_con_su_titulo_su_texto_y_la_banda_final(self):
        for ruta, (titulo, h1, textos) in PAGINAS.items():
            with self.subTest(ruta=ruta):
                respuesta = self.url_open(ruta)
                self.assertEqual(respuesta.status_code, 200)
                html = respuesta.text
                self.assertIn(f'<title>{titulo}</title>', html)
                self.assertRegex(html, r'<meta name="description" content="[^"]{60,}"', 'con su descripción')
                # Un solo h1, para el lector de pantalla y los buscadores (su web: <h1 className="sr-only">).
                self.assertEqual(html.count('<h1'), 1, 'un solo h1')
                self.assertRegex(html, rf'<h1 class="visually-hidden">{re.escape(h1)}</h1>')
                for texto in textos:
                    self.assertIn(texto, html)
                self.assertIn('Dale a tu bebé el cuidado que su piel merece.', html, 'cierra con la banda final')
                for de_dcasa in DE_DCASA:
                    self.assertNotIn(de_dcasa, html)

    def test_no_promete_pagar_en_la_misma_pagina(self):
        """Su web dice «paga con Yappy en la misma página» y «eliges tu zona al pagar»; aquí el pago se elige al pedir
        (Yappy o transferencia) y el costo del envío se confirma por WhatsApp."""
        for ruta in ('/beneficios', '/como-comprar', '/faq'):
            with self.subTest(ruta=ruta):
                texto = ' '.join(re.sub(r'<[^>]+>', ' ', self.url_open(ruta).text).split())
                self.assertNotIn('en la misma página', texto)
                self.assertNotIn('Eliges tu zona al pagar', texto)
                self.assertNotIn('pagas en la página', texto)
        comprar = ' '.join(re.sub(r'<[^>]+>', ' ', self.url_open('/como-comprar').text).split())
        self.assertIn('eliges si pagas con Yappy o por transferencia', comprar)
        self.assertIn('te lo confirmamos por WhatsApp antes de cobrar', comprar)

    def test_faq_para_google_con_las_mismas_preguntas(self):
        html = self.url_open('/faq').text
        bloques = [json.loads(b) for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]
        faq = next((b for b in bloques if b.get('@type') == 'FAQPage'), None)
        self.assertTrue(faq, 'FAQPage en /faq (src/pages/FAQ.tsx)')
        preguntas = [p['name'] for p in faq['mainEntity']]
        self.assertEqual(len(preguntas), 8)
        for pregunta in preguntas:
            self.assertIn(pregunta, html, 'la misma pregunta en la página')
        tienda = next(p for p in faq['mainEntity'] if p['name'] == '¿Tienen tienda física?')
        self.assertIn('pagas con Yappy o por transferencia', tienda['acceptedAnswer']['text'])
        # Se abren con el teclado y sin JavaScript: <details>/<summary>.
        self.assertEqual(html.count('<details class="o_dcasa_pregunta"'), 8)
        self.assertNotIn('FAQPage', self.url_open('/').text, 'solo en /faq')

    def test_fotos_de_los_tips_existen_y_no_saltan(self):
        html = self.url_open('/tips').text
        for tip in TIPS:
            with self.subTest(tip=tip):
                for ancho in (480, 720):
                    foto_url = f'/website_dcasa/static/src/img/{tip}-{ancho}.webp'
                    self.assertEqual(self.url_open(foto_url).status_code, 200)
                foto = re.search(rf'<img[^>]*{tip}-720\.webp[^>]*>', html).group(0)
                self.assertIn('width="720"', foto)
                self.assertIn('height="900"', foto, '4:5, sin salto al cargar')
                self.assertRegex(foto, r'alt="[^"]+"')

    def test_el_menu_y_el_pie_llevan_a_las_paginas(self):
        html = self.url_open('/').text
        cabecera = re.search(r'<header id="top".*?</header>', html, re.S).group(0)
        pie = re.search(r'<div id="footer".*?o_dcasa_pie_legales', html, re.S).group(0)
        for ruta in ('/shop', *PAGINAS):
            self.assertIn(f'href="{ruta}"', cabecera, f'{ruta} en el menú')
            self.assertIn(f'href="{ruta}"', pie, f'{ruta} en el pie')


@tagged('post_install', '-at_install')
class TestTarjetaDelHero(HttpCase):
    """La tarjetita de su hero (S02Hero.tsx): «Desde talla RN · Pañal Nateen · Desde $…», con el menor precio de los
    Nateen de cierre publicados. Ni los Pants (NAT-P-…) ni lo que no está publicado cuentan."""

    def _producto(self, nombre, precio, codigo, publicado=True):
        plantilla = self.env['product.template'].create({
            'name': nombre, 'list_price': precio, 'sale_ok': True, 'is_published': publicado, 'type': 'consu',
        })
        plantilla.product_variant_id.default_code = codigo
        return plantilla

    def test_desde_el_menor_precio_de_los_nateen_de_cierre(self):
        self._producto('Pañal de prueba RN', 50, 'NAT-RN')
        self._producto('Pañal de prueba L', 45, 'NAT-L')
        self._producto('Pañal Pants de prueba', 30, 'NAT-P-L')
        self._producto('Pañal sin publicar', 10, 'NAT-S', publicado=False)
        tarjeta = self.env.ref('website.default_website')._dcasa_hero_tarjeta()
        self.assertTrue(tarjeta)
        self.assertEqual(tarjeta['desde'], 45)
        html = self.url_open('/').text
        bloque = re.search(r'<a [^>]*class="o_dcasa_hero_tarjeta".*?</a>', html, re.S)
        self.assertTrue(bloque, 'la tarjeta sale en la portada')
        self.assertIn('Desde talla RN', bloque.group(0))
        self.assertIn('Pañal Nateen', bloque.group(0))
        self.assertRegex(bloque.group(0), r'45\.00')
        self.assertRegex(bloque.group(0), r'href="/shop/[^"]+"', 'lleva a la ficha')

    def test_sin_nateen_publicado_no_sale(self):
        self.env['product.product'].sudo().search([('default_code', '=like', 'NAT-%')]).product_tmpl_id.write(
            {'is_published': False})
        self.assertFalse(self.env.ref('website.default_website')._dcasa_hero_tarjeta())
        self.assertNotIn('o_dcasa_hero_tarjeta"', self.url_open('/').text)
