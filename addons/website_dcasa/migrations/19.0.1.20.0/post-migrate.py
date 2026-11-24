"""El menú de babycaleb.com (2026-11-24) en bases que ya tenían el módulo (staging).

El menú se arma una sola vez al instalar (data/website_menu_data.xml, ``noupdate``): una actualización con ``-u`` no lo
vuelve a escribir. Aquí se arma una vez con el de su web (models/website.py, MENU_PRINCIPAL): Productos, Beneficios,
Historia, Tips, Cómo comprar y FAQ. Socios y Contacto salen del menú (siguen en el pie y en el menú del celular); lo que
la dueña haya agregado desde el editor se queda.
"""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['website']._dcasa_armar_menu_principal()
