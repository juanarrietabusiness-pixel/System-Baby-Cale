"""Las seis plantillas de Sofía dicen el nombre de la empresa de Ajustes y no ofrecen Socios ni cumpleaños.

Decisión del dueño (2026-11-18): donde decían «D'CASA», ahora va ``{empresa}`` (``res.company.name``), que Sofía llena
al armar el mensaje, igual que ``{vendedora}``. Las partes que ofrecían el programa de puntos y los beneficios de
cumpleaños se quitaron: el programa no tiene cifras todavía. Las plantillas son ``noupdate``: esto vale para una
instalación nueva; una base que ya las tenía conserva lo que Gerencia escribió.
"""
from odoo.addons.dcasa_conversaciones.tests.common import JuanCase
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from ..models import reglas as R
from ..models.plantilla import CLAVES


@tagged('post_install', '-at_install')
class TestPlantillasConLaEmpresa(JuanCase):

    def setUp(self):
        super().setUp()
        self.Plantilla = self.env['dcasa.sofia.plantilla'].sudo()
        self.Sofia = self.env['dcasa.sofia']

    def test_las_seis_de_fabrica_usan_la_empresa_y_no_ofrecen_socios_ni_cumpleanos(self):
        textos = self.Plantilla._textos()
        self.assertEqual(set(textos), {clave for clave, _nombre in CLAVES})
        for clave, texto in textos.items():
            with self.subTest(plantilla=clave):
                self.assertNotIn("D'CASA", texto)
                self.assertNotIn('D’CASA', texto)
                for prohibida in ('Socios', 'socios', 'puntos', 'cumplea', 'el día y el mes'):
                    self.assertNotIn(prohibida, texto)
                self.assertEqual(R.claves_desconocidas(texto), [], 'Sofía sabe llenar todo lo que traen')
                if clave != 'posdata_datos':      # la posdata va al final de otro mensaje: no se presenta
                    self.assertIn('Soy {vendedora} de {empresa}.', texto)

    def test_pedir_datos_sigue_pidiendo_nombre_y_correo_para_avisar_de_promociones(self):
        textos = self.Plantilla._textos()
        for clave in ('pedir_datos', 'posdata_datos'):
            with self.subTest(plantilla=clave):
                self.assertIn('{que_falta}', textos[clave])
                self.assertIn('Así te avisamos de promociones.', textos[clave])
                self.assertFalse(R.pide_el_cumple(textos[clave]), 'ya no pide el cumpleaños')

    def _propuesta(self, plantilla, valores):
        return self.env['dcasa.sofia.propuesta'].sudo().new({
            'tipo': 'pedir_datos' if plantilla == 'pedir_datos' else 'escribir', 'plantilla': plantilla,
            'datos': {'valores': valores}})

    def test_el_mensaje_dice_el_nombre_que_la_empresa_tiene_en_ajustes(self):
        self.env.company.name = 'Pañalera de Prueba'
        propuesta = self._propuesta('seguimiento_interes', {'nombre': 'Ana', 'interes': 'pañales talla 3'})
        texto = self.Sofia._texto(propuesta, self.vendedora)
        self.assertTrue(texto.startswith('¡Hola Ana! Soy Vendedora de Pañalera de Prueba.'), texto)
        self.assertIn('pañales talla 3', texto)
        self.assertNotIn('{', texto)
        self.env.company.name = 'Otra Empresa'
        self.assertIn('Soy Vendedora de Otra Empresa.', self.Sofia._texto(propuesta, self.vendedora),
                      'el nombre se lee al armar el mensaje: si cambia en Ajustes, cambia el mensaje')

    def test_pedir_datos_completo(self):
        self.env.company.name = 'Pañalera de Prueba'
        propuesta = self._propuesta('pedir_datos', {'nombre': 'Luz', 'que_falta': 'tu correo'})
        texto = self.Sofia._texto(propuesta, self.vendedora)
        self.assertEqual(texto, '¡Hola Luz! Soy Vendedora de Pañalera de Prueba. Para atenderte mejor, ¿me regalas '
                                'tu correo? Así te avisamos de promociones. Solo los usamos para eso y puedes pedir '
                                'que no te escribamos cuando quieras.')

    def test_gerencia_puede_usar_empresa_en_sus_plantillas(self):
        plantilla = self.Plantilla.search([('clave', '=', 'seguimiento_cotizacion')])
        plantilla.texto = 'Hola {nombre}, te escribe {vendedora} de {empresa}.'
        self.assertIn('{empresa}', plantilla.texto)
        with self.assertRaisesRegex(ValidationError, 'no sabe llenar'):
            plantilla.texto = 'Hola {nombre}, te escribe {vendedora} de {compania}.'
