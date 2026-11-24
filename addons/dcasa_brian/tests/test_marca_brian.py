"""Brian y la marca del panel (Ajustes › Marca del panel, 2026-11-18): ver, cambiar colores, poner logo o ícono y
volver a la marca de fábrica. Solo administradores; la vuelta a fábrica pide Permitir; por MCP las sensibles nunca
se ejecutan solas y la imagen no viaja (se usa una que ya se le mandó a Brian)."""
import io
import json
from datetime import timedelta

from PIL import Image

from odoo import fields
from odoo.addons.dcasa_interfaz.marca import colores as C
from odoo.tests import HttpCase, new_test_user, tagged

from .common import BrianCase

PRINCIPAL = '#173A2B'   # verde oscuro: solo de prueba, no es la marca de nadie
ACENTO = '#F2C14E'      # amarillo: solo de prueba
HERRAMIENTAS = {'ver_marca_del_panel': 'lectura', 'cambiar_colores_del_panel': 'construccion',
                'poner_imagen_del_panel': 'construccion', 'volver_a_la_marca_de_fabrica': 'sensible'}


def png(ancho=300, alto=120):
    salida = io.BytesIO()
    Image.new('RGBA', (ancho, alto), (27, 50, 70, 255)).save(salida, 'PNG')
    return salida.getvalue()


@tagged('post_install', '-at_install')
class TestMarcaConBrian(BrianCase):

    def ejecutar(self, nombre, argumentos=None, usuario=None, **contexto):
        herramientas = self.herramientas(usuario or self.jefe).with_context(**contexto)
        return herramientas.ejecutar(nombre, argumentos or {})

    def ok(self, respuesta):
        self.assertTrue(respuesta.get('ok'), respuesta)
        return respuesta['datos']

    def imagen_en_el_chat(self, nombre='logo-empresa.png', crudo=None, mimetype='image/png'):
        conversacion = self.env['brian.conversacion'].with_user(self.jefe).create({})
        return self.env['ir.attachment'].with_user(self.jefe).create({
            'name': nombre, 'raw': crudo or png(), 'mimetype': mimetype,
            'res_model': 'brian.conversacion', 'res_id': conversacion.id})

    def test_solo_las_ve_un_administrador_con_su_nivel(self):
        jefe = {h['name']: h['nivel'] for h in self.herramientas(self.jefe).catalogo()}
        normal = {h['name'] for h in self.herramientas().catalogo()}
        for nombre, nivel in HERRAMIENTAS.items():
            self.assertEqual(jefe.get(nombre), nivel, nombre)
            self.assertNotIn(nombre, normal, f'{nombre}: solo administradores')
        self.assertFalse(self.ejecutar('ver_marca_del_panel', usuario=self.usuario)['ok'])

    def test_ver_la_marca_de_fabrica_y_el_boton_a_la_pantalla(self):
        datos = self.ok(self.ejecutar('ver_marca_del_panel'))
        self.assertTrue(datos['todo_de_fabrica'])
        self.assertEqual((datos['color_principal'], datos['color_acento']), (C.FABRICA_PRINCIPAL, C.FABRICA_ACENTO))
        self.assertEqual(datos['logo'], 'de fábrica')
        self.assertIn('Se lee bien', datos['como_se_lee'])
        self.assertIn('no cambia', datos['la_web'])
        self.assertEqual(datos['abrir']['accion'], self.env.ref('dcasa_interfaz.action_dcasa_marca_panel').id)

    def test_cambiar_los_colores(self):
        datos = self.ok(self.ejecutar('cambiar_colores_del_panel', {'principal': '173a2b', 'acento': ACENTO}))
        self.assertIn('Listo', datos['mensaje'])
        empresa = self.env.company
        self.assertEqual((empresa.dcasa_panel_color_principal, empresa.dcasa_panel_color_acento), (PRINCIPAL, ACENTO))
        self.assertFalse(datos['todo_de_fabrica'])
        otra_vez = self.ok(self.ejecutar('cambiar_colores_del_panel', {'principal': PRINCIPAL}))
        self.assertIn('no cambié nada', otra_vez['mensaje'])
        accion = self.env['brian.accion'].search([('herramienta', '=', 'cambiar_colores_del_panel')], limit=1)
        self.assertEqual(accion.estado, 'hecha', 'queda en el registro de acciones')

    def test_un_color_que_no_se_lee_no_se_pone_y_dice_cual_si(self):
        respuesta = self.ejecutar('cambiar_colores_del_panel', {'principal': ACENTO})
        self.assertFalse(respuesta['ok'])
        self.assertIn('muy claro', respuesta['error'])
        self.assertIn('Prueba con #', respuesta['error'])
        self.assertIn('No cambié nada', respuesta['error'])
        respuesta = self.ejecutar('cambiar_colores_del_panel', {'acento': 'amarillito'})
        self.assertIn('no es un color', respuesta['error'])
        self.assertFalse(self.ejecutar('cambiar_colores_del_panel', {})['ok'])
        self.assertEqual(self.env.company.dcasa_panel_color_principal, C.FABRICA_PRINCIPAL)

    def test_poner_el_logo_con_una_imagen_que_le_mandaron(self):
        adjunto = self.imagen_en_el_chat()
        # En el turno en que llega la foto, pide Permitir (la regla de los adjuntos).
        respuesta = self.ejecutar('poner_imagen_del_panel', {'adjunto': adjunto.name, 'uso': 'logo'},
                                  brian_turno_con_adjuntos=True)
        self.assertTrue(respuesta.get('requiere_confirmacion'), respuesta)
        self.assertIn('logo del panel', respuesta['resumen'])
        self.assertFalse(self.env.company._dcasa_panel_tiene('dcasa_panel_logo'), 'nada hasta que se permita')
        self.ok(self.herramientas(self.jefe).confirmar(respuesta['accion_id']))
        self.assertTrue(self.env.company._dcasa_panel_tiene('dcasa_panel_logo'))
        self.assertEqual(self.env.company._dcasa_panel_resumen()['icono'], 'sale del logo del panel')
        # Más tarde, sin adjunto en el turno (por ejemplo desde MCP, por su nombre): directo.
        datos = self.ok(self.ejecutar('poner_imagen_del_panel', {'adjunto': str(adjunto.id), 'uso': 'icono'}))
        self.assertEqual(datos['icono'], 'propio')

    def test_una_imagen_que_no_sirve(self):
        texto = self.imagen_en_el_chat('notas.txt', b'hola', 'text/plain')
        respuesta = self.ejecutar('poner_imagen_del_panel', {'adjunto': texto.name, 'uso': 'logo'})
        self.assertIn('no es una imagen', respuesta['error'])
        respuesta = self.ejecutar('poner_imagen_del_panel', {'adjunto': 'no-existe.png', 'uso': 'logo'})
        self.assertIn('No encuentro', respuesta['error'])
        self.assertFalse(self.env.company._dcasa_panel_tiene('dcasa_panel_logo'))

    def test_volver_a_fabrica_pide_permitir(self):
        self.env.company.write({'dcasa_panel_color_principal': PRINCIPAL})
        respuesta = self.ejecutar('volver_a_la_marca_de_fabrica', {'que': 'colores'})
        self.assertTrue(respuesta.get('requiere_confirmacion'), respuesta)
        self.assertIn('colores de fábrica', respuesta['resumen'])
        self.assertEqual(self.env.company.dcasa_panel_color_principal, PRINCIPAL, 'nada hasta que se permita')
        datos = self.ok(self.herramientas(self.jefe).confirmar(respuesta['accion_id']))
        self.assertTrue(datos['color_principal_de_fabrica'])
        self.assertEqual(self.env.company.dcasa_panel_color_principal, C.FABRICA_PRINCIPAL)


@tagged('post_install', '-at_install')
class TestMarcaPorMCP(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin = new_test_user(cls.env, login='brian_mcp_marca', groups='base.group_user,base.group_system')
        cls.clave = cls.env['res.users.apikeys'].with_user(cls.admin).sudo()._generate(
            'brian', 'MCP marca', fields.Datetime.now() + timedelta(days=1))

    def rpc(self, metodo, params):
        cuerpo = {'jsonrpc': '2.0', 'id': 1, 'method': metodo, 'params': params}
        respuesta = self.url_open('/brian/mcp', data=json.dumps(cuerpo), headers={
            'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream',
            'Authorization': f'Bearer {self.clave}'})
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.json()['result']

    def test_las_herramientas_de_la_marca_salen_por_mcp(self):
        herramientas = {h['name']: h for h in self.rpc('tools/list', {})['tools']}
        self.assertTrue(herramientas['ver_marca_del_panel']['annotations']['readOnlyHint'])
        self.assertFalse(herramientas['cambiar_colores_del_panel']['annotations']['readOnlyHint'])
        self.assertTrue(herramientas['volver_a_la_marca_de_fabrica']['annotations']['destructiveHint'])
        cambio = self.rpc('tools/call', {'name': 'cambiar_colores_del_panel', 'arguments': {'principal': PRINCIPAL}})
        self.assertFalse(cambio.get('isError'), cambio)
        self.assertEqual(self.env.company.dcasa_panel_color_principal, PRINCIPAL)
        # La sensible no se ejecuta sola por MCP: queda por confirmar.
        vuelta = self.rpc('tools/call', {'name': 'volver_a_la_marca_de_fabrica', 'arguments': {'que': 'todo'}})
        self.assertTrue(vuelta.get('isError'), vuelta)
        self.assertEqual(self.env.company.dcasa_panel_color_principal, PRINCIPAL)
