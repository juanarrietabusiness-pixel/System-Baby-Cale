"""La marca de fábrica del panel pasa a ser la de Baby Caleb (pedido del dueño, 2026-11-19, docs/MARCA_BABY_CALEB.md).

Una base instalada antes guarda en cada empresa los colores de fábrica de entonces, los de D'CASA (#1340B1 y #FED00F).
Con la fábrica nueva esos dos ya serían colores «propios» y el panel se pintaría de azul y amarillo: aquí pasan a los de
ahora (navy y naranja). Un color que la empresa sí eligió no se toca; si con el cambio el par dejara de leerse, la
empresa vuelve entera a la marca de fábrica. La versión de la marca cambia para que los navegadores pidan lo nuevo. Es
seguro de repetir.
"""
import logging
import secrets

from odoo.addons.dcasa_interfaz.marca import colores as C

_logger = logging.getLogger(__name__)

ANTES = {'dcasa_panel_color_principal': (C.DCASA_PRINCIPAL, C.FABRICA_PRINCIPAL),
         'dcasa_panel_color_acento': (C.DCASA_ACENTO, C.FABRICA_ACENTO)}


def migrate(cr, version):
    cr.execute('SELECT id, dcasa_panel_color_principal, dcasa_panel_color_acento FROM res_company')
    for empresa, principal, acento in cr.fetchall():
        nuevo = {'dcasa_panel_color_principal': principal, 'dcasa_panel_color_acento': acento}
        for campo, (de_dcasa, de_ahora) in ANTES.items():
            if (nuevo[campo] or '').upper() in ('', de_dcasa):
                nuevo[campo] = de_ahora
        if C.problema_del_principal(nuevo['dcasa_panel_color_principal']) or C.problema_del_acento(
                nuevo['dcasa_panel_color_acento'], nuevo['dcasa_panel_color_principal']):
            nuevo = {campo: de_ahora for campo, (_de_dcasa, de_ahora) in ANTES.items()}
        if (nuevo['dcasa_panel_color_principal'], nuevo['dcasa_panel_color_acento']) == (principal, acento):
            continue
        cr.execute('UPDATE res_company SET dcasa_panel_color_principal = %s, dcasa_panel_color_acento = %s, '
                   'dcasa_panel_version = %s WHERE id = %s',
                   (nuevo['dcasa_panel_color_principal'], nuevo['dcasa_panel_color_acento'], secrets.token_hex(4),
                    empresa))
        _logger.info('Marca del panel: la empresa %s pasa de %s/%s a %s/%s (la fábrica ahora es Baby Caleb).',
                     empresa, principal, acento, nuevo['dcasa_panel_color_principal'],
                     nuevo['dcasa_panel_color_acento'])
