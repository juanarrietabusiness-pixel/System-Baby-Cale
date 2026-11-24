"""Decisiones del dueño de Baby Caleb (2026-11-24) sobre lo que ya está en la base.

* Lo agotado no se pide en la web (``no_vender_agotados``).
* La Nateen L de cierre queda archivada (``archivar_variantes``): se reactiva si vuelve.
* Velvee no se publica sola (``"publicar": false`` en ``data/catalogo.json``): aquí no se despublica, porque si ya
  está publicada lo hizo una persona.
"""
from odoo import SUPERUSER_ID, api
from odoo.addons.dcasa_catalogo.catalogo import archivar_variantes, no_vender_agotados


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    archivar_variantes(env)
    no_vender_agotados(env)
