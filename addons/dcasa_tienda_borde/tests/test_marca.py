"""La tienda del borde no sirve nada que se vea con colores o letras propios; lo que un administrador sí ve (el nombre
del módulo y sus tareas programadas) no dice el nombre de la plantilla de origen (D'CASA): marca Baby Caleb,
docs/MARCA_BABY_CALEB.md."""
from pathlib import Path

from odoo.tests import TransactionCase, tagged

MODULO = Path(__file__).resolve().parents[1]


@tagged('post_install', '-at_install')
class TestMarcaBorde(TransactionCase):

    def test_el_nombre_del_modulo_no_es_el_de_la_plantilla_de_origen(self):
        modulo = self.env['ir.module.module'].search([('name', '=', MODULO.name)])
        self.assertTrue(modulo.shortdesc.startswith('Baby Caleb — '), modulo.shortdesc)
        self.assertNotIn("D'CASA", modulo.shortdesc + (modulo.summary or ''))

    def test_las_tareas_programadas_no_dicen_d_casa(self):
        self.assertEqual(self.env.ref('dcasa_tienda_borde.cron_avisar_borde').name,
                         'Tienda del borde: avisar de lo que cambió')
        self.assertEqual(self.env.ref('dcasa_tienda_borde.cron_vigilar_black_weekend').name,
                         'Tienda del borde: encender o apagar Black Weekend')
