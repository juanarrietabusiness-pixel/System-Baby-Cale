import os
from urllib.parse import unquote

from odoo.addons.dcasa_base.nombres import nombre_en_mayusculas
from odoo.addons.dcasa_catalogo import catalogo as C
from odoo.addons.dcasa_catalogo.catalogo import cargar_catalogo, leer_catalogo, xmlid_de
from odoo.addons.dcasa_catalogo.models import combo_armable
from odoo.addons.dcasa_catalogo.reglas import categoria_de_nombre
from odoo.modules.module import get_module_path
from odoo.tests import HttpCase, TransactionCase, tagged
from odoo.tools.misc import file_open

# La lista del dueño de Baby Caleb (2026-11-18), tal como la dio: código, texto, precio en dólares y existencias (más
# NAT-L, que el dueño decidió cargar después).
# La prueba la repite aquí (y no la lee del JSON) para que un cambio en data/catalogo.json no pase sin que se vea.
LISTA_DEL_DUENO = {
    'MOON-FUL': ('Fular prearmado Moon de bambú color gris — unitalla ajustable XS a 3XL (RN hasta ~25 lbs)', 46.00, 2),
    'NAT-P-L': ('Pañal Nateen Talla L de pants — caja de 160 (19-31 lbs) (9 kg - 14 kg)', 55.00, 6),
    'NAT-M': ('Pañal Nateen Talla M de cierre — caja de 144 (8–19 lbs / 4–9 kg)', 50.00, 7),
    # No venía en la lista: el dueño decidió cargarlo después ($45.00, sin existencias), con el texto de la web.
    'NAT-L': ('Caja L — 15 a 39 lb — 128 uds', 45.00, 0),
    'NAT-RN': ('Pañal Nateen Talla RN de cierre — caja de 160 (4–11 lbs / 2–5 kg)', 50.00, 4),
    'NAT-S': ('Pañal Nateen Talla S de cierre — caja de 160 (6–13 lbs / 3–6 kg)', 50.00, 3),
    'NAT-XL': ('Pañal Nateen Talla XL de cierre — caja de 112 (26–55 lbs / 12–25 kg)', 45.00, 0),
    'NAT-P-XL': ('Pañal Nateen Talla XL de pants — caja de 160 (26-37.5 lbs) (12 kg - 17kg)', 55.00, 2),
    'NAT-XXL': ('Pañal Nateen Talla XXL de cierre — caja de 112 (+55 lbs / +25 kg)', 45.00, 3),
    'NAT-P-XXL': ('Pañal Nateen Talla XXL de pants — caja de 160 (+33 lbs) (+ de 15 kg)', 55.00, 9),
    'VELVEE-P': ('Pañal Velvee Talla P (S): (7.5 - 13 lb) (3.5 - 6 kg) 150 pañales', 35.00, 2),
    'VELVEE-L': ('Pañal Velvee Talla G (L): (20 - 27 lb) (9 - 12.5 kg) 126 pañales', 33.00, 3),
    'VELVEE-M': ('Pañal Velvee Talla M (M): (12 - 21 lb) (5.5 - 9.5 kg) 132 pañales', 35.00, 1),
    'DANY-AW600': ('Water wipes hipoalergénicas Dany Baby — caja de 600 toallitas (6 paquetes de 100)', 20.00, 26),
    'WIPESNAT': ('Water wipes hipoalergénicas Nateen — Caja de 960 toallitas (12 paquetes de 80)', 45.00, 15),
}
# Cómo se agrupan: producto → (nombre, categoría, tallas en el orden de la tienda con su código; None = sin variantes).
PRODUCTOS = {
    'nateen-diapers': ('Pañales Nateen de cierre', 'panales',
                       [('RN', 'NAT-RN'), ('S', 'NAT-S'), ('M', 'NAT-M'), ('L', 'NAT-L'), ('XL', 'NAT-XL'),
                        ('XXL', 'NAT-XXL')]),
    'nateen-pants': ('Pañales Nateen Pants', 'panales', [('L', 'NAT-P-L'), ('XL', 'NAT-P-XL'), ('XXL', 'NAT-P-XXL')]),
    'velvee-diapers': ('Pañales Velvee', 'panales', [('P', 'VELVEE-P'), ('M', 'VELVEE-M'), ('G', 'VELVEE-L')]),
    'nateen-wipes': ('Water wipes Nateen', 'toallitas', [(None, 'WIPESNAT')]),
    'danybaby-aquawipes': ('Water wipes Dany Baby', 'toallitas', [(None, 'DANY-AW600')]),
    'fular-moon': ('Fular Moon', 'fulares', [(None, 'MOON-FUL')]),
}
# Una muestra de las referencias del catálogo de D'CASA que ya no se cargan (camas, colchones, combos, inventario).
CODIGOS_DE_DCASA = ('888K', '908K-NEGRO', 'XHT022-T-W', 'Y0300300-LTSC07', 'HK-BF-022-N-K-1-W', 'N-F10018-F-BK-FULL',
                    'CSOK-10', 'IM-2001', 'YPN272102', 'ALMOHADA001', 'LXI100713')


def _item(clave, variantes, atributo=None, **otros):
    """Un producto del JSON para las pruebas de la carga (con datos de prueba, no los del negocio)."""
    item = {'clave': clave, 'nombre': f'Producto de prueba {clave}', 'categoria': 'panales', 'orden': 99,
            'descripcion': None, 'variantes': variantes}
    if atributo:
        item['atributo'] = atributo
    item.update(otros)
    return item


@tagged('post_install', '-at_install')
class TestCatalogoBabyCaleb(TransactionCase):
    """El catálogo de Baby Caleb quedó cargado al instalar, tal como lo dio el dueño, y nada del de D'CASA."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref('base.main_company')
        cls.ubicacion = cls.env['stock.warehouse'].search(
            [('company_id', '=', cls.company.id)], limit=1).lot_stock_id
        cls.Variante = cls.env['product.product'].with_context(active_test=False)

    def producto(self, clave):
        return self.env.ref(f'dcasa_catalogo.{xmlid_de(clave)}')

    def variante(self, codigo):
        variante = self.Variante.search([('default_code', '=', codigo)])
        self.assertEqual(len(variante), 1, codigo)
        return variante

    def test_las_quince_variantes_con_su_codigo_precio_existencias_y_texto(self):
        impuesto = self.company.account_sale_tax_id
        for codigo, (texto, precio, existencias) in LISTA_DEL_DUENO.items():
            variante = self.variante(codigo)
            self.assertTrue(variante.active, codigo)
            self.assertEqual(variante.lst_price, precio, f'{codigo}: el precio exacto de la lista')
            self.assertEqual(variante.with_context(location=self.ubicacion.id).qty_available, existencias, codigo)
            self.assertEqual(variante.dcasa_presentacion, texto, f'{codigo}: el texto del dueño, tal cual')
            self.assertEqual(variante.taxes_id, impuesto, f'{codigo}: el mismo ITBMS que llevaba la carga de D’CASA')
            self.assertTrue(variante.is_storable and variante.sale_ok, codigo)
        self.assertEqual(self.Variante.search_count([('product_tmpl_id', 'in', self.plantillas().ids)]), 15)

    def plantillas(self):
        return self.env['product.template'].with_context(active_test=False).browse(
            self.env['ir.model.data'].search([('module', '=', 'dcasa_catalogo'), ('model', '=', 'product.template')])
            .mapped('res_id'))

    def test_agrupados_con_variantes_de_talla(self):
        talla = self.env['product.attribute'].search([('name', '=', 'Talla')])
        self.assertEqual(len(talla), 1)
        self.assertEqual(talla.create_variant, 'always')
        for clave, (nombre, _categoria, variantes) in PRODUCTOS.items():
            producto = self.producto(clave)
            self.assertEqual(producto.name, nombre_en_mayusculas(nombre))
            self.assertEqual(producto.product_variant_count, len(variantes), clave)
            if variantes[0][0] is None:
                self.assertFalse(producto.attribute_line_ids, f'{clave}: producto simple')
                self.assertEqual(producto.default_code, variantes[0][1])
                continue
            self.assertEqual(producto.attribute_line_ids.attribute_id, talla, clave)
            # El orden de la tienda (el de los valores del atributo) y cada talla con su código.
            self.assertEqual(producto.attribute_line_ids.product_template_value_ids.sorted().mapped('name'),
                             [valor for valor, _codigo in variantes], clave)
            for valor, codigo in variantes:
                self.assertEqual(self.variante(codigo).product_template_attribute_value_ids.name, valor, codigo)

    def test_precio_de_lista_y_el_itbms_que_se_suma(self):
        """Como la carga de D'CASA: el precio de la lista es el de lista y el ITBMS de la empresa se suma."""
        producto = self.producto('nateen-diapers')
        self.assertEqual(producto.list_price, 45.0, 'El de la talla más barata; las demás, con su extra')
        impuesto = producto.taxes_id
        self.assertEqual(impuesto, self.company.account_sale_tax_id, 'El impuesto por defecto')
        self.assertFalse(impuesto.price_include)
        self.assertEqual(impuesto.amount, 7)
        orden = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Clienta'}).id,
            'order_line': [(0, 0, {'product_id': self.variante('NAT-M').id}),
                           (0, 0, {'product_id': self.variante('NAT-XL').id})],
        })
        self.assertEqual(orden.order_line.mapped('price_unit'), [50.0, 45.0])
        self.assertAlmostEqual(orden.amount_untaxed, 95.0, places=2)
        self.assertAlmostEqual(orden.amount_tax, 6.65, places=2)
        self.assertAlmostEqual(orden.amount_total, 101.65, places=2)
        self.assertEqual(self.env['website'].get_current_website().show_line_subtotals_tax_selection,
                         'tax_excluded')

    def test_categorias_de_baby_caleb(self):
        for clave, (_nombre, categoria, _variantes) in PRODUCTOS.items():
            producto = self.producto(clave)
            self.assertEqual(producto.categ_id, self.env.ref(f'dcasa_catalogo.product_category_{categoria}'), clave)
            self.assertEqual(producto.public_categ_ids, self.env.ref(f'dcasa_catalogo.public_category_{categoria}'),
                             clave)
        self.assertEqual(self.env.ref('dcasa_catalogo.public_category_toallitas').name, 'Toallitas húmedas')
        for viejo in ('product_category_zapateras', 'product_category_organizacion', 'product_category_oficina',
                      'public_category_muebles_tv'):
            self.assertFalse(self.env.ref(f'dcasa_catalogo.{viejo}', raise_if_not_found=False), viejo)

    def test_descripcion_de_la_web_y_presentacion_a_la_vista(self):
        pants = self.producto('nateen-pants')
        self.assertIn('Tipo pantaloncito (pull-ups)', str(pants.description_ecommerce))
        self.assertFalse(self.producto('velvee-diapers').description_ecommerce, 'Velvee: solo el texto del dueño')
        self.assertNotIn('12 paquetes de 50', str(self.producto('danybaby-aquawipes').description_ecommerce),
                         'Lo que contradice la lista del dueño no se copia de la web')
        moon = self.producto('fular-moon')
        self.assertEqual(moon.dcasa_presentacion, LISTA_DEL_DUENO['MOON-FUL'][0], 'Una sola variante: en la ficha')
        self.assertFalse(pants.dcasa_presentacion, 'Con tallas, cada variante tiene la suya')
        moon.dcasa_presentacion = 'Fular Moon gris'
        self.assertEqual(moon.product_variant_id.dcasa_presentacion, 'Fular Moon gris', 'Se edita desde la ficha')
        self.assertEqual([texto for _v, texto in pants._dcasa_presentaciones()],
                         [LISTA_DEL_DUENO[c][0] for c in ('NAT-P-L', 'NAT-P-XL', 'NAT-P-XXL')])
        # En el orden de las tallas, no en el del código (NAT-L, NAT-M, NAT-RN… y VELVEE-L, -M, -P).
        for clave in ('nateen-diapers', 'velvee-diapers'):
            esperado = [LISTA_DEL_DUENO[codigo][0] for _talla, codigo in PRODUCTOS[clave][2]]
            self.assertEqual([texto for _v, texto in self.producto(clave)._dcasa_presentaciones()], esperado, clave)

    def test_las_vistas_muestran_la_presentacion(self):
        for modelo, xmlid, tipo in (('product.template', 'product.product_template_only_form_view', 'form'),
                                    ('product.product', 'product.product_normal_form_view', 'form'),
                                    ('product.product', 'product.product_variant_easy_edit_view', 'form'),
                                    ('product.product', 'product.product_product_tree_view', 'list')):
            arch = self.env[modelo].get_view(self.env.ref(xmlid).id, tipo)['arch']
            self.assertIn('name="dcasa_presentacion"', arch, xmlid)

    def test_con_su_foto_se_publica(self):
        """Las fotos del catálogo (2026-11-24): las de la web de Baby Caleb para los Nateen y las que tomó el dueño para
        Velvee, Dany Baby y Fular Moon. Todos los productos tienen su foto principal y salen en la web; cada talla, la
        suya y las de más que dice data/catalogo.json."""
        extras = {v['codigo']: len(v.get('fotos_extra') or []) for item in leer_catalogo()['productos']
                  for v in item['variantes']}
        for clave in PRODUCTOS:
            producto = self.producto(clave)
            self.assertTrue(producto.allow_out_of_stock_order)
            self.assertTrue(producto.image_1920, clave)
            self.assertTrue(producto.is_published, f'{clave}: con su foto sale en la web')
            for variante in producto.product_variant_ids:
                self.assertEqual(len(variante.product_variant_image_ids), extras[variante.default_code],
                                 f'{variante.default_code}: sus fotos de más')
        self.assertEqual((extras['VELVEE-P'], extras['VELVEE-M'], extras['VELVEE-L'], extras['DANY-AW600'],
                          extras['MOON-FUL']), (3, 4, 4, 6, 4), 'las del dueño, sin las casi iguales')
        for clave in ('nateen-diapers', 'nateen-pants', 'velvee-diapers'):
            variantes = self.producto(clave).product_variant_ids
            self.assertEqual(len(variantes), len(PRODUCTOS[clave][2]))
            for variante in variantes:
                self.assertTrue(variante.image_variant_1920, f'{variante.default_code}: la foto de su talla')
            fotos = {v.image_variant_1920 for v in variantes}
            self.assertEqual(len(fotos), len(variantes), f'{clave}: cada talla con la suya')

    def test_cada_foto_del_archivo_existe_y_ninguna_sobra(self):
        carpeta = os.path.join(get_module_path('dcasa_catalogo'), 'data', 'fotos')
        nombradas = set()
        for item in leer_catalogo()['productos']:
            nombradas.update(filter(None, [item.get('foto')]))
            for variante in item['variantes']:
                nombradas.update(filter(None, [variante.get('foto'), *(variante.get('fotos_extra') or [])]))
            if not item.get('foto'):
                self.assertTrue(item.get('origen_foto'), f"{item['clave']}: sin foto, dice por qué")
        self.assertEqual(nombradas, set(os.listdir(carpeta)))
        for nombre in nombradas:
            self.assertRegex(nombre, r'\.(jpg|png)$', 'JPEG o PNG: Odoo saca de ahí los tamaños chicos (el WEBP no)')

    def test_nada_del_catalogo_de_dcasa(self):
        self.assertEqual(sorted(self.plantillas().mapped('product_variant_ids.default_code')), sorted(LISTA_DEL_DUENO))
        self.assertEqual(sorted(self.env['ir.model.data'].search([
            ('module', '=', 'dcasa_catalogo'), ('model', '=', 'product.template')]).mapped('name')),
            sorted(xmlid_de(clave) for clave in PRODUCTOS))
        self.assertFalse(self.Variante.search_count([('default_code', 'in', CODIGOS_DE_DCASA)]))
        self.assertFalse(os.path.exists(os.path.join(get_module_path('dcasa_catalogo'), 'static', 'img', 'productos')),
                         'Las fotos de D’CASA ya no viajan con el módulo')
        catalogo = leer_catalogo()
        self.assertFalse([i['clave'] for i in catalogo['productos'] if 'fotos' in i])
        self.assertEqual(C.BLACK_WEEKEND, [], 'La selección de Black Weekend de D’CASA no es de este negocio')
        self.assertEqual(combo_armable.PRECIOS_COMBO_APROBADOS, {}, 'Ni los precios en combo de D’CASA')
        with file_open('dcasa_catalogo/data/inventario_anterior.csv', 'r') as archivo:
            self.assertEqual(len(archivo.read().splitlines()), 1, 'Del inventario de D’CASA: solo el encabezado')
        self.assertFalse(self.env['product.template'].search_count([('dcasa_black_weekend', '=', True)]))

    def test_existencias_con_su_motivo_solo_al_crear(self):
        movimientos = self.env['stock.move'].search([('product_id', '=', self.variante('NAT-M').id)])
        self.assertEqual(movimientos.mapped('inventory_name'),
                         ['Existencias iniciales del catálogo (lista del dueño de Baby Caleb, 2026-11-18)'])
        self.assertFalse(self.env['stock.move'].search_count([('product_id', '=', self.variante('NAT-XL').id)]),
                         'En 0 no hace falta ajuste')

    def test_idempotente_y_respeta_cambios(self):
        producto = self.producto('fular-moon')
        producto.list_price = 1  # el dueño lo cambió en Odoo
        variante = self.variante('NAT-M')
        self.env['stock.quant'].with_context(inventory_mode=True, inventory_name='Conteo de prueba').create({
            'product_id': variante.id, 'location_id': self.ubicacion.id, 'inventory_quantity': 1})._apply_inventory()
        antes = self.env['product.template'].search_count([])
        self.assertEqual(cargar_catalogo(self.env), 0)
        self.assertEqual(self.env['product.template'].search_count([]), antes)
        self.assertEqual(producto.list_price, 1)
        self.assertEqual(variante.with_context(location=self.ubicacion.id).qty_available, 1, 'Un conteo no se pisa')

    def test_nombres_distintos(self):
        """Ni la clienta ni la vendedora deben ver dos productos con el mismo nombre."""
        nombres = self.plantillas().mapped(lambda p: p.name.lower())
        self.assertEqual(len(nombres), len(set(nombres)))

    def test_busqueda_por_varias_palabras(self):
        encontrados = self.env['product.product'].search([('display_name', 'ilike', 'nateen xxl')])
        self.assertIn(self.variante('NAT-XXL'), encontrados)
        self.assertIn(self.variante('NAT-P-XXL'), encontrados)
        self.assertNotIn(self.variante('NAT-XL'), encontrados)
        self.assertNotIn(self.variante('DANY-AW600'), encontrados)

    def test_cotizacion_por_whatsapp(self):
        cliente = self.env['res.partner'].create({'name': 'Ana Pérez', 'phone': '6123-4567'})
        orden = self.env['sale.order'].create({
            'partner_id': cliente.id,
            'order_line': [(0, 0, {'product_id': self.variante('DANY-AW600').id})],
        })
        accion = orden.action_dcasa_whatsapp()
        self.assertTrue(accion['url'].startswith('https://wa.me/50761234567?text='))
        self.assertIn(orden.name, accion['url'])
        self.assertEqual(orden.state, 'sent')
        # El mensaje dice la empresa (Ajustes › Empresa), nunca el nombre de la plantilla de origen.
        texto = unquote(accion['url'].split('?text=', 1)[1])
        self.assertIn(f' de {orden.company_id.name} por ', texto)
        self.assertNotIn("D'CASA", texto)

    def test_migracion_pasa_del_incluido_al_que_se_suma(self):
        """Bases cargadas con «ITBMS 7% incluido»: cambia el impuesto, no el precio."""
        venta = self.company.account_sale_tax_id
        incluido = venta.copy({'name': 'ITBMS 7% incluido', 'price_include_override': 'tax_included'})
        viejo = self.producto('nateen-diapers') | self.producto('danybaby-aquawipes')
        a_mano = self.producto('fular-moon')
        exento = self.env['account.tax'].create({'name': 'Exento prueba', 'amount': 0, 'type_tax_use': 'sale'})
        viejo.taxes_id = incluido
        a_mano.taxes_id = exento  # el dueño le puso otro impuesto: no se toca
        precios = {p: (p.list_price, p.product_variant_ids.mapped('lst_price')) for p in viejo | a_mano}
        self.env['website'].search([]).show_line_subtotals_tax_selection = 'tax_included'

        self.assertEqual(C.pasar_a_itbms_que_se_suma(self.env), 2)
        self.assertEqual(viejo.taxes_id, venta)
        self.assertEqual(a_mano.taxes_id, exento)
        for producto, (lista, variantes) in precios.items():
            self.assertEqual(producto.list_price, lista, 'El precio de la lista no cambia')
            self.assertEqual(producto.product_variant_ids.mapped('lst_price'), variantes)
        self.assertFalse(incluido.active, 'Sin uso: archivado')
        self.assertEqual(self.env['website'].get_current_website().show_line_subtotals_tax_selection, 'tax_excluded')
        self.assertEqual(C.pasar_a_itbms_que_se_suma(self.env), 0, 'Se puede repetir')


@tagged('post_install', '-at_install')
class TestCargaDelArchivo(TransactionCase):
    """Las reglas de la carga, con productos de prueba (no los del negocio)."""

    def catalogo(self, *productos, atributos=None):
        return {'fuente': 'Lista de prueba', 'atributos': atributos or {'Talla de prueba': ['CH', 'MED', 'GR']},
                'productos': list(productos)}

    def variante(self, codigo):
        return self.env['product.product'].with_context(active_test=False).search([('default_code', '=', codigo)])

    def test_crea_lo_que_falta_con_cada_precio_exacto(self):
        item = _item('zz-tallas', [
            {'valor': 'GR', 'codigo': 'ZZ-GR', 'precio': 12.5, 'existencias': 2, 'texto': 'Grande'},
            {'valor': 'CH', 'codigo': 'ZZ-CH', 'precio': 9.99, 'existencias': None, 'texto': 'Chica'},
        ], atributo='Talla de prueba', descripcion='Para <probar> el texto')
        self.assertEqual(cargar_catalogo(self.env, self.catalogo(item)), 1)
        producto = self.env.ref(f'dcasa_catalogo.{xmlid_de("zz-tallas")}')
        self.assertEqual(producto.list_price, 9.99)
        self.assertEqual((self.variante('ZZ-GR').lst_price, self.variante('ZZ-CH').lst_price), (12.5, 9.99))
        self.assertEqual(self.variante('ZZ-GR').qty_available, 2)
        self.assertEqual(self.variante('ZZ-CH').qty_available, 0, 'Sin existencias en el archivo: no se ajusta')
        self.assertFalse(self.env['stock.move'].search_count([('product_id', '=', self.variante('ZZ-CH').id)]))
        self.assertEqual(producto.attribute_line_ids.product_template_value_ids.sorted().mapped('name'), ['CH', 'GR'],
                         'El orden del atributo, no el del archivo')
        self.assertIn('Para &lt;probar&gt; el texto', str(producto.description_ecommerce))
        self.assertEqual(cargar_catalogo(self.env, self.catalogo(item)), 0, 'La segunda vez no crea nada')

    def test_vuelve_a_crear_lo_que_falta(self):
        item = _item('zz-simple', [{'codigo': 'ZZ-SIMPLE', 'precio': 7.0, 'existencias': 0, 'texto': 'Uno'}])
        cargar_catalogo(self.env, self.catalogo(item))
        self.env.ref(f'dcasa_catalogo.{xmlid_de("zz-simple")}').unlink()
        self.assertEqual(cargar_catalogo(self.env, self.catalogo(item)), 1)
        self.assertEqual(self.variante('ZZ-SIMPLE').dcasa_presentacion, 'Uno')

    def test_las_fotos_solo_llenan_lo_vacio_y_publican_lo_que_reciben(self):
        foto = 'producto-wipes-caja.jpg'
        con_tallas = _item('zz-fotos', [
            {'valor': 'CH', 'codigo': 'ZZ-F-CH', 'precio': 5.0, 'existencias': 0, 'foto': foto,
             'fotos_extra': [foto, foto]},
            {'valor': 'GR', 'codigo': 'ZZ-F-GR', 'precio': 6.0, 'existencias': 0},
        ], atributo='Talla de prueba', foto=foto)
        ya_tenia = _item('zz-ya-tenia', [{'codigo': 'ZZ-YA', 'precio': 7.0, 'existencias': 0}], foto=foto)
        sin_foto = _item('zz-sin-foto', [{'codigo': 'ZZ-SIN-FOTO', 'precio': 8.0, 'existencias': 0}])
        catalogo = self.catalogo(con_tallas, ya_tenia, sin_foto)
        cargar_catalogo(self.env, catalogo)
        # Una persona ya le puso otra foto a «zz-ya-tenia» y lo dejó sin publicar: se respeta.
        propia = self.env.ref(f'dcasa_catalogo.{xmlid_de("zz-ya-tenia")}')
        propia.image_1920 = C.foto_del_catalogo('producto-nateen-cierre-rn.jpg')
        antes = propia.image_1920
        self.assertEqual(C.poner_fotos(self.env, catalogo), 1)
        producto = self.env.ref(f'dcasa_catalogo.{xmlid_de("zz-fotos")}')
        self.assertTrue(producto.image_1920 and producto.is_published)
        self.assertTrue(self.variante('ZZ-F-CH').image_variant_1920)
        self.assertEqual(self.variante('ZZ-F-CH').product_variant_image_ids.mapped('sequence'), [1, 2])
        self.assertFalse(self.variante('ZZ-F-GR').image_variant_1920, 'Sin foto de la talla: usa la del producto')
        self.assertEqual(propia.image_1920, antes, 'La foto que puso una persona no se cambia')
        self.assertFalse(propia.is_published, 'ni se publica lo que ella dejó sin publicar')
        sin = self.env.ref(f'dcasa_catalogo.{xmlid_de("zz-sin-foto")}')
        self.assertFalse(sin.image_1920 or sin.is_published)
        # Repetir no duplica nada, ni vuelve a publicar lo que alguien quitó de la web.
        producto.is_published = False
        self.assertEqual(C.poner_fotos(self.env, catalogo), 0)
        self.assertFalse(producto.is_published)
        self.assertEqual(len(self.variante('ZZ-F-CH').product_variant_image_ids), 2)

    def test_un_precio_que_falta_no_se_inventa(self):
        item = _item('zz-sin-precio', [{'codigo': 'ZZ-SIN-PRECIO', 'precio': None, 'existencias': 3}])
        with self.assertLogs('odoo.addons.dcasa_catalogo.catalogo', 'WARNING') as registro:
            self.assertEqual(cargar_catalogo(self.env, self.catalogo(item)), 0)
        self.assertIn('el precio no se inventa', '\n'.join(registro.output))
        self.assertFalse(self.variante('ZZ-SIN-PRECIO'))

    def test_un_codigo_que_ya_esta_en_odoo_no_se_duplica(self):
        """Si alguien (o Brian, con el Excel de un proveedor) ya creó el código, la carga no lo duplica ni lo pisa."""
        a_mano = self.env['product.template'].create({'name': 'Hecho a mano', 'default_code': 'ZZ-MANO'})
        item = _item('zz-mano', [{'codigo': 'ZZ-MANO', 'precio': 5.0, 'existencias': 1}])
        with self.assertLogs('odoo.addons.dcasa_catalogo.catalogo', 'WARNING'):
            self.assertEqual(cargar_catalogo(self.env, self.catalogo(item)), 0)
        self.assertEqual(self.variante('ZZ-MANO'), a_mano.product_variant_id)

    def test_la_categoria_sale_del_nombre_como_en_la_importacion_de_brian(self):
        """Las reglas de ``reglas.CATEGORIAS`` (las de Baby Caleb) y los valores de un producto nuevo: lo mismo que usan
        el inventario anterior y la importación del Excel de un proveedor con Brian."""
        impuesto = self.env.ref('base.main_company').account_sale_tax_id
        for nombre, clave in (('Pañal Nateen Talla M', 'panales'), ('Toallitas húmedas de agua', 'toallitas'),
                              ('Water wipes Dany Baby', 'toallitas'), ('Fular Moon gris', 'fulares'),
                              ('Portabebés ergonómico', 'fulares')):
            self.assertEqual(categoria_de_nombre(nombre), clave, nombre)
            vals = C.valores_producto_nuevo(self.env, nombre, 10.0, impuesto, categoria_de_nombre(nombre))
            self.assertEqual(vals['categ_id'], self.env.ref(f'dcasa_catalogo.product_category_{clave}').id, nombre)
        self.assertIsNone(categoria_de_nombre('Cama tapizada King'), 'Los muebles de D’CASA ya no tienen categoría')
        self.assertNotIn('categ_id', C.valores_producto_nuevo(self.env, 'Cama', 1.0, impuesto, None))

    def test_un_archivo_mal_escrito_detiene_la_carga(self):
        malos = [
            _item('zz-1', [{'valor': 'XS', 'codigo': 'ZZ-XS', 'precio': 1.0}], atributo='Talla de prueba'),
            _item('zz-2', [{'valor': 'CH', 'codigo': 'ZZ-A', 'precio': 1.0}], atributo='Color que no está'),
            _item('zz-3', [{'codigo': 'ZZ-B', 'precio': 1.0}, {'codigo': 'ZZ-C', 'precio': 2.0}]),
            _item('zz-4', [{'codigo': 'ZZ-D', 'precio': 1.0}], categoria='muebles'),
            _item('zz-5', [{'valor': 'CH', 'codigo': 'ZZ-E', 'precio': 1.0},
                           {'valor': 'MED', 'codigo': 'ZZ-E', 'precio': 1.0}], atributo='Talla de prueba'),
        ]
        for item in malos:
            with self.subTest(item['clave']), self.assertRaises(ValueError):
                cargar_catalogo(self.env, self.catalogo(item))
        self.assertFalse(self.variante('ZZ-B') | self.variante('ZZ-D'), 'No se creó nada a medias')


@tagged('post_install', '-at_install')
class TestFichaConPresentacion(HttpCase):
    """La ficha de la tienda muestra la presentación de cada talla (unidades y rango de peso), aparte del precio."""

    def test_la_ficha_dice_la_presentacion_de_cada_talla(self):
        producto = self.env.ref(f'dcasa_catalogo.{xmlid_de("nateen-pants")}')
        producto.is_published = True
        html = self.url_open(producto.website_url).text
        self.assertIn('<dt>Presentación</dt>', html)
        for codigo in ('NAT-P-L', 'NAT-P-XL', 'NAT-P-XXL'):
            self.assertIn(LISTA_DEL_DUENO[codigo][0], html, codigo)


@tagged('post_install', '-at_install')
class TestBuscarProductos(TransactionCase):

    def test_filtros_rapidos_y_categorias(self):
        vista = self.env['product.template'].get_view(
            self.env.ref('product.product_template_search_view').id, 'search')
        arch = vista['arch']
        for nombre in ('dcasa_disponibles', 'dcasa_pocas', 'dcasa_agotados', 'dcasa_precio_1', 'dcasa_precio_4',
                       'dcasa_en_web'):
            self.assertIn(f'name="{nombre}"', arch)
        self.assertIn('<searchpanel', arch)
        self.assertIn('public_categ_ids', arch)
        # Los dominios funcionan de verdad (campos buscables).
        Producto = self.env['product.template']
        barato = Producto.create({'name': 'Banco de prueba', 'list_price': 50, 'is_storable': True})
        caro = Producto.create({'name': 'Sofá de prueba', 'list_price': 900, 'is_storable': True})
        self.assertIn(barato, Producto.search([('list_price', '<=', 100)]))
        self.assertNotIn(caro, Producto.search([('list_price', '<=', 100)]))
        self.assertIn(caro, Producto.search([('is_storable', '=', True), ('qty_available', '<=', 0)]))
