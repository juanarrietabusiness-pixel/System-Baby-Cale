"""El aviso de cookies con la marca Baby Caleb (docs/MARCA_BABY_CALEB.md), como su aviso de Meta: la tarjeta crema,
«Aceptar» naranja con letra navy y «Solo las necesarias» de contorno. El texto ya no habla de muebles."""
import re
from pathlib import Path

from odoo.tests import tagged

from .test_render import SitioMetaCase

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
class TestMarcaAviso(SitioMetaCase):

    def test_la_hoja_del_aviso(self):
        revisar_hoja(self, 'static/src/scss/meta.scss', ('#EE924A', '#1B3246', '#F2EFE5', '#C3783D', 'Montserrat'))

    def test_el_aviso_habla_de_productos_no_de_muebles(self):
        self.encender_pixel()
        self.website.cookies_bar = True
        html = self.url_open('/').text
        self.assertIn('o_dcasa_aviso_cookies', html)
        inicio = html.index('id="website_cookies_bar"')
        aviso = html[inicio:html.index('</section>', inicio)]
        self.assertIn('anuncios de nuestros', aviso)
        self.assertIn('productos', aviso)
        self.assertNotIn('muebles', aviso)
