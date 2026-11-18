"""Camila dice el nombre de la empresa de Ajustes, nunca el de otra (decisión del dueño, 2026-11-18).

El asunto fijo, el mensaje de WhatsApp ya escrito del botón del correo, el logo y el pie del correo, la página
«Sí, quiero» de /novedades/si y el cuadro «¿quiere recibir novedades?» leen ``res.company.name``.
"""
from unittest.mock import patch

from lxml import html as lxml_html

from odoo.addons.dcasa_brian.models import proveedores as P
from odoo.tests import HttpCase, tagged

from ..models import envio as E
from ..models import reglas as R
from .comun import CamilaComun

EMPRESA = 'Tienda de Prueba ZZ'


@tagged('post_install', '-at_install')
class TestCamilaDiceLaEmpresa(CamilaComun):

    def setUp(self):
        super().setUp()
        self.env.company.name = EMPRESA

    def test_el_asunto_fijo_y_el_correo_dicen_la_empresa(self):
        with patch.object(P.ProveedorPrueba, 'chatear', side_effect=P.ProveedorError('sin conexión')):
            datos = self.armar()
        self.assertEqual(datos['campana']['asunto'], f'Lo que hay en {EMPRESA} esta quincena')
        campana = self.env['dcasa.camila.campana'].browse(datos['campana']['id'])
        campana.boton_whatsapp = True
        valores = self.Camila._valores_correo(campana)
        self.assertEqual(valores['empresa'], EMPRESA)
        self.assertIn(f'novedades de {EMPRESA} y me interesa', valores['whatsapp'].replace('%20', ' '))
        cuerpo = self.Camila._html(campana, para_resend=True)
        arbol = lxml_html.fromstring(cuerpo)
        self.assertEqual(arbol.xpath('//img')[0].get('alt'), EMPRESA, 'el logo lleva el nombre de la empresa')
        self.assertIn(f'Te llega porque nos diste tu correo en {EMPRESA}.', ' '.join(arbol.text_content().split()))
        self.assertNotIn('CASA', arbol.text_content())

    def test_el_segmento_de_resend_se_llama_como_la_empresa(self):
        self.assertEqual(E.NOMBRE_SEGMENTO.format(empresa=EMPRESA), f'{EMPRESA}: campaña que sale (Odoo)')

    def test_el_cuadro_de_la_venta_pregunta_por_la_empresa(self):
        vista = self.env.ref('dcasa_camila.dcasa_camila_pregunta_form')
        self.assertNotIn("D'CASA", vista.arch)
        self.assertIn('name="empresa"', vista.arch)
        pregunta = self.env['dcasa.camila.pregunta'].sudo().create({'partner_id': self.env.user.partner_id.id})
        self.assertEqual(pregunta.empresa, EMPRESA)
        self.assertNotIn("D'CASA", R.texto_whatsapp(1, EMPRESA))


@tagged('post_install', '-at_install')
class TestNovedadesDiceLaEmpresa(HttpCase):

    def test_la_pagina_si_quiero_dice_la_empresa(self):
        self.env['website'].get_current_website().company_id.name = EMPRESA
        html = self.url_open('/novedades/si?t=no-sirve').text
        self.assertIn(f'{EMPRESA} · Novedades por correo', html)
        self.assertNotIn("D'CASA Panamá · Novedades", html)
        self.assertNotIn('D&#39;CASA Panamá · Novedades', html)
