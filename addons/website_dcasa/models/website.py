import functools
import hashlib
import json
import math
import os
from urllib.parse import quote, urlsplit

from markupsafe import Markup

from odoo import api, fields, models
from odoo.addons.dcasa_socios.models import reglas as reglas_socios
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.http import request
from odoo.tools.json import scriptsafe as json_scriptsafe
from odoo.tools.misc import file_open, file_path

LOGO_DE_FABRICA = 'dcasa_base/static/img/logo.png'


@functools.cache
def _sha1_logo_de_fabrica():
    with file_open(LOGO_DE_FABRICA, 'rb') as archivo:
        return hashlib.sha1(archivo.read()).hexdigest()


# El nombre con que el sitio saluda en los mensajes de WhatsApp ya escritos (docs/BABY_CALEB.md, 2026-11-18).
MARCA = 'Baby Caleb'

# Baby Caleb vende 100% en línea, sin tienda física (decisión del dueño, 2026-11-18): en lugar de una dirección y un
# mapa, el sitio dice esta frase (la de su web, content.json › nap › address). La usan «Contacto» (/visitanos), el pie
# y la portada.
COBERTURA = 'Venta 100% online con entrega a domicilio — Ciudad de Panamá'

DEFAULT_WHATSAPP_MESSAGE = f'Hola {MARCA}, quiero información'

# Hosts que nunca deben salir en los datos estructurados: son de la máquina, no del sitio.
HOSTS_LOCALES = ('localhost', '0.0.0.0', '::1')

# Título y descripción de la portada para Google: los de la web de Baby Caleb (content.json › meta), tal cual
# (regla 4: no inventar).
SEO_PORTADA = {
    'website_meta_title': 'Baby Caleb Panamá | Pañales y Wipes Nateen hipoalergénicos',
    'website_meta_description': (
        'Pañales Nateen hipoalergénicos, sin cloro, sin perfumes. Tallas RN a XXL en caja para todo el mes. '
        'Venta online con delivery en Ciudad de Panamá.'),
}
# Valores que se pueden pisar: vacíos, los de ejemplo de Odoo y los que traía la copia de origen (D'CASA).
# Lo que la dueña escriba desde el editor (Sitio web > SEO) no se toca.
SEO_PORTADA_REEMPLAZABLES = {
    'website_meta_title': {'', "Mueblería en La Chorrera | D'CASA Panamá"},
    'website_meta_description': {
        '',
        'This is the homepage of the website',
        'Esta es la página principal del sitio web',
        'Esta es la página de inicio del sitio web',
        'Recámaras, colchones, zapateras, muebles de TV, estantes y escritorios con precios claros '
        'en La Chorrera. Entregas en Panamá Oeste, Panamá y Colón. Escríbenos por WhatsApp.',
        'Salas, recámaras, colchones y comedores con precios claros en La Chorrera. '
        'Entrega a todo Panamá y financiamiento. Escríbenos por WhatsApp.',
        'Recámaras, colchones, zapateras, muebles de TV, estantes y escritorios con precios claros '
        'en La Chorrera. Entrega a todo Panamá. Escríbenos por WhatsApp.',
    },
}

# Las dos listas de abajo solo las usan migraciones viejas (19.0.1.8.0, 19.0.1.13.0, 19.0.1.14.0) de las bases de la
# tienda de origen (D'CASA), con sus textos de ese entonces: en una instalación nueva no corren.
#
# Promesas sin respaldo que versiones anteriores publicaron (SW-03): si quedaron copiadas en
# una vista del sitio (bloque guardado desde el editor, copia por sitio), se reemplazan por el
# texto nuevo. Solo coincidencias exactas: lo que la dueña haya reescrito se respeta.
PROMESAS_RETIRADAS = [
    ('<span class="d-none d-md-inline"><i class="fa fa-credit-card me-2" aria-hidden="true"/>'
     'Financiamiento flexible</span>',
     '<span class="d-none d-md-inline"><i class="fa fa-map-marker me-2" aria-hidden="true"/>'
     'Tienda en La Chorrera</span>'),
    ('<li><i class="fa fa-credit-card" aria-hidden="true"/><span><strong>Financiamiento.</strong> '
     'Crédito flexible, te explicamos cómo.</span></li>',
     ''),
    ('<svg viewBox="0 0 32 32" aria-hidden="true"><rect x="3" y="7" width="26" height="18" rx="3"/>'
     '<path d="M3 13h26M8 20h6"/></svg>',
     '<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M16 29s-9-8.5-9-15a9 9 0 0 1 18 0c0 6.5-9 15-9 15z"/>'
     '<circle cx="16" cy="14" r="3.2"/></svg>'),
    ('<strong>Financiamiento</strong><span>Crédito flexible para que amueblar no te apriete.</span>',
     '<strong>Míralo en tienda</strong><span>Visítanos en La Chorrera y pruébalo antes de llevártelo.</span>'),
    ('Varias, y también financiamiento flexible. Escríbenos y te explicamos la que mejor te sirve.',
     'Transferencia bancaria, Yappy, o pagas al recibir o en la tienda. Escríbenos y te explicamos '
     'la que mejor te sirve.'),
    ('Pagas al recibir o en la tienda: efectivo, Yappy o tarjeta.',
     'Pagas al recibir o en la tienda: efectivo o Yappy.'),
]

# Textos de la portada que ya no son ciertos (decisión de la dueña, 2026-10-17: no hay pago contra entrega y las
# entregas son por zona). Se corrigen en las copias por sitio; solo coincidencias exactas.
TEXTOS_CORREGIDOS = [
    ('Transferencia bancaria, Yappy, o pagas al recibir o en la tienda. Escríbenos y te explicamos '
     'la que mejor te sirve.',
     'Transferencia bancaria, Yappy o en la tienda (efectivo o Yappy). El mueble se entrega cuando está '
     'pagado completo. Escríbenos y te explicamos la que mejor te sirve.'),
    ('Sí, llegamos a todo el país. Cuéntanos tu zona por WhatsApp y te decimos costo y fecha de entrega.',
     'Hacemos entregas en La Chorrera, Arraiján, Capira, Panamá y Colón; al interior todavía no. El costo y la '
     'fecha dependen de tu zona: te los confirma una vendedora por WhatsApp.'),
    # Al interior todavía no se entrega (decisión de la dueña, 2026-10-17): la portada, la barra de arriba y el pie.
    ('¿Hacen entregas a todo Panamá?', '¿A dónde hacen entregas?'),
    ('Entrega a todo Panamá', 'Entregas en Panamá Oeste, Panamá y Colón'),
]

# Categorías de la tienda de la copia de origen (xmlid, nombre). Con la marca de Baby Caleb (2026-11-19) la portada ya
# no las enseña («Compra por espacio» y sus fotos de muebles se quitaron): solo las ofrece la búsqueda sin resultados, y
# solo las que tienen algo publicado (``_dcasa_categorias``, models/buscador.py).
CATEGORIAS_PORTADA = [
    ('salas', 'Salas'),
    ('recamaras', 'Recámaras'),
    ('colchones', 'Colchones'),
    ('zapateras', 'Zapateras'),
    ('organizacion', 'Estantes'),
    ('oficina', 'Oficina'),
]

# Menú principal: tres opciones. Las categorías viven dentro del catálogo (/shop). Baby Caleb no tiene tienda que
# visitar: /visitanos es su página de contacto (cobertura, horario y canales).
# El menú de babycaleb.com (src/blocks/S01Nav.tsx), en el mismo orden (pedido del dueño, 2026-11-24: «tal cual»).
# «Productos» es la tienda de Odoo. Socios, Mi cuenta y Contacto siguen en el pie y en el menú del celular.
MENU_PRINCIPAL = [
    ('Productos', '/shop'),
    ('Beneficios', '/beneficios'),
    ('Historia', '/historia'),
    ('Tips', '/tips'),
    ('Cómo comprar', '/como-comprar'),
    ('FAQ', '/faq'),
]

# Las preguntas frecuentes de babycaleb.com (content.json › faq), en su orden. Dos respuestas dicen lo que este
# sistema hace y su web no: la de la tienda física (se paga con Yappy o por transferencia al pedir) y la del delivery
# (el costo se confirma por WhatsApp; allá se elige la zona al pagar). Las usan /faq y su FAQPage para Google.
PREGUNTAS_FRECUENTES = [
    ('¿Cómo sé qué talla necesita mi bebé?',
     'Las tallas van por peso: RN (4-11 lb), S (6-13 lb), M (8-19 lb), L (15-39 lb), XL (26-55 lb) '
     'y XXL (más de 55 lb). '
     'Para prematuros y recién nacidos es la talla RN. En pants: L (19-31 lb), XL (26-37.5 lb) y XXL (más de 33 lb). '
     'Si dudas, escríbenos por WhatsApp y te asesoramos.'),
    ('¿Tienen talla XXL?',
     'Sí. Manejamos la talla XXL para niños de más de 55 libras, una talla que casi no se consigue en Panamá. '
     'Caja de 112 unidades.'),
    ('¿Por qué venden en caja y no por paquete?',
     'Porque la caja te alcanza para todo el mes y el costo por pañal te sale más accesible que comprando paquete por '
     'paquete. Solo vendemos cajas completas, así que antes de pedir te ayudamos por WhatsApp a elegir bien la talla '
     'según el peso de tu bebé.'),
    ('¿Cuál es la diferencia entre hipoalergénico y sin cloro?',
     'Hipoalergénico significa que tiene bajo riesgo de causar alergias. Sin cloro significa que no se usaron '
     'compuestos de cloro para blanquear la pulpa del pañal. Nuestros pañales Nateen son las dos cosas: '
     'hipoalergénicos y sin cloro ni perfumes.'),
    ('¿Los wipes tienen alcohol o parabenos?',
     'No. Nuestros wipes son hipoalergénicos, sin alcohol, sin parabenos y sin perfumes. Los wipes de agua Dany Baby '
     'son 99% agua pura, ideales para recién nacidos.'),
    ('¿Tienen tienda física?',
     'Hoy vendemos únicamente online: haces tu pedido aquí mismo en la página, pagas con Yappy o por transferencia '
     'y te lo entregamos por delivery en Ciudad de Panamá.'),
    ('¿Cuánto cuesta el delivery?',
     'Depende de tu zona. Te confirmamos el costo del envío por WhatsApp antes de cobrarte.'),
    ('¿Los pañales son biodegradables?',
     'Sí — Nateen fabrica sus pañales con 100% fibras de bambú, biodegradables, transpirables y sin cloro ni '
     'perfumes.'),
]

# El pañal de la tarjetita que flota sobre la foto del hero (S02Hero.tsx): los Nateen de cierre, de RN a XXL. Los
# Pants (NAT-P-…) quedan fuera, como en su web.
CODIGOS_TARJETA_HERO = ('NAT-%', 'NAT-P-%')


def _es_menu_viejo(url):
    """Menús que el menú corto reemplaza: los de Odoo por defecto y los de una categoría."""
    url = url or ''
    return (url in ('/', '/shop', '/contactus', '/socios', '/#visitanos', '/visitanos')
            or url.startswith('/shop/category/'))


_RESENAS = {'mtime': None, 'datos': None}


def _leer_resenas():
    """data/resenas.json, leído una vez y releído solo si el archivo cambia."""
    ruta = file_path('website_dcasa/data/resenas.json')
    mtime = os.path.getmtime(ruta)
    if _RESENAS['mtime'] != mtime:
        with open(ruta, encoding='utf-8') as archivo:
            _RESENAS['datos'] = json.load(archivo)
        _RESENAS['mtime'] = mtime
    return _RESENAS['datos']


class Website(models.Model):
    _inherit = 'website'

    dcasa_whatsapp_number = fields.Char(
        string='WhatsApp de ventas',
        help='Número con código de país, p. ej. +507 6757-5065. Lo usan los botones de WhatsApp del sitio. '
             'Si está vacío se usa el teléfono de la empresa.',
    )

    # ------------------------------------------------------------------
    # WhatsApp
    # ------------------------------------------------------------------

    @api.constrains('dcasa_whatsapp_number')
    def _check_dcasa_whatsapp_number(self):
        """Un número inválido borraría en silencio todos los botones de WhatsApp del sitio."""
        for website in self.filtered('dcasa_whatsapp_number'):
            digitos = reglas_socios.solo_digitos(website.dcasa_whatsapp_number)
            if not (len(digitos) == 8 or 10 <= len(digitos) <= 15):
                raise ValidationError(self.env._(
                    'El WhatsApp de ventas debe ser un número, como +507 6757-5065 o 6757-5065.'))

    def _dcasa_whatsapp_url(self, message=None):
        """Link wa.me con mensaje precargado; '/contactus' si no hay número."""
        self.ensure_one()
        digits = reglas_socios.solo_digitos(self.dcasa_whatsapp_number or self.company_id.phone)
        if not digits:
            return '/contactus'
        if len(digits) == 8:  # número de Panamá sin el código de país
            digits = f'507{digits}'
        return f'https://wa.me/{digits}?text={quote(message or DEFAULT_WHATSAPP_MESSAGE)}'

    def _dcasa_logo_de_fabrica(self):
        """¿El logo del sitio sigue siendo el de fábrica que trae el módulo (dcasa_base)?

        Entonces la cabecera usa su copia en WebP (3-7 KB, static/src/img/logo-*.webp) en lugar del
        PNG de 56 KB que pedía cada página con prioridad alta, compitiendo con la foto LCP. Si la
        dueña cambia el logo desde el editor, se muestra el suyo como siempre.
        """
        self.ensure_one()
        adjunto = self.env['ir.attachment'].sudo().search_read(
            [('res_model', '=', 'website'), ('res_field', '=', 'logo'), ('res_id', '=', self.id)],
            ['checksum'], limit=1)
        return bool(adjunto) and adjunto[0]['checksum'] == _sha1_logo_de_fabrica()

    def _dcasa_whatsapp_producto(self, product):
        """Mensaje de WhatsApp con el nombre del mueble y su código público ya escritos (nunca la referencia del
        proveedor: la vendedora busca ese código en Productos y encuentra el mueble)."""
        texto = f'Hola {MARCA}, me interesa: {product._dcasa_nombre_cliente()}'
        codigo = product.dcasa_codigo_publico
        return self._dcasa_whatsapp_url(f'{texto} (código {codigo})' if codigo else texto)

    def _dcasa_mas_itbms(self, producto):
        """¿Va «+ ITBMS» junto al precio? Sí, si la tienda muestra el precio sin impuesto y el
        producto lleva ITBMS: los precios de D'CASA son sin ITBMS y el 7 % se suma en el carrito."""
        self.ensure_one()
        return bool(
            self.show_line_subtotals_tax_selection == 'tax_excluded'
            # sudo: el visitante no lee impuestos; solo se pregunta si el producto lleva alguno.
            and producto.sudo().taxes_id._filter_taxes_by_company(self.company_id)
        )

    # ------------------------------------------------------------------
    # Menú
    # ------------------------------------------------------------------

    @api.model
    def _dcasa_armar_menu_principal(self):
        """Deja el menú de cada sitio en Catálogo · Socios Baby Caleb · Contacto.

        Solo quita los menús que reemplaza (Inicio, Tienda, Contáctanos, uno por categoría) y
        no duplica: se puede volver a correr sin perder lo que la dueña agregó desde el editor.
        """
        Menu = self.env['website.menu']
        idiomas = [codigo for codigo, _nombre in self.env['res.lang'].get_installed()]
        nuestros = {url for _nombre, url in MENU_PRINCIPAL}
        for website in self.search([]):
            raiz = website.menu_id
            if not raiz:
                continue
            raiz.child_id.filtered(lambda m: _es_menu_viejo(m.url) and m.url not in nuestros).unlink()
            for orden, (nombre, url) in enumerate(MENU_PRINCIPAL, start=1):
                valores = {'name': nombre, 'sequence': orden * 10}
                menu = raiz.child_id.filtered(lambda m, url=url: m.url == url)[:1]
                if menu:
                    menu.write(valores)  # p. ej. «Shop» de Odoo pasa a «Catálogo»
                else:
                    menu = Menu.create(dict(valores, url=url, parent_id=raiz.id, website_id=website.id))
                # El nombre es traducible: el mismo en todos los idiomas (si no, en español
                # seguiría la traducción de Odoo, «Tienda»).
                menu.update_field_translations('name', dict.fromkeys(idiomas, nombre))

    # ------------------------------------------------------------------
    # Portada
    # ------------------------------------------------------------------

    def _dcasa_categoria(self, clave):
        return self.env.ref(f'website_dcasa.public_category_{clave}', raise_if_not_found=False)

    def _dcasa_categoria_url(self, clave):
        """URL canónica (con slug) de una categoría de la tienda; '/shop' si ya no existe.

        En sudo: el visitante no puede leer una categoría aún sin productos, y el enlace igual sirve.
        """
        categoria = self._dcasa_categoria(clave)
        return f"/shop/category/{self.env['ir.http']._slug(categoria.sudo())}" if categoria else '/shop'

    def _dcasa_categoria_tiene_productos(self, clave):
        """¿Hay algo publicado y a la venta en esta categoría (o sus hijas) para este sitio?"""
        return bool(self._dcasa_categoria_cantidad(clave, limit=1))

    def _dcasa_categoria_cantidad(self, clave, limit=None):
        """Cuántos productos publicados y a la venta hay en esta categoría (o sus hijas) para este sitio: el número
        que la portada pone debajo de cada categoría (dato real del catálogo, nunca escrito a mano)."""
        categoria = self._dcasa_categoria(clave)
        if not categoria:
            return 0
        dominio = Domain.AND([self._dcasa_dominio_publicado(), [('public_categ_ids', 'child_of', categoria.sudo().id)]])
        return self.env['product.template'].sudo().search_count(dominio, limit=limit)

    def _dcasa_categorias(self):
        """Las categorías de la tienda con su URL real y cuántos productos publicados tienen.

        Una categoría sin nada publicado no lleva a una página vacía o de error: abre WhatsApp con el mensaje listo.
        Cuando se publique algo, vuelve sola a su página de la tienda (pedido de la dueña, 2026-11-09)."""
        self.ensure_one()
        tarjetas = []
        for clave, nombre in CATEGORIAS_PORTADA:
            cantidad = self._dcasa_categoria_cantidad(clave)
            con_productos = bool(cantidad)
            tarjetas.append({
                'clave': clave,
                'nombre': nombre,
                'cantidad': cantidad,
                'url': self._dcasa_categoria_url(clave) if con_productos else self._dcasa_whatsapp_url(
                    f'Hola {MARCA}, quiero información de {nombre.lower()}'),
                'whatsapp': not con_productos,
            })
        return tarjetas

    def _dcasa_dominio_publicado(self):
        """Lo que un visitante puede comprar: se vende en este sitio y está publicado.

        Lo usan los carruseles y el «Agregar» de un clic: los dos tienen que coincidir.
        """
        return Domain.AND([self.sale_product_domain(), [('is_published', '=', True)]])

    def _dcasa_productos(self, limit=8, categorias=None):
        """Productos publicados para los carruseles de la portada, con el mismo precio que la tienda.

        :param categorias: claves de categoría pública (p. ej. ``['colchones', 'recamaras']``).
        """
        self.ensure_one()
        dominio = self._dcasa_dominio_publicado()
        if categorias:
            ids = [c.id for clave in categorias if (c := self._dcasa_categoria(clave))]
            dominio = Domain.AND([dominio, [('public_categ_ids', 'child_of', ids)]])
        productos = self.env['product.template'].search(dominio, limit=limit, order='website_sequence asc, id desc')
        # El precio y la moneda de la tarifa del visitante necesitan la petición web; sin ella, los de lista.
        con_tarifa = bool(productos) and bool(request) and hasattr(request, 'pricelist')
        precios = productos._get_sales_prices(self) if con_tarifa else {}
        moneda = (request.pricelist.currency_id if con_tarifa else None) or self.currency_id
        # Sin petición no hay visitante ni carrito: nada se compra en un clic.
        acceso = con_tarifa and self.has_ecommerce_access()
        items = []
        for p in productos:
            precio = precios.get(p.id, {}).get('price_reduce', p.list_price)
            items.append({
                'producto': p,
                'precio': precio,
                'moneda': moneda,
                'directo': acceso and self._dcasa_compra_directa(p, precio),
            })
        return items

    def _dcasa_preguntas(self):
        """[(pregunta, respuesta)] de /faq (PREGUNTAS_FRECUENTES)."""
        return PREGUNTAS_FRECUENTES

    def _dcasa_faq_json_ld(self):
        """Las mismas preguntas como FAQPage para Google (src/pages/FAQ.tsx), en JSON seguro dentro de <script>."""
        return json_scriptsafe.dumps({
            '@context': 'https://schema.org',
            '@type': 'FAQPage',
            'mainEntity': [
                {'@type': 'Question', 'name': pregunta, 'acceptedAnswer': {'@type': 'Answer', 'text': respuesta}}
                for pregunta, respuesta in PREGUNTAS_FRECUENTES
            ],
        }, ensure_ascii=False)

    def _dcasa_hero_tarjeta(self):
        """La tarjetita que flota sobre la foto del hero de babycaleb.com: «Desde talla RN · Pañal Nateen · Desde $…».

        El precio es el menor de los pañales Nateen de cierre publicados y a la venta, leído de Odoo como el de la
        tienda (nunca escrito a mano: CLAUDE.md, «un dato, un solo dueño»). Sin ninguno publicado, la tarjeta no sale.
        """
        self.ensure_one()
        si, no = CODIGOS_TARJETA_HERO
        # En sudo: el visitante anónimo no lee el código interno de la variante. Solo se expone lo publicado (el precio
        # y la ficha que ya ve cualquiera en la tienda).
        publicados = self.env['product.template'].sudo().search(self._dcasa_dominio_publicado())
        variantes = self.env['product.product'].sudo().search(Domain.AND([
            [('default_code', '=like', si), ('default_code', 'not like', no)],
            [('product_tmpl_id', 'in', publicados.ids)],
        ]))
        if not variantes:
            return False
        plantilla = variantes[:1].product_tmpl_id
        con_tarifa = bool(request) and hasattr(request, 'pricelist')
        if con_tarifa:
            precios = [v._get_combination_info_variant()['price'] for v in variantes]
            moneda = request.pricelist.currency_id or self.currency_id
        else:
            precios = variantes.mapped('lst_price')
            moneda = self.currency_id
        return {'desde': min(precios), 'moneda': moneda, 'url': plantilla.website_url}

    def _dcasa_compra_directa(self, producto, precio=None):
        """¿Se puede agregar al carrito sin pasar por la ficha?

        No, si hay que elegir algo (variantes, atributos configurables, combos, opcionales) o si
        la tienda no deja comprarlo así (precio cero bloqueado). Son las reglas del botón de Odoo.
        Los carruseles pasan el ``precio`` ya calculado para no volver a pasar por la tarifa
        producto por producto; sin precio, esa regla la revisa quien llama.
        """
        return bool(
            producto.product_variant_count == 1
            and not producto.has_configurable_attributes
            and producto.type != 'combo'
            and not producto.optional_product_ids
            and (precio is None or precio or not self.prevent_zero_price_sale)
        )

    def _dcasa_resenas(self):
        """Opiniones reales de la ficha de Google (copia literal en data/resenas.json).

        La cinta necesita repetir la lista para cerrar el bucle sin salto: ``copias`` dice
        cuántas veces se imprime (par, y cada mitad con al menos 8 tarjetas para cubrir
        pantallas anchas). Solo la primera copia la leen los lectores de pantalla.
        Un archivo incompleto no tumba la portada: la sección simplemente no sale.
        """
        try:
            datos = _leer_resenas()
        except (OSError, ValueError):
            return {'opiniones': []}
        opiniones = [
            o for o in datos.get('opiniones', [])
            if (o.get('texto') or '').strip() and o.get('autor') and o.get('estrellas')
        ]
        if not opiniones or not datos.get('ficha'):
            return {'opiniones': []}
        copias = 2 * math.ceil(8 / len(opiniones)) if len(opiniones) >= 3 else 1
        return {
            'ficha': datos['ficha'],
            'puntuacion': datos.get('puntuacion'),
            'total': datos.get('total'),
            'opiniones': opiniones,
            'copias': copias,
            'duracion': f'{max(30, round(len(opiniones) * copias * 5.5))}s',
        }

    def _dcasa_reglas_socios(self):
        """Cifras del programa de socios, leídas de puntos.json (nunca escritas a mano)."""
        return reglas_socios.cargar_reglas()

    def _dcasa_socios_con_cifras(self):
        """¿El programa de Socios ya tiene sus cifras (puntos por dólar, o los del referido)? Solo entonces la portada
        enseña su banda: con todo en PENDIENTE (Baby Caleb, 2026-11-18) prometería puntos que nadie gana. La portada de
        babycaleb.com no la tiene; vuelve sola el día que el dueño ponga sus cifras en puntos.json."""
        reglas = self._dcasa_reglas_socios()
        referido = reglas.get('referido') or {}
        return bool((reglas.get('acumulacion') or {}).get('puntosPorDolar')
                    or (referido.get('puntosAlPadrino') and referido.get('puntosAlAhijado')))

    # ------------------------------------------------------------------
    # SEO
    # ------------------------------------------------------------------

    def _dcasa_url_publica(self):
        """URL pública del sitio para los datos estructurados; '' si solo hay una local.

        Sale de ``website.domain`` o, si está vacío, del parámetro ``web.base.url``
        (``get_base_url``). En el despliegue hay que fijar ``web.base.url`` con el dominio
        real (https://…) y ``web.base.url.freeze = True``: sin el «freeze», Odoo lo reescribe
        con la URL desde la que entra el administrador. Si aun así quedara una URL local
        (localhost, 127.x…), los JSON-LD salen sin URLs absolutas antes que mandarle a Google
        una dirección de la máquina.
        """
        self.ensure_one()
        base = (self.get_base_url() or '').rstrip('/')
        host = (urlsplit(base).hostname or '').lower()
        if not host or host in HOSTS_LOCALES or host.startswith('127.') or host.endswith('.localhost'):
            return ''
        return base

    def _dcasa_json_ld_organizacion(self, company=None):
        """JSON-LD ``Organization`` de todas las páginas (reemplaza el de website_sale).

        El de Odoo arma el JSON a mano con ``t-out``, que escapa para HTML: «D'CASA» salía como
        ``D&#39;CASA`` dentro del JSON y Google lee el texto literal. Aquí va como JSON seguro
        para <script> (json_scriptsafe), y la URL nunca es la de una máquina local.
        """
        self.ensure_one()
        company = company or self.company_id
        base = self._dcasa_url_publica()
        datos = {
            '@context': 'https://schema.org',
            '@type': 'Organization',
            'name': company.name,
        }
        if base:
            datos['url'] = base
            datos['logo'] = self._dcasa_logo_publico(base)
        return json_scriptsafe.dumps(datos, ensure_ascii=False)

    def _dcasa_logo_publico(self, base):
        """El logo para Google, uno solo en todos los datos estructurados: el del sitio (el de la cabecera), en una
        dirección estable. Antes la portada decía dos distintos (``/logo.png?company=1`` y
        ``/web/image/website/1/logo?unique=…``, que cambiaba con cada cambio del sitio)."""
        self.ensure_one()
        return f'{base}/web/image/website/{self.id}/logo' if base else ''

    def _dcasa_json_ld(self):
        """Datos estructurados OnlineStore para Google: Baby Caleb vende en línea, sin tienda física (decisión del
        dueño, 2026-11-18). Sin coordenadas ni mapa: no hay local que ubicar. La dirección, solo con lo que la empresa
        tenga escrito (hoy, el país).

        JSON seguro dentro de <script> (escapa <, >, & y U+2028/9) con el helper de Odoo. El logo es el mismo que el de
        ``Organization`` (``_dcasa_logo_publico``).
        """
        self.ensure_one()
        company = self.company_id
        base = self._dcasa_url_publica()  # '' si solo hay una URL local: sin URLs absolutas
        datos = {
            '@context': 'https://schema.org',
            '@type': 'OnlineStore',
            '@id': base and f'{base}/#tienda',
            'name': company.name,
            'url': base,
            'logo': self._dcasa_logo_publico(base),
            'telephone': company.phone,
            'email': company.email,
            'currenciesAccepted': company.currency_id.name,
            'address': {
                '@type': 'PostalAddress',
                'streetAddress': ', '.join(filter(None, [company.street, company.street2])),
                'addressLocality': company.city,
                'addressRegion': company.state_id.name,
                'addressCountry': company.country_id.code or 'PA',
            },
            'sameAs': [url for url in (self.social_instagram, self.social_tiktok, self.social_facebook) if url],
        }
        # Sin campos vacíos (Google los marca como error). Nada de cifras inventadas (rango de precios).
        datos = {k: v for k, v in datos.items() if v}
        datos['address'] = {k: v for k, v in datos['address'].items() if v}
        return json_scriptsafe.dumps(datos, ensure_ascii=False)

    @api.model
    def _dcasa_seo_portada(self):
        """Título y descripción de la portada en todos los idiomas y en todas sus copias.

        Odoo crea una copia de la portada por sitio (``_bootstrap_homepage``) con su descripción
        de ejemplo, y la carga de traducciones pone la suya en español: un registro de datos sobre
        ``website.homepage_page`` no llegaba a lo que ve Google. Se corre en cada actualización y
        solo pisa valores vacíos, de ejemplo o anteriores de D'CASA.
        """
        idiomas = list(dict.fromkeys(['en_US', *(c for c, _n in self.env['res.lang'].get_installed())]))
        paginas = self.env['website.page'].sudo().with_context(active_test=False).search([('url', '=', '/')])
        for pagina in paginas:
            for idioma in idiomas:
                en_idioma = pagina.with_context(lang=idioma)
                valores = {
                    campo: valor for campo, valor in SEO_PORTADA.items()
                    if (en_idioma[campo] or '').strip() in SEO_PORTADA_REEMPLAZABLES[campo]
                    and en_idioma[campo] != valor
                }
                if valores:
                    en_idioma.write(valores)

    @api.model
    def _dcasa_retirar_promesas(self):
        """Quita las promesas sin respaldo (SW-03) de lo que quedó copiado fuera de las plantillas.

        Vistas por sitio (copias y bloques guardados desde el editor) y el mensaje del pago al
        recibir. Las plantillas del módulo ya traen el texto nuevo. Devuelve cuántos registros
        cambió.
        """
        idiomas = list(dict.fromkeys(['en_US', *(c for c, _n in self.env['res.lang'].get_installed())]))
        # Todas las promesas viejas de las vistas dicen «financiamiento»; se busca en todos los
        # idiomas a la vez (el texto traducido vive en el jsonb de arch_db).
        self.env['ir.ui.view'].flush_model(['arch_db', 'website_id', 'type'])
        self.env.cr.execute("""
            SELECT id FROM ir_ui_view
             WHERE website_id IS NOT NULL AND type = 'qweb' AND arch_db::text ILIKE '%%financiamiento%%'
        """)
        View = self.env['ir.ui.view'].sudo().with_context(active_test=False, no_cow=True)
        registros = [(vista, 'arch_db') for vista in View.browse(r[0] for r in self.env.cr.fetchall())]
        cod = self.env.ref('delivery.payment_provider_cod', raise_if_not_found=False)
        if cod:
            registros.append((cod.sudo(), 'pending_msg'))
        cambiados = 0
        for registro, campo in registros:
            tocado = False
            for idioma in idiomas:
                texto = registro.with_context(lang=idioma)[campo] or ''
                nuevo = str(texto)
                for viejo, reemplazo in PROMESAS_RETIRADAS:
                    nuevo = nuevo.replace(viejo, reemplazo)
                if nuevo != str(texto):
                    registro.with_context(lang=idioma).write(
                        {campo: Markup(nuevo) if isinstance(texto, Markup) else nuevo})
                    tocado = True
            cambiados += tocado
        return cambiados

    @api.model
    def _dcasa_corregir_textos(self):
        """Corrige TEXTOS_CORREGIDOS en las copias por sitio de la portada (todas las lenguas). Devuelve cuántas
        vistas cambió; se puede volver a correr."""
        idiomas = list(dict.fromkeys(['en_US', *(c for c, _n in self.env['res.lang'].get_installed())]))
        self.env['ir.ui.view'].flush_model(['arch_db', 'website_id', 'type'])
        condiciones = ' OR '.join(['arch_db::text ILIKE %s'] * len(TEXTOS_CORREGIDOS))
        self.env.cr.execute(
            f"SELECT id FROM ir_ui_view WHERE website_id IS NOT NULL AND type = 'qweb' AND ({condiciones})",
            [f'%{viejo[:60]}%' for viejo, _nuevo in TEXTOS_CORREGIDOS])
        View = self.env['ir.ui.view'].sudo().with_context(active_test=False, no_cow=True)
        cambiadas = 0
        for vista in View.browse(r[0] for r in self.env.cr.fetchall()):
            tocada = False
            for idioma in idiomas:
                texto = vista.with_context(lang=idioma).arch_db or ''
                nuevo = texto
                for viejo, reemplazo in TEXTOS_CORREGIDOS:
                    nuevo = nuevo.replace(viejo, reemplazo)
                if nuevo != texto:
                    vista.with_context(lang=idioma).write({'arch_db': nuevo})
                    tocada = True
            cambiadas += tocada
        return cambiadas
