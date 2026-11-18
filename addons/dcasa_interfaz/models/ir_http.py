import base64
import binascii
import logging

from odoo import api, models
from odoo.http import request

_logger = logging.getLogger(__name__)

SVG_BASE64 = 'data:image/svg+xml;base64,'


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @api.private
    def color_scheme(self):
        """El modo oscuro del panel lo elige cada persona en su navegador (menú de usuario › «Modo oscuro»).

        Odoo Community trae el andamio (la hoja ``web.assets_web_dark``) pero contesta siempre «light». Aquí manda la
        cookie ``color_scheme``: solo el valor exacto ``dark`` enciende el modo oscuro; sin cookie o con cualquier
        otro valor, el panel sale claro, como siempre.

        Privado para RPC: solo lo usa el servidor al armar la página (``webclient_rendering_context``).
        """
        if request and request.httprequest.cookies.get('color_scheme') == 'dark':
            return 'dark'
        return super().color_scheme()

    def session_info(self):
        """Además, la marca del panel para el JavaScript (``static/src/js/marca.js``): el logo de la empresa y su
        nombre, o vacío si es el de fábrica. Si algo falla, el panel arranca igual con el de fábrica."""
        info = super().session_info()
        if info.get('is_internal_user'):
            try:
                info['dcasa_marca'] = self.env.company._dcasa_panel_navegador()
            except Exception:
                _logger.exception('Marca del panel: no se pudo leer el logo de la empresa')
        return info


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def load_web_menus(self, debug):
        """Los íconos SVG de las apps (azul de la marca y el punto amarillo) con los colores de la empresa
        (Ajustes › Marca del panel). Con los de fábrica, tal cual."""
        menus = super().load_web_menus(debug)
        try:
            tinte = self.env.company._dcasa_panel_tinte()
        except Exception:
            _logger.exception('Marca del panel: no se pudieron leer los colores de la empresa')
            return menus
        if tinte.de_fabrica:
            return menus
        for menu in menus.values():
            datos = menu.get('webIconData') or ''
            if not datos.startswith(SVG_BASE64):
                continue
            try:
                svg = base64.b64decode(datos[len(SVG_BASE64):]).decode('utf-8')
            except (binascii.Error, ValueError, UnicodeDecodeError):
                continue
            menu['webIconData'] = SVG_BASE64 + base64.b64encode(tinte.svg(svg).encode('utf-8')).decode('ascii')
        return menus
