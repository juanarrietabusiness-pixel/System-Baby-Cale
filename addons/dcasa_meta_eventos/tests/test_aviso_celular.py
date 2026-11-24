"""El aviso de cookies en el celular: entero a la vista (texto, «Política de privacidad» y los dos botones), sin salirse
de lado y con botones que se tocan con el dedo (44 px). La prueba de «nada se sale del ancho» del sitio corre con el
aviso apagado; esta lo mide encendido, como queda con el píxel."""
from odoo.addons.website_dcasa.tests.chrome_movil import ALTO, ChromeMovilCase
from odoo.tests import tagged

from .test_render import SitioMetaCase

MEDIR_AVISO = """
    (async () => {
        const esperar = (ms) => new Promise((ok) => setTimeout(ok, ms));
        const visible = (el) => el && el.getBoundingClientRect().height > 0
            && getComputedStyle(el).visibility !== 'hidden';
        for (let i = 0; i < 100 && !visible(document.querySelector('#cookies-consent-all')); i++) {
            await esperar(100);
        }
        await esperar(600);
        const ancho = document.documentElement.clientWidth, alto = innerHeight;
        const caja = (sel) => { const el = document.querySelector(sel); if (!visible(el)) { return null; }
            const r = el.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; };
        const color = (sel) => { const e = getComputedStyle(document.querySelector(sel));
            return [e.backgroundColor, e.color, e.borderTopColor, e.borderTopLeftRadius, e.fontFamily.split(',')[0]]; };
        const tarjeta = document.querySelector('#website_cookies_bar .modal-content');
        return { ancho, alto, desplazable: document.documentElement.scrollWidth,
                 marca: { aceptar: color('#cookies-consent-all'), necesarias: color('#cookies-consent-essential'),
                          tarjeta: getComputedStyle(tarjeta).backgroundColor },
                 texto: caja('#website_cookies_bar p'),
                 politica: caja('#website_cookies_bar .o_cookies_bar_text_policy'),
                 necesarias: caja('#cookies-consent-essential'), aceptar: caja('#cookies-consent-all') };
    })()
"""


@tagged('post_install', '-at_install')
class TestAvisoDeCookiesEnElCelular(SitioMetaCase, ChromeMovilCase):

    def test_el_aviso_cabe_entero_y_sus_botones_se_tocan_con_el_dedo(self):
        self.encender_pixel()
        for ancho in (360, 390):
            with self.subTest(ancho=ancho), self._chrome_movil(ancho) as browser:
                browser.navigate_to(self.base_url() + '/', wait_stop=True)
                self.assertTrue(browser._wait_ready(), 'la portada no terminó de cargar')
                medida = self._evaluar(browser, MEDIR_AVISO)
                self.assertEqual((medida['ancho'], medida['alto']), (ancho, ALTO))
                self.assertLessEqual(medida['desplazable'], ancho + 1, 'El aviso no ensancha la página')
                for parte in ('texto', 'politica', 'necesarias', 'aceptar'):
                    caja = medida[parte]
                    self.assertTrue(caja, f'{parte}: no se ve')
                    izquierda, arriba, derecha, abajo = caja
                    self.assertGreaterEqual(izquierda, 0, parte)
                    self.assertGreaterEqual(arriba, 0, parte)
                    self.assertLessEqual(derecha, ancho + 0.5, f'{parte}: se sale de lado')
                    self.assertLessEqual(abajo, ALTO + 0.5, f'{parte}: queda debajo de la pantalla')
                for boton in ('necesarias', 'aceptar'):
                    self.assertGreaterEqual(medida[boton][3] - medida[boton][1], 44 - 0.5, f'{boton}: muy chico')
                # La marca Baby Caleb (su aviso de Meta): la tarjeta crema, «Aceptar» naranja con letra navy y «Solo las
                # necesarias» de contorno, en pastilla, y los dos del mismo alto (rechazar, igual de fácil).
                marca = medida['marca']
                self.assertEqual(marca['tarjeta'], 'rgb(242, 239, 229)')
                self.assertEqual(marca['aceptar'][:2], ['rgb(238, 146, 74)', 'rgb(27, 50, 70)'])
                self.assertEqual(marca['necesarias'][:3], ['rgba(0, 0, 0, 0)', 'rgb(152, 93, 47)', 'rgb(195, 120, 61)'])
                self.assertEqual({marca['aceptar'][3], marca['necesarias'][3]}, {'999px'})
                self.assertEqual({marca['aceptar'][4], marca['necesarias'][4]}, {'Montserrat'})
                self.assertAlmostEqual(medida['necesarias'][3] - medida['necesarias'][1],
                                       medida['aceptar'][3] - medida['aceptar'][1], delta=1)
