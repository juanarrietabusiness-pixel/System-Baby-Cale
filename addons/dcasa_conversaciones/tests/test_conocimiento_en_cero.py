"""El conocimiento del bot arranca en cero (pedido del dueño, 2026-11-18).

«Cada negocio le va a poner el conocimiento de su negocio manualmente o vía MCP. Nada de la información de D'CASA, ni
las preguntas por responder.» El mecanismo es el de siempre (las fichas de «Conocimiento del bot», las «Preguntas sin
respuesta» y las herramientas del asistente); lo que se vigila aquí es que nada de una empresa en particular venga
escrito en el código que lee el asistente:

* las herramientas de Juan (lo que el Worker recibe en ``GET /herramientas``) no traen el giro, la ciudad ni el
  catálogo de D'CASA como ejemplos;
* ``horario_y_tienda`` saca la provincia y la ruta en el mapa de la empresa, no de una constante.

Que la instalación nueva no traiga fichas ni preguntas lo prueba ``test_conocimiento.py``.
"""
import json
import re

from odoo.tests import tagged

from ..controllers.juan import JuanAPI
from .test_herramientas import HerramientasCase

# El giro, la ciudad, el dominio y el catálogo de D'CASA: nada de esto viene de fábrica en lo que lee el asistente.
HECHOS_DE_DCASA = re.compile(
    r'mueble|chorrera|panam[aá] oeste|dcasapty|libertadores|discoteca seven|6026|1919|155779346|'
    r'\bcolch[oó]n(es)?\b|\bcamas?\b|\bsof[aá]s?\b|\bqueen\b', re.IGNORECASE)


@tagged('post_install', '-at_install')
class TestConocimientoEnCero(HerramientasCase):

    def test_las_herramientas_de_juan_no_traen_lo_que_es_d_casa(self):
        catalogo = JuanAPI._catalogo(self.env(user=self.juan))
        self.assertTrue(catalogo, 'El Worker recibe las herramientas de siempre')
        for herramienta in catalogo:
            texto = json.dumps(herramienta, ensure_ascii=False)
            self.assertFalse(HECHOS_DE_DCASA.findall(texto), herramienta['nombre'])

    def test_la_ruta_en_el_mapa_sale_de_la_ubicacion_de_la_empresa(self):
        """Ninguna ubicación escrita en el código: sin la latitud y la longitud de la empresa no hay ruta; con ellas, la
        ruta va a ese punto. La provincia también sale de la empresa: sin ella, no se inventa una."""
        contacto = self.env.company.partner_id
        contacto.write({'partner_latitude': 0.0, 'partner_longitude': 0.0, 'state_id': False})
        datos = self.salida('horario_y_tienda')
        self.assertNotIn('google.com/maps', datos['como_llegar'])
        self.assertNotIn('8.8765881', json.dumps(datos), 'nada de la ubicación de otra tienda')
        self.assertNotIn('Panamá Oeste', datos['direccion'])
        provincia = self.env['res.country.state'].search([], limit=1)
        contacto.write({'partner_latitude': 9.1234567, 'partner_longitude': -79.7654321, 'state_id': provincia.id})
        datos = self.salida('horario_y_tienda')
        self.assertIn('https://www.google.com/maps/dir/?api=1&destination=9.1234567%2C-79.7654321',
                      datos['como_llegar'])
        self.assertTrue(datos['direccion'].endswith(provincia.name))

    def test_una_empresa_sin_direccion_no_deja_frases_rotas(self):
        """Una instalación nueva puede no tener aún la dirección: el texto no dice «está en .»."""
        self.env.company.partner_id.write({'street': False, 'street2': False, 'city': False, 'state_id': False,
                                           'partner_latitude': 0.0, 'partner_longitude': 0.0})
        entrada = self.env['dcasa.conocimiento'].create({'titulo': 'Dónde estamos', 'fuente': 'tienda'})
        texto = entrada.contenido_vigente
        self.assertNotIn('está en .', texto)
        self.assertNotIn('Cómo llegar: .', texto)
        self.assertIn('El equipo atiende', texto)
