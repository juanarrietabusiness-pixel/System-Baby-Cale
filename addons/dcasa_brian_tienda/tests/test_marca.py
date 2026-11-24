"""El chat de la tienda con la marca Baby Caleb (docs/MARCA_BABY_CALEB.md), como el de su web (Chatbot.tsx). Lo que se
ve lo mide tests/test_navegador.py; aquí, la hoja y lo que ya no está: el robot de D'CASA, sus poses y su nombre."""
import re
from pathlib import Path

from odoo.tests import tagged

from .common import TiendaCase

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
class TestMarcaChat(TiendaCase):

    def test_la_hoja_del_chat(self):
        revisar_hoja(self, 'static/src/scss/brian_tienda.scss',
                     ('#EE924A', '#1B3246', '#F9F6ED', '#F2EFE5', '#985D2F', '#C3783D', 'Montserrat'))

    def test_sin_el_robot_ni_el_nombre_de_d_casa(self):
        self.assertFalse((MODULO / 'static/src/img/poses').exists(), 'las 16 poses del robot se fueron')
        js = (MODULO / 'static/src/js/brian_tienda.js').read_text(encoding='utf-8')
        codigo = '\n'.join(linea for linea in js.splitlines() if not linea.lstrip().startswith(('*', '/*', '//')))
        for de_origen in ("\"D'CASA", "D'CASA Panamá", 'Hola D', '.webp', 'Colchones", "Salas'):
            self.assertNotIn(de_origen, codigo)

    def test_el_nombre_del_modulo_no_es_el_de_la_plantilla_de_origen(self):
        modulo = self.env['ir.module.module'].search([('name', '=', MODULO.name)])
        self.assertTrue(modulo.shortdesc.startswith('Baby Caleb — '), modulo.shortdesc)
        self.assertNotIn("D'CASA", modulo.shortdesc + (modulo.summary or ''))
