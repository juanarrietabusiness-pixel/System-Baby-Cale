"""Mi cuenta con la marca Baby Caleb (docs/MARCA_BABY_CALEB.md): crema, navy, el naranja de relleno con letra navy y
el verde salvia; Montserrat; nada del azul, el amarillo, el Anton ni el Oswald de D'CASA, ni la foto del sofá."""
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
class TestMarcaMiCuenta(HttpCase):

    def test_la_hoja_de_mi_cuenta(self):
        revisar_hoja(self, 'static/src/scss/mi_cuenta.scss', ('#EE924A', '#1B3246', '#F9F6ED', '#91C9A2', 'Montserrat'))

    def test_la_cabecera_ya_no_lleva_la_foto_del_sofa(self):
        html = self.url_open('/mi-cuenta').text
        self.assertIn('o_dcasa_mc', html)
        self.assertNotIn('split-hoy', html, 'la foto de la sala (D’CASA) se fue de Mi cuenta')
