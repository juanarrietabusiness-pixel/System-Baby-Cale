"""Carga del catálogo (data/catalogo.json) en productos de Odoo.

El JSON se escribe a mano con la lista que da el dueño (hoy, la de Baby Caleb del 2026-11-18): código, precio,
existencias y su texto por cada variante. Aquí no se escribe ni se calcula ningún precio, solo se copian; un precio
que falta no se rellena (el producto no se crea y queda en el registro). El producto lleva el ITBMS de venta de la
empresa, que se suma al precio de lista (la misma regla que tenía la carga de D'CASA: ``itbms_de_venta``).

Formato de ``data/catalogo.json``::

    {"fuente": "…",                                  # de dónde salen las cifras (va en el motivo del ajuste)
     "atributos": {"Talla": ["RN", "S", …]},          # cada atributo con sus valores, en el orden de la tienda
     "productos": [{
        "clave": "nateen-diapers",                    # su xmlid (producto_nateen_diapers): no cambia nunca
        "nombre": "…", "categoria": "panales", "orden": 1,
        "descripcion": "…" | null,                    # la de la web del negocio; null si no hay
        "atributo": "Talla",                          # solo si tiene variantes
        "foto": "producto-nateen-cierre-m.jpg",          # opcional: archivo de data/fotos/ (la foto principal)
        "variantes": [{"valor": "RN", "codigo": "NAT-RN", "precio": 50.0, "existencias": 4, "texto": "…",
                       "foto": "…", "fotos_extra": ["…"],   # opcionales: la de esa talla y las de más
                       "precio_par": 35.0}]   # opcional: la promoción «2 por…» (``poner_precios_par``)
     }]}

Las claves que empiezan por ``origen_`` dicen de dónde salió cada dato (no se cargan).

Las fotos (``data/fotos/``) son las de la web del negocio, pasadas a JPEG o PNG; ``poner_fotos`` las pone solo donde
no hay ninguna y publica lo que recibe su foto principal. Lo que no tiene foto no se publica en la tienda (la misma
regla de siempre); se publica desde Odoo cuando ya la tiene.
"""
import base64
import json
import logging
import re

from markupsafe import escape

from odoo.addons.dcasa_base import archivar_itbms_incluido, itbms_de_venta
from odoo.exceptions import ValidationError
from odoo.tools import float_compare
from odoo.tools.misc import file_open

from .reglas import (  # noqa: F401 (API del módulo)
    TAMANOS,
    categoria_de_nombre,
    precio_terminado_en_99,
    tamano_del_nombre,
)

_logger = logging.getLogger(__name__)

MODULO = 'dcasa_catalogo'

# Categoría del catálogo → categoría interna (inventario/contabilidad) y de la tienda web. Las claves son las de
# ``reglas.CATEGORIAS`` (la importación del Excel de un proveedor con Brian usa las mismas).
CATEGORIA_INTERNA = {
    'panales': 'dcasa_catalogo.product_category_panales',
    'toallitas': 'dcasa_catalogo.product_category_toallitas',
    'fulares': 'dcasa_catalogo.product_category_fulares',
}
CATEGORIA_WEB = {
    'panales': 'dcasa_catalogo.public_category_panales',
    'toallitas': 'dcasa_catalogo.public_category_toallitas',
    'fulares': 'dcasa_catalogo.public_category_fulares',
}


def leer_catalogo():
    """``data/catalogo.json`` tal cual: ``{'fuente', 'atributos', 'productos'}``."""
    with file_open(f'{MODULO}/data/catalogo.json', 'rb') as archivo:
        return json.load(archivo)


def xmlid_de(clave):
    """``nateen-diapers`` → ``producto_nateen_diapers`` (también vale un código: ``1062010734/5/6N``)."""
    return 'producto_' + re.sub(r'[^a-z0-9]+', '_', clave.lower()).strip('_')


def pasar_a_itbms_que_se_suma(env):
    """Bases cargadas con el «ITBMS incluido»: los productos de esta carga pasan al ITBMS que se suma.

    El ``list_price`` ya es la cifra correcta y no se toca; solo cambia el impuesto. Un producto cuyo impuesto
    se cambió a mano (ya no es solo el «incluido» de la carga) se deja como está. La tienda pasa a mostrar el
    precio sin ITBMS («+ ITBMS») y, si el impuesto incluido queda sin uso, se archiva. Devuelve cuántos
    productos se corrigieron.
    """
    company = env.ref('base.main_company')
    venta = itbms_de_venta(env, company)
    ids = env['ir.model.data'].search([('module', '=', MODULO), ('model', '=', 'product.template')]).mapped('res_id')
    productos = env['product.template'].with_context(active_test=False).browse(ids).exists()
    corregidos = productos.filtered(lambda p: p.taxes_id and all(
        t.price_include and t.type_tax_use == 'sale' and t.amount == venta.amount for t in p.taxes_id))
    if venta and corregidos:
        corregidos.taxes_id = [(6, 0, venta.ids)]
    env['website'].search([]).show_line_subtotals_tax_selection = 'tax_excluded'
    archivar_itbms_incluido(env, company)
    _logger.info('Catálogo: %s productos pasan al ITBMS que se suma al precio.', len(corregidos))
    return len(corregidos)


def atributo_tamano(env):
    """Atributo «Tamaño» (Twin, Full, Queen, King): lo usan los combos cama + colchón y la importación de Brian."""
    Atributo = env['product.attribute']
    atributo = Atributo.search([('name', '=', 'Tamaño')], limit=1) or Atributo.create({
        'name': 'Tamaño', 'create_variant': 'always', 'display_type': 'radio',
    })
    valores = {}
    for orden, nombre in enumerate(TAMANOS, start=1):
        valor = atributo.value_ids.filtered(lambda v, n=nombre: v.name == n)[:1]
        valores[nombre] = valor or env['product.attribute.value'].create({
            'name': nombre, 'attribute_id': atributo.id, 'sequence': orden,
        })
    return atributo, valores


def atributo_con_valores(env, nombre, valores):
    """Atributo que crea variantes (p. ej. «Talla») con sus valores en ese orden: ``(atributo, {valor: registro})``.

    El atributo y los valores que ya existen se usan tal cual (sin importar mayúsculas); los que faltan se crean con
    el orden de la lista (así la tienda muestra RN, S, M… y no el orden en que se crearon).
    """
    Atributo = env['product.attribute']
    atributo = Atributo.search([('name', '=', nombre), ('create_variant', '=', 'always')], limit=1)
    atributo = atributo or Atributo.create({'name': nombre, 'create_variant': 'always', 'display_type': 'radio'})
    registros = {}
    for orden, valor in enumerate(valores, start=1):
        existente = atributo.value_ids.filtered(lambda v, n=valor: v.name.lower() == n.lower())[:1]
        registros[valor] = existente or env['product.attribute.value'].create({
            'name': valor, 'attribute_id': atributo.id, 'sequence': orden,
        })
    return atributo, registros


def categoria_web(env, clave):
    return env.ref(CATEGORIA_WEB[clave])


def valores_producto_nuevo(env, nombre, precio, impuesto, clave_categoria=None, tamano=None):
    """Lo que lleva un producto nuevo del catálogo (lo usan esta carga, el inventario anterior y la de Brian).

    Inventariable, sin ``allow_out_of_stock_order`` (lo agotado no se pide en la web: decisión del dueño de Baby Caleb,
    2026-11-24),
    ``list_price`` = el precio que llega, con el ITBMS de venta que se suma, categoría interna y de la tienda según la
    clave de ``reglas.CATEGORIAS`` y, si es de un solo tamaño de cama, la línea de atributo «Tamaño» (para el filtro de
    la tienda y los combos). La publicación la decide quien llama.
    """
    vals = {
        'name': nombre,
        'type': 'consu',
        'is_storable': True,
        'allow_out_of_stock_order': False,
        'list_price': precio,
        'taxes_id': [(6, 0, impuesto.ids)],
    }
    if clave_categoria in CATEGORIA_INTERNA:
        vals['categ_id'] = env.ref(CATEGORIA_INTERNA[clave_categoria]).id
        vals['public_categ_ids'] = [(6, 0, categoria_web(env, clave_categoria).ids)]
    if tamano in TAMANOS:
        atributo, valores = atributo_tamano(env)
        vals['attribute_line_ids'] = [(0, 0, {
            'attribute_id': atributo.id, 'value_ids': [(6, 0, valores[tamano].ids)]})]
    return vals


def motivo_existencias(catalogo):
    """El motivo del ajuste de inventario de la carga (la bitácora de bodega lo exige y lo muestra)."""
    fuente = (catalogo.get('fuente') or '').strip()
    return f'Existencias iniciales del catálogo ({fuente})' if fuente else 'Existencias iniciales del catálogo'


def _error(item, texto):
    return ValueError(f"data/catalogo.json, producto «{item.get('clave')}»: {texto}")


def _validar(item, atributos):
    """Lo que el JSON tiene que traer para crear el producto sin adivinar nada (si no, la instalación se detiene)."""
    for campo in ('clave', 'nombre', 'orden', 'variantes'):
        if not item.get(campo):
            raise _error(item, f'falta «{campo}»')
    if item.get('categoria') and item['categoria'] not in CATEGORIA_INTERNA:
        raise _error(item, f"la categoría «{item['categoria']}» no existe ({', '.join(CATEGORIA_INTERNA)})")
    variantes = item['variantes']
    codigos = [v.get('codigo') for v in variantes]
    if not all(codigos) or len(set(codigos)) != len(codigos):
        raise _error(item, 'cada variante necesita su código, y no se repiten')
    nombre_atributo = item.get('atributo')
    if not nombre_atributo:
        if len(variantes) != 1:
            raise _error(item, 'varias variantes necesitan su «atributo»')
        return
    if nombre_atributo not in atributos:
        raise _error(item, f'el atributo «{nombre_atributo}» no está en «atributos»')
    valores = [v.get('valor') for v in variantes]
    faltan = [v for v in valores if v not in atributos[nombre_atributo]]
    if faltan or len(set(valores)) != len(valores):
        raise _error(item, f'valores de «{nombre_atributo}» fuera de «atributos» o repetidos: {faltan or valores}')


def _poner_existencias(env, variante, ubicacion, cantidad, motivo):
    """Ajuste de inventario a ``cantidad`` (el de Odoo, con su movimiento y el motivo en la bitácora de bodega)."""
    env['stock.quant'].with_context(inventory_mode=True, inventory_name=motivo).create({
        'product_id': variante.id,
        'location_id': ubicacion.id,
        'inventory_quantity': cantidad,
    })._apply_inventory()


def _crear_producto(env, item, atributos, impuesto, ubicacion, motivo):
    """El producto de un ``item`` del JSON, con sus variantes (código, precio exacto, presentación) y existencias."""
    variantes = item['variantes']
    base = min(v['precio'] for v in variantes)
    vals = valores_producto_nuevo(env, item['nombre'], base, impuesto, item.get('categoria'))
    vals.update({
        'website_sequence': item['orden'] * 10,
        'is_published': False,  # sin foto todavía: se publica desde Odoo cuando la tenga
    })
    if item.get('descripcion'):
        vals['description_ecommerce'] = f"<p>{escape(item['descripcion'])}</p>"
    nombre_atributo = item.get('atributo')
    if nombre_atributo:
        atributo, valores = atributo_con_valores(env, nombre_atributo, atributos[nombre_atributo])
        vals['attribute_line_ids'] = [(0, 0, {
            'attribute_id': atributo.id,
            'value_ids': [(6, 0, [valores[v['valor']].id for v in variantes])],
        })]
    else:
        vals['default_code'] = variantes[0]['codigo']
    producto = env['product.template'].create(vals)
    if nombre_atributo:
        por_valor = {v['valor'].lower(): v for v in variantes}

        def datos_de(registro):
            return por_valor[registro.product_attribute_value_id.name.lower()]

        for ptav in producto.attribute_line_ids.product_template_value_ids:
            ptav.price_extra = datos_de(ptav)['precio'] - base
        pares = [(v, datos_de(v.product_template_attribute_value_ids)) for v in producto.product_variant_ids]
    else:
        pares = [(producto.product_variant_id, variantes[0])]
    for variante, datos in pares:
        variante.write({'default_code': datos['codigo'], 'dcasa_presentacion': datos.get('texto') or False})
        if float_compare(variante.lst_price, datos['precio'], precision_digits=2):
            raise _error(item, f"{datos['codigo']} quedó a {variante.lst_price}; el archivo dice {datos['precio']}")
        if datos.get('existencias') and ubicacion:
            _poner_existencias(env, variante, ubicacion, datos['existencias'], motivo)
    return producto


def cargar_catalogo(env, catalogo=None):
    """Crea los productos que falten. Lo que ya existe (por su xmlid) no se toca: ni precio, ni nombre, ni existencias.

    Tampoco se crea un producto si alguno de sus códigos ya está en Odoo sin ser de esta carga (lo cargó Brian o una
    persona): no se duplica ni se pisa; queda en el registro. Un producto sin precio en alguna variante tampoco se crea
    (no se inventa una cifra). Las existencias del JSON entran como ajuste de inventario solo al crear el producto.
    Con «atributo», cada variante es un valor (``list_price`` = el precio más bajo y ``price_extra`` = lo que cada una
    tiene de más: cada variante queda con su precio exacto); sin él, el producto tiene una sola variante.
    Devuelve cuántos productos se crearon.
    """
    company = env.ref('base.main_company')
    env = env(context=dict(env.context, allowed_company_ids=company.ids, lang='es_419'))
    catalogo = leer_catalogo() if catalogo is None else catalogo
    atributos = catalogo.get('atributos') or {}
    productos = catalogo.get('productos') or []
    for item in productos:
        _validar(item, atributos)
    impuesto = itbms_de_venta(env, company)
    ubicacion = env['stock.warehouse'].search([('company_id', '=', company.id)], limit=1).lot_stock_id
    motivo = motivo_existencias(catalogo)
    Variante = env['product.product'].with_context(active_test=False)
    creados = 0
    for item in productos:
        xmlid = xmlid_de(item['clave'])
        if env.ref(f'{MODULO}.{xmlid}', raise_if_not_found=False):
            continue
        codigos = [v['codigo'] for v in item['variantes']]
        if Variante.search_count([('default_code', 'in', codigos)], limit=1):
            _logger.warning('Catálogo: %s ya está en Odoo (no es de esta carga): no se crea.', ', '.join(codigos))
            continue
        if any(v.get('precio') is None for v in item['variantes']):
            _logger.warning('Catálogo: %s sin precio en el archivo: no se crea (el precio no se inventa).',
                            item['clave'])
            continue
        producto = _crear_producto(env, item, atributos, impuesto, ubicacion, motivo)
        env['ir.model.data'].create({
            'module': MODULO, 'name': xmlid, 'model': 'product.template',
            'res_id': producto.id, 'noupdate': True,
        })
        creados += 1

    # La tienda muestra el precio de lista (sin ITBMS) con «+ ITBMS»; el carrito suma el impuesto.
    env['website'].search([]).show_line_subtotals_tax_selection = 'tax_excluded'
    _logger.info('Catálogo: %s productos nuevos.', creados)
    return creados


def foto_del_catalogo(nombre):
    """Los bytes (base64) de ``data/fotos/<nombre>``, listos para un campo de imagen."""
    with file_open(f'{MODULO}/data/fotos/{nombre}', 'rb') as archivo:
        return base64.b64encode(archivo.read())


def poner_fotos(env, catalogo=None):
    """Las fotos del catálogo en los productos que no tienen, y se publica lo que recibe su foto principal.

    Solo se llena lo vacío: una foto que ya está (la puso una persona) no se cambia, y a ese producto no se le toca la
    publicación. Las fotos de más de una talla se agregan solo si la talla no tiene ninguna. Un producto del archivo
    que ya no está en Odoo (lo borraron) se salta. Se puede repetir sin duplicar nada. Devuelve cuántos productos se
    publicaron.
    """
    catalogo = leer_catalogo() if catalogo is None else catalogo
    Imagen = env['product.image']
    publicados = 0
    for item in catalogo.get('productos') or []:
        plantilla = env.ref(f'{MODULO}.{xmlid_de(item["clave"])}', raise_if_not_found=False)
        if not plantilla:
            continue
        if item.get('foto') and not plantilla.image_1920:
            plantilla.image_1920 = foto_del_catalogo(item['foto'])
            if not plantilla.is_published and item.get('publicar', True):
                plantilla.is_published = True
                publicados += 1
        variantes = plantilla.with_context(active_test=False).product_variant_ids
        for datos in item.get('variantes') or []:
            variante = variantes.filtered(lambda v, c=datos['codigo']: v.default_code == c)[:1]
            if not variante:
                continue
            if datos.get('foto') and not variante.image_variant_1920:
                variante.image_variant_1920 = foto_del_catalogo(datos['foto'])
            if datos.get('fotos_extra') and not variante.product_variant_image_ids:
                nombre = ' '.join(filter(None, (plantilla.name, datos.get('valor'))))
                Imagen.create([{'name': nombre, 'product_variant_id': variante.id, 'sequence': orden,
                                'image_1920': foto_del_catalogo(archivo)}
                               for orden, archivo in enumerate(datos['fotos_extra'], start=1)])
    _logger.info('Catálogo: fotos puestas; %s productos publicados.', publicados)
    return publicados


def poner_precios_par(env, catalogo=None):
    """El «Precio por par» (la promoción «2 por…», ``models/precio_par.py``) de las variantes que lo traen en
    ``data/catalogo.json`` (``precio_par``), solo donde está vacío: el que ya puso Gerencia no se pisa. Hoy, DANY-AW600
    a $35.00 (decisión del dueño, 2026-11-24). Se puede repetir.

    Devuelve ``{código: resultado}``: ``cargado``, ``ya_tenia``, ``no_encontrado``, ``repetido`` o ``no_vale`` (la
    variante cambió y la cifra ya no es una promoción válida: menor que dos sueltas y partible en dos al centavo; no
    se adivina otra, la pone Gerencia)."""
    catalogo = leer_catalogo() if catalogo is None else catalogo
    Variante = env['product.product'].sudo().with_context(active_test=False)
    resultado = {}
    for item in catalogo.get('productos') or []:
        for datos in item.get('variantes') or []:
            precio = datos.get('precio_par')
            if precio is None:
                continue
            codigo = datos['codigo']
            variantes = Variante.search([('default_code', '=', codigo)])
            if len(variantes) != 1:
                resultado[codigo] = 'repetido' if variantes else 'no_encontrado'
                continue
            if variantes.dcasa_precio_par:
                resultado[codigo] = 'ya_tenia'
                continue
            try:
                with env.cr.savepoint():
                    variantes.dcasa_precio_par = precio
                    variantes.flush_recordset(['dcasa_precio_par'])
            except ValidationError as error:
                _logger.warning('Catálogo: el precio por par de %s no se puso: %s', codigo, error)
                resultado[codigo] = 'no_vale'
                continue
            resultado[codigo] = 'cargado'
    if resultado:
        _logger.info('Catálogo: precio por par %s.', resultado)
    return resultado


def no_vender_agotados(env):
    """Lo agotado no se pide en la web (decisión del dueño de Baby Caleb, 2026-11-24: «¿se deja que los pidan igual?
    No»). El ajuste de Odoo «Continuar vendiendo sin existencias» queda apagado para los productos nuevos y se apaga en
    los que ya están. Se puede repetir. Devuelve cuántos productos cambiaron."""
    env['ir.default'].sudo().set('product.template', 'allow_out_of_stock_order', False)
    productos = env['product.template'].sudo().with_context(active_test=False).search([
        ('allow_out_of_stock_order', '=', True)])
    productos.allow_out_of_stock_order = False
    _logger.info('Catálogo: lo agotado ya no se pide en la web (%s productos).', len(productos))
    return len(productos)


def archivar_variantes(env, catalogo=None):
    """Archiva las tallas marcadas ``"archivada": true`` en ``data/catalogo.json`` (hoy, la Nateen L de cierre).

    La variante se archiva, no se borra: conserva su código, su precio y su presentación, y se reactiva desde
    Inventario › Productos › Variantes (filtro «Archivado»). Archivada, no sale en la tienda, ni en la lista
    «Presentación», ni en lo que busca Juan. Devuelve las que archivó.
    """
    catalogo = leer_catalogo() if catalogo is None else catalogo
    codigos = [v['codigo'] for item in catalogo.get('productos') or [] for v in item['variantes']
               if v.get('archivada')]
    variantes = env['product.product'].sudo().search([('default_code', 'in', codigos)]) if codigos else \
        env['product.product']
    variantes.active = False
    if variantes:
        _logger.info('Catálogo: archivadas %s.', ', '.join(variantes.mapped('default_code')))
    return variantes


# --- Black Weekend ------------------------------------------------------------------------------

# Productos de la campaña: (código del producto o de la variante destacada, nota de dónde salió la selección), en el
# orden de la lista. Los precios NO están aquí: la web muestra los del catálogo (website_dcasa/models/black_weekend.py).
# Vacía: la selección de D'CASA no es de este negocio; la de Baby Caleb la decide su dueño.
BLACK_WEEKEND = []


def marcar_black_weekend(env, seleccion=None):
    """Marca los productos de Black Weekend por su código (``default_code`` de la variante).

    Idempotente: deja la marca, el orden (10, 20, …) y, si el código es de una variante de un producto con varias,
    esa variante como la destacada. No quita la marca a otros productos (se pueden sumar más desde Odoo). Un código
    que no está se anota en el registro y se sigue. Devuelve cuántos productos quedaron marcados.
    """
    seleccion = BLACK_WEEKEND if seleccion is None else seleccion
    Variante = env['product.product'].with_context(active_test=False)
    marcados = 0
    for orden, (codigo, _nota) in enumerate(seleccion, start=1):
        variante = Variante.search([('default_code', '=', codigo)], limit=1)
        if not variante:
            _logger.warning('Black Weekend: el código %s no está en el catálogo: no se marca.', codigo)
            continue
        producto = variante.product_tmpl_id
        vals = {'dcasa_black_weekend': True, 'dcasa_bw_orden': orden * 10}
        vals['dcasa_bw_variante_id'] = variante.id if producto.product_variant_count > 1 else False
        cambios = {k: v for k, v in vals.items()
                   if (producto[k].id if k == 'dcasa_bw_variante_id' else producto[k]) != v}
        if cambios:
            producto.write(cambios)
        marcados += 1
    _logger.info('Black Weekend: %s productos marcados.', marcados)
    return marcados


# --- Existencias de prueba (solo staging) ------------------------------------------------------

PARAM_STOCK_PRUEBA = 'dcasa_catalogo.stock_prueba'


def stock_de_prueba(env):
    """Unidades de prueba por producto (``dcasa_catalogo.stock_prueba``); vacío, 0 o inválido = apagado.

    Lo fija docker/entrypoint.sh desde DCASA_STOCK_PRUEBA: 10 en staging, siempre 0 en producción.
    """
    valor = env['ir.config_parameter'].sudo().get_param(PARAM_STOCK_PRUEBA) or '0'
    try:
        return max(int(float(valor)), 0)
    except ValueError:
        return 0


def aplicar_stock_prueba(env):
    """Pone las unidades de prueba en el almacén principal a los productos que nunca tuvieron stock.

    Solo productos inventariables, sin lote/serie, con existencias 0 y SIN ningún movimiento de
    inventario: un conteo real (o una venta) nunca se pisa. Usa el ajuste de inventario de Odoo
    (``stock.quant._apply_inventory``), que deja su movimiento: por eso es idempotente (la
    segunda vez ya tienen movimiento). Devuelve cuántos productos recibieron existencias.
    """
    cantidad = stock_de_prueba(env)
    if cantidad <= 0:
        return 0
    company = env.ref('base.main_company')
    env = env(context=dict(env.context, allowed_company_ids=company.ids))
    almacen = env['stock.warehouse'].search([('company_id', '=', company.id)], limit=1)
    if not almacen:
        return 0
    productos = env['product.product'].search([
        ('is_storable', '=', True), ('tracking', '=', 'none'),
        ('company_id', 'in', [False, company.id]),
    ])
    con_movimientos = {
        producto.id for [producto] in env['stock.move'].sudo().with_context(active_test=False)._read_group(
            [('product_id', 'in', productos.ids)], ['product_id'])
    }
    sin_stock = productos.filtered(
        lambda p: p.id not in con_movimientos and p.with_company(company).qty_available == 0)
    if not sin_stock:
        return 0
    Quant = env['stock.quant'].with_context(inventory_mode=True, inventory_name='Existencias de prueba (staging)')
    quants = Quant.browse()
    for producto in sin_stock:
        quants |= Quant.create({
            'product_id': producto.id,
            'location_id': almacen.lot_stock_id.id,
            'inventory_quantity': cantidad,
        })
    quants._apply_inventory()
    _logger.info('Existencias de prueba: %s productos con %s unidades en %s.',
                 len(sin_stock), cantidad, almacen.lot_stock_id.complete_name)
    return len(sin_stock)
