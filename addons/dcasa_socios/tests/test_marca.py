"""Socios con la marca Baby Caleb (docs/MARCA_BABY_CALEB.md): la placa de puntos en verde salvia con todo en navy,
el botón principal naranja con letra navy, Montserrat, y el nombre de la tienda en lugar de «D'CASA». El panel de
Ajustes de vendedores, con el filo naranja y el navy."""
import re
from pathlib import Path

from odoo.tests import HttpCase, tagged

from ..models.bien_escrito import mensaje_del_correo
from ..models.res_partner_vend import TIPOS_VENDEDOR

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
class TestMarcaSocios(HttpCase):

    def test_las_hojas_de_socios_y_de_ajustes_de_vendedores(self):
        revisar_hoja(self, 'static/src/scss/socios.scss', ('#EE924A', '#1B3246', '#91C9A2', 'Montserrat'))
        revisar_hoja(self, 'static/src/scss/vendedores_ajustes.scss', ('#C3783D', '#1B3246'))

    def test_socios_dice_tus_puntos_con_el_nombre_de_la_tienda(self):
        html = self.url_open('/socios').text
        self.assertIn('Tus puntos', html, 'lo mira el CI')
        self.assertIn('Tus puntos Baby Caleb', html)
        for de_origen in ("Tus puntos D'CASA", 'Tus puntos D&#39;CASA', 'Socios D’CASA', "compraste en D'CASA"):
            self.assertNotIn(de_origen, html)

    def test_el_nombre_del_modulo_no_es_el_de_la_plantilla_de_origen(self):
        modulo = self.env['ir.module.module'].search([('name', '=', MODULO.name)])
        self.assertTrue(modulo.shortdesc.startswith('Baby Caleb — '), modulo.shortdesc)
        self.assertNotIn("D'CASA", modulo.shortdesc + (modulo.summary or ''))

    def test_nada_de_lo_que_se_ve_dice_d_casa(self):
        """El nombre de la empresa donde el texto se arma en el código; «Baby Caleb» en las etiquetas fijas."""
        empresa = self.env.company.name
        self.assertEqual(dict(TIPOS_VENDEDOR)['empleado'], 'Empleado de Baby Caleb')
        self.assertEqual(self.env.ref('dcasa_socios.product_premio_canje').name,
                         'Premio del programa Socios Baby Caleb')
        self.assertEqual(self.env.ref('dcasa_socios.ir_cron_programa_socios').name,
                         'Socios: vencer canjes y regalos de cumpleaños')
        self.assertTrue(self.env['dcasa.premio']._fields['costo'].help.startswith(
            'Lo que de verdad le cuesta a la tienda.'))
        self.assertEqual(mensaje_del_correo(self.env, 'ventas@ejemplo.com', 'equipo'),
                         f'Ese correo es de {empresa} o de alguien del equipo: escribe el del cliente.')
        for vista, pestana in (('dcasa_socios.view_partner_form_dcasa_socios', 'Socio Baby Caleb'),
                               ('dcasa_socios.view_partner_form_dcasa_vendedores', 'Vendedor Baby Caleb')):
            arco = self.env.ref(vista).arch
            self.assertIn(f'string="{pestana}"', arco)
            self.assertNotIn("D'CASA", arco)
