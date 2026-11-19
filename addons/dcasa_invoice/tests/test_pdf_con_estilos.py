"""El PDF sale con el diseño de la marca (Baby Caleb) aunque la URL pública no se alcance desde el contenedor.

wkhtmltopdf pide los estilos y las fuentes por HTTP. Si los pide a la URL pública (web.base.url),
desde dentro del contenedor no llegan y la factura sale como texto suelto, sin cuadros ni marca:
así se vio en staging. Los pide siempre al propio Odoo (127.0.0.1).
"""
import re
import shutil
from unittest import skipUnless

from odoo import fields
from odoo.tests import HttpCase, tagged
from odoo.tools import config

from . import marca

HOJA = '/dcasa_invoice/static/src/scss/report_dcasa.scss'
MONTSERRAT = [f'/dcasa_base/static/src/fonts/Montserrat-{peso}.ttf'
              for peso in ('Regular', 'Medium', 'SemiBold', 'Bold')]


@tagged('post_install', '-at_install')
class TestPdfConEstilos(HttpCase):

    def setUp(self):
        super().setUp()
        parametros = self.env['ir.config_parameter'].sudo()
        # Una URL pública que desde aquí no responde, como la de Cloudflare vista desde el contenedor.
        parametros.set_param('web.base.url', 'https://dcasa-no-alcanzable.invalid')
        parametros.set_param('web.base.url.freeze', True)
        parametros.set_param('report.url', False)

    def test_los_estilos_se_piden_al_propio_odoo(self):
        url = self.env['ir.actions.report']._get_report_url()
        self.assertEqual(url, f"http://127.0.0.1:{config['http_port']}")

    def test_report_url_explicito_manda(self):
        self.env['ir.config_parameter'].sudo().set_param('report.url', 'http://interno:9000')
        self.assertEqual(self.env['ir.actions.report']._get_report_url(), 'http://interno:9000')

    def _factura(self):
        cliente = self.env['res.partner'].create({'name': 'Cliente PDF'})
        producto = self.env['product.product'].create({'name': 'Producto PDF', 'type': 'consu'})
        factura = self.env['account.move'].create({
            'move_type': 'out_invoice', 'partner_id': cliente.id, 'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {'product_id': producto.id, 'quantity': 1, 'price_unit': 99.0})],
        })
        factura.action_post()
        return factura

    @skipUnless(shutil.which('wkhtmltopdf'), 'sin wkhtmltopdf (la imagen Docker lo comprueba en CI)')
    def test_la_factura_en_pdf_lleva_las_fuentes_de_marca(self):
        pdf, _tipo = self.env['ir.actions.report'].with_context(force_report_rendering=True)._render_qweb_pdf(
            'account.account_invoices', self._factura().ids)
        self.assertTrue(pdf.startswith(b'%PDF'))
        # La letra de la marca solo llega si wkhtmltopdf pudo cargar la hoja de estilos.
        self.assertIn(b'Montserrat', pdf, 'La factura salió sin estilos (wkhtmltopdf no cargó el CSS)')
        for letra in (b'Anton', b'Oswald', b'Inter-'):
            self.assertNotIn(letra, pdf, 'ni rastro de las letras de D\'CASA')

    def test_la_hoja_de_los_documentos_es_la_de_baby_caleb(self):
        """Lo que wkhtmltopdf lee (el CSS ya compilado que enlaza el informe, pedido al propio Odoo): Montserrat de los
        TTF fijos de dcasa_base (wkhtmltopdf no lee woff2), que se sirven de verdad; el texto en navy, el naranja y el
        verde solo de relleno y filete, y nada del azul, del amarillo ni de las letras de D\'CASA. Se comprueba sin
        wkhtmltopdf: corre en cualquier máquina."""
        css, hoja = marca.css_de_la_hoja(self, 'account.report_invoice_with_payments', self._factura(), HOJA)
        self.assertIn("font-family:'DCASAMontserrat'", hoja.replace(' ', '').replace('"', "'"))
        for ruta in MONTSERRAT:
            self.assertIn(ruta, hoja, f'la hoja no declara {ruta}')
            respuesta = self.url_open(ruta)
            self.assertEqual(respuesta.status_code, 200, ruta)
            self.assertTrue(respuesta.content.startswith(b'\x00\x01\x00\x00'), f'{ruta} no es un TrueType')
        self.assertNotIn('woff', hoja, 'wkhtmltopdf no lee woff2')
        marca.sin_rastro_de_dcasa(self, hoja, HOJA)
        minusculas = hoja.lower()
        for color in (marca.NAVY, marca.NARANJA, marca.SALVIA):
            self.assertIn(color, minusculas, f'falta el #{color.upper()} del contrato')
        # El naranja y el verde de relleno nunca son el color de una letra (2.37 y 1.90 sobre el papel).
        self.assertEqual(marca.letra_de_relleno(hoja), [])
        # Los titulares, como frase: la hoja no pone el título del documento en caja alta.
        titulo = re.search(r'\.o_report_layout_dcasa \.o_dcasa_title,[^{]*\{([^}]*)\}', hoja)
        self.assertTrue(titulo, 'no encontré el estilo del título')
        self.assertIn('text-transform:none', titulo.group(1).replace(' ', ''))
        self.assertIn('font-weight:700', titulo.group(1).replace(' ', ''))
        self.assertTrue(css)
