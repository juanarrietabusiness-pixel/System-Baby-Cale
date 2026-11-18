"""Páginas legales: existen, están enlazadas en el pie y dicen lo que el sistema hace de verdad.

Baby Caleb (decisión del dueño, 2026-11-18): el mismo texto de la tienda de origen, palabra por palabra; solo cambia la
empresa. El RUC y la dirección que el dueño todavía no dio dicen PENDIENTE, a la vista."""
from odoo.tests import HttpCase, tagged

EMPRESA = 'Baby Caleb, RUC PENDIENTE, dirección PENDIENTE.'
CORREO = 'babycalebpanama@gmail.com'
# Lo de la tienda de origen que no puede quedar en ninguna de las dos páginas.
DE_LA_TIENDA_DE_ORIGEN = ("D'CASA", 'D&#39;CASA', '155779346', 'Libertadores', 'La Chorrera', 'dcasapty')


@tagged('post_install', '-at_install')
class TestPaginasLegales(HttpCase):

    def test_privacidad(self):
        respuesta = self.url_open('/privacidad')
        self.assertEqual(respuesta.status_code, 200)
        html = respuesta.text
        self.assertIn('Política de privacidad', html)
        self.assertIn(EMPRESA, html)
        self.assertIn(f'href="mailto:{CORREO}"', html)
        self.assertIn('Ley 81 de 2019', html)
        # Socios, con el nombre de la empresa, y el respaldo de Anthropic: el texto es el mismo, palabra por palabra.
        self.assertIn('Si eres Socio Baby Caleb', html)
        self.assertIn('nadie en Baby Caleb puede leerlo', html)
        self.assertIn('del programa Socios Baby Caleb', html)
        self.assertIn('Como respaldo podemos usar <strong>Anthropic</strong>', html)
        # El nombre de la plantilla sale en og:title: sin la marca de otra empresa.
        self.assertIn('<meta property="og:title" content="Página legal | Baby Caleb"/>', html)
        for dato in DE_LA_TIENDA_DE_ORIGEN:
            self.assertNotIn(dato, html)
        # El uso de IA con entrenamiento (Meta «-contributor») tiene que estar dicho en claro.
        self.assertIn('id="inteligencia-artificial"', html)
        self.assertIn('Meta puede usar ese contenido para entrenar', html)
        # Juan (el asistente que contesta a los clientes) usa el modelo «contributor» desde el 2026-11-03: la política
        # lo nombra a él, no solo a Brian, y dice que sus conversaciones pueden entrenar a Meta (Ley 81 de 2019).
        self.assertIn('te contesta primero <strong>Juan</strong>', html)
        self.assertRegex(html, r'tanto tus\s+conversaciones con Juan')
        self.assertRegex(html, r'notas de voz\s+y lee las fotos')
        self.assertIn('id="cookies"', html)

    def test_terminos(self):
        respuesta = self.url_open('/terminos')
        self.assertEqual(respuesta.status_code, 200)
        html = respuesta.text
        self.assertIn('Términos y condiciones', html)
        self.assertIn(f'Este sitio es de {EMPRESA}', html)
        self.assertIn('Programa Socios Baby Caleb', html)
        self.assertIn('una persona de Baby Caleb, vale lo que te confirmó la persona', html)
        self.assertIn('no incluyen el ITBMS', html)
        for dato in DE_LA_TIENDA_DE_ORIGEN:
            self.assertNotIn(dato, html)
        self.assertIn('href="/privacidad#inteligencia-artificial"', html)
        self.assertIn('href="/socios/terminos"', html)

    def test_pie_enlaza_paginas_legales_sin_ruc_inventado(self):
        """El pie enlaza las dos páginas. El RUC de Baby Caleb todavía no está: el pie no muestra ninguno."""
        html = self.url_open('/').text
        self.assertIn('href="/privacidad"', html)
        self.assertIn('href="/terminos"', html)
        self.assertNotIn('RUC ', html.split('id="footer"', 1)[-1].split('</footer>', 1)[0])
