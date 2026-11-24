"""El conocimiento inicial de Baby Caleb (conocimiento_inicial/baby_caleb.json): se siembra una vez por ficha.

Pedido del dueño (2026-11-24): una sola fuente de verdad, el conocimiento del panel, que él configura, apaga y
archiva. El archivo solo siembra: lo que se cambie en el panel no se pisa, lo que se borre no vuelve, y una
instalación sin ``DCASA_CONOCIMIENTO_INICIAL`` sigue en cero (test_conocimiento.py)."""
import copy

from odoo.tests import TransactionCase, tagged

from ..conocimiento_inicial import PARAM_CARGADAS, cargar_conocimiento_inicial, leer_conocimiento_inicial
from ..models.conocimiento import MAX_CONTENIDO
from .test_conocimiento_en_cero import HECHOS_DE_DCASA


@tagged('post_install', '-at_install')
class TestConocimientoInicial(TransactionCase):

    def setUp(self):
        super().setUp()
        self.datos = leer_conocimiento_inicial('baby_caleb')
        self.Conocimiento = self.env['dcasa.conocimiento'].with_context(active_test=False)

    def test_el_archivo_es_de_baby_caleb_y_cabe(self):
        claves = [e['clave'] for e in self.datos['entradas']]
        self.assertEqual(len(claves), len(set(claves)), 'cada clave una sola vez')
        for entrada in self.datos['entradas']:
            with self.subTest(entrada['clave']):
                texto = f"{entrada['titulo']} {entrada['contenido']} {' '.join(entrada.get('etiquetas') or [])}"
                self.assertFalse([m.group(0) for m in HECHOS_DE_DCASA.finditer(texto)], 'nada de D’CASA')
                self.assertLessEqual(len(entrada['contenido']), MAX_CONTENIDO)
                self.assertNotIn('ITBMS', texto, 'Baby Caleb no cobra ITBMS')

    def test_siembra_una_vez_y_respeta_el_panel(self):
        creadas = cargar_conocimiento_inicial(self.env, 'baby_caleb')
        self.assertEqual(len(creadas), len(self.datos['entradas']))
        self.assertTrue(all(c.fuente == 'manual' for c in creadas), 'fichas normales del panel')
        apartado = creadas.filtered(lambda c: c.titulo.startswith('Talla agotada'))
        self.assertFalse(apartado.activo, 'el apartado con abono queda apagado (decisión del dueño)')
        self.assertIn('Apagado por decisión del dueño', apartado.nota)
        self.assertEqual(len(creadas.filtered('activo')), len(creadas) - 1)
        # La segunda vez no crea nada.
        self.assertFalse(cargar_conocimiento_inicial(self.env, 'baby_caleb'))
        # Lo que cambia el equipo en el panel no se pisa, y lo que borra no vuelve.
        horario = creadas.filtered(lambda c: c.titulo == 'Horario de los envíos')
        horario.contenido = 'Texto corregido en el panel'
        forrado = creadas.filtered(lambda c: c.titulo == 'Forrado para regalo')
        forrado.unlink()
        self.assertFalse(cargar_conocimiento_inicial(self.env, 'baby_caleb'))
        self.assertEqual(horario.contenido, 'Texto corregido en el panel')
        self.assertFalse(self.Conocimiento.search([('titulo', '=', 'Forrado para regalo')]))
        self.assertIn('baby_caleb:horario-de-envios',
                      self.env['ir.config_parameter'].sudo().get_param(PARAM_CARGADAS))

    def test_una_ficha_nueva_en_el_archivo_se_crea_en_el_siguiente_arranque(self):
        cargar_conocimiento_inicial(self.env, 'baby_caleb')
        datos = copy.deepcopy(self.datos)
        datos['entradas'].append({'clave': 'nueva-de-prueba', 'titulo': 'Ficha nueva de prueba',
                                  'contenido': 'Una ficha que se agregó después.', 'etiquetas': ['prueba']})
        self.assertEqual(cargar_conocimiento_inicial(self.env, 'baby_caleb', datos).titulo, 'Ficha nueva de prueba')

    def test_el_asistente_la_encuentra(self):
        cargar_conocimiento_inicial(self.env, 'baby_caleb')
        Conocimiento = self.env['dcasa.conocimiento']
        for pregunta, titulo in (('¿hacen envíos el domingo?', 'Horario de los envíos'),
                                 ('¿qué talla para un bebé de 10 libras?', 'Tallas de los pañales Nateen de cierre'),
                                 ('¿aceptan yappy?', 'Formas de pago')):
            with self.subTest(pregunta):
                titulos = [e.titulo for e, _puntos in Conocimiento._buscar(pregunta, 3)]
                self.assertIn(titulo, titulos)
        self.assertNotIn('Talla agotada: apartado con abono de $5.00 (apagado)',
                         [e.titulo for e, _puntos in Conocimiento._buscar('apartar una talla agotada con abono', 3)],
                         'lo apagado no lo ve el asistente')

    def test_un_negocio_sin_archivo(self):
        with self.assertRaises(ValueError):
            leer_conocimiento_inicial('d_casa')
