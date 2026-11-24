import re

from odoo import models

# Donde la burbuja no sale: el pago (taparía «Confirmar»), las pantallas de Odoo y el acceso.
# Sin burbuja de Brian (vuelve la de WhatsApp, o ninguna): el pago, el panel, el portal de Odoo y Mi cuenta (su barra
# de secciones va fija abajo en el celular y esconde la flotante de WhatsApp: la de Brian la taparía).
RUTAS_SIN_BURBUJA = ('/shop/checkout', '/shop/address', '/shop/payment', '/shop/confirm', '/shop/extra_info',
                     '/shop/confirmation', '/payment/status', '/web', '/odoo', '/my', '/mi-cuenta', '/brian',
                     '/envios/choferes')
RE_WA = re.compile(r'^https://wa\.me/(\d{8,15})\?')


class Website(models.Model):
    _inherit = 'website'

    def _dcasa_brian_tienda_activa(self):
        """¿Se dibuja la burbuja de Brian? (Sitio web › Brian de la tienda). Apagada vuelve la de WhatsApp."""
        return self.env['dcasa.brian.tienda']._activo()

    def _dcasa_brian_en_esta_pagina(self, ruta):
        return self._dcasa_brian_tienda_activa() and not str(ruta or '').startswith(RUTAS_SIN_BURBUJA)

    def _dcasa_brian_datos(self):
        """Lo que la página necesita para la burbuja, igual para todo visitante (la página se puede guardar en el
        borde): el WhatsApp del sitio, el nombre de la tienda (la empresa del sitio: el título del chat) y la clave
        pública de Turnstile si el sitio lo tiene. Nada de la sesión."""
        self.ensure_one()
        coincide = RE_WA.match(self._dcasa_whatsapp_url('') or '')
        return {
            'whatsapp': coincide.group(1) if coincide else '',
            'marca': (self.company_id.name or self.name or '').strip(),
            'turnstile': self.env['dcasa.brian.tienda'].sudo()._turnstile_clave_publica(),
        }
