"""El conocimiento inicial de un negocio: se carga UNA vez por entrada en su base y desde ahí manda el panel.

Pedido del dueño de Baby Caleb (2026-11-24): «Aquí solamente vamos a tener una fuente de verdad y es el
conocimiento», y lo tiene que poder configurar, apagar y archivar. Por eso este archivo no es una segunda fuente:

* ``conocimiento_inicial/<negocio>.json`` solo SIEMBRA. Cada entrada se crea una vez (la clave queda anotada en
  ``dcasa_conversaciones.conocimiento_inicial_cargado``) como una ficha normal de «Conocimiento del bot» (escrita a
  mano). Lo que el equipo cambie, apague, archive o borre ahí no se vuelve a pisar ni a crear.
* Una entrada NUEVA en el archivo se crea en el siguiente arranque; una CORRECCIÓN a una que ya existe se hace en el
  panel (cambiar el archivo no la toca).
* Lo corre el arranque solo si ``DCASA_CONOCIMIENTO_INICIAL`` nombra el negocio (staging y producción de Baby Caleb,
  docker/negocio.env, dentro de la imagen). Ningún módulo trae entradas en sus datos: una instalación sin la variable
  sigue en cero (decisión del 2026-11-18, test_conocimiento.py).
"""
import json
import logging

from odoo.tools.misc import file_open

_logger = logging.getLogger(__name__)

MODULO = 'dcasa_conversaciones'
NEGOCIOS = ('baby_caleb',)
PARAM_CARGADAS = 'dcasa_conversaciones.conocimiento_inicial_cargado'


def leer_conocimiento_inicial(negocio):
    """``conocimiento_inicial/<negocio>.json`` tal cual: ``{'fuente', 'entradas': [...]}``."""
    if negocio not in NEGOCIOS:
        raise ValueError(f'No hay conocimiento inicial para «{negocio}» ({", ".join(NEGOCIOS)})')
    with file_open(f'{MODULO}/conocimiento_inicial/{negocio}.json', 'rb') as archivo:
        return json.load(archivo)


def cargar_conocimiento_inicial(env, negocio, datos=None):
    """Crea las entradas del archivo que nunca se cargaron en esta base. Devuelve las que creó."""
    datos = leer_conocimiento_inicial(negocio) if datos is None else datos
    icp = env['ir.config_parameter'].sudo()
    cargadas = set(filter(None, (icp.get_param(PARAM_CARGADAS) or '').split(',')))
    Conocimiento = env['dcasa.conocimiento'].sudo()
    creadas = Conocimiento.browse()
    for entrada in datos.get('entradas') or []:
        clave = f"{negocio}:{entrada['clave']}"
        if clave in cargadas:
            continue
        nota = f"Cargada del conocimiento inicial ({datos.get('fuente') or negocio}). Se corrige aquí."
        if entrada.get('nota'):
            nota = f"{entrada['nota']}\n{nota}"
        creadas |= Conocimiento.create({
            'titulo': entrada['titulo'],
            'contenido': entrada['contenido'],
            'etiquetas': ', '.join(entrada.get('etiquetas') or []),
            'activo': entrada.get('activo', True),
            'fuente': 'manual',
            'nota': nota,
        })
        cargadas.add(clave)
    icp.set_param(PARAM_CARGADAS, ','.join(sorted(cargadas)))
    _logger.info('Conocimiento inicial (%s): %s entradas nuevas.', negocio, len(creadas))
    return creadas
