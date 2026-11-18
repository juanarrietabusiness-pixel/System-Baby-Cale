"""Lo que el navegador pide de la marca del panel: la hoja pintada con los colores de la empresa y sus íconos.

* ``/dcasa_interfaz/marca/hoja/<empresa>/<versión>/<la de Odoo>``: la hoja compilada del panel (``web.assets_web`` o
  ``web.assets_web_dark``) con los colores de la empresa (``marca/tinte.py``). Solo para quien entró al panel y solo de
  una empresa suya. Se pinta una vez por hoja y por colores (queda en memoria) y el navegador la guarda un año: la
  dirección cambia sola si cambian los colores (versión) o el código (la de Odoo). **Si algo falla, redirige a la hoja
  de Odoo**: el panel nunca se queda sin estilos (a lo sumo, con los colores de fábrica).
* ``/dcasa_interfaz/marca/icono/<empresa>/<versión>/<nombre>.png``: favicon, apple-touch-icon y los íconos del
  manifiesto, hechos del ícono (o del logo) que subió la empresa. Públicos, como los de fábrica: la pantalla de inicio
  del celular los pide a veces sin la sesión, y una marca no es un secreto. Sin imagen propia, redirige a los de
  fábrica.
"""
import logging
import re
import threading
from collections import OrderedDict

from odoo import SUPERUSER_ID, http
from odoo.http import request

from ..marca import iconos as I
from ..models.marca import ICONOS_DE_FABRICA

_logger = logging.getLogger(__name__)

# Lo que va después de /web/assets/ en la hoja del panel: [sitio/]versión/archivo.
HOJA = re.compile(r'(?:(?P<sitio>\d+)/)?(?P<unico>[0-9a-f]{7})/'
                  r'(?P<archivo>web\.assets_web(?:_dark)?(?:\.rtl)?\.min\.css)')
UN_ANO = 'max-age=31536000, immutable'


class _Memoria:
    """Las últimas hojas o íconos hechos, en memoria del proceso (unos pocos MB): se rehacen al reiniciar."""

    def __init__(self, tope):
        self.tope = tope
        self._datos = OrderedDict()
        self._candado = threading.Lock()

    def get(self, clave):
        with self._candado:
            if clave in self._datos:
                self._datos.move_to_end(clave)
                return self._datos[clave]
        return None

    def put(self, clave, valor):
        with self._candado:
            self._datos[clave] = valor
            self._datos.move_to_end(clave)
            while len(self._datos) > self.tope:
                self._datos.popitem(last=False)

    def clear(self):
        with self._candado:
            self._datos.clear()


HOJAS = _Memoria(6)       # ~1,5 MB cada una
ICONOS = _Memoria(40)


def hoja_compilada(env, original):
    """Los bytes de la hoja de Odoo ``/web/assets/<original>``; ``None`` si esa versión ya no es la de ahora."""
    url = f'/web/assets/{original}'
    adjunto = env['ir.attachment'].sudo().search([
        ('public', '=', True), ('url', '=', url), ('res_model', '=', 'ir.ui.view'), ('res_id', '=', 0),
        ('create_uid', '=', SUPERUSER_ID)], limit=1)
    if adjunto:
        return adjunto.raw
    # Nadie la pidió todavía (la página ya no enlaza la de Odoo): se arma igual que en /web/assets.
    hallado = HOJA.fullmatch(original)
    nombre, rtl, _tipo, autoprefijo = env['ir.asset']._parse_bundle_name(hallado.group('archivo'), False)
    paquete = env['ir.qweb'].sudo()._get_asset_bundle(nombre, css=True, js=False, rtl=rtl, autoprefix=autoprefijo)
    if paquete.get_version('css') != hallado.group('unico'):
        return None
    adjunto = paquete.css()
    return adjunto.raw if adjunto else None


class MarcaDelPanel(http.Controller):

    @http.route('/dcasa_interfaz/marca/hoja/<int:empresa>/<string:version>/<path:original>', type='http',
                auth='user', methods=['GET'])
    def hoja(self, empresa, version, original, **_kw):
        hallado = HOJA.fullmatch(original or '')
        if not hallado or empresa not in request.env.user._get_company_ids():
            raise request.not_found()
        de_odoo = f'/web/assets/{original}'
        compania = request.env['res.company'].browse(empresa)
        tinte = compania._dcasa_panel_tinte()
        if tinte.de_fabrica:
            return request.redirect(de_odoo, local=True)
        clave = (request.env.cr.dbname, original, tinte.principal, tinte.acento)
        pintada = HOJAS.get(clave)
        if pintada is None:
            try:
                crudo = hoja_compilada(request.env, original)
                if crudo is None:
                    # El código cambió desde que se armó la página: la versión de ahora.
                    esquema = 'dark' if '_dark' in hallado.group('archivo') else 'light'
                    return request.redirect(compania._dcasa_panel_url_hoja(esquema) or de_odoo, local=True)
                pintada = tinte.css(crudo.decode('utf-8')).encode('utf-8')
            except Exception:
                _logger.exception('Marca del panel: no se pudo pintar %s; se usa la hoja de Odoo', original)
                return request.redirect(de_odoo, local=True)
            HOJAS.put(clave, pintada)
        return request.make_response(pintada, headers=[
            ('Content-Type', 'text/css; charset=utf-8'),
            ('Cache-Control', f'private, {UN_ANO}'),
            ('X-Content-Type-Options', 'nosniff'),
        ])

    @http.route('/dcasa_interfaz/marca/icono/<int:empresa>/<string:version>/<string:nombre>', type='http',
                auth='public', methods=['GET'], readonly=True)
    def icono(self, empresa, version, nombre, **_kw):
        if nombre not in I.ICONOS:
            raise request.not_found()
        compania = request.env['res.company'].sudo().browse(empresa).exists()
        if not compania:
            raise request.not_found()
        actual = compania.dcasa_panel_version or '0'
        clave = (request.env.cr.dbname, empresa, actual, nombre)
        png = ICONOS.get(clave)
        if png is None:
            fuente = compania._dcasa_panel_fuente_del_icono()
            if not fuente:
                return request.redirect(ICONOS_DE_FABRICA[nombre], local=True)
            try:
                png = I.icono(fuente, nombre)
            except Exception:
                _logger.exception('Marca del panel: no se pudo hacer el ícono %s de la empresa %s', nombre, empresa)
                return request.redirect(ICONOS_DE_FABRICA[nombre], local=True)
            ICONOS.put(clave, png)
        cache = f'public, {UN_ANO}' if version == actual else 'no-cache'
        return request.make_response(png, headers=[
            ('Content-Type', 'image/png'), ('Cache-Control', cache), ('X-Content-Type-Options', 'nosniff')])
