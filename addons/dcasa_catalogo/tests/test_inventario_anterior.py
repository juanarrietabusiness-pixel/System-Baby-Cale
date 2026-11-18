import base64
import io
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from odoo.addons.dcasa_catalogo import inventario_anterior as I
from odoo.addons.dcasa_catalogo.catalogo import atributo_tamano
from odoo.addons.dcasa_catalogo.inventario_anterior import (
    cargar_inventario_anterior,
    leer_inventario_anterior,
    xmlid_inventario,
)
from odoo.addons.dcasa_catalogo.reglas import (
    categoria_de_inventario,
    clase_de_fila_inventario,
    filas_inventario,
    foto_por_codigo,
    planificar_inventario,
)
from odoo.tests import TransactionCase, tagged
from odoo.tools.misc import file_open

FIXTURE = Path(__file__).with_name('inventario_fixture.csv')
FOTOS_PRUEBA = {'INV-PRUEBA-FOTO': 'INV-PRUEBA-FOTO.jpg'}


def foto(color='white'):
    archivo = io.BytesIO()
    Image.new('RGB', (40, 40), color).save(archivo, 'JPEG')
    return base64.b64encode(archivo.getvalue())


@tagged('post_install', '-at_install')
class TestReglasInventario(TransactionCase):
    """Reglas puras (sin Odoo) del inventario anterior."""

    def test_clases_de_fila(self):
        self.assertEqual(clase_de_fila_inventario('Descuento'), 'omitir')
        self.assertEqual(clase_de_fila_inventario('Propinas'), 'omitir')
        self.assertEqual(clase_de_fila_inventario('X COLCHON IMPERIAL TWIN 2/3 PARA COMBO'), 'omitir')
        self.assertEqual(clase_de_fila_inventario('COMBO CAMA BUTTERFLY UP TWIN + COLCHO IMPERIAL'), 'combo')
        self.assertEqual(clase_de_fila_inventario('COMBO CAMA QUEEN IVORY 8017-1002-Q + COLCHÓN DULCES SUEÑOS'),
                         'combo')
        self.assertEqual(clase_de_fila_inventario('COMBO CAMAROTE TRIPLE 3 TWIN W160969418 + 3 COLCHONES IMPERIAL'),
                         'combo')
        self.assertEqual(clase_de_fila_inventario('COLCHON FLEX FULL RELAX'), 'producto')
        self.assertEqual(clase_de_fila_inventario('PAÑAL NATEEN + TOALLITAS DE REGALO'), 'producto',
                         'El «+» solo no es combo')

    def test_filas_y_categorias(self):
        filas = filas_inventario(FIXTURE.read_text(encoding='utf-8'))
        self.assertEqual(len(filas), 9)
        combo = filas[3]
        self.assertEqual(combo['llave'], combo['nombre'], 'Sin código, la llave es el nombre exacto')
        self.assertIsNone(combo['a_la_mano'])
        self.assertEqual(combo['costo'], 0.0)
        self.assertEqual(categoria_de_inventario(filas[1]), 'panales', 'Pañal → pañales')
        self.assertEqual(categoria_de_inventario(filas[2]), 'toallitas', 'Toallitas → toallitas húmedas')
        self.assertEqual(categoria_de_inventario(filas[7]), 'fulares')
        self.assertEqual(categoria_de_inventario({'nombre': 'COMBO FULAR MOON + PAÑALES DE REGALO', 'clase': 'combo'}),
                         'fulares', 'Un combo se clasifica por lo que va antes del «+»')
        self.assertIsNone(categoria_de_inventario(combo), 'Una cama no es de ninguna categoría de Baby Caleb')
        self.assertEqual(filas[2]['a_la_mano'], -3.0)
        self.assertEqual(filas[0]['precio'], 70.99)

    def test_foto_por_codigo(self):
        fotos = foto_por_codigo({'ALJ021439', 'CZX100308', 'NADA'},
                                ['ALJ021439_2.png', 'ALJ021439_1.png', 'CZX100308.jpg', 'CZX1003081.jpg', 'x.txt'])
        self.assertEqual(fotos, {'ALJ021439': 'ALJ021439_1.png', 'CZX100308': 'CZX100308.jpg'})

    def test_plan(self):
        filas = filas_inventario(FIXTURE.read_text(encoding='utf-8'))
        plan = planificar_inventario(filas, {'INV-PRUEBA-EXISTE'}, FOTOS_PRUEBA)
        self.assertEqual([f['llave'] for f in plan['actualizar']], ['INV-PRUEBA-EXISTE'])
        self.assertEqual([f['llave'] for f in plan['crear']],
                         ['INV-PRUEBA-FOTO', 'INV-PRUEBA-SINFOTO', 'COMBO CAMA DE PRUEBA KING + COLCHÓN IMPERIAL',
                          'FULAR DE PRUEBA SIN CODIGO'])
        self.assertEqual(len(plan['omitidos']), 3)
        self.assertEqual([f['fila'] for f in plan['repetidos']], [9])
        self.assertEqual([f['llave'] for f in plan['negativos']], ['INV-PRUEBA-SINFOTO'])
        self.assertEqual([f['llave'] for f in plan['con_foto']], ['INV-PRUEBA-FOTO'])
        self.assertEqual([f['llave'] for f in plan['sin_foto']],
                         ['INV-PRUEBA-SINFOTO', 'FULAR DE PRUEBA SIN CODIGO'])
        self.assertEqual(len(plan['combos']), 1)
        self.assertEqual(len(plan['dudas']), 1)


@tagged('post_install', '-at_install')
class TestCargaInventario(TransactionCase):
    """La carga del fixture pequeño (datos de prueba) aplica las reglas y se puede repetir."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref('base.main_company')
        cls.ubicacion = cls.env['stock.warehouse'].search([('company_id', '=', cls.company.id)], limit=1).lot_stock_id
        cls.filas = filas_inventario(FIXTURE.read_text(encoding='utf-8'))
        cls.existente = cls.env['product.product'].create({
            'name': 'Pañal de prueba con su nombre', 'default_code': 'INV-PRUEBA-EXISTE', 'type': 'consu',
            'is_storable': True, 'list_price': 60.0, 'image_1920': foto('blue'),
        })
        cls.nombre_antes = cls.existente.name
        cls.foto_antes = cls.existente.product_tmpl_id.image_1920
        cls.movimientos = cls.env['stock.move'].search_count([])

    def cargar(self):
        # La foto de prueba no viaja con el módulo (static/img/productos ya no existe): se genera aquí.
        with patch.object(I, '_foto_b64', return_value=foto()):
            return cargar_inventario_anterior(self.env, self.filas, fotos=FOTOS_PRUEBA)

    def variante(self, codigo):
        variante = self.env['product.product'].with_context(active_test=False).search([('default_code', '=', codigo)])
        self.assertEqual(len(variante), 1, codigo)
        return variante

    def existencias(self, variante):
        return variante.with_context(location=self.ubicacion.id).qty_available

    def test_carga_y_segunda_corrida(self):
        resumen = self.cargar()
        self.assertEqual(resumen['actualizados'], ['INV-PRUEBA-EXISTE'])
        self.assertEqual(resumen['creados'], ['INV-PRUEBA-FOTO', 'INV-PRUEBA-SINFOTO',
                                              'COMBO CAMA DE PRUEBA KING + COLCHÓN IMPERIAL',
                                              'FULAR DE PRUEBA SIN CODIGO'])
        self.assertEqual(resumen['omitidos'], ['Descuento', 'TIPS', 'X COLCHON IMPERIAL TWIN 2/3 PARA COMBO'])
        self.assertEqual(resumen['repetidos'], ['INV-PRUEBA-FOTO'])
        self.assertEqual(resumen['negativos'], ['INV-PRUEBA-SINFOTO'])
        self.assertEqual(resumen['combos'], ['COMBO CAMA DE PRUEBA KING + COLCHÓN IMPERIAL'])
        self.assertEqual(resumen['con_foto'], ['INV-PRUEBA-FOTO'])
        self.assertEqual(resumen['sin_foto'], ['INV-PRUEBA-SINFOTO', 'FULAR DE PRUEBA SIN CODIGO'])

        # Mismo código = mismo producto: existencias, precio y costo; nombre y foto intactos.
        existente = self.existente
        self.assertEqual(existente.name, self.nombre_antes)
        self.assertEqual(existente.product_tmpl_id.image_1920, self.foto_antes)
        self.assertAlmostEqual(existente.lst_price, 70.99, places=2)
        self.assertAlmostEqual(existente.standard_price, 40.00, places=2)
        self.assertEqual(self.existencias(existente), 5)

        # Código nuevo con foto: producto publicado, con el ITBMS que se suma y su categoría.
        con_foto = self.variante('INV-PRUEBA-FOTO')
        plantilla = con_foto.product_tmpl_id
        self.assertTrue(plantilla.is_published)
        self.assertTrue(plantilla.image_1920)
        self.assertEqual(plantilla.taxes_id, self.company.account_sale_tax_id)
        self.assertFalse(plantilla.taxes_id.price_include, 'Precio de lista sin ITBMS, como el resto del catálogo')
        self.assertAlmostEqual(plantilla.list_price, 199.99, places=2)
        self.assertAlmostEqual(con_foto.standard_price, 100.50, places=2)
        self.assertEqual(plantilla.categ_id, self.env.ref('dcasa_catalogo.product_category_panales'))
        self.assertEqual(plantilla.public_categ_ids, self.env.ref('dcasa_catalogo.public_category_panales'))
        self.assertTrue(plantilla.is_storable)
        self.assertEqual(self.existencias(con_foto), 7, 'La fila repetida (99) no se aplica')
        self.assertTrue(self.env.ref(f'dcasa_catalogo.{xmlid_inventario("INV-PRUEBA-FOTO")}'))

        # Sin foto: en inventario sin publicar; negativo → 0.
        sin_foto = self.variante('INV-PRUEBA-SINFOTO')
        self.assertFalse(sin_foto.product_tmpl_id.is_published)
        self.assertFalse(sin_foto.product_tmpl_id.image_1920)
        self.assertEqual(sin_foto.product_tmpl_id.categ_id,
                         self.env.ref('dcasa_catalogo.product_category_toallitas'))
        self.assertEqual(self.existencias(sin_foto), 0)

        # Combo: producto sin publicar, sin existencias.
        combo = self.env.ref(f'dcasa_catalogo.{xmlid_inventario("COMBO CAMA DE PRUEBA KING + COLCHÓN IMPERIAL")}')
        self.assertFalse(combo.is_published)
        self.assertAlmostEqual(combo.list_price, 319.99, places=2)
        self.assertEqual(self.existencias(combo.product_variant_id), 0)
        self.assertFalse(self.env['stock.move'].search_count([('product_id', '=', combo.product_variant_id.id)]))

        # Sin código: la llave es el nombre exacto.
        fular = self.env['product.template'].search([('name', '=', 'FULAR DE PRUEBA SIN CODIGO')])
        self.assertEqual(len(fular), 1)
        self.assertFalse(fular.default_code)
        self.assertEqual(self.existencias(fular.product_variant_id), 4)

        # No se importan.
        for nombre in ('Descuento', 'Propinas', 'X COLCHON IMPERIAL TWIN 2/3 PARA COMBO'):
            self.assertFalse(self.env['product.template'].search_count([('name', '=', nombre)]), nombre)
        self.assertFalse(self.env['product.product'].search_count([('default_code', '=', 'TIPS')]))

    def test_segunda_corrida_no_cambia_nada(self):
        self.cargar()
        fular = self.env['product.template'].search([('name', '=', 'FULAR DE PRUEBA SIN CODIGO')])
        movimientos = self.env['stock.move'].search_count([])
        self.assertGreater(movimientos, self.movimientos)
        fular.name = 'Fular que el dueño renombró'  # se sigue encontrando por su xmlid, no se duplica
        otra_vez = self.cargar()
        self.assertEqual(otra_vez['creados'], [])
        self.assertEqual(otra_vez['actualizados'], [])
        self.assertEqual(len(otra_vez['sin_cambios']), 5)
        self.assertEqual(self.env['stock.move'].search_count([]), movimientos)
        self.assertEqual(self.env['product.template'].search_count([('name', 'ilike', 'FULAR DE PRUEBA SIN CODIGO')]),
                         0)
        self.assertEqual(self.existencias(fular.product_variant_id), 4)

    def test_el_csv_manda_sobre_un_precio_cambiado_en_odoo(self):
        """El inventario anterior es la fuente de esta carga: al repetirla, el precio vuelve al del CSV."""
        self.cargar()
        existente = self.existente
        existente.product_tmpl_id.list_price = 123.45  # el dueño cambió el precio en Odoo
        resumen = self.cargar()
        self.assertIn('INV-PRUEBA-EXISTE', resumen['actualizados'], 'El CSV manda: vuelve al precio del inventario')
        self.assertAlmostEqual(existente.lst_price, 70.99, places=2)

    def test_sin_columna_de_costo_no_se_borra_el_costo(self):
        """El repositorio es público: el CSV del módulo no trae costos, y cargar uno sin esa columna no le borra el
        costo a lo que ya lo tiene en Odoo."""
        with file_open('dcasa_catalogo/data/inventario_anterior.csv', 'r') as archivo:
            self.assertNotIn('costo', archivo.readline().strip().split(','))
        self.existente.standard_price = 123.45
        filas = filas_inventario('pagina,fila,nombre,codigo,precio_venta,a_la_mano,pronosticado,dudas\n'
                                 '1,1,PAÑAL DE PRUEBA,INV-PRUEBA-EXISTE,60.00,2,2,\n')
        self.assertIsNone(filas[0]['costo'])
        cargar_inventario_anterior(self.env, filas)
        self.assertAlmostEqual(self.existente.standard_price, 123.45, places=2)
        self.assertEqual(self.existencias(self.existente), 2)

    def test_codigo_sin_el_sufijo_de_tamano_es_esa_variante(self):
        """«ZZ-CAMA … TAMAÑO FULL» es la variante Full del producto ZZ-CAMA (códigos ZZ-CAMA-FULL, ZZ-CAMA-QUEEN): no se
        crea otro producto, se actualiza esa variante y las otras no reciben existencias."""
        atributo, valores = atributo_tamano(self.env)
        cama = self.env['product.template'].create({
            'name': 'Cama de prueba', 'type': 'consu', 'is_storable': True, 'list_price': 100.0,
            'attribute_line_ids': [(0, 0, {'attribute_id': atributo.id,
                                           'value_ids': [(6, 0, (valores['Full'] | valores['Queen']).ids)]})]})
        for variante in cama.product_variant_ids:
            variante.default_code = f'ZZ-CAMA-{variante.product_template_attribute_value_ids.name.upper()}'
        filas = filas_inventario('pagina,fila,nombre,codigo,precio_venta,a_la_mano,pronosticado,dudas\n'
                                 '1,1,CAMA DE PRUEBA TAMAÑO FULL,ZZ-CAMA,100.00,3,3,\n')
        resumen = cargar_inventario_anterior(self.env, filas)
        self.assertEqual(resumen['creados'], [])
        full = self.variante('ZZ-CAMA-FULL')
        self.assertEqual(self.existencias(full), 3)
        self.assertEqual(self.existencias(self.variante('ZZ-CAMA-QUEEN')), 0, 'La otra medida no recibe existencias')


@tagged('post_install', '-at_install')
class TestInventarioDelModulo(TransactionCase):
    """El CSV que trae el módulo es solo el encabezado: el inventario anterior de D'CASA no es de este negocio."""

    def test_solo_el_encabezado_y_nada_cargado_al_instalar(self):
        self.assertEqual(leer_inventario_anterior(), [])
        self.assertFalse(self.env['ir.model.data'].search_count([
            ('module', '=', 'dcasa_catalogo'), ('name', '=like', 'inventario_anterior_%')]))
        self.assertEqual(I.fotos_del_modulo(), [], 'Sin fotos en el módulo: lo nuevo del inventario no se publica')
