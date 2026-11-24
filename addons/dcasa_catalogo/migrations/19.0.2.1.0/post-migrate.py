"""Las fotos de la web de Baby Caleb en los productos del catálogo, y publicados (pedido del dueño, 2026-11-24).

Hasta aquí el catálogo se cargaba sin fotos y sin publicar («las fotos se ponen a mano en Odoo»). Ahora
``data/catalogo.json`` dice cuál foto de ``data/fotos/`` es de cada producto y de cada talla (las de la web de Baby
Caleb). Solo se llena lo vacío: una foto que alguien ya puso se queda, y ese producto no cambia de publicado a no
publicado ni al revés. Lo que no tiene foto (Velvee y Dany Baby) sigue sin publicar.
"""
from odoo import SUPERUSER_ID, api
from odoo.addons.dcasa_catalogo.catalogo import poner_fotos


def migrate(cr, version):
    poner_fotos(api.Environment(cr, SUPERUSER_ID, {}))
