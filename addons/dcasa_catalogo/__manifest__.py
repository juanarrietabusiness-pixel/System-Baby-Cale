{
    'name': "D'CASA Panamá — Catálogo",
    'summary': "Productos del catálogo (Baby Caleb: pañales, toallitas y fulares) en inventario y tienda web",
    'description': """
Carga el catálogo del negocio en Odoo: el mismo producto para el inventario, las ventas y la tienda web.

* data/catalogo.json se escribe a mano con la lista del dueño (Baby Caleb, 2026-11-18): un producto por línea de
  producto, con un atributo y sus valores en los datos («Talla»: RN, S, M…) y, en cada variante, su código, su precio
  exacto, sus existencias y el texto del dueño (campo «Presentación»). Ver docs/CATALOGO.md.
* Precios del archivo tal cual, como precio de lista, con el ITBMS de venta de la empresa que se suma (la misma regla
  que tenía la carga anterior); un precio que falta no se inventa (el producto no se crea).
* Existencias de la lista: entran como ajuste de inventario (con su motivo) solo al crear el producto.
* Sin fotos: el dueño las sube a mano en Odoo; lo que no tiene foto queda en inventario sin publicar en la web.
* Categorías de Baby Caleb (Pañales, Toallitas húmedas, Fulares), internas y de la tienda.
* En Odoo: buscar por varias palabras («pañal m»), lista de productos con foto y cotización por WhatsApp en un clic.
* Disponibilidad en la ficha de la tienda («Disponible», «Quedan pocas» o «Agotado», nunca el número): la regla de
  dcasa_base/disponibilidad.py con las unidades libres de la variante elegida, la misma que dice Juan
  (``product.template._dcasa_disponibilidad``). Comprar o no comprar no cambia.
* Black Weekend: marca por código los productos de catalogo.BLACK_WEEKEND (hoy vacía). La ventana de la campaña vive
  en website_dcasa.
* Existencias de prueba solo en staging (dcasa_catalogo.stock_prueba; producción siempre 0).
* Inventario de un sistema anterior (data/inventario_anterior.csv, hoy solo el encabezado): existencias y precio por
  código; los códigos nuevos entran como productos sin publicar.
* Stock ordenable en Productos (campo dcasa_stock, guardado en cada producto): la lista de Productos ordena, filtra
  y suma por stock, precio y categoría para elegir qué empujar en una campaña; Productos abre en lista.
* Código público (DC-K7M4PX) a la vista en la ficha del producto, columna opcional en la lista y buscable en
  Productos y en las cotizaciones (el campo y el sorteo viven en dcasa_base).
* Combos que se arman en la venta (cama + colchón): botón «Armar combo» en la cotización; cada pieza puede tener su
  «Precio en combo» por medida, que pone Gerencia en Ventas › Productos › Precios en combo. Reglas en el servidor
  (models/combo_armable.py). Ver docs/OPERACION.md.
* Idempotente: volver a correr la carga solo crea lo que falta; no pisa lo que se cambió en Odoo (precios, fotos,
  textos, existencias).
""",
    'version': '19.0.2.0.0',
    'category': 'Sales',
    'author': "D'CASA Panamá",
    'website': 'https://dcasapty.com',
    'license': 'LGPL-3',
    'depends': ['dcasa_base', 'website_dcasa', 'website_sale_stock'],
    'data': [
        'data/product_category_data.xml',
        'data/product_public_category_data.xml',
        'views/backend_views.xml',
        'views/codigo_publico_views.xml',
        'views/copiar_views.xml',
        'views/product_templates.xml',
        'views/combos_views.xml',
        'views/report_combos.xml',
        'security/ir.model.access.csv',
        'views/productos_limpios_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'dcasa_catalogo/static/src/scss/catalogo.scss',
            'dcasa_catalogo/static/src/js/disponibilidad.js',
            'dcasa_catalogo/static/src/xml/disponibilidad.xml',
        ],
        'web.assets_backend': [
            'dcasa_catalogo/static/src/combo/armar_combo.js',
            'dcasa_catalogo/static/src/combo/armar_combo.xml',
            'dcasa_catalogo/static/src/combo/armar_combo.scss',
        ],
    },
    'post_init_hook': '_dcasa_catalogo_post_init',
    'installable': True,
}
