"""Originales del catálogo: dónde están y qué cargó cada uno. Lo usa scripts/procesar_up_media.py.

En la instalación de D'CASA, este script leía su Excel de productos y las fotos de «up media/» y generaba
``addons/dcasa_catalogo/data/catalogo.json`` y las fotos de ``static/img/productos/``. En esta instalación (Baby Caleb)
el catálogo **se escribe a mano** con la lista del dueño (``data/catalogo.json``, formato en
``addons/dcasa_catalogo/catalogo.py`` y docs/CATALOGO.md) y las fotos las sube el dueño en Odoo. No hay ningún Excel
registrado (``EXCEL = None``): ``main()`` no lee ni escribe nada y devuelve que no se cargó ningún original, así la
bandeja deja cada archivo pendiente con su motivo (y nunca pisa el catalogo.json escrito a mano).

Para que un Excel o unas fotos de la bandeja entren solos al catálogo hay que escribir aquí cómo se leen y que
generen el formato de catalogo.json de hoy (el lector del Excel de D'CASA está en el historial de git de este archivo;
escribía el formato anterior, que la carga ya no lee).

Dónde están los originales: «up media/» es la bandeja de entrada (solo lo pendiente) y «fuentes/<carpeta>/» guarda lo
que ya se procesó (lo mueve scripts/procesar_up_media.py). Un archivo se busca primero en «up media/» y después en
«fuentes/**» (y en el índice de lo archivado en R2, ``fuentes/ARCHIVADO.tsv``).
"""
from collections import OrderedDict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ORIGEN = RAIZ / 'up media'          # bandeja de entrada: solo lo pendiente
FUENTES = RAIZ / 'fuentes'          # originales ya procesados, por carga
# Índice de los originales que scripts/archivar_fuentes.sh pasó a R2 (prefijo fuentes/) y quitó del
# repositorio: ruta relativa a la raíz, sha256, bytes, fecha. Siguen contando como fuente (por nombre).
ARCHIVADO = FUENTES / 'ARCHIVADO.tsv'
# El Excel de productos que este script sabe leer. Ninguno: el catálogo de Baby Caleb se escribe a mano.
EXCEL = None
# Las gráficas de una campaña que la bandeja guarda sin cargar (no son fotos de producto) van a esta carpeta.
CARPETA_GRAFICAS_BW = 'graficas-black-weekend'
MODULO = RAIZ / 'addons' / 'dcasa_catalogo'
DESTINO_JSON = MODULO / 'data' / 'catalogo.json'


def fuentes_disponibles(origen=None, fuentes=None):
    """Archivos de origen por nombre: los de «up media/» mandan; después, «fuentes/**».

    Devuelve {nombre: ruta}. Solo archivos sueltos de la bandeja (las subcarpetas de «up media» son de otros flujos);
    de «fuentes/» todo lo que no sea un LEEME.
    """
    origen = ORIGEN if origen is None else origen
    fuentes = FUENTES if fuentes is None else fuentes
    rutas = OrderedDict()
    if origen.is_dir():
        for f in sorted(origen.iterdir()):
            if f.is_file() and f.suffix.lower() != '.md':
                rutas[f.name] = f
    if fuentes.is_dir():
        for f in sorted(fuentes.rglob('*')):
            if f.is_file() and f.suffix.lower() not in ('.md', '.tsv'):
                rutas.setdefault(f.name, f)
    for nombre in archivados_en_r2(fuentes / ARCHIVADO.name):
        rutas.setdefault(nombre, None)   # está en R2, no en disco: ruta_fuente() lo explica
    return rutas


def archivados_en_r2(indice=None):
    """Nombres de los originales que están en R2 según fuentes/ARCHIVADO.tsv (vacío si no hay índice)."""
    indice = ARCHIVADO if indice is None else indice
    if not indice.is_file():
        return []
    nombres = []
    for linea in indice.read_text(encoding='utf-8').splitlines():
        if linea and not linea.startswith('#'):
            nombres.append(Path(linea.split('\t')[0]).name)
    return nombres


def ruta_fuente(nombre, rutas=None):
    """Ruta de un original por su nombre (bandeja primero, luego fuentes/). Falla si no está."""
    rutas = fuentes_disponibles() if rutas is None else rutas
    if nombre not in rutas:
        raise FileNotFoundError(f'No encuentro «{nombre}» ni en «{ORIGEN.name}/» ni en «{FUENTES.name}/».')
    if rutas[nombre] is None:
        raise FileNotFoundError(f'«{nombre}» está archivado en R2 (fuentes/ARCHIVADO.tsv): '
                                'tráelo con `scripts/archivar_fuentes.sh traer` antes de regenerar.')
    return rutas[nombre]


def main():
    """Qué original cargó cada parte del catálogo: ninguno (el catálogo se escribe a mano). No toca catalogo.json."""
    print(f'Catálogo: se escribe a mano ({DESTINO_JSON.relative_to(RAIZ)}); ningún Excel registrado: nada que generar.')
    return {'excel_inicial': EXCEL, 'fotos_inicial': {}, 'pedidos': []}


if __name__ == '__main__':
    main()
