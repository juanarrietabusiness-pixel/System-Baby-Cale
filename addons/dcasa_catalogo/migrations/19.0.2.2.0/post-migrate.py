"""Las fotos que tomó el dueño (2026-11-24): Velvee (P, M y G), Dany Baby y Fular Moon.

Las subió a «up media» y quedaron en ``data/fotos/`` con su lugar en ``data/catalogo.json``. Es la misma
``poner_fotos`` de la migración 19.0.2.1.0: solo llena lo vacío (una foto que alguien ya puso se queda) y publica lo
que recibe su foto principal y no estaba publicado.
"""
from odoo import SUPERUSER_ID, api
from odoo.addons.dcasa_catalogo.catalogo import poner_fotos


def migrate(cr, version):
    poner_fotos(api.Environment(cr, SUPERUSER_ID, {}))
