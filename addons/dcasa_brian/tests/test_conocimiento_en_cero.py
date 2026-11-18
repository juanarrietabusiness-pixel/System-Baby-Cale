"""Brian no trae escrito lo que es la empresa (pedido del dueño, 2026-11-18: el conocimiento arranca en cero).

El giro, la ciudad y la dirección del negocio no van en sus instrucciones fijas: lo que Brian sabe de la empresa lo
consulta con sus herramientas (los datos de Odoo). El nombre de la marca y el de Brian se cambian en otro trabajo.
"""
import re

from odoo.tests import TransactionCase, tagged

HECHOS_DE_DCASA = re.compile(r'mueble|chorrera|panam[aá] oeste|dcasapty|libertadores|6026|1919|155779346',
                             re.IGNORECASE)


@tagged('post_install', '-at_install')
class TestBrianSinConocimientoDeFabrica(TransactionCase):

    def test_las_instrucciones_fijas_no_traen_el_giro_ni_la_ciudad(self):
        fijo = self.env['brian.conversacion']._sistema_fijo()
        self.assertFalse(HECHOS_DE_DCASA.findall(fijo))
        # Lo que sí se queda: las reglas de siempre.
        self.assertIn('No inventes cifras, precios, nombres ni resultados', fijo)
        self.assertIn('Las acciones sensibles las confirma la persona con un botón', fijo)
