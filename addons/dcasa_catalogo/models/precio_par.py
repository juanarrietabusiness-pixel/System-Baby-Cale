"""Promoción por pares: «2 cajas por $35.00» (decisión del dueño de Baby Caleb, 2026-11-24, sin fecha de fin).

La regla del dueño, con sus palabras: «la promoción solamente son 2 cajas… si no, la tercera caja se cobra completa».
Cada par de cajas va al precio del par y una caja suelta, a su precio normal: 1 caja = normal; 2 = el par; 3 = el par
más una normal; 4 = dos pares; 5 = dos pares más una normal…

* **El dato** es del producto: ``product.product.dcasa_precio_par`` («Precio por par»: lo que cuestan 2 juntas, sin
  ITBMS, en la moneda de la empresa). Lo cambia solo quien cambia precios (Gerencia y administradores:
  ``_puede_cambiar_precios`` de dcasa_base). Vacío: sin promoción. Tiene que ser menor que dos sueltas y partirse en
  dos al centavo (cada caja del par se cobra a la mitad: así el total queda exacto). En el código no hay ninguna cifra:
  el de DANY-AW600 entra por ``data/catalogo.json`` (``precio_par``) y, en una base ya instalada, por la migración
  19.0.2.4.0, solo si el campo está vacío (``catalogo.poner_precios_par``).
* **El cobro**: una línea con un número PAR de cajas va a la mitad del precio del par por caja (``_get_display_price``,
  el mismo camino del precio de lista, como el precio en combo); una línea con un número impar, a su precio normal.
  Para que el total salga exacto, las cajas de un mismo producto en una venta abierta (borrador o enviada) se acomodan
  solas en, como mucho, dos líneas: la de los pares y la de la caja suelta (``sale.order._dcasa_pares_al_dia``).
  3 cajas = 2 a $17.50 + 1 a $20.00 = $55.00. Es igual en el carrito de la web, en la cotización de Juan y en una venta
  del panel, porque todo pasa por las líneas de venta.
* **Acomodar no rompe el carrito**: la línea que alguien acaba de crear o cambiar (el «+», el «−» o la cantidad del
  carrito, la que agregó la ficha) nunca se borra; las demás del mismo producto se juntan con ella o se parten. Así el
  carrito, que se vuelve a pintar desde el servidor después de cada cambio, nunca pierde ni duplica cajas. Si para
  llegar a la forma exacta habría que borrar una línea recién tocada (dos líneas nuevas del mismo producto en un mismo
  guardado), se deja para el final del guardado del pedido (``sale.order.create``/``write``).
* **Lo que no se acomoda**: una línea con precio o descuento puesto a mano (la vendedora decidió: como en los combos,
  no se reparte), lo facturado o entregado, las piezas de un combo, las secciones y los anticipos, y las ventas ya
  confirmadas o bloqueadas. Ahí cada línea se cobra por su número de cajas (par: precio del par; impar: normal).
* **No se suma a otra rebaja**: si la tarifa del pedido (la campaña del sitio, por ejemplo) ya deja la caja igual o más
  barata que la mitad del par, va la tarifa y no la promoción; si la promoción es mejor, va la promoción sin el
  descuento de la tarifa. Nunca las dos.
* **El tope de la vendedora se mide sobre el precio de la promoción** (``_dcasa_precio_autorizado``): el par lo
  autorizó Gerencia, así que no cuenta como rebaja de la vendedora; lo que ella rebaje encima, sí.
* **Lo que se lee**: la ficha de la tienda dice «Promoción: 2 cajas por $35.00» y que una caja suelta va a su precio
  normal (``product.template._dcasa_promos_par``); el carrito, la cotización en PDF, la página del cliente y la factura
  rotulan la línea del par («Promoción: 2 cajas por $35.00») y la caja suelta («Caja suelta: precio normal»); Juan y
  Andrés reciben el precio del par ya escrito en la ficha del producto (no calculan nada).
* Las banderas internas de contexto valen solo con ``INTERNO`` (website_dcasa), que una llamada por RPC no fabrica.
"""
from odoo import api, fields, models
from odoo.addons.dcasa_base.models.product import _puede_cambiar_precios
from odoo.addons.dcasa_base.models.venta_online import CLAVE_PRECIO, PRECIO_DEL_SISTEMA
from odoo.addons.website_dcasa.models.campana import INTERNO, con_defaults, es_interno
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import float_compare, float_is_zero, float_round

from .combo_armable import SIN_RECALCULAR, _moneda

# El acomodo de las líneas ya está corriendo (o lo hace otro paso del mismo guardado): no se vuelve a entrar.
SIN_ACOMODAR = 'dcasa_par_sin_acomodar'
# Lo que, al cambiar en una línea, puede dejar las cajas de un producto mal repartidas.
CAMPOS_DE_PARES = frozenset({'product_id', 'product_uom_qty', 'product_uom_id', 'order_id', 'price_unit', 'discount'})


def _aviso_gerencia(env):
    return AccessError(env._('Solo Gerencia cambia el precio por par (la promoción «2 por…»).'))


def _sin_pares(ordenes, productos):
    """¿Ninguna línea de estas ventas (ni ``productos``, los que se van a poner) tiene precio por par? Entonces no hay
    nada que acomodar ni que medir de más (el tope ya lo mide dcasa_base)."""
    return not any(producto.dcasa_precio_par > 0 for producto in ordenes.order_line.product_id | productos)


def _productos_de(env, valores):
    """Los productos que traen unos ``vals`` de líneas de venta."""
    return env['product.product'].browse(
        [vals['product_id'] for vals in valores if isinstance(vals.get('product_id'), int)])


def _entero(cantidad):
    """La cantidad como entero, o ``None`` si no es un número entero de unidades."""
    if float_is_zero(cantidad - round(cantidad), precision_digits=6):
        return int(round(cantidad))
    return None


class ProductProduct(models.Model):
    _inherit = 'product.product'

    dcasa_precio_par = fields.Float(
        string='Precio por par', digits='Product Price', copy=False, aggregator=None,
        help='Promoción «2 por…»: lo que cuestan 2 juntas (sin ITBMS). Cada par se cobra a este precio y una suelta va '
             'a su precio normal (3 = un par + una normal). Lo pone Gerencia; tiene que ser menor que 2 sueltas y '
             'poder partirse en dos al centavo. Vacío: sin promoción.')

    @api.constrains('dcasa_precio_par')
    def _check_dcasa_precio_par(self):
        digitos = self.env['decimal.precision'].precision_get('Product Price')
        for variante in self:
            precio = variante.dcasa_precio_par
            if not precio:
                continue
            if precio < 0:
                raise ValidationError(self.env._(
                    'El precio por par tiene que ser mayor que 0 (o vacío: sin promoción).'))
            mitad = float_round(precio / 2, precision_digits=digitos)
            if float_compare(mitad * 2, precio, precision_digits=digitos):
                raise ValidationError(self.env._(
                    'El precio por par de «%(producto)s» tiene que poder partirse en dos al centavo, porque cada una '
                    'del par se cobra a la mitad (por ejemplo 35.00 o 35.02, no 35.01).',
                    producto=variante.display_name))
            if float_compare(precio, 2 * variante.lst_price, precision_digits=digitos) >= 0:
                raise ValidationError(self.env._(
                    'El precio por par de «%(producto)s» tiene que ser menor que el de 2 sueltas (%(dos)s).',
                    producto=variante.display_name,
                    dos=_moneda(variante.currency_id or self.env.company.currency_id, 2 * variante.lst_price)))

    @api.model_create_multi
    def create(self, vals_list):
        # Con los ``default_`` del contexto (ver ``con_defaults``): el precio por par lo pone Gerencia.
        if not _puede_cambiar_precios(self.env) and any(
                con_defaults(self.env, vals, ('dcasa_precio_par',)).get('dcasa_precio_par') for vals in vals_list):
            raise _aviso_gerencia(self.env)
        return super().create(vals_list)

    def write(self, vals):
        if 'dcasa_precio_par' in vals and not _puede_cambiar_precios(self.env) and any(
                float_compare(vals['dcasa_precio_par'] or 0.0, variante.dcasa_precio_par, precision_digits=2)
                for variante in self):
            raise _aviso_gerencia(self.env)
        return super().write(vals)

    # --- Textos (los mismos en la ficha, el carrito, el papel, Juan y Brian) -------------------------------

    def _dcasa_par_en_moneda(self, moneda=None, compania=None, fecha=None):
        """El precio por par en ``moneda`` (por defecto, la de la empresa), sin ITBMS y sin redondear."""
        self.ensure_one()
        compania = compania or self.env.company
        moneda = moneda or compania.currency_id
        return compania.currency_id._convert(self.dcasa_precio_par, moneda, compania,
                                             fecha or fields.Date.context_today(self), round=False)

    def _dcasa_par_dice_caja(self):
        """¿Se vende por caja? Lo dice su presentación («caja de 600 toallitas»): así el texto dice «2 cajas»."""
        self.ensure_one()
        return 'caja' in (self.dcasa_presentacion or '').lower()

    def _dcasa_par_texto(self, moneda=None, compania=None, fecha=None):
        """«2 cajas por $35.00» (o «2 por $35.00» si no se vende por caja); vacío sin promoción."""
        self.ensure_one()
        if self.dcasa_precio_par <= 0:
            return ''
        compania = compania or self.env.company
        moneda = moneda or compania.currency_id
        monto = _moneda(moneda, moneda.round(self._dcasa_par_en_moneda(moneda, compania, fecha)))
        if self._dcasa_par_dice_caja():
            return self.env._('2 cajas por %s', monto)
        return self.env._('2 por %s', monto)

    def _dcasa_par_nota(self):
        """La regla del dueño en una línea: los pares van a la promoción y la que sobra, a su precio normal."""
        self.ensure_one()
        if self._dcasa_par_dice_caja():
            return self.env._('Va por pares: una caja suelta va a su precio normal.')
        return self.env._('Va por pares: una suelta va a su precio normal.')

    def _dcasa_par_texto_suelta(self):
        self.ensure_one()
        if self._dcasa_par_dice_caja():
            return self.env._('Caja suelta: precio normal')
        return self.env._('Suelta: precio normal')


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Como «Presentación»: el dato es de la variante; aquí se ve y se edita cuando el producto tiene una sola.
    dcasa_precio_par = fields.Float(
        string='Precio por par', digits='Product Price',
        compute='_compute_dcasa_precio_par', inverse='_inverse_dcasa_precio_par',
        help='Promoción «2 por…»: lo que cuestan 2 juntas (sin ITBMS). Cada par se cobra a este precio y una suelta va '
             'a su precio normal (3 = un par + una normal). Lo pone Gerencia. Vacío: sin promoción. Con tallas, cada '
             'variante tiene el suyo.')

    @api.depends('product_variant_ids.dcasa_precio_par')
    def _compute_dcasa_precio_par(self):
        for plantilla in self:
            unica = plantilla.product_variant_ids if len(plantilla.product_variant_ids) == 1 else None
            plantilla.dcasa_precio_par = unica.dcasa_precio_par if unica else 0.0

    def _inverse_dcasa_precio_par(self):
        for plantilla in self:
            if len(plantilla.product_variant_ids) == 1:
                plantilla.product_variant_ids.dcasa_precio_par = plantilla.dcasa_precio_par

    def _dcasa_promos_par(self):
        """Lo que dice la ficha de la tienda: ``['2 cajas por $35.00. Va por pares: …']``. Con tallas de promoción
        distinta, una por talla («Talla M: …»); sin promoción, vacía."""
        self.ensure_one()
        variantes = self.sudo().product_variant_ids.filtered(lambda v: v.dcasa_precio_par > 0)
        if not variantes:
            return []
        textos = {v: f'{v._dcasa_par_texto()}. {v._dcasa_par_nota()}' for v in variantes}
        if len(set(textos.values())) == 1 and len(variantes) == len(self.sudo().product_variant_ids):
            return [next(iter(textos.values()))]
        return [f'{v.product_template_attribute_value_ids._get_combination_name() or v.display_name}: {texto}'
                for v, texto in textos.items()]


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model_create_multi
    def create(self, vals_list):
        ordenes = super().create(vals_list)
        # Lo que las líneas no pudieron acomodar solas (dos líneas nuevas del mismo producto en el mismo guardado).
        if not es_interno(self.env, SIN_ACOMODAR) and ordenes._dcasa_pares_al_dia():
            ordenes._dcasa_validar_tope_del_pedido({})
        return ordenes

    def write(self, vals):
        if 'order_line' not in vals or es_interno(self.env, SIN_ACOMODAR):
            return super().write(vals)
        nuevas = [comando[2] for comando in vals['order_line'] if isinstance(comando, (list, tuple))
                  and len(comando) > 2 and comando[0] in (0, 1) and isinstance(comando[2], dict)]
        if _sin_pares(self, _productos_de(self.env, nuevas)):
            return super().write(vals)
        antes = self._dcasa_exceso_previo()
        resultado = super().write(vals)
        if self._dcasa_pares_al_dia():
            self._dcasa_validar_tope_del_pedido(antes)
        return resultado

    def _dcasa_pares_al_dia(self, protegidas=None):
        """Acomoda las cajas de cada producto con precio por par en, como mucho, dos líneas: la de los pares y la de
        la caja suelta. Solo en ventas abiertas (borrador o enviada) y sin bloquear. ``protegidas``: líneas que no se
        borran (las que alguien acaba de crear o cambiar). ¿Cambió algo?"""
        if es_interno(self.env, SIN_ACOMODAR) or es_interno(self.env, SIN_RECALCULAR):
            return False
        protegidas = protegidas if protegidas is not None else self.env['sale.order.line']
        cambio = False
        for orden in self.exists():
            if orden.state not in ('draft', 'sent') or orden.locked:
                continue
            grupos = {}
            for linea in orden.order_line:
                if linea._dcasa_par_se_puede_acomodar():
                    clave = (linea.product_id.id, tuple(sorted(linea.product_no_variant_attribute_value_ids.ids)))
                    grupos[clave] = grupos.get(clave, linea.browse()) | linea
            for grupo in grupos.values():
                cambio = orden._dcasa_acomodar_par(grupo, protegidas) or cambio
        return cambio

    def _dcasa_acomodar_par(self, grupo, protegidas):
        """Deja las líneas ``grupo`` (un mismo producto) en la forma exacta: una con los pares y, si sobra una, otra
        con esa caja. La línea de los pares es la que se acaba de tocar (si hay una); las demás se ajustan, se crea la
        de la caja suelta (copia de la del par) o se quitan. ¿Cambió algo?"""
        self.ensure_one()
        lineas = grupo.sorted(lambda ln: (ln.sequence, ln.id))
        cantidades = [_entero(ln.product_uom_qty) for ln in lineas]
        pares, suelta = divmod(sum(cantidades), 2)
        quiero = sorted(q for q in (2 * pares, suelta) if q)
        if sorted(cantidades) == quiero:
            return False
        fijas = lineas & protegidas
        if len(fijas) > len(quiero):
            return False   # haría falta borrar una línea que alguien está usando: lo termina el guardado del pedido
        en_orden = list(fijas) + list(lineas - fijas)
        par = en_orden[0] if pares else None
        resto = [ln for ln in en_orden if ln != par]
        sola = None
        if suelta:
            sola = en_orden[0] if par is None else next(
                (ln for ln in resto if _entero(ln.product_uom_qty) == 1), resto[0] if resto else None)
        sobran = [ln for ln in resto if ln != sola]
        # Lo hace el sistema: en sudo (el tope no se mide a la mitad del acomodo; se mide entero al final, como en los
        # combos), sin volver a entrar aquí ni en los combos, y con la llave del precio del sistema (nadie lo tecleó).
        contexto = {SIN_ACOMODAR: INTERNO, SIN_RECALCULAR: INTERNO, CLAVE_PRECIO: PRECIO_DEL_SISTEMA}
        Linea = self.env['sale.order.line'].sudo().with_context(**contexto)
        if par and _entero(par.product_uom_qty) != 2 * pares:
            Linea.browse(par.id).write({'product_uom_qty': 2 * pares})
        if sola and _entero(sola.product_uom_qty) != 1:
            Linea.browse(sola.id).write({'product_uom_qty': 1})
        elif suelta and not sola:
            copia = {'order_id': self.id, 'product_uom_qty': 1, 'sequence': par.sequence,
                     'dcasa_fecha_precio': par.dcasa_fecha_precio}
            if 'shop_warning' in par._fields:
                copia['shop_warning'] = False
            nueva = Linea.browse(par.id).copy(copia)
            nueva._dcasa_reponer_precio()
            nueva._compute_discount()
        if sobran:
            Linea.browse([ln.id for ln in sobran]).unlink()
        return True

    # --- El aviso «agregaste…» del carrito ------------------------------------------------------------------

    def _dcasa_par_importe_agregado(self, linea, agregadas, con_itbms):
        """Lo que de verdad costaron las ``agregadas`` cajas que se acaban de poner en el carrito (con la promoción
        por pares, no es el precio de una línea por la cantidad: dos sueltas que se vuelven par bajan las dos).
        ``None`` si la línea no es de un producto con la promoción aplicando."""
        self.ensure_one()
        grupo = self.order_line.filtered(
            lambda ln: ln.product_id == linea.product_id and ln._dcasa_par_simple()
            and ln.product_no_variant_attribute_value_ids == linea.product_no_variant_attribute_value_ids)
        total = sum(_entero(ln.product_uom_qty) or 0 for ln in grupo)
        par = grupo.filtered(lambda ln: ln._dcasa_par_unitario() is not None)[:1]
        if not par or not agregadas or agregadas > total:
            return None
        tipo = 'total_included' if con_itbms else 'total_excluded'

        def neto(ln, precio):
            return ln.tax_ids.compute_all(precio, ln.currency_id, 1, ln.product_id, ln.order_partner_id)[tipo]

        mitad = neto(par, par.price_unit)
        # Una caja sin la promoción: la de la caja suelta si está; si no, lo que da la tarifa.
        sola = (grupo - par).filtered(lambda ln: _entero(ln.product_uom_qty) == 1)[:1]
        normal = neto(sola, sola.price_unit * (1 - (sola.discount or 0.0) / 100)) if sola \
            else neto(par, par._dcasa_con_impuestos(par._get_pricelist_price()))

        def cuesta(cajas):
            return (cajas // 2) * 2 * mitad + (cajas % 2) * normal

        return self.currency_id.round(cuesta(total) - cuesta(total - int(agregadas)))


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # --- Qué líneas van por pares --------------------------------------------------------------------------

    def _dcasa_par_simple(self):
        """Una línea de producto que puede ir por pares: no sección ni nota, no anticipo, no combo ni pieza de combo,
        no colgada de otra línea, sin atributos escritos por el cliente y en la unidad del producto."""
        self.ensure_one()
        producto = self.product_id
        return bool(producto and not self.display_type and not self.is_downpayment and producto.type != 'combo'
                    and not self.combo_item_id and not self.linked_line_id
                    and self.product_uom_id == producto.uom_id and not self.product_custom_attribute_value_ids)

    def _dcasa_par_a_mano(self):
        """¿Le pusieron el precio o el descuento a mano? (Odoo guarda en ``technical_price_unit`` el que puso el
        sistema; un descuento que no viene de la tarifa lo escribió una persona.)"""
        self.ensure_one()
        moneda = self.currency_id or self.order_id.currency_id or self.env.company.currency_id
        if moneda.compare_amounts(self.technical_price_unit, self.price_unit):
            return True
        return bool(self.discount) and not self.pricelist_item_id._show_discount()

    def _dcasa_par_se_puede_acomodar(self):
        """¿Entra esta línea en el acomodo por pares? Producto con precio por par, línea simple, un número entero de
        cajas, sin facturar ni entregar y al precio del sistema (lo puesto a mano no se reparte)."""
        self.ensure_one()
        return bool(self.product_id.dcasa_precio_par > 0 and self._dcasa_par_simple()
                    and self.product_uom_qty > 0 and _entero(self.product_uom_qty) is not None
                    and not self.qty_invoiced and not self.qty_delivered and not self._dcasa_par_a_mano())

    def _dcasa_par_en_moneda(self):
        """El precio por par del producto de esta línea, en la moneda de la venta y sin ITBMS."""
        self.ensure_one()
        compania = self.company_id or self.order_id.company_id or self.env.company
        moneda = self.currency_id or compania.currency_id
        fecha = (self.order_id and self.order_id.date_order) or fields.Datetime.now()
        return self.product_id._dcasa_par_en_moneda(moneda, compania, fecha)

    def _dcasa_par_unitario(self):
        """El precio de cada caja de esta línea por la promoción (la mitad del precio por par, en la moneda de la venta
        y sin ITBMS) o ``None``: el producto tiene precio por par, la línea es simple, lleva un número PAR de cajas y
        la tarifa no la deja igual o más barata (la promoción no se suma a otra rebaja)."""
        self.ensure_one()
        producto = self.product_id
        if not producto or producto.dcasa_precio_par <= 0 or not self.order_id or not self._dcasa_par_simple():
            return None
        cajas = _entero(self.product_uom_qty) if self.product_uom_qty > 0 else None
        if not cajas or cajas % 2:
            return None
        mitad = self._dcasa_par_en_moneda() / 2
        moneda = self.currency_id or self.order_id.currency_id
        if moneda.compare_amounts(mitad, self._get_pricelist_price()) >= 0:
            return None
        return mitad

    # --- Precio, descuento y tope ----------------------------------------------------------------------------

    def _get_display_price(self):
        precio = super()._get_display_price()
        mitad = self._dcasa_par_unitario()
        return mitad if mitad is not None and mitad < precio else precio

    def _compute_discount(self):
        super()._compute_discount()
        # Con la promoción no va también el descuento de la tarifa (nunca las dos rebajas).
        for linea in self:
            if linea.discount and linea.pricelist_item_id._show_discount() and linea._dcasa_par_unitario() is not None:
                linea.discount = 0.0

    def _dcasa_precio_autorizado(self):
        """El precio del par lo autorizó Gerencia: no cuenta como rebaja de la vendedora (sí lo que rebaje encima). Su
        tope se mide sobre el precio de la promoción."""
        autorizado = super()._dcasa_precio_autorizado()
        mitad = self._dcasa_par_unitario()
        if mitad is None:
            return autorizado
        return min(autorizado, self._dcasa_con_impuestos(mitad))

    # --- Acomodar al guardar ---------------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        if es_interno(self.env, SIN_ACOMODAR) or es_interno(self.env, SIN_RECALCULAR):
            return super().create(vals_list)
        ids = [vals.get('order_id') for vals in vals_list if isinstance(vals.get('order_id'), int)]
        if _sin_pares(self.env['sale.order'].browse(ids), _productos_de(self.env, vals_list)):
            return super().create(vals_list)
        antes = self.env['sale.order']._dcasa_exceso_previo_de(ids)
        lineas = super().create(vals_list)
        ordenes = lineas.order_id
        if ordenes._dcasa_pares_al_dia(protegidas=lineas):
            ordenes._dcasa_validar_tope_del_pedido(antes)
        return lineas

    def write(self, vals):
        if not CAMPOS_DE_PARES & set(vals) or es_interno(self.env, SIN_ACOMODAR) \
                or es_interno(self.env, SIN_RECALCULAR):
            return super().write(vals)
        ordenes = self.order_id
        if isinstance(vals.get('order_id'), int):
            ordenes |= ordenes.browse(vals['order_id'])
        if _sin_pares(ordenes, _productos_de(self.env, [vals])):
            return super().write(vals)
        antes = ordenes._dcasa_exceso_previo()
        resultado = super().write(vals)
        ordenes |= self.order_id
        if ordenes._dcasa_pares_al_dia(protegidas=self):
            ordenes._dcasa_validar_tope_del_pedido(antes)
        return resultado

    def unlink(self):
        if es_interno(self.env, SIN_ACOMODAR) or es_interno(self.env, SIN_RECALCULAR):
            return super().unlink()
        ordenes = self.order_id
        if _sin_pares(ordenes, self.env['product.product']):
            return super().unlink()
        antes = ordenes._dcasa_exceso_previo()
        resultado = super().unlink()
        ordenes = ordenes.exists()
        if ordenes._dcasa_pares_al_dia():
            ordenes._dcasa_validar_tope_del_pedido(antes)
        return resultado

    # --- Lo que se lee: carrito, papel, página del cliente y Juan --------------------------------------------

    def _dcasa_par_al_precio_del_sistema(self):
        """¿Va esta línea al precio del par que puso el sistema? (un precio puesto a mano no se rotula)."""
        self.ensure_one()
        mitad = self._dcasa_par_unitario()
        if mitad is None or self.discount:
            return False
        moneda = self.currency_id or self.order_id.currency_id
        return not moneda.compare_amounts(self.technical_price_unit, self.price_unit) \
            and not moneda.compare_amounts(self.price_unit, self._dcasa_con_impuestos(mitad))

    def _dcasa_par_etiqueta(self):
        """«Promoción: 2 cajas por $35.00» en la línea del par; «Caja suelta: precio normal» en la caja que sobra
        cuando en la misma venta va el par. Vacío en lo demás."""
        self.ensure_one()
        producto = self.product_id
        if not producto or producto.dcasa_precio_par <= 0 or self.display_type:
            return ''
        if self._dcasa_par_al_precio_del_sistema():
            orden = self.order_id
            compania = orden.company_id or self.env.company
            texto = producto._dcasa_par_texto(self.currency_id or orden.currency_id, compania,
                                               orden.date_order or fields.Datetime.now())
            return self.env._('Promoción: %s', texto)
        if _entero(self.product_uom_qty) == 1 and self._dcasa_par_simple() and any(
                ln != self and ln.product_id == producto and ln._dcasa_par_al_precio_del_sistema()
                for ln in self.order_id.order_line):
            return producto._dcasa_par_texto_suelta()
        return ''

    def _dcasa_etiqueta(self):
        return super()._dcasa_etiqueta() or self._dcasa_par_etiqueta()


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _dcasa_etiqueta(self):
        """En la factura, la misma etiqueta de su línea de venta, mientras siga siendo esa línea y a ese precio."""
        etiqueta = super()._dcasa_etiqueta()
        if etiqueta or self.display_type != 'product' or self.move_id.move_type != 'out_invoice':
            return etiqueta
        venta = self.sudo().sale_line_ids   # quien solo ve facturas también imprime la promoción
        if len(venta) != 1 or venta.product_id != self.product_id or venta.product_id.dcasa_precio_par <= 0 \
                or self.currency_id.compare_amounts(self.price_unit, venta.price_unit) \
                or float_compare(self.quantity, venta.product_uom_qty, precision_digits=6):
            return etiqueta
        return venta._dcasa_par_etiqueta()
