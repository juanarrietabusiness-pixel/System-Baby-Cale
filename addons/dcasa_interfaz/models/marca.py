"""La marca del panel por empresa: logo, ícono y colores (Ajustes › Marca del panel).

Pedido del dueño (2026-11-18): «como esto es un template que se va a seguir copiando para otras empresas, en Ajustes
cada empresa tiene que poder cargar su logo y customizar su interfaz con los colores de la empresa». La página web
pública NO cambia: la programa el equipo, no el usuario.

* **Campos propios** (no ``res.company.logo`` ni ``primary_color``/``secondary_color``): esos son de los documentos
  (factura, cotización, correos) y del sitio, y se imprimen sobre papel blanco; los del panel tienen reglas de lectura
  propias (el principal es la letra sobre el crema, el acento es el relleno con la letra del principal encima). Así
  cambiar uno no cambia el otro.
* **De fábrica = la marca de Baby Caleb** (2026-11-19): crema, navy (principal ``#1B3246``) y naranja (acento
  ``#EE924A``), ya compilados en la hoja de Odoo. Sin logo ni ícono, y con los colores de fábrica, la página del panel
  enlaza la hoja de Odoo tal cual y los íconos de siempre.
* **En caliente.** Los colores no recompilan nada: la página enlaza la hoja compilada pintada con los colores de la
  empresa (``controllers/marca.py`` y ``marca/tinte.py``). Al guardar, el panel se recarga y ya se ve.
* **Lo que se guarda se valida aquí** (y lo mismo dicen Ajustes y Brian): el principal es la letra de títulos y enlaces
  sobre el crema, así que pide 4.5:1 con la superficie crema (#F2EFE5); el acento es el relleno del botón principal y
  lleva encima la letra en el principal, así que pide 4.5:1 con él. Si no llega, se dice por qué y qué color sí sirve.
* Quién: los administradores (Ajustes), como los datos de la empresa (Ajustes › Empresas).
"""
import base64
import binascii
import logging
import secrets

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.http import request

from ..marca import colores as C
from ..marca import iconos as I
from ..marca.tinte import Tinte

LOGO_DE_FABRICA = '/dcasa_base/static/img/logo.png'
CARPETA_DE_FABRICA = '/dcasa_base/static/img/icono'
ICONOS_DE_FABRICA = {
    'icono-192.png': f'{CARPETA_DE_FABRICA}/logo-192.png',
    'icono-512.png': f'{CARPETA_DE_FABRICA}/logo-512.png',
    'icono-maskable-192.png': f'{CARPETA_DE_FABRICA}/logo-maskable-192.png',
    'icono-maskable-512.png': f'{CARPETA_DE_FABRICA}/logo-maskable-512.png',
    'apple-touch-icon.png': f'{CARPETA_DE_FABRICA}/apple-touch-icon.png',
}
# Las del manifiesto de la app instalable: (nombre, tamaño, uso).
ICONOS_DEL_MANIFIESTO = (
    ('icono-192.png', '192x192', 'any'),
    ('icono-512.png', '512x512', 'any'),
    ('icono-maskable-192.png', '192x192', 'maskable'),
    ('icono-maskable-512.png', '512x512', 'maskable'),
)
CAMPOS_DE_LA_MARCA = ('dcasa_panel_logo', 'dcasa_panel_icono', 'dcasa_panel_color_principal',
                      'dcasa_panel_color_acento')
COLORES = (('dcasa_panel_color_principal', C.FABRICA_PRINCIPAL), ('dcasa_panel_color_acento', C.FABRICA_ACENTO))
GRUPO = 'base.group_system'
_logger = logging.getLogger(__name__)
SOLO_IMAGENES = ('{que} del panel tiene que ser una imagen PNG, JPG o WebP. Un SVG no sirve: con él no se pueden hacer '
                 'los tamaños del ícono del celular. Si lo tienes en SVG, expórtalo como PNG con fondo transparente.')


def _bytes(valor):
    """El valor de un campo de imagen (base64 en texto o en bytes) como bytes de la imagen; vacío → b''."""
    if not valor:
        return b''
    try:
        return base64.b64decode(valor)
    except (binascii.Error, ValueError, TypeError):
        return b''


class ResCompany(models.Model):
    _inherit = 'res.company'

    dcasa_panel_logo = fields.Image(
        'Logo del panel', max_width=1024, max_height=1024,
        help='Se ve arriba en la barra de la izquierda y en el menú del celular. Si no subes uno, se ve el de fábrica. '
             'No cambia el logo de las facturas ni el de la página web.')
    dcasa_panel_icono = fields.Image(
        'Ícono del panel', max_width=1024, max_height=1024,
        help='El de la pestaña del navegador y el de la app cuando la guardan en la pantalla de inicio del celular. '
             'Mejor cuadrado. Si no lo subes, sale del logo del panel.')
    dcasa_panel_color_principal = fields.Char(
        'Color principal del panel', default=C.FABRICA_PRINCIPAL,
        help='La tinta de tu marca: la letra, los títulos, los enlaces, los íconos y lo activo de la barra de la '
             'izquierda. Tiene que ser oscuro: va como letra sobre el crema del panel.')
    dcasa_panel_color_acento = fields.Char(
        'Color de acento del panel', default=C.FABRICA_ACENTO,
        help='El relleno de tu marca: el botón principal, lo elegido, las barras y los puntos. Tiene que ser claro y '
             'vivo: lleva encima la letra en el color principal y nunca se usa como letra.')
    dcasa_panel_version = fields.Char(
        'Versión de la marca del panel', readonly=True, copy=False,
        help='Cambia cada vez que cambia la marca del panel: así los navegadores piden la hoja y los íconos nuevos.')

    # --- Guardar --------------------------------------------------------------------------------------------------

    @api.model
    def _dcasa_panel_normalizar(self, vals):
        """Los colores como #RRGGBB (vacío = el de fábrica); un color mal escrito se dice en palabras sencillas."""
        vals = dict(vals)
        for campo, fabrica in COLORES:
            if campo in vals:
                try:
                    vals[campo] = C.normalizar(vals[campo]) or fabrica
                except ValueError as error:
                    raise ValidationError(str(error)) from None
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        return super().create([self._dcasa_panel_normalizar(vals) for vals in vals_list])

    def write(self, vals):
        vals = self._dcasa_panel_normalizar(vals)
        if any(campo in vals for campo in CAMPOS_DE_LA_MARCA) and self._dcasa_panel_cambia(vals):
            vals['dcasa_panel_version'] = secrets.token_hex(4)
        return super().write(vals)

    def _dcasa_panel_cambia(self, vals):
        """¿Cambia de verdad la marca de alguna? Ajustes reescribe todos sus campos al guardar: sin esto, cualquier
        «Guardar» haría que todos los navegadores volvieran a bajar la hoja del panel."""
        for empresa in self.with_context(bin_size=False):
            for campo in CAMPOS_DE_LA_MARCA:
                if campo not in vals:
                    continue
                if campo in ('dcasa_panel_logo', 'dcasa_panel_icono'):
                    if _bytes(empresa[campo]) != _bytes(vals[campo]):
                        return True
                elif (empresa[campo] or '') != (vals[campo] or ''):
                    return True
        return False

    @api.constrains('dcasa_panel_color_principal', 'dcasa_panel_color_acento')
    def _check_dcasa_panel_colores(self):
        for empresa in self:
            problema = (C.problema_del_principal(empresa.dcasa_panel_color_principal)
                        or C.problema_del_acento(empresa.dcasa_panel_color_acento,
                                                 empresa.dcasa_panel_color_principal))
            if problema:
                raise ValidationError(problema)

    @api.constrains('dcasa_panel_logo', 'dcasa_panel_icono')
    def _check_dcasa_panel_imagenes(self):
        for empresa in self.with_context(bin_size=False):
            for campo, que in (('dcasa_panel_logo', 'El logo'), ('dcasa_panel_icono', 'El ícono')):
                datos = _bytes(empresa[campo])
                if not datos:
                    continue
                try:
                    I.abrir(datos)
                except (ValueError, UserError, OSError):
                    raise ValidationError(SOLO_IMAGENES.format(que=que)) from None

    def _dcasa_panel_poner(self, vals):
        """El único camino para cambiar la marca desde el código (Ajustes y Brian): exige ser administrador ANTES de
        escribir y valida como al guardar. Devuelve ``True`` si algo cambió."""
        self.ensure_one()
        if not self.env.user.has_group(GRUPO):
            raise AccessError(self.env._(
                'Solo un administrador cambia la marca del panel (Ajustes › Marca del panel).'))
        vals = {campo: valor for campo, valor in vals.items() if campo in CAMPOS_DE_LA_MARCA}
        if not vals:
            return False
        antes = self.dcasa_panel_version
        self.write(vals)
        return self.dcasa_panel_version != antes

    def _dcasa_panel_fabrica(self, que='todo'):
        """Vuelve a la marca de fábrica: ``colores``, ``logo``, ``icono`` o ``todo``."""
        vals = {}
        if que in ('colores', 'todo'):
            vals.update({'dcasa_panel_color_principal': C.FABRICA_PRINCIPAL,
                         'dcasa_panel_color_acento': C.FABRICA_ACENTO})
        if que in ('logo', 'todo'):
            vals['dcasa_panel_logo'] = False
        if que in ('icono', 'todo'):
            vals['dcasa_panel_icono'] = False
        return self._dcasa_panel_poner(vals)

    # --- Leer -----------------------------------------------------------------------------------------------------

    def _dcasa_panel_tinte(self):
        self.ensure_one()
        empresa = self.sudo()
        return Tinte(empresa.dcasa_panel_color_principal, empresa.dcasa_panel_color_acento)

    def _dcasa_panel_imagenes(self):
        """Qué imágenes subió: un conjunto con ``'dcasa_panel_logo'`` y/o ``'dcasa_panel_icono'``. Se pregunta a los
        adjuntos (una consulta, sin bajar la imagen) y no a la memoria del ORM: así sale bien también justo después de
        cambiarla en la misma transacción (Brian la pone y en seguida dice cómo quedó)."""
        self.ensure_one()
        adjuntos = self.env['ir.attachment'].sudo().search_read([
            ('res_model', '=', 'res.company'), ('res_id', '=', self.id),
            ('res_field', 'in', ('dcasa_panel_logo', 'dcasa_panel_icono'))], ['res_field'])
        return {adjunto['res_field'] for adjunto in adjuntos}

    def _dcasa_panel_tiene(self, campo):
        """¿Subió esta imagen (el logo o el ícono)?"""
        return campo in self._dcasa_panel_imagenes()

    def _dcasa_panel_fuente_del_icono(self):
        """Los bytes de la imagen de la que salen los íconos: el ícono, o si no hay, el logo. ``b''`` = de fábrica."""
        self.ensure_one()
        empresa = self.sudo().with_context(bin_size=False)
        return _bytes(empresa.dcasa_panel_icono) or _bytes(empresa.dcasa_panel_logo)

    def _dcasa_panel_url_icono(self, nombre, imagenes=None):
        self.ensure_one()
        if not (self._dcasa_panel_imagenes() if imagenes is None else imagenes):
            return ICONOS_DE_FABRICA[nombre]
        return f'/dcasa_interfaz/marca/icono/{self.id}/{self.sudo().dcasa_panel_version or "0"}/{nombre}'

    def _dcasa_panel_url_logo(self, imagenes=None):
        self.ensure_one()
        if 'dcasa_panel_logo' not in (self._dcasa_panel_imagenes() if imagenes is None else imagenes):
            return LOGO_DE_FABRICA
        return f'/web/image/res.company/{self.id}/dcasa_panel_logo?unique={self.sudo().dcasa_panel_version or "0"}'

    def _dcasa_panel_url_hoja(self, esquema='light'):
        """La hoja del panel pintada con los colores de la empresa, o ``None`` si se usa la de Odoo tal cual (colores
        de fábrica, o el modo de depuración de estilos, que arma la hoja de otra forma)."""
        self.ensure_one()
        if self._dcasa_panel_tinte().de_fabrica:
            return None
        debug = (request.session.debug if request else '') or ''
        if 'assets' in debug:
            return None
        paquete = 'web.assets_web_dark' if esquema == 'dark' else 'web.assets_web'
        for url in self.env['ir.qweb']._get_asset_link_urls(paquete, debug=debug):
            if url.startswith('/web/assets/') and url.endswith('.css'):
                original = url[len('/web/assets/'):]
                return f'/dcasa_interfaz/marca/hoja/{self.id}/{self.sudo().dcasa_panel_version or "0"}/{original}'
        return None

    def _dcasa_panel_pagina(self, esquema='light'):
        """Lo que la página del panel (``web.webclient_bootstrap``) necesita. Vacío si todo es de fábrica: la página
        sale exactamente como antes. Si algo falla al leer la marca, también vacío: el panel abre con la de fábrica."""
        try:
            return self._dcasa_panel_pagina_sin_red(esquema)
        except Exception:
            _logger.exception('Marca del panel: no se pudo leer la marca de la empresa %s; va la de fábrica', self.id)
            return {}

    def _dcasa_panel_pagina_sin_red(self, esquema):
        self.ensure_one()
        datos = {}
        tinte = self._dcasa_panel_tinte()
        if not tinte.de_fabrica:
            hoja = self._dcasa_panel_url_hoja(esquema)
            if hoja:
                datos['hoja'] = hoja
        imagenes = self._dcasa_panel_imagenes()
        if imagenes:
            datos['favicon'] = self._dcasa_panel_url_icono('icono-192.png', imagenes)
            datos['apple'] = self._dcasa_panel_url_icono('apple-touch-icon.png', imagenes)
        return datos

    def _dcasa_panel_navegador(self):
        """Para el JavaScript del panel (``session_info``): el logo y el nombre a mostrar, o ``False`` (de fábrica)."""
        self.ensure_one()
        imagenes = self._dcasa_panel_imagenes()
        if 'dcasa_panel_logo' not in imagenes:
            return {'logo': False, 'nombre': False}
        return {'logo': self._dcasa_panel_url_logo(imagenes), 'nombre': self.sudo().name}

    def _dcasa_panel_manifiesto(self):
        """Los íconos de la app instalable (``None`` = los de fábrica). El color de la barra no cambia con la marca:
        es el crema de la página del panel (``controllers/webmanifest.py``)."""
        self.ensure_one()
        iconos = None
        imagenes = self._dcasa_panel_imagenes()
        if imagenes:
            iconos = [{'src': self._dcasa_panel_url_icono(nombre, imagenes), 'sizes': tamano, 'type': 'image/png',
                       'purpose': uso} for nombre, tamano, uso in ICONOS_DEL_MANIFIESTO]
        return {'iconos': iconos}

    def _dcasa_panel_resumen(self):
        """La marca del panel en palabras (para Brian y las pruebas)."""
        self.ensure_one()
        empresa = self.sudo()
        principal = empresa.dcasa_panel_color_principal or C.FABRICA_PRINCIPAL
        acento = empresa.dcasa_panel_color_acento or C.FABRICA_ACENTO
        imagenes = self._dcasa_panel_imagenes()
        logo = 'dcasa_panel_logo' in imagenes
        icono = 'dcasa_panel_icono' in imagenes
        return {
            'empresa': empresa.name,
            'logo': 'propio' if logo else 'de fábrica',
            'icono': 'propio' if icono else ('sale del logo del panel' if logo else 'de fábrica'),
            'color_principal': principal,
            'color_principal_de_fabrica': principal == C.FABRICA_PRINCIPAL,
            'color_acento': acento,
            'color_acento_de_fabrica': acento == C.FABRICA_ACENTO,
            'oscuro_de_la_marca': C.oscuro_de(principal),
            'como_se_lee': C.como_se_lee(principal, acento),
            'todo_de_fabrica': not logo and not icono and principal == C.FABRICA_PRINCIPAL
                               and acento == C.FABRICA_ACENTO,
        }


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    dcasa_panel_logo = fields.Image(related='company_id.dcasa_panel_logo', readonly=False)
    dcasa_panel_icono = fields.Image(related='company_id.dcasa_panel_icono', readonly=False)
    # Los dos colores se guardan juntos (un solo write): campos «related» los escribirían uno por uno, y el par
    # intermedio (el principal nuevo con el acento de antes) podría no leerse y frenar un par final que sí se lee.
    dcasa_panel_color_principal = fields.Char(
        'Color principal del panel', compute='_compute_dcasa_panel_colores', inverse='_inverse_dcasa_panel_colores',
        readonly=False)
    dcasa_panel_color_acento = fields.Char(
        'Color de acento del panel', compute='_compute_dcasa_panel_colores', inverse='_inverse_dcasa_panel_colores',
        readonly=False)
    dcasa_panel_lectura = fields.Char('Cómo se va a leer', compute='_compute_dcasa_panel_lectura')

    @api.depends('company_id.dcasa_panel_color_principal', 'company_id.dcasa_panel_color_acento')
    def _compute_dcasa_panel_colores(self):
        for ajustes in self:
            ajustes.dcasa_panel_color_principal = ajustes.company_id.dcasa_panel_color_principal
            ajustes.dcasa_panel_color_acento = ajustes.company_id.dcasa_panel_color_acento

    def _inverse_dcasa_panel_colores(self):
        for ajustes in self:
            ajustes.company_id.write({campo: ajustes[campo]
                                      for campo in ('dcasa_panel_color_principal', 'dcasa_panel_color_acento')})

    @api.depends('dcasa_panel_color_principal', 'dcasa_panel_color_acento')
    def _compute_dcasa_panel_lectura(self):
        for ajustes in self:
            try:
                ajustes.dcasa_panel_lectura = C.como_se_lee(ajustes.dcasa_panel_color_principal,
                                                            ajustes.dcasa_panel_color_acento)
            except ValueError as error:
                ajustes.dcasa_panel_lectura = str(error)

    def action_dcasa_panel_fabrica(self):
        """Botón «Volver a la marca de fábrica»: logo, ícono y colores de fábrica, y el panel se recarga."""
        if not self.env.user.has_group(GRUPO):
            raise AccessError(self.env._('Solo un administrador cambia la marca del panel.'))
        empresa = self[:1].company_id or self.env.company
        empresa._dcasa_panel_fabrica('todo')
        return {'type': 'ir.actions.client', 'tag': 'reload'}
