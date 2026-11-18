"""Staging arranca sin conversaciones de ejemplo (decisión del dueño, 2026-11-18).

Antes había un botón «Cargar conversaciones de ejemplo» (solo con existencias de prueba) que creaba cuatro chats de
otra empresa (camas, colchones, «soy Juan de D'CASA», cifras de puntos). Se quitó entero y no se inventaron otros: un
entorno de prueba empieza con la pantalla vacía, igual que producción.
"""
from lxml import etree

from odoo.tests import tagged

from .common import JuanCase

PARAM = 'dcasa_catalogo.stock_prueba'
PREFIJO_DE_LOS_EJEMPLOS = '5076000000'


@tagged('post_install', '-at_install')
class TestSinEjemplos(JuanCase):

    def test_no_queda_el_boton_ni_el_metodo(self):
        Ajustes = self.env['dcasa.juan.ajustes']
        self.assertFalse(hasattr(Ajustes, 'action_cargar_ejemplos'), 'el botón de los ejemplos ya no existe')
        self.assertFalse(hasattr(self.env['dcasa.conversacion'], '_cargar_ejemplos'))
        self.assertNotIn('es_entorno_de_prueba', Ajustes._fields)
        arbol = etree.fromstring(Ajustes.get_view(view_type='form')['arch'])
        self.assertFalse(arbol.xpath("//button[@name='action_cargar_ejemplos']"))
        self.assertNotIn('Cargar conversaciones de ejemplo', etree.tostring(arbol, encoding='unicode'))

    def test_con_existencias_de_prueba_no_aparece_ninguna_conversacion(self):
        """Con el parámetro de staging puesto (como lo deja docker/entrypoint.sh), abrir los ajustes no crea nada."""
        self.env['ir.config_parameter'].sudo().set_param(PARAM, '10')
        self.env['dcasa.juan.ajustes'].with_user(self.gerente).obtener()
        Conversacion = self.env['dcasa.conversacion'].sudo()
        self.assertFalse(Conversacion.search([('id_externo', '=like', f'{PREFIJO_DE_LOS_EJEMPLOS}%')]))
        self.assertFalse(self.env['res.partner'].sudo().search([('name', '=like', '%(ejemplo)')]))
        self.assertFalse(self.env['dcasa.mensaje'].sudo().search([('id_mensaje', '=like', 'ejemplo-%')]))
