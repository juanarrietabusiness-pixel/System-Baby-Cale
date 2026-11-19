"""Marca de Baby Caleb (2026-11-19) en bases que ya tenían el módulo (staging).

El menú se arma una sola vez al instalar (data/website_menu_data.xml, ``noupdate``) y las entregas y los pagos los
crea ``_dcasa_configurar_tienda`` al instalar: una actualización con ``-u`` no los vuelve a escribir. Aquí se corrige
una vez lo que el cliente ve con la tienda de origen: «Socios Baby Caleb» en el menú, «Retiro en tienda» sin el lugar
de D'CASA y «El pedido se entrega…» en el mensaje del pago en la tienda (models/tienda.py).
"""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['website']._dcasa_sin_restos_de_dcasa()
