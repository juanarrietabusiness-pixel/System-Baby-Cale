"""Mi cuenta con el ``puntos.json`` de fábrica (todo PENDIENTE: decisión del dueño, 2026-11-18).

Se entra igual, se ven las compras y lo que falta pagar igual, y la parte de los puntos dice que el programa todavía
no está disponible: sin cifras, sin premios, sin «invita y gana» y sin el enlace para invitar.
"""
import re
from html import unescape

from odoo.addons.dcasa_socios.models import reglas as R
from odoo.tests import HttpCase, tagged

from ..models.mi_cuenta import monto
from .common import MiCuentaComun

CIFRAS = re.compile(r'\b\d[\d,]*\s+puntos?\b|equivalen a|\b\d+\s+horas\b|punto por cada dólar', re.IGNORECASE)


@tagged('post_install', '-at_install')
class TestMiCuentaConTodoPendiente(MiCuentaComun, HttpCase):

    def setUp(self):
        super().setUp()
        self.preparar(con_cifras_de_prueba=False)
        self.assertFalse(R.programa_disponible(R.cargar_reglas()))
        self.authenticate(None, None)

    def visible(self, html):
        sin_codigo = re.sub(r'<script.*?</script>|<style.*?</style>', '', unescape(html), flags=re.S)
        return ' '.join(re.sub(r'<[^>]+>', ' ', sin_codigo).split())

    def test_el_inicio_dice_lo_que_falta_pagar_y_que_el_programa_no_esta_disponible(self):
        html = self.entrar(origen='mi-cuenta').text
        texto = self.visible(html)
        self.assertIn('Te falta', texto, 'lo que falta pagar sigue igual')
        self.assertIn(monto(self.factura._dcasa_estado_abono()['saldo']), texto)
        self.assertIn(R.NO_DISPONIBLE, texto)
        for promesa in ("Socios D'CASA · tus puntos", 'Ver premios', 'Invitar a un amigo', 'Activar mis puntos',
                        'Cada compra suma'):
            self.assertNotIn(promesa, texto)
        self.assertFalse(CIFRAS.findall(texto), texto)

    def test_la_pagina_de_puntos_no_promete_nada(self):
        self.entrar()
        respuesta = self.url_open('/mi-cuenta/puntos')
        self.assertEqual(respuesta.status_code, 200)
        texto = self.visible(respuesta.text)
        self.assertIn(R.NO_DISPONIBLE, texto)
        for promesa in ('Invita y gana', 'Ver y pedir premios', 'Te faltan', 'Tu primera compra suma puntos',
                        f'/r/{self.socia.dcasa_socio_codigo}'):
            self.assertNotIn(promesa, respuesta.text)
        self.assertFalse(CIFRAS.findall(texto), texto)
        datos = self.env['dcasa.mi.cuenta']._mc_puntos(self.socia)
        self.assertEqual((datos['disponible'], datos['canje_disponible'], datos['link'], datos['al_padrino'],
                          datos['siguiente'], datos['premios']), (False, False, '', '', None, 0))

    def test_las_compras_se_ven_igual(self):
        self.entrar()
        html = self.url_open('/mi-cuenta/compras').text
        for nombre in (self.pedido.name, self.suelta.name):
            self.assertIn(nombre, html)
        detalle = self.url_open(f'/mi-cuenta/compras/{self.pedido.id}')
        self.assertEqual(detalle.status_code, 200)
        self.assertNotIn('te sumó', detalle.text, 'ninguna compra suma puntos')
