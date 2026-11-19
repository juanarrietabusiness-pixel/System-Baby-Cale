"""Los colores de la empresa para documentos y correos pasan a la marca de Baby Caleb (2026-11-19,
docs/MARCA_BABY_CALEB.md): ``primary_color`` navy #1B3246 (lleva texto encima en los documentos) y ``secondary_color``
naranja #EE924A.

``data/res_company_data.xml`` es ``noupdate``: una base ya instalada no los recibe al actualizar. Aquí se cambian solo
si la empresa todavía tiene los de D'CASA que puso ese archivo (#1340B1 y #0E2A6B); un color elegido a mano desde
Ajustes › Empresas no se toca. Es seguro de repetir.
"""
import logging

_logger = logging.getLogger(__name__)

CAMBIOS = (('primary_color', '#1340B1', '#1B3246'), ('secondary_color', '#0E2A6B', '#EE924A'))


def migrate(cr, version):
    for campo, de_dcasa, de_baby_caleb in CAMBIOS:
        cr.execute(f'UPDATE res_company SET {campo} = %s WHERE upper({campo}) = %s RETURNING id',  # noqa: S608
                   (de_baby_caleb, de_dcasa))
        empresas = [fila[0] for fila in cr.fetchall()]
        if empresas:
            _logger.info('Empresa: %s pasa de %s a %s en %s.', campo, de_dcasa, de_baby_caleb, empresas)
