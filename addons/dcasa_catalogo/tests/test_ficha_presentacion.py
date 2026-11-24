"""El bloque «Presentación» de la ficha, con la marca Baby Caleb (docs/MARCA_BABY_CALEB.md), medido en Chrome como
teléfono con la ficha de verdad de los Pañales Nateen (una presentación por talla, del catálogo del dueño).

Estaba roto (2026-11-19): era una rejilla de dos columnas y, con varias presentaciones, el antetítulo y cada línea se
repartían entre las dos (una angostísima, «Caja L — 15 a 39 lb» palabra por palabra); en el celular la ficha medía
607 px de ancho a 390. Ahora es una tarjeta `surface` con su filo y radio de 16 px, el antetítulo en el naranja de texto
y una línea por renglón, a todo el ancho."""
from odoo.addons.website_dcasa.tests.chrome_movil import ChromeMovilCase
from odoo.tests import tagged

MEDIR = """
    (async () => {
        const esperar = (ms) => new Promise((ok) => setTimeout(ok, ms));
        for (let i = 0; i < 200 && document.body.getAttribute('is-ready') !== 'true'; i++) { await esperar(50); }
        await esperar(300);
        const dl = document.querySelector('.o_dcasa_ficha_datos');
        const e = getComputedStyle(dl);
        const caja = dl.getBoundingClientRect();
        const interior = caja.width - parseFloat(e.paddingLeft) - parseFloat(e.paddingRight)
            - parseFloat(e.borderLeftWidth) - parseFloat(e.borderRightWidth);
        const dt = [...dl.querySelectorAll('dt')].find((d) => d.textContent.trim() === 'Presentación');
        const anchos = [];
        for (let y = 0; y <= document.body.scrollHeight; y += 400) {
            window.scrollTo(0, y);
            await esperar(30);
            anchos.push(document.documentElement.scrollWidth);
        }
        const vecina = document.querySelector('.o_wsale_product_details_content_section_price').getBoundingClientRect();
        return {
            pantalla: innerWidth, pagina: Math.max(...anchos), vecina: vecina.right,
            caja: { izquierda: caja.left, derecha: caja.right, interior },
            fondo: e.backgroundColor, radio: e.borderTopLeftRadius,
            filo: [e.borderLeftWidth, e.borderLeftColor, e.borderTopColor],
            antetitulo: dt ? [getComputedStyle(dt).color, getComputedStyle(dt).textTransform] : null,
            letra: e.fontFamily.split(',')[0],
            lineas: [...dl.querySelectorAll('dd.o_dcasa_presentacion')].map((d) => {
                const r = d.getBoundingClientRect();
                return [d.textContent.trim(), r.left, r.width];
            }),
        };
    })()
"""


@tagged('post_install', '-at_install')
class TestFichaConPresentacionesEnElCelular(ChromeMovilCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        variante = cls.env['product.product'].search([('default_code', '=', 'NAT-M')])
        cls.panales = variante.product_tmpl_id
        cls.panales.is_published = True

    def test_una_tarjeta_de_la_marca_a_todo_el_ancho_y_nada_se_sale(self):
        presentaciones = self.panales._dcasa_presentaciones()
        self.assertGreaterEqual(len(presentaciones), 3, 'la ficha de verdad, con una presentación por talla')
        for ancho in (360, 390):
            with self.subTest(ancho=ancho), self._chrome_movil(ancho) as browser:
                browser.navigate_to(self.base_url() + self.panales.website_url, wait_stop=True)
                self.assertTrue(browser._wait_ready())
                m = self._evaluar(browser, MEDIR)
                self.assertEqual(m['pantalla'], ancho)
                self.assertLessEqual(m['pagina'], ancho, 'la ficha no se sale de lado')
                self.assertGreaterEqual(m['caja']['izquierda'], 0)
                self.assertLessEqual(m['caja']['derecha'], ancho)
                self.assertLessEqual(m['caja']['derecha'], m['vecina'] + 1, 'alineada con las secciones de la ficha')
                # La tarjeta de la marca: surface, el filo `line` (no el borde azul de D'CASA) y radio de 16 px.
                self.assertEqual(m['fondo'], 'rgb(242, 239, 229)')
                self.assertEqual(m['radio'], '16px')
                self.assertEqual(m['filo'], ['1px', 'rgba(27, 50, 70, 0.12)', 'rgba(27, 50, 70, 0.12)'])
                self.assertEqual(m['antetitulo'], ['rgb(152, 93, 47)', 'uppercase'], 'antetítulo en accent-strong')
                self.assertEqual(m['letra'], 'Montserrat')
                # Una línea por renglón, todas a todo el ancho de la tarjeta (nada de dos columnas).
                self.assertEqual(len(m['lineas']), len(presentaciones))
                izquierdas = {round(izquierda) for _texto, izquierda, _ancho in m['lineas']}
                self.assertEqual(len(izquierdas), 1, 'todas empiezan en el mismo borde: una sola columna')
                for texto, _izquierda, ancho_linea in m['lineas']:
                    self.assertAlmostEqual(ancho_linea, m['caja']['interior'], delta=1.5, msg=texto)
