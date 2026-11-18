"""Camila no trae escrito lo que es la empresa (pedido del dueño, 2026-11-18: el conocimiento arranca en cero).

Las instrucciones con las que la IA escribe el correo, la línea de cada producto y la selección no dicen el giro ni la
ciudad del negocio: los productos llegan con sus datos reales desde Odoo. El nombre de la marca se cambia en otro
trabajo.
"""
import re

from odoo.tests import BaseCase, tagged

from ..models import camila as K

HECHOS_DE_DCASA = re.compile(r'mueble|chorrera|panam[aá] oeste|dcasapty|libertadores|6026|1919|155779346',
                             re.IGNORECASE)


@tagged('post_install', '-at_install')
class TestCamilaSinConocimientoDeFabrica(BaseCase):

    def test_las_instrucciones_de_la_ia_no_traen_el_giro_ni_la_ciudad(self):
        for nombre in ('SISTEMA_IA', 'SISTEMA_LINEA', 'SISTEMA_SUGERIR'):
            self.assertFalse([m.group(0) for m in HECHOS_DE_DCASA.finditer(getattr(K, nombre))], nombre)
        # Lo que sí se queda: las reglas de siempre.
        self.assertIn('Sin cifras ni números de ningún tipo', K.SISTEMA_IA)
        self.assertIn('No inventes nada que no esté en los datos', K.SISTEMA_LINEA)
        self.assertIn('solo de esa lista', K.SISTEMA_SUGERIR)
