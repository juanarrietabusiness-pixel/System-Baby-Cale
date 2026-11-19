"""«Busca con una foto» con la marca Baby Caleb (docs/MARCA_BABY_CALEB.md): la pastilla de contorno y la principal,
la banda verde salvia del final y Montserrat; los textos hablan de productos, no de muebles."""
import re
from pathlib import Path

from odoo.tests import HttpCase, tagged

MODULO = Path(__file__).resolve().parents[1]
# Lo de D'CASA que no puede quedar en las hojas de estilo (docs/MARCA_BABY_CALEB.md › De D'CASA a Baby Caleb).
DE_DCASA = re.compile(r'#1340B1|#FED00F|#0E2A6B|#0F3591|#0B2A6F|#0B2160|rgba?\(\s*19,\s*64,\s*177|\bAnton\b'
                      r'|\bOswald\b|\bInter\b', re.I)
# El naranja y el verde de Baby Caleb son RELLENO (2.20 y 1.75 sobre el crema): nunca color de letra, borde ni aro.
RELLENO_COMO_LETRA = re.compile(r'(?<![-\w])(?:color|border(?:-[a-z]+)*|outline(?:-color)?)\s*:[^;{]*'
                                r'(?:#EE924A|#91C9A2|var\(--o-dcbt-(?:accent|sage)\)|var\(--dcc-acento\)'
                                r'|\$[a-z]+-(?:accent|sage)\b(?!-))', re.I)


def sin_comentarios(scss):
    return re.sub(r'//[^\n]*', '', re.sub(r'/\*.*?\*/', '', scss, flags=re.S))


def revisar_hoja(caso, ruta, de_baby_caleb=('#EE924A', '#1B3246', 'Montserrat')):
    """La hoja no trae nada de D'CASA, sí los colores y la letra de Baby Caleb, y no usa el relleno como letra."""
    texto = sin_comentarios((MODULO / ruta).read_text(encoding='utf-8'))
    caso.assertEqual(DE_DCASA.findall(texto), [], f'{ruta}: queda la marca de D’CASA')
    for valor in de_baby_caleb:
        caso.assertIn(valor.lower(), texto.lower(), f'{ruta}: falta {valor} de la marca Baby Caleb')
    caso.assertEqual(RELLENO_COMO_LETRA.findall(texto), [], f'{ruta}: el naranja o el verde como letra o borde')


@tagged('post_install', '-at_install')
class TestMarcaBuscarFoto(HttpCase):

    def setUp(self):
        super().setUp()
        self.env['ir.config_parameter'].sudo().set_param('dcasa_buscar_foto.activo', 'True')

    def test_la_hoja(self):
        revisar_hoja(self, 'static/src/scss/buscar_foto.scss',
                     ('#EE924A', '#1B3246', '#91C9A2', '#C3783D', 'Montserrat'))

    def test_la_pagina_habla_de_productos(self):
        html = self.url_open('/shop/foto').text
        cuerpo = html[html.index('o_dcasa_foto_pagina'):html.index('id="busca-con-una-foto"')
                      if 'id="busca-con-una-foto"' in html else len(html)]
        self.assertIn('Toma una foto de un producto', cuerpo)
        self.assertNotIn('cama queen', cuerpo)
        self.assertNotIn('mueble', cuerpo.split('o_dcasa_foto_privacidad')[0], 'la política (texto legal) no se toca')

    def test_el_nombre_del_modulo_no_es_el_de_la_plantilla_de_origen(self):
        modulo = self.env['ir.module.module'].search([('name', '=', MODULO.name)])
        self.assertTrue(modulo.shortdesc.startswith('Baby Caleb — '), modulo.shortdesc)
        self.assertNotIn("D'CASA", modulo.shortdesc + (modulo.summary or ''))
