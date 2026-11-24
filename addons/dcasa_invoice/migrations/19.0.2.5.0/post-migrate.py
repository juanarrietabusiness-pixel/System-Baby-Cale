"""Garantía, cambios y términos del comprobante: fuera los textos de D'CASA (Baby Caleb, 2026-11-24).

Una base ya instalada (staging) tiene los textos iniciales de D'CASA, que hablan de muebles, colchones, flete y «el
ITBMS se suma». Aquí se cambian por los de Baby Caleb (``TEXTOS_INICIALES``), pero SOLO donde el texto sigue siendo
exactamente el de D'CASA: lo que el dueño escribió o borró en Ajustes › Empresas no se toca. Es seguro de repetir.
"""
import logging

from odoo import SUPERUSER_ID, api
from odoo.addons.dcasa_invoice.models.res_company import TEXTOS_INICIALES

_logger = logging.getLogger(__name__)

TEXTOS_DCASA = {
    'dcasa_factura_garantia': (
        "Tus muebles tienen garantía de 30 días desde la entrega contra defectos de fabricación. "
        "No cubre golpes, humedad, mal uso ni armado hecho por terceros. Escríbenos por WhatsApp "
        "con tu factura y fotos del detalle y lo resolvemos."),
    'dcasa_factura_cambios': (
        "Puedes cambiar tu compra dentro de los 7 días siguientes a la entrega, con la factura, "
        "el producto sin uso y en su empaque original. Los colchones no tienen cambio por "
        "higiene, salvo defecto de fábrica."),
    'dcasa_factura_terminos': (
        "Precios en dólares; el ITBMS se suma al precio. Un apartado se confirma con un abono y "
        "el mueble queda reservado hasta completar el pago en el plazo acordado. El flete se "
        "cotiza según la zona y se paga aparte; la entrega se coordina por WhatsApp."),
}


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for empresa in env['res.company'].search([]):
        cambios = {campo: TEXTOS_INICIALES[campo] for campo, viejo in TEXTOS_DCASA.items() if empresa[campo] == viejo}
        if cambios:
            empresa.write(cambios)
            _logger.info('Empresa %s: textos del comprobante de Baby Caleb en %s.', empresa.id, ', '.join(cambios))
