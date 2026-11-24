"""Lo que encontró la auditoría de la web (axe-core, WCAG 2.2 AA, 2026-11-24) en lo que dibuja la tienda de Odoo, y que
arreglan views/accesibilidad_templates.xml y la sección «Auditoría» de dcasa.scss: nombres para el lector de pantalla,
roles válidos, un h1 por página, títulos en orden y todo lo que se toca a 44 px."""
import re

from lxml import etree

from odoo.tests import HttpCase, tagged


def _arco(env, xmlid):
    return etree.tostring(env.ref(xmlid)._get_combined_arch(), encoding='unicode')


@tagged('post_install', '-at_install')
class TestAccesibilidadTienda(HttpCase):

    def test_iconos_de_adorno_sin_role_img_sin_nombre(self):
        """Íconos con role="img" y sin nombre (axe: role-img-alt, «serious»): fuera del árbol de accesibilidad."""
        for xmlid, icono in (('website_sale.products', 'oi-settings-adjust'),
                             ('website_sale.product', 'oi-chevron-left'),
                             ('website_sale.checkout_layout', 'fa-angle-right')):
            with self.subTest(vista=xmlid):
                arco = _arco(self.env, xmlid)
                for etiqueta in re.findall(rf'<i [^>]*{icono}[^>]*>', arco):
                    if 'aria-label' in etiqueta:
                        continue
                    self.assertNotIn('role="img"', etiqueta)
                    self.assertIn('aria-hidden="true"', etiqueta)

    def test_tarjeta_de_la_tienda_sin_rol_invalido(self):
        """Un <form> no admite role="article" (axe: aria-allowed-role); su nombre se queda."""
        arco = _arco(self.env, 'website_sale.products_item')
        formulario = re.search(r'<form [^>]*oe_product_cart[^>]*>', arco).group(0)
        self.assertNotIn('role="article"', formulario)
        self.assertIn('aria-label', formulario, 'el nombre lo cambia tarjeta_nombre_cliente')

    def test_casillas_escondidas_de_la_tira_de_categorias(self):
        arco = _arco(self.env, 'website_sale.filmstrip_categories')
        for casilla in re.findall(r'<input [^>]*btn-check[^>]*>', arco):
            self.assertIn('aria-hidden="true"', casilla)

    def test_titulo_de_las_tallas_de_nivel_dos(self):
        """«Talla» es un h6 justo debajo del h1 del producto: para el lector, de nivel 2 (axe: heading-order)."""
        arco = _arco(self.env, 'website_sale.variants')
        self.assertRegex(arco, r'<h6 [^>]*attribute_name[^>]*aria-level="2"|<h6 [^>]*aria-level="2"[^>]*attribute_name')

    def test_rango_de_precio_con_nombre(self):
        arco = _arco(self.env, 'website_sale.filter_products_price')
        rangos = re.findall(r'<input [^>]*type="range"[^>]*>', arco)
        self.assertEqual(len(rangos), 2)
        for rango in rangos:
            self.assertIn('aria-label="Rango de precio"', rango)

    def test_carrito_y_pago_con_h1_titulos_en_orden_y_cantidad_con_nombre(self):
        layout = _arco(self.env, 'website_sale.checkout_layout')
        self.assertIn('<h1 class="visually-hidden"', layout, 'un h1 en el carrito y en cada paso del pago')
        self.assertIn("'Tu carrito' if request.httprequest.path.startswith('/shop/cart') else 'Tu pedido'", layout)
        self.assertRegex(_arco(self.env, 'website_sale.cart'), r'<h4 [^>]*aria-level="2"')
        self.assertIn('aria-level="3"', _arco(self.env, 'website_sale.cart_lines'), 'el nombre de cada producto')
        self.assertRegex(_arco(self.env, 'website_sale.cart_lines_price'),
                         r'<h6 [^>]*role="none"', 'el precio no es un título')
        self.assertRegex(_arco(self.env, 'website_sale.address'), r'<h4 [^>]*aria-level="2"')
        cantidades = re.findall(r'<input [^>]*js_quantity[^>]*>', _arco(self.env, 'website_sale.cart_lines_quantity'))
        self.assertEqual(len(cantidades), 2)
        for cantidad in cantidades:
            self.assertIn('aria-label="Cantidad"', cantidad)

    def test_lo_que_se_toca_mide_44_px(self):
        """Las reglas de la auditoría están en el CSS del sitio: el menú, las tallas en pastilla, la cantidad, el pago y
        los íconos de lucide del mismo tamaño."""
        html = self.url_open('/').text
        css_url = re.search(r'href="([^"]*web\.assets_frontend[^"]*\.css)"', html).group(1)
        css = re.sub(r'\s+', ' ', self.url_open(css_url).text)
        for regla in (r'#top_menu \.nav-link\s*\{[^}]*min-height: ?2\.75rem',
                      r'\.o_wsale_product_attribute\s*>\s*\.js_attribute_value\s*>\s*'
                      r'label\.col-form-label \.form-check\s*\{[^}]*min-height: ?2\.75rem',
                      r'\.css_quantity \.btn[^{]*\{[^}]*min-width: ?2\.75rem',
                      r'\.o_website_sale_checkout_container \.btn:not\(\.btn-close\)[^{]*\{[^}]*min-height: ?2\.75rem',
                      r'\.o_dcasa_icono\s*\{[^}]*width: ?1\.5rem[^}]*height: ?1\.5rem'):
            with self.subTest(regla=regla):
                self.assertRegex(css, regla)
        # La talla elegida: relleno verde con borde verde de bordes (nunca el naranja de texto).
        self.assertRegex(css, r'(?i):has\(\.form-check-input:checked\) \.form-check\s*\{[^}]*background:\s*#91c9a2',
                         'la talla elegida, en verde salvia')
