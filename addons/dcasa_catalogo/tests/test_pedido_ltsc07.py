from odoo.addons.dcasa_catalogo.catalogo import PARAM_STOCK_PRUEBA, aplicar_stock_prueba
from odoo.addons.dcasa_catalogo.reglas import (
    asignar_foto,
    codigo_del_pedido,
    fila_para_comparar,
    precio_terminado_en_99,
)
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestReglasPedido(TransactionCase):
    """Reglas sin Odoo: precio .99, código aparte y a qué fila va cada foto."""

    def test_precios_terminan_en_99(self):
        self.assertEqual(precio_terminado_en_99(318.66), 318.99)
        self.assertEqual(precio_terminado_en_99(318.65999999999997), 318.99, 'Así viene del Excel')
        self.assertEqual(precio_terminado_en_99(439.98), 439.99)
        self.assertEqual(precio_terminado_en_99(186.64), 186.99)
        self.assertEqual(precio_terminado_en_99(129.99), 129.99, 'Ya termina en .99: igual')
        self.assertEqual(precio_terminado_en_99(100), 100.99, 'Se conserva la parte entera')
        self.assertIsNone(precio_terminado_en_99(None), 'Celda vacía: no se inventa un precio')

    def test_codigo_que_ya_existe_va_aparte(self):
        self.assertEqual(codigo_del_pedido('Y0300300', {'Y0300300'}, 'LTSC07'), 'Y0300300-LTSC07')
        self.assertEqual(codigo_del_pedido('908K', {'Y0300300'}, 'LTSC07'), '908K')

    def filas(self):
        datos = [
            ('908K', 'Cama tapizada King – beige', '203 × 193 × 123 cm'),
            ('908K', 'Cama tapizada King – negro', '203 × 193 × 123 cm'),
            ('908K', 'Cama tapizada King – gris', '203 × 193 × 123 cm'),
            ('809Q', 'Cama tapizada Queen – beige', '213 × 158 × 120 cm'),
            ('811Q', 'Cama tapizada Queen – beige', '213 × 158 × 120 cm'),
            ('822F', 'Cama tapizada Full – blanco', '193 × 135 × 110 cm'),
            ('825Q', 'Cama tapizada Queen – crema', '205 × 151 × 110 cm'),
            ('HK-BF-022-N-F-1-W', 'Cama tapizada Full – blanco', 'Full'),
            ('Y0400300-Q', 'Cama tapizada Queen – tela negra', '205 × 151 × 110 cm'),
            ('Y0400400-Q', 'Cama tapizada Queen – tela marrón', '205 × 151 × 110 cm'),
        ]
        return [fila_para_comparar(*d) for d in datos]

    def test_foto_por_codigo(self):
        filas = self.filas()
        r = asignar_foto('908K Cama tapizada King – Gris 203 × 193 × 123 cm.jpg', filas)
        self.assertEqual((r['fila'], r['como']), (2, 'codigo'), 'Código con varios colores: manda el color')
        r = asignar_foto('HK-BF-022-N-F-1-W.jpg', filas)
        self.assertEqual((r['fila'], r['como']), (7, 'codigo'))
        r = asignar_foto('908K Cama tapizada King.jpg', filas)
        self.assertIsNone(r['fila'], 'Sin color no se sabe de cuál de los tres es')

    def test_foto_por_descripcion(self):
        filas = self.filas()
        r = asignar_foto('Cama tapizada Queen – crema 205 × 151 × 110 cm.jpg', filas)
        self.assertEqual((filas[r['fila']]['codigo'], r['como']), ('825Q', 'descripcion'))
        r = asignar_foto('Cama tapizada Full – blanco 193 × 135 × 110 cm.jpg', filas)
        self.assertEqual(filas[r['fila']]['codigo'], '822F', 'Las medidas descartan al Full blanco sin medidas')

    def test_foto_dudosa_no_se_adivina(self):
        filas = self.filas()
        archivo = 'Cama tapizada Queen – beige 213 × 158 × 120 cm.jpg'
        r = asignar_foto(archivo, filas)
        self.assertEqual((r['fila'], r['como']), (None, 'ambigua'))
        self.assertIn('809Q', r['nota'])
        self.assertIn('811Q', r['nota'])
        r = asignar_foto(archivo, filas, {archivo: ('811Q', None, 'cabecero de canales')})
        self.assertEqual((filas[r['fila']]['codigo'], r['como']), ('811Q', 'decision'))
        self.assertEqual(asignar_foto('foto.jpg', filas)['como'], 'sin_coincidencia')

    def test_color_del_archivo_distinto_queda_avisado(self):
        filas = self.filas()
        archivo = 'Y0400300-Q  Queen tela marron205×151×110 cm.jpg'
        r = asignar_foto(archivo, filas)
        self.assertEqual(filas[r['fila']]['codigo'], 'Y0400300-Q')
        self.assertIn('marron', r['nota'], 'Se asigna por código, pero queda el aviso en el reporte')
        r = asignar_foto(archivo, filas, {archivo: ('Y0400400-Q', None, 'la cama es marrón')})
        self.assertEqual(filas[r['fila']]['codigo'], 'Y0400400-Q')


@tagged('post_install', '-at_install')
class TestStockDePrueba(TransactionCase):
    """Existencias de prueba (solo staging) para lo que nunca tuvo stock, también lo del catálogo."""

    def test_stock_de_prueba(self):
        Producto = self.env['product.product']
        ubicacion = self.env['stock.warehouse'].search(
            [('company_id', '=', self.env.ref('base.main_company').id)], limit=1).lot_stock_id
        sin_nada = Producto.create({'name': 'Nuevo sin stock', 'is_storable': True})
        contado = Producto.create({'name': 'Contado', 'is_storable': True})
        vendido = Producto.create({'name': 'Vendido (0 con movimientos)', 'is_storable': True})
        Quant = self.env['stock.quant'].with_context(inventory_mode=True)

        def contar(producto, cantidad):
            Quant.create({'product_id': producto.id, 'location_id': ubicacion.id,
                          'inventory_quantity': cantidad})._apply_inventory()

        contar(contado, 3)
        contar(vendido, 2)
        contar(vendido, 0)
        # Del catálogo, la talla que llegó en 0 (sin movimientos): NAT-XL.
        del_catalogo = Producto.search([('default_code', '=', 'NAT-XL')])
        self.assertFalse(self.env['stock.move'].search_count([('product_id', '=', del_catalogo.id)]))

        parametros = self.env['ir.config_parameter'].sudo()
        parametros.set_param(PARAM_STOCK_PRUEBA, '0')
        self.assertEqual(aplicar_stock_prueba(self.env), 0, 'En 0 (producción) no hace nada')
        self.assertEqual(sin_nada.qty_available, 0)

        parametros.set_param(PARAM_STOCK_PRUEBA, '10')
        self.assertGreater(aplicar_stock_prueba(self.env), 0)
        self.env.invalidate_all()
        self.assertEqual(sin_nada.qty_available, 10)
        self.assertEqual(del_catalogo.qty_available, 10, 'También los productos del catálogo')
        self.assertEqual(contado.qty_available, 3, 'Un conteo real no se pisa')
        self.assertEqual(vendido.qty_available, 0, 'Con movimientos no se toca')
        self.assertEqual(aplicar_stock_prueba(self.env), 0, 'Idempotente')
        self.assertEqual(sin_nada.qty_available, 10)
