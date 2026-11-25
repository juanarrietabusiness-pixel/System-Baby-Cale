"""El correo con la marca Baby Caleb (docs/MARCA_BABY_CALEB.md) y lo que pidió la dueña el 17/10/2026: limpio, un
solo botón en pastilla naranja con la letra navy, WhatsApp como enlace de texto, nada de D'CASA (ni su azul, ni su
amarillo, ni sus letras), Montserrat con respaldo Arial/Helvetica, estilos en línea, sistema plano, el logo con la
dirección pública del sitio y un pie corto que sale de la empresa (nada escrito a mano)."""
from unittest.mock import patch

from lxml import html

from odoo import Command
from odoo.addons.dcasa_invoice.tests import marca
from odoo.addons.dcasa_invoice.tests.marca import estilo
from odoo.tests import tagged

from .common import CorreoCase


@tagged('post_install', '-at_install')
class TestLayout(CorreoCase):

    def cuerpo(self, registro=None, plantilla='dcasa_correo.plantilla_bienvenida', tipo='bienvenida'):
        """El correo tal como queda en la cola (con el layout ya aplicado)."""
        registro = registro or self.ana
        destino = registro if registro._name == 'res.partner' else registro.partner_id
        self.encender()
        self.env['dcasa.correo'].sudo()._postear(registro, self.env.ref(plantilla), destino, tipo=tipo)
        return self.correos_de(registro)[-1].body_html

    def botones(self, arbol):
        """Las celdas con el relleno naranja que hacen de botón."""
        return marca.botones_naranja(arbol)

    def test_la_marca_de_baby_caleb_sin_rastro_de_dcasa_y_sistema_plano(self):
        factura = self.factura()
        self.pagar(factura, contexto={'dcasa_sin_correo_auto': True})
        cuerpos = {
            'bienvenida': self.cuerpo(),
            'factura': self.cuerpo(factura, 'dcasa_correo.plantilla_factura', 'factura'),
        }
        for nombre, cuerpo in cuerpos.items():
            with self.subTest(correo=nombre):
                arbol = marca.correo_con_la_marca(self, cuerpo, nombre)
                self.assertIn('name="color-scheme" content="light"', cuerpo)
                # La página crema y la tarjeta en la superficie, con su radio grande (24 px).
                cuerpo_html = arbol.find('.//body')
                self.assertIn('background-color:#f9f6ed', estilo(cuerpo_html))
                (tarjeta,) = [t for t in arbol.iter('table') if 'background-color:#f2efe5' in estilo(t)]
                self.assertIn('border-radius:24px', estilo(tarjeta))
                # El texto del correo en navy y con Montserrat.
                (texto,) = [td for td in arbol.iter('td') if 'line-height:1.6' in estilo(td)
                            and 'font-size:16px' in estilo(td) and td.find('.//table') is None]
                self.assertIn(f'color:#{marca.NAVY}', estilo(texto))

    def test_un_solo_boton_en_pastilla_naranja_con_letra_navy_y_whatsapp_de_texto(self):
        cuerpo = self.cuerpo()
        arbol = html.fromstring(cuerpo)
        (celda,) = self.botones(arbol)
        boton = marca.es_pastilla_navy_sobre_naranja(self, celda)
        self.assertEqual(boton.text_content().strip(), 'Entrar a Mi cuenta')
        self.assertEqual(cuerpo.count('Escríbenos por WhatsApp'), 1)
        (whatsapp,) = [a for a in arbol.iter('a') if 'WhatsApp' in a.text_content()]
        self.assertEqual(whatsapp.text_content().strip(), '¿Dudas? Escríbenos por WhatsApp')
        self.assertTrue(whatsapp.get('href').startswith(('https://api.whatsapp.com/send?phone=', 'http')),
                        whatsapp.get('href'))
        self.assertFalse([a for a in whatsapp.iterancestors() if f'bgcolor:#{marca.NARANJA}' in estilo(a)],
                         'Es texto, no botón')
        # El enlace de acción va en el naranja de letra (#985D2F: 4.60 sobre la superficie), subrayado.
        self.assertIn(f'color:#{marca.NARANJA_TEXTO}', estilo(whatsapp))
        self.assertIn('text-decoration:underline', estilo(whatsapp))
        for enlace in arbol.iter('a'):
            self.assertNotIn('access_token', enlace.get('href') or '')
        self.assertNotIn('o_mail_notification_btn', cuerpo, 'No usa el botón de acceso de Odoo')

    def test_la_factura_lleva_a_mi_cuenta_y_la_cotizacion_a_whatsapp(self):
        factura = self.factura()
        self.pagar(factura, contexto={'dcasa_sin_correo_auto': True})
        with patch('odoo.addons.dcasa_correo.models.correo.DcasaCorreo._mi_cuenta_instalado', return_value=True):
            arbol = html.fromstring(self.cuerpo(factura, 'dcasa_correo.plantilla_factura', 'factura'))
        (celda,) = self.botones(arbol)
        self.assertEqual(celda.text_content().strip(), 'Ver en Mi cuenta')
        self.assertEqual(next(celda.iter('a')).get('href'), f"{self.env['dcasa.correo']._base()}/mi-cuenta")
        orden = self.env['sale.order'].create({
            'partner_id': self.ana.id,
            'order_line': [Command.create({'product_id': self.mueble.id, 'product_uom_qty': 1})]})
        cuerpo = self.cuerpo(orden, 'dcasa_correo.plantilla_cotizacion', 'cotizacion')
        (celda,) = self.botones(html.fromstring(cuerpo))
        self.assertEqual(celda.text_content().strip(), 'Escríbenos por WhatsApp')
        self.assertNotIn('¿Dudas?', cuerpo, 'Si el botón ya es WhatsApp, no se repite')

    def test_el_logo_usa_la_direccion_publica_del_sitio(self):
        website = self.env['website'].search([('company_id', '=', self.company.id)], limit=1)
        # Una copia sin ninguna dirección pública (como una base en una máquina): web.base.url tal cual.
        self.ICP.set_param('web.base.url', 'http://localhost:8069')
        self.company.website = False
        website.domain = False
        (logo,) = html.fromstring(self.cuerpo()).iter('img')
        self.assertEqual(logo.get('src'), 'http://localhost:8069/dcasa_base/static/img/logo.png')
        # Producción: la dirección pública del sitio, aunque web.base.url fuera una local.
        website.domain = 'https://babycaleb.com'
        (logo,) = html.fromstring(self.cuerpo(self.beto)).iter('img')
        self.assertEqual(logo.get('src'), 'https://babycaleb.com/dcasa_base/static/img/logo.png')
        self.assertEqual(logo.get('alt'), 'Baby Caleb Panamá', 'el nombre de la empresa')

    def test_el_pie_corto_sale_de_la_empresa_y_del_sitio(self):
        website = self.env['website'].search([], order='sequence, id', limit=1)
        website.dcasa_whatsapp_number = '+507 6999-0001'
        self.company.write({'street': 'Frente al Parque de Prueba', 'street2': False, 'city': 'La Chorrera'})
        texto = html.fromstring(self.cuerpo()).text_content()
        self.assertIn(self.company.name, texto)
        self.assertIn('Frente al Parque de Prueba, La Chorrera', texto)
        self.assertIn('WhatsApp +507 6999-0001', texto)
        website.dcasa_whatsapp_number = '+507 6999-0002'
        self.assertIn('WhatsApp +507 6999-0002', html.fromstring(self.cuerpo(self.beto)).text_content())

    def test_el_titular_saluda_por_el_nombre_en_navy_como_frase(self):
        arbol = html.fromstring(self.cuerpo())
        (titular,) = arbol.iter('h1')
        self.assertEqual(titular.text_content().strip(), '¡Te damos la bienvenida, Ana!')
        propio = estilo(titular)
        self.assertIn(f'color:#{marca.NAVY}', propio)
        self.assertIn('font-weight:bold', propio)
        self.assertTrue(propio.startswith('margin:0;font-family:montserrat,arial,helvetica'), propio)
        self.assertNotIn('text-transform', propio, 'Nunca en caja alta: el titular se escribe como frase')

    def test_los_titulares_se_escriben_como_frase(self):
        """Marca Baby Caleb: ningún titular en caja alta (los de D'CASA lo estaban: «RECIBIMOS TU ABONO»)."""
        factura = self.factura()
        self.pagar(factura, contexto={'dcasa_sin_correo_auto': True})
        (titular,) = html.fromstring(self.cuerpo(factura, 'dcasa_correo.plantilla_factura', 'factura')).iter('h1')
        texto = titular.text_content().strip()
        self.assertEqual(texto, '¡Tu compra está pagada!')
        self.assertNotEqual(texto, texto.upper())
