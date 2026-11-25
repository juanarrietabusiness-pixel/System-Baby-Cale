"""La promoción de Dany Baby por pares (decisión del dueño de Baby Caleb, 2026-11-24): en la base ya instalada
(staging), el «Precio por par» de ``data/catalogo.json`` (DANY-AW600, $35.00) entra solo donde está vacío. El que ya
puso Gerencia no se pisa (``catalogo.poner_precios_par``).
"""
from odoo import SUPERUSER_ID, api
from odoo.addons.dcasa_catalogo.catalogo import poner_precios_par


def migrate(cr, version):
    poner_precios_par(api.Environment(cr, SUPERUSER_ID, {}))
