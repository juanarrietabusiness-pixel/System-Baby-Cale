"""La puerta del equipo (/master), el doble factor y los avisos con la marca Baby Caleb (docs/MARCA_BABY_CALEB.md):
crema, navy y el naranja de relleno con letra navy, Montserrat, el nombre de la empresa (nunca el de la plantilla de
origen) y nada del azul, el amarillo ni el Anton de D'CASA."""
import re

from odoo.tests import HttpCase, tagged

DE_DCASA_TEXTO = ("D'CASA", 'D&#39;CASA', 'D’CASA', 'dcasapty')
DE_DCASA_ESTILO = ('#1340b1', '#fed00f', '#0b2160', 'anton', 'oswald')


@tagged('post_install', '-at_install')
class TestMarcaDeLaPuerta(HttpCase):

    def test_la_puerta_del_equipo_con_la_marca_y_el_nombre_de_la_empresa(self):
        empresa = self.env.company.name
        html = self.url_open('/master').text
        main = html[html.index('<main'):html.index('</main>')]
        self.assertIn(f'Solo personal de {empresa}', main)
        self.assertIn('tucorreo@ejemplo.com', main, 'el ejemplo de correo no es de ninguna empresa')
        for de_origen in DE_DCASA_TEXTO:
            self.assertNotIn(de_origen, main)
        estilo = next(e for e in re.findall(r'<style>(.*?)</style>', html, re.S) if 'o_dcasa_master_tarjeta' in e)
        self.assertIn('body.o_dcasa_master { background: #F9F6ED; color: #1B3246;', estilo, 'el fondo crema')
        self.assertIn('background: #EE924A; color: #1B3246;', estilo, '«Entrar»: naranja con letra navy (5.56)')
        self.assertIn('border-radius: 999px', estilo, 'botones en pastilla')
        self.assertIn('Montserrat', estilo)
        for de_origen in DE_DCASA_ESTILO:
            self.assertNotIn(de_origen, estilo.lower())

    def test_la_marca_de_los_avisos_y_de_la_app_de_codigos_es_la_empresa(self):
        Usuarios = self.env['res.users']
        self.assertEqual(Usuarios._dcasa_marca(), self.env.company.name)
        self.assertEqual(Usuarios._dcasa_marca(self.env.ref('base.user_admin')),
                         self.env.ref('base.user_admin').company_id.name)
