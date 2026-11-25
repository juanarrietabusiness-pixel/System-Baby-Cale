"""Ajustes › Correo a clientes y la clave: nunca en la base, nunca en un log, nunca en una respuesta."""
import logging
import os
from email.message import EmailMessage
from unittest.mock import patch

from odoo.addons.website_dcasa.tests.ajustes_navegador import GuardarAjustesComoElNavegador
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import new_test_user, tagged

from ..models import correo as correo_modelo
from ..models import resend
from ..models.correo import P_NOMBRE, P_REMITENTE, P_RESPONDER_A, REMITENTE, RESPONDER_A
from .common import CLAVE, CorreoCase, respuesta

# Lugares de la base donde podría colarse un texto: si la clave aparece en alguno, la prueba falla.
COLUMNAS_A_REVISAR = (
    ('ir_config_parameter', 'value'), ('mail_mail', 'failure_reason'), ('mail_mail', 'headers'),
    ('mail_mail', 'body_html'), ('mail_message', 'body'), ('mail_notification', 'failure_reason'),
    ('dcasa_correo_envio', 'motivo'), ('ir_logging', 'message'),
)


@tagged('post_install', '-at_install')
class TestAjustes(CorreoCase):

    def ajustes(self, usuario=None):
        ajustes = self.env['res.config.settings'].create({})
        return ajustes.with_user(usuario) if usuario else ajustes

    def test_no_hay_campo_para_la_clave(self):
        campos = self.env['res.config.settings']._fields
        self.assertFalse([n for n in campos if n.startswith('dcasa_correo') and 'clave' in n])
        self.encender()
        self.ajustes().execute()
        self.assertFalse(self.env['ir.config_parameter'].sudo().search([('value', 'ilike', CLAVE)]))

    def test_el_estado_muestra_la_clave_tapada(self):
        self.assertIn('Sin clave', self.ajustes().dcasa_correo_estado)
        self.con_clave()
        estado = self.ajustes().dcasa_correo_estado
        self.assertIn('Clave cargada (…_123)', estado)
        self.assertNotIn(CLAVE, estado)
        self.assertIn('Apagado', estado)
        self.encender()
        self.assertIn('Encendido', self.ajustes().dcasa_correo_estado)
        with patch.dict(os.environ, {'DCASA_ENTORNO': 'staging'}):
            self.assertIn('Staging: nunca se envía a clientes', self.ajustes().dcasa_correo_estado)

    def test_vienen_apagados_con_la_factura_y_la_bienvenida_listas(self):
        ajustes = self.ajustes()
        self.assertFalse(ajustes.dcasa_correo_a_clientes)
        self.assertTrue(ajustes.dcasa_correo_al_pagar)
        self.assertTrue(ajustes.dcasa_correo_bienvenida)
        # El remitente de las pruebas (common.py); el de fábrica es ventas@babycaleb.com (TestRemitenteDeBabyCaleb).
        self.assertEqual(ajustes.dcasa_correo_remitente, 'ventas@example.com')
        self.assertEqual(ajustes.dcasa_correo_responder_a, 'clientes@babycaleb.com')
        self.assertEqual(ajustes.dcasa_correo_nombre, 'Baby Caleb')
        # Apagar «al pagar» se queda apagado (Odoo borra el parámetro: no vuelve el valor de fábrica).
        ajustes.dcasa_correo_al_pagar = False
        ajustes.execute()
        self.assertFalse(self.env['dcasa.correo']._config()['al_pagar'])
        self.assertFalse(self.ajustes().dcasa_correo_al_pagar)

    def test_el_remitente_tiene_que_ser_un_correo(self):
        with self.assertRaises(ValidationError):
            self.env['res.config.settings'].create({'dcasa_correo_remitente': 'ventas@dcasapty'})
        with self.assertRaises(ValidationError):
            self.env['res.config.settings'].create({'dcasa_correo_responder_a': 'info dcasapty.com'})

    def test_la_prueba_solo_la_manda_un_administrador_y_pide_correo(self):
        vendedora = self.vendedora
        with self.assertRaises(AccessError):
            self.env['res.config.settings'].with_user(vendedora).action_dcasa_correo_prueba()
        self.con_clave()
        sin_correo = new_test_user(self.env, login='correo_admin_sin', email=False,
                                   groups='base.group_user,base.group_system')
        sin_correo.partner_id.email = False
        with self.assertRaisesRegex(UserError, 'no tiene un correo'):
            self.ajustes(sin_correo).action_dcasa_correo_prueba()

    def test_sin_clave_la_prueba_explica_donde_va(self):
        with self.assertRaisesRegex(UserError, 'RESEND_API_KEY'):
            self.ajustes(self.admin).action_dcasa_correo_prueba()

    def test_la_prueba_le_llega_a_quien_la_pide_aunque_este_apagado(self):
        self.con_clave()
        with self.transporte():
            accion = self.ajustes(self.admin).action_dcasa_correo_prueba()
        self.assertEqual(accion['params']['type'], 'success')
        self.assertIn(self.admin.email, accion['params']['message'])
        (llamada,) = self.post.call_args_list
        datos = llamada.kwargs['json']
        self.assertEqual(datos['to'], [self.admin.email])
        self.assertIn('Este es un correo de prueba', datos['html'])
        self.assertIn('Escríbenos por WhatsApp', datos['html'])
        # El titular, como frase (marca Baby Caleb: nunca en caja alta).
        self.assertRegex(datos['html'], r'<h1[^>]*>Correo de prueba</h1>')

    def test_si_resend_rechaza_la_prueba_el_error_se_ve_sin_la_clave(self):
        self.con_clave()
        eco = respuesta(403, {'message': f'The dcasapty.com domain is not verified (key {CLAVE})'})
        with self.transporte(eco), self.errores_de_envio(), self.assertRaises(UserError) as error:
            self.ajustes(self.admin).action_dcasa_correo_prueba()
        texto = error.exception.args[0]
        self.assertIn('domain is not verified', texto)
        self.assertNotIn(CLAVE, texto)
        self.assertNotIn('DCASA_', texto)

    def test_la_clave_no_queda_en_la_base_ni_en_los_logs(self):
        """El camino completo (pago, cola, envío con Resend rechazando y repitiendo la clave): ni rastro de ella."""
        self.encender()
        eco = respuesta(401, {'message': f'API key {CLAVE} is invalid'})
        with self.assertLogs('odoo', level=logging.DEBUG) as logs:
            logging.getLogger('odoo.addons.dcasa_correo').debug('inicio de la prueba de la clave')
            factura = self.factura()
            self.pagar(factura)
            self.procesar()
            correos = self.correos_de(factura) | self.correos_de(self.ana)
            self.assertEqual(len(correos), 2, 'La factura pagada y la bienvenida')
            with self.transporte(*([eco] * len(correos))):
                correos.send()
            self.ajustes().dcasa_correo_estado  # noqa: B018 - también lo que se muestra en Ajustes
        self.assertTrue(all(c.state == 'exception' for c in correos))
        self.assertNotIn(CLAVE, '\n'.join(logs.output))
        self.env.flush_all()
        for tabla, columna in COLUMNAS_A_REVISAR:
            with self.subTest(tabla=tabla, columna=columna):
                self.env.cr.execute(f'SELECT COUNT(*) FROM {tabla} WHERE {columna}::text LIKE %s',  # noqa: S608
                                    [f'%{CLAVE}%'])
                self.assertEqual(self.env.cr.fetchone()[0], 0)


@tagged('post_install', '-at_install')
class TestGuardarDesdeElNavegador(GuardarAjustesComoElNavegador):
    """La dueña (administradora sin el grupo de diseñador del sitio) guarda Ajustes › Correo a clientes con «Guardar».

    Antes fallaba con «No tienes permiso para modificar registros "Sitio web"» (website_dcasa,
    models/res_config_settings.py).
    """

    def test_la_duena_guarda_correo_a_clientes(self):
        nunca = patch('requests.post', side_effect=AssertionError('Guardar no le habla a Resend'))
        nunca.start()
        self.addCleanup(nunca.stop)
        self.guardar_ajustes('ajustes_duena', {'dcasa_correo_nombre': "D'CASA Prueba"})
        self.assertEqual(self.env['ir.config_parameter'].sudo().get_param(P_NOMBRE), "D'CASA Prueba")


@tagged('post_install', '-at_install')
class TestRemitenteDeBabyCaleb(CorreoCase):
    """Baby Caleb (el dueño, 2026-11-25): de fábrica sale de ventas@babycaleb.com y las respuestas llegan a
    clientes@babycaleb.com. Si alguien deja el remitente vacío (y la fábrica también), no sale ningún correo, ni la
    prueba, y Ajustes lo dice."""

    def setUp(self):
        super().setUp()
        self.ICP.set_param(P_REMITENTE, False)   # como queda al instalar
        self.ICP.set_param(P_RESPONDER_A, False)

    def sin_remitente_de_fabrica(self):
        return patch.object(correo_modelo, 'REMITENTE', '')

    def test_de_fabrica_ventas_y_respuestas_a_clientes(self):
        self.assertEqual((REMITENTE, RESPONDER_A), ('ventas@babycaleb.com', 'clientes@babycaleb.com'))
        config = self.env['dcasa.correo']._config()
        self.assertEqual((config['remitente'], config['nombre'], config['responder_a']),
                         ('ventas@babycaleb.com', 'Baby Caleb', 'clientes@babycaleb.com'))
        self.con_clave()
        estado = self.env['res.config.settings'].create({}).dcasa_correo_estado
        self.assertIn('Clave cargada', estado)
        self.assertNotIn('Falta el remitente', estado)

    def test_ajustes_dice_que_falta_el_remitente(self):
        self.con_clave()
        with self.sin_remitente_de_fabrica():
            estado = self.env['res.config.settings'].create({}).dcasa_correo_estado
        self.assertIn('Falta el remitente', estado)

    def test_sin_remitente_no_sale_ni_la_prueba(self):
        self.con_clave()
        with self.sin_remitente_de_fabrica(), self.transporte(), self.assertRaises(UserError) as error:
            self.env['dcasa.correo']._enviar_prueba(self.admin)
        self.assertIn('Falta el remitente', str(error.exception))
        self.post.assert_not_called()

    def test_sin_remitente_la_sesion_no_le_pide_nada_a_resend(self):
        """Si algo llegara a la sesión sin remitente (un correo ya en la cola), no se manda: queda como no enviado."""
        sesion = resend.SesionResend(CLAVE, {'remitente': '', 'nombre': 'Baby Caleb', 'responder_a': '',
                                             'a_clientes': True, 'entorno': 'produccion'}, ['admin.correo@example.com'])
        mensaje = EmailMessage()
        mensaje['Subject'] = 'Prueba'
        mensaje['To'] = 'admin.correo@example.com'
        mensaje['X-Dcasa-Clase'] = 'prueba'   # la prueba al equipo sí podría salir: solo la frena el remitente
        mensaje.set_content('Hola')
        with self.assertRaises(RuntimeError) as error:
            sesion.send_message(mensaje, smtp_to_list=['admin.correo@example.com'])
        self.assertIn(resend.PREFIJO_NO_ENVIADO, str(error.exception))
        self.assertIn('Falta el remitente', str(error.exception))
        self.post.assert_not_called()
