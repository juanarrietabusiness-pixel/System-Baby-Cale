"""Con el ``puntos.json`` de fábrica (todas las cifras en PENDIENTE y el programa de vendedores apagado: decisión del
dueño, 2026-11-18) las ventas funcionan igual y el programa no acredita, no canjea y no promete nada.

Aquí NO se ponen cifras de prueba: rige el archivo tal cual. Lo que se comprueba:

* una venta del mostrador (cotización → confirmar → factura → pago), una de la tienda web y una factura directa se
  completan sin error, sin puntos de compra, sin referido, sin comisión de vendedor y sin avisos en el registro;
* la ficha del cliente sí recibe su código de socio (llave = celular): es con lo que entra a Mi cuenta;
* devolver, volver a borrador y cancelar siguen funcionando;
* ningún premio se puede pedir (ni con puntos de un ajuste de Gerencia), ni en la app, ni en el carrito, ni de vendedor;
* el cumpleaños no regala nada y la compra manual se niega diciendo por qué;
* la factura impresa no promete puntos;
* la pantalla de Ajustes › Programa de vendedores se abre, dice qué falta y no guarda;
* las páginas /socios, /socios/premios, /socios/terminos, /socios/registro, /vendedores/terminos y el carrito no
  enseñan cifras ni se rompen.
"""
import re
from html import unescape

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import HttpCase, new_test_user, tagged

from ..models import reglas as R
from ..models import reglas_vendedores as RV
from .common import PIN_DE_PRUEBA, SociosCommon, reglas_de_fabrica

# Cifras que no pueden aparecer en ninguna página (eran las de la empresa de la que se copió el sistema).
CIFRAS_PROHIBIDAS = re.compile(
    r'\b(?:1|500|250|400|1,000|2,500|5,000|10,000|3,000|20,000)\s+puntos?\b|\b72\s+horas\b|100 puntos = \$1|'
    r'punto por cada dólar|\b\d+(?:[.,]\d+)?\s?%', re.IGNORECASE)


@tagged('post_install', '-at_install')
class TestVentasConTodoPendiente(SociosCommon):
    CON_CIFRAS_DE_PRUEBA = False

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env.ref('website.default_website')

    def setUp(self):
        super().setUp()
        self.assertEqual(R.cargar_reglas(), reglas_de_fabrica(), 'rige puntos.json tal cual, sin parches')
        self.assertFalse(R.programa_disponible(R.cargar_reglas()))

    # ------------------------------------------------------------------ ayudas

    def sin_rastro_del_programa(self, *personas, factura=None):
        """Nada del programa se movió: ni compras, ni puntos, ni comisiones."""
        for persona in personas:
            ficha = persona.commercial_partner_id
            self.assertFalse(self.env['dcasa.compra'].search([('partner_id', '=', ficha.id)]), persona.name)
            self.assertFalse(self.env['dcasa.movimiento'].search([('partner_id', '=', ficha.id)]), persona.name)
            self.assertEqual(ficha.dcasa_saldo, 0, persona.name)
            self.assertFalse(self.env['dcasa.vend.movimiento'].search([('partner_id', '=', ficha.id)]), persona.name)
        if factura:
            self.assertFalse(factura.dcasa_compra_ids)
            self.assertFalse(factura.dcasa_vend_comision_ids)

    def pagada(self, factura):
        factura.invalidate_recordset(['payment_state'])
        self.assertIn(factura.payment_state, ('paid', 'in_payment'))

    # ------------------------------------------------------------------ ventas

    def test_venta_del_mostrador_se_cobra_sin_puntos_ni_errores(self):
        """Cotización → confirmar → factura → pago, como en la tienda, con un cliente invitado por otro socio."""
        self.assertTrue(self.cliente._dcasa_asignar_padrino(self.padrino))
        with self.assertNoLogs('odoo.addons.dcasa_socios', level='WARNING'):
            orden = self.env['sale.order'].create({
                'partner_id': self.cliente.id,
                'order_line': [Command.create({'product_id': self.producto.id, 'product_uom_qty': 2})],
            })
            orden.action_confirm()
            factura = orden._create_invoices()
            factura.action_post()
            self.pagar(factura)
        self.assertEqual(orden.state, 'sale')
        self.pagada(factura)
        self.sin_rastro_del_programa(self.cliente, self.padrino, factura=factura)
        self.assertFalse(self.cliente.dcasa_referido_pagado_en, 'el referido no se paga ni se sella')
        # La ficha sí queda con su código (llave = celular): con él entra a Mi cuenta a ver la compra.
        self.assertTrue(self.cliente.commercial_partner_id.dcasa_socio_codigo)
        self.assertEqual(self.cliente.commercial_partner_id.dcasa_celular, '60000002')

    def test_venta_de_la_tienda_web_se_cobra_sin_puntos(self):
        orden = self.env['sale.order'].sudo().create({
            'partner_id': self.cliente.id, 'website_id': self.website.id,
            'order_line': [Command.create({'product_id': self.producto.id, 'product_uom_qty': 1})],
        })
        valores = orden._dcasa_valores_puntos_web()
        self.assertFalse(valores['dcasa_programa_disponible'], 'el carrito no habla del programa')
        self.assertFalse(valores['dcasa_premios'])
        with self.assertNoLogs('odoo.addons.dcasa_socios', level='WARNING'):
            orden.action_confirm()
            factura = orden._create_invoices()
            factura.action_post()
            self.pagar(factura)
        self.pagada(factura)
        self.sin_rastro_del_programa(self.cliente, factura=factura)

    def test_factura_directa_pagada_en_dos_abonos(self):
        factura = self.factura(precio=300.0, pagar=False)
        self.assertIsNone(factura._dcasa_socios_factura(), 'sin código y sin programa: la factura no dice nada')
        self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=factura.ids,
        ).create({'payment_date': factura.invoice_date, 'amount': 100.0})._create_payments()
        factura.invalidate_recordset(['payment_state'])
        self.assertEqual(factura.payment_state, 'partial')
        self.pagar(factura)   # el último abono, por lo que falta
        self.pagada(factura)
        self.sin_rastro_del_programa(self.cliente, factura=factura)

    def test_con_vendedor_no_hay_comision_y_la_venta_sigue(self):
        """El programa de vendedores está apagado: una venta con código de vendedor se cobra igual y no paga nada."""
        self.assertIs(RV.seccion(R.cargar_reglas())['programaActivo'], False)
        vera = self.vendedor('Vera Vende', '8-777-777', '6100-0077', tipo='empleado')
        factura = self.factura(vendedor=vera)
        self.pagada(factura)
        self.assertFalse(self.env['dcasa.vend.comision'].search([('partner_id', '=', vera.id)]))
        self.assertEqual(vera.dcasa_vend_saldo, 0)
        self.sin_rastro_del_programa(self.cliente, factura=factura)

    def test_devolver_volver_a_borrador_y_cancelar_siguen_funcionando(self):
        factura = self.factura()
        nota = factura._reverse_moves([{'ref': 'Devolución de prueba'}])
        nota.action_post()
        self.assertEqual(nota.state, 'posted')
        otra = self.factura()
        otra.button_draft()
        otra.button_cancel()
        self.assertEqual(otra.state, 'cancel')
        self.sin_rastro_del_programa(self.cliente)

    # ------------------------------------------------------------------ nada se canjea ni se regala

    def test_ningun_premio_se_puede_pedir_ni_con_puntos_de_un_ajuste(self):
        socia = self.env['res.partner'].create({'name': 'Sara Socia', 'phone': '6000-0050'})
        socia._dcasa_asegurar_ficha()
        socia._dcasa_guardar_pin(PIN_DE_PRUEBA)
        self.env['dcasa.ajuste.wizard'].create(
            {'partner_id': socia.id, 'puntos': 5000, 'motivo': 'Prueba: un ajuste de Gerencia'}).action_confirmar()
        premio = self.env['dcasa.premio'].create({'name': 'Premio de prueba', 'puntos': 100, 'valor': 1, 'costo': 1})
        libre = self.env.ref('dcasa_socios.premio_libre_web')
        for cual, puntos in ((premio, None), (libre, 200)):
            with self.subTest(premio=cual.name), self.assertRaisesRegex(UserError, 'todavía no se pueden pedir'):
                self.env['dcasa.canje']._pedir(socia, cual, puntos=puntos)
        self.assertFalse(self.env['dcasa.canje'].search([('partner_id', '=', socia.id)]))
        self.assertEqual(socia.dcasa_saldo, 5000, 'los puntos no se movieron')
        orden = self.env['sale.order'].sudo().create({
            'partner_id': socia.id, 'website_id': self.website.id,
            'order_line': [Command.create({'product_id': self.producto.id, 'product_uom_qty': 1})],
        })
        with self.assertRaises(UserError):
            orden._dcasa_usar_puntos_web(premio=premio)
        self.assertFalse(orden.order_line.filtered('dcasa_canje_id'))

    def test_el_vendedor_tampoco_canjea(self):
        vera = self.vendedor('Vera Canje', '8-778-778', '6100-0078', tipo='empleado')
        premio = self.env['dcasa.premio'].create({'name': 'Mercancía de prueba', 'puntos': 100, 'tipo': 'producto',
                                                  'para_vendedores': True})
        with self.assertRaisesRegex(UserError, 'todavía no está encendido'):
            self.env['dcasa.vend.canje']._pedir(vera, premio)

    def test_el_cumpleanos_no_regala_nada(self):
        self.factura()
        ficha = self.cliente.commercial_partner_id
        ficha.dcasa_cumple = fields.Datetime.now().strftime('%m-%d')
        self.assertFalse(self.env['dcasa.canje']._felicitar_a_los_de_hoy(fields.Datetime.now()))
        self.env['dcasa.canje']._cron_programa()
        self.sin_rastro_del_programa(self.cliente)

    def test_la_compra_manual_se_niega_y_dice_por_que(self):
        asistente = self.env['dcasa.compra.manual.wizard'].create(
            {'partner_id': self.cliente.id, 'factura': 'F-0001', 'monto': 107.0})
        with self.assertRaisesRegex(UserError, 'todavía no da puntos'):
            asistente.action_confirmar()
        self.assertFalse(self.env['dcasa.compra'].search([]))

    # ------------------------------------------------------------------ lo que se imprime y se ve

    def test_la_factura_impresa_no_promete_puntos(self):
        factura = self.factura()
        datos = factura._dcasa_socios_factura()
        self.assertFalse(datos['disponible'])
        self.assertFalse(datos['compra'])
        self.assertEqual(datos['por_ganar'], 0)
        html = unescape(self.env['ir.actions.report']._render_qweb_html(
            'account.report_invoice', factura.ids)[0].decode())
        self.assertIn(self.cliente.commercial_partner_id.dcasa_socio_codigo, html, 'el código sí: entra a Mi cuenta')
        for promesa in ('Puntos de esta compra', 'Suma puntos', 'Revísalos y canjéalos', 'Tu saldo'):
            self.assertNotIn(promesa, html)
        sin_codigo = self.env['res.partner'].create({'name': 'Sin Código', 'phone': '6000-0051'})
        borrador = self.factura(partner=sin_codigo, pagar=False)
        self.assertIsNone(borrador._dcasa_socios_factura(), 'sin código, ninguna invitación a un programa sin cifras')

    def test_la_pantalla_de_ajustes_de_vendedores_se_abre_y_no_guarda(self):
        gerente = new_test_user(self.env, login='pend_gerente', name='Gerente Pendiente',
                                groups='base.group_user,sales_team.group_sale_manager,dcasa_base.group_gerencia')
        Ajustes = self.env['dcasa.vend.ajustes'].with_user(gerente)
        with self.assertNoLogs('odoo.addons.dcasa_socios', level='WARNING'):
            pantalla = Ajustes.create({})
            self.assertFalse(pantalla.dcasa_vend_cargado)
            self.assertIn('puntos vale un dólar', str(pantalla.dcasa_vend_resumen))
            self.env['res.config.settings'].create({})   # Ajustes de Odoo se abre igual
        pantalla.dcasa_vend_programa = True
        with self.assertRaisesRegex(UserError, 'No se guardó nada'):
            pantalla.execute()
        self.assertFalse(self.env['dcasa.vend.reglas'].search([]), 'no nació ninguna versión')
        self.assertFalse(RV.seccion(self.env['dcasa.vend.reglas']._vigentes())['programaActivo'])


@tagged('post_install', '-at_install')
class TestPaginasConTodoPendiente(HttpCase):
    """Las páginas del programa con el puntos.json de fábrica: se abren, dicen que no está disponible y no enseñan
    ninguna cifra."""

    def setUp(self):
        super().setUp()
        self.assertFalse(R.programa_disponible(R.cargar_reglas()))
        self.authenticate(None, None)

    def pagina(self, ruta):
        respuesta = self.url_open(ruta)
        self.assertEqual(respuesta.status_code, 200, ruta)
        return ' '.join(unescape(respuesta.text).split())

    @staticmethod
    def visible(html):
        # Solo el contenido de la página (``<main>``): la cabecera y el pie del sitio son de todas las páginas y llevan
        # textos que decidió el dueño («Venta 100% online», 2026-11-18), que no son cifras del programa.
        principal = re.search(r'<main\b.*?</main>', html, flags=re.S)
        html = principal.group(0) if principal else html
        return ' '.join(re.sub(r'<[^>]+>', ' ', re.sub(r'<script.*?</script>|<style.*?</style>', '', html,
                                                       flags=re.S)).split())

    def sin_cifras(self, html, ruta):
        self.assertFalse(CIFRAS_PROHIBIDAS.findall(self.visible(html)), ruta)

    def test_socios_dice_que_no_esta_disponible(self):
        for ruta in ('/socios', '/socios/terminos', '/socios/premios'):
            with self.subTest(ruta=ruta):
                html = self.pagina(ruta)
                self.assertIn(R.NO_DISPONIBLE, html)
                self.sin_cifras(html, ruta)
                for promesa in ('o_dcasa_steps', 'Cómo los ganas', 'Cómo ganas invitando', 'Tu cumpleaños',
                                'tus puntos te están esperando', '>Pedir<'):
                    self.assertNotIn(promesa, html)
        # Entrar con celular y PIN sigue: es la puerta de Mi cuenta.
        self.assertIn('action="/socios/entrar"', self.pagina('/socios'))

    def test_el_registro_no_promete_puntos_ni_regalos(self):
        html = self.pagina('/socios/registro')
        self.assertIn('Tu cumpleaños (opcional)', html)
        self.assertNotIn('te regalamos puntos', html)
        self.assertNotIn('ganan los dos', html)
        self.sin_cifras(html, '/socios/registro')

    def test_los_terminos_de_vendedores_no_inventan_cifras(self):
        html = self.pagina('/vendedores/terminos')
        self.assertIn('todavía no está encendido', html)
        self.assertNotRegex(self.visible(html), r'\b72\b')
        self.sin_cifras(html, '/vendedores/terminos')
