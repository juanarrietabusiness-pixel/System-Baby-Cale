"""La razón social de la empresa pasa a «Baby Caleb Panamá» (el dueño, 2026-11-24, docs/BABY_CALEB.md).

``data/res_company_data.xml`` es ``noupdate``: una base ya instalada no recibe el nombre nuevo al actualizar. Aquí se
cambia solo si la empresa principal todavía se llama «Baby Caleb», como la dejó ese archivo; un nombre escrito a mano en
Ajustes › Empresas no se toca. Va por el ORM para que la ficha de contacto de la empresa (``partner_id``) cambie con
ella. Es seguro de repetir.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

ANTES = 'Baby Caleb'
AHORA = 'Baby Caleb Panamá'


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    empresa = env.ref('base.main_company', raise_if_not_found=False)
    if empresa and empresa.name == ANTES:
        empresa.name = AHORA
        _logger.info('Empresa %s: la razón social pasa de «%s» a «%s».', empresa.id, ANTES, AHORA)
