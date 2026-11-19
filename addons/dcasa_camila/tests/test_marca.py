"""La pantalla de Camila en el panel y la página «Sí, quiero» con la marca Baby Caleb (docs/MARCA_BABY_CALEB.md).

Los correos se comprueban en test_campana.py y test_enlace.py; aquí, el CSS ya compilado de las dos hojas propias.
"""
import re

from odoo.addons.dcasa_invoice.tests import marca
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestMarcaCamila(TransactionCase):

    def test_la_pantalla_del_panel(self):
        hoja = marca.css_de_los_informes(self, '/dcasa_camila/static/src/scss/camila.scss',
                                         paquete='web.assets_backend')
        marca.sin_rastro_de_dcasa(self, hoja, 'camila.scss')
        self.assertEqual(marca.letra_de_relleno(hoja), [])
        plano = hoja.lower().replace(' ', '')
        for token in (f'--cm-tinta:#{marca.NAVY}', f'--cm-naranja:#{marca.NARANJA}', f'--cm-salvia:#{marca.SALVIA}',
                      f'--cm-crema:#{marca.CREMA}', '--cm-superficie:#f2efe5',
                      f'--cm-naranja-texto:#{marca.NARANJA_TEXTO}'):
            self.assertIn(token, plano)
        # El botón principal: pastilla naranja con la letra navy; lo que se toca, de 44 px.
        self.assertIn(f'--bs-btn-bg:#{marca.NARANJA}', plano)
        self.assertIn(f'--bs-btn-color:#{marca.NAVY}', plano)
        self.assertIn('border-radius:999px', plano)
        self.assertIn('min-height:44px', plano)
        # El titular de la pantalla en Montserrat 700, como frase.
        titulo = re.search(r'\.o_camila\.o_camila_tituloh1[^{]*\{([^}]*)\}', plano)
        self.assertTrue(titulo, 'no encontré el titular de la pantalla')
        self.assertIn('font-weight:700', titulo.group(1))
        self.assertIn('text-transform:none', titulo.group(1))
        self.assertIn('montserrat', titulo.group(1))

    def test_la_pagina_de_novedades(self):
        hoja = marca.css_de_los_informes(self, '/dcasa_camila/static/src/frontend/novedades.scss',
                                         paquete='web.assets_frontend')
        marca.sin_rastro_de_dcasa(self, hoja, 'novedades.scss')
        self.assertEqual(marca.letra_de_relleno(hoja), [])
        plano = hoja.lower().replace(' ', '')
        banda = re.search(r'\.o_camila_novedades\.o_camila_novedades_banda\{([^}]*)\}', plano)
        self.assertTrue(banda, 'no encontré la banda')
        self.assertIn(f'background:#{marca.SALVIA}', banda.group(1))
        self.assertIn(f'color:#{marca.NAVY}', banda.group(1))
        boton = re.search(r'\.o_camila_novedades\.btn\{([^}]*)\}', plano)
        self.assertTrue(boton, 'no encontré el botón')
        for regla in ('border-radius:999px', f'background:#{marca.NARANJA}', f'color:#{marca.NAVY}', 'font-weight:700',
                      'min-height:44px'):
            self.assertIn(regla, boton.group(1))
        titulo = re.search(r'\.o_camila_novedades\.o_camila_novedades_titulo\{([^}]*)\}', plano)
        self.assertIn('text-transform:none', titulo.group(1))
