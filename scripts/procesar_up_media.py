"""Procesa la bandeja «up media/»: python scripts/procesar_up_media.py [--simular] [--fecha AAAA-MM-DD]

«up media/» es el buzón de entrada del dueño en GitHub (sube fotos y Excel desde el navegador, sin terminal). Este
script la deja ordenada y explicada:

  1. Pregunta a scripts/importar_catalogo.py qué originales cargó al catálogo. Hoy, ninguno: el catálogo de Baby Caleb
     se escribe a mano (addons/dcasa_catalogo/data/catalogo.json) y las fotos se ponen en Odoo.
  2. Mueve con `git mv` cada archivo suelto de la bandeja según lo que pasó con él:
       · cargado      → fuentes/<carga>/           (originales ya en el catálogo; no se borran)
       · conservado   → fuentes/<carpeta>/         (archivos que no son fotos de producto pero sirven; ``CONOCIDOS``)
       · descartado   → descartado/<fecha>/        (no es de ningún producto; motivo en LEEME.md)
       · pendiente    → se queda en «up media/»     (foto, Excel sin registrar, PDF, carpetas de otros flujos) con su
                                                    motivo en RESUMEN.md
  3. Escribe «up media/RESUMEN.md»: qué foto fue a qué producto, qué no se asignó y por qué, qué
     Excel se cargó y qué sigue pendiente. Y un LEEME.md en cada carpeta destino (histórico).

Nada se adivina ni se borra: lo que no se entiende se queda en la bandeja y se explica. En CI lo
ejecuta .github/workflows/up-media.yml con cada push que toque «up media/**».
"""
import argparse
import datetime
import shutil
import subprocess
import sys
from collections import namedtuple
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import importar_catalogo as importador  # noqa: E402

RAIZ = importador.RAIZ
ORIGEN = importador.ORIGEN
FUENTES = importador.FUENTES
DESCARTADO = RAIZ / 'descartado'
RESUMEN = 'RESUMEN.md'
CARPETA_INICIAL = 'carga-inicial'
EXTENSIONES_FOTO = ('.png', '.jpg', '.jpeg', '.webp')
EXTENSIONES_EXCEL = ('.xlsx', '.xlsm')

# Archivos que no son fotos de producto pero se conservan: (patrón, carpeta, motivo). Vacío: las gráficas de Black
# Weekend de D'CASA (115.png … 153.png) no son de este negocio.
CONOCIDOS = []

MOTIVOS = {
    'carpeta': 'carpeta: la procesa otro flujo (ver su LEEME); este script no la toca',
    'excel_desconocido': 'Excel que el importador no conoce: el catálogo se escribe a mano '
                         '(`addons/dcasa_catalogo/data/catalogo.json`); para cargar un Excel, primero hay que '
                         'enseñarle a `scripts/importar_catalogo.py` cómo se lee',
    'sin_pedido': 'foto que ninguna carga reclama: por ahora las fotos de los productos se ponen a mano en Odoo '
                  '(Inventario › Productos › la foto del producto); aquí queda guardada hasta que alguien la ponga',
    'ajena': 'no es de ningún producto: el nombre no trae un código del Excel ni describe una cama '
             '(tamaño, color o medidas)',
    'otro_tipo': 'tipo de archivo que este flujo no procesa; lo revisa una persona',
    'destino_ocupado': 'ya existe un archivo con ese nombre en {destino}: se deja aquí para que alguien decida',
}

# estado: cargado | conservado | descartado | pendiente. destino: carpeta relativa a la raíz o None.
Movimiento = namedtuple('Movimiento', 'archivo estado destino motivo producto')


def hoy():
    return datetime.datetime.now(ZoneInfo('America/Panama')).date().isoformat()


def _en_pedidos(nombre, resultado):
    """(pedido, producto, optimizada, cómo, nota) si algún pedido usó esta foto; dudosa; o None."""
    for p in resultado['pedidos']:
        for archivo, producto, optimizada, como, nota in p['asignadas']:
            if archivo == nombre:
                return 'asignada', (p['pedido'], producto, optimizada, como, nota)
    for p in resultado['pedidos']:
        for archivo, nota in p['dudosas']:
            if archivo == nombre:
                return 'dudosa', (p['pedido'], nota)
    return None, None


def _conocido(nombre):
    return next(((carpeta, motivo) for patron, carpeta, motivo in CONOCIDOS if patron.match(nombre)), None)


def clasificar_uno(entrada, resultado, fecha):
    """Un archivo (o carpeta) de la bandeja → Movimiento, o None si no es asunto de este script."""
    nombre = entrada.name
    if nombre.startswith('.') or entrada.suffix.lower() == '.md':
        return None    # .gitkeep, LEEME.md, RESUMEN.md: son de la bandeja misma
    if entrada.is_dir():
        return Movimiento(nombre, 'pendiente', None, MOTIVOS['carpeta'], None)
    sufijo = entrada.suffix.lower()
    if sufijo in EXTENSIONES_EXCEL:
        if nombre == resultado['excel_inicial']:
            return Movimiento(nombre, 'cargado', f'{FUENTES.name}/{CARPETA_INICIAL}', 'Excel de la carga inicial',
                              'todos los productos de la hoja «Productos»')
        pedido = next((p for p in resultado['pedidos'] if p['excel'] == nombre), None)
        if pedido:
            return Movimiento(nombre, 'cargado', f'{FUENTES.name}/{pedido["pedido"]}',
                              f'Excel del pedido {pedido["pedido"]}', f'los productos del pedido {pedido["pedido"]}')
        return Movimiento(nombre, 'pendiente', None, MOTIVOS['excel_desconocido'], None)
    if sufijo in EXTENSIONES_FOTO:
        if nombre in resultado['fotos_inicial']:
            return Movimiento(nombre, 'cargado', f'{FUENTES.name}/{CARPETA_INICIAL}',
                              'foto de la carga inicial (el nombre es el código)', resultado['fotos_inicial'][nombre])
        tipo, datos = _en_pedidos(nombre, resultado)
        if tipo == 'asignada':
            pedido, producto, optimizada, como, nota = datos
            return Movimiento(nombre, 'cargado', f'{FUENTES.name}/{pedido}', f'{como} — {nota}',
                              f'{producto} (`{optimizada}`)')
        if tipo == 'dudosa':
            pedido, nota = datos
            return Movimiento(nombre, 'pendiente', None, f'foto dudosa del pedido {pedido}: {nota}. '
                              'Falta una decisión a mano (`decisiones` del pedido) o el código en el nombre', None)
        conocido = _conocido(nombre)
        if conocido:
            carpeta, motivo = conocido
            return Movimiento(nombre, 'conservado', f'{FUENTES.name}/{carpeta}', motivo, None)
        if not resultado['pedidos']:
            return Movimiento(nombre, 'pendiente', None, MOTIVOS['sin_pedido'], None)
        return Movimiento(nombre, 'descartado', f'{DESCARTADO.name}/{fecha}', MOTIVOS['ajena'], None)
    return Movimiento(nombre, 'pendiente', None, MOTIVOS['otro_tipo'], None)


def clasificar(entradas, resultado, fecha):
    """Todas las entradas de la bandeja → movimientos (sin tocar nada)."""
    movimientos = [clasificar_uno(e, resultado, fecha) for e in sorted(entradas, key=lambda e: e.name)]
    return [m for m in movimientos if m is not None]


def mover(raiz, origen, destino):
    """`git mv` (conserva el historial); si el archivo no está en git, mueve y agrega."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(['git', 'mv', str(origen), str(destino)], cwd=raiz, capture_output=True, text=True, check=False)
    if r.returncode != 0:
        shutil.move(str(origen), str(destino))
        subprocess.run(['git', 'add', '--', str(destino)], cwd=raiz, capture_output=True, text=True, check=False)


def ejecutar(movimientos, raiz, bandeja, fecha):
    """Mueve lo que haya que mover. Devuelve los movimientos finales (un destino ocupado → pendiente)."""
    finales = []
    for m in movimientos:
        if m.destino is None:
            finales.append(m)
            continue
        destino = raiz / m.destino / m.archivo
        if destino.exists():
            finales.append(m._replace(estado='pendiente', destino=None,
                                      motivo=MOTIVOS['destino_ocupado'].format(destino=f'`{m.destino}/`')))
            continue
        mover(raiz, bandeja / m.archivo, destino)
        finales.append(m)
    escribir_leemes(finales, raiz, fecha)
    return finales


def escribir_leemes(movimientos, raiz, fecha):
    """Un LEEME.md por carpeta destino, con el histórico de lo que llegó y por qué."""
    por_destino = {}
    for m in movimientos:
        if m.destino:
            por_destino.setdefault(m.destino, []).append(m)
    for destino, lista in por_destino.items():
        leeme = raiz / destino / 'LEEME.md'
        if lista[0].estado == 'descartado':
            cabecera = (f'# Descartado el {fecha}\n\nNada de esta carpeta se cargó al catálogo. Los archivos no se '
                        'borran: si alguno sí era de un producto, se vuelve a subir a «up media/» con el código '
                        'en el nombre. Motivo por archivo:\n')
            lineas = [f'- `{m.archivo}`: {m.motivo}.' for m in lista]
        else:
            cabecera = (f'# {destino}: originales ya procesados\n\nLos movió `scripts/procesar_up_media.py` desde '
                        '«up media/». No se editan ni se borran a mano: el catálogo se regenera leyendo de aquí. '
                        'Si pesan demasiado, `scripts/archivar_fuentes.sh` los pasa a R2 (docs/OPERACION.md).\n')
            lineas = [f'- `{m.archivo}`' + (f' → {m.producto}' if m.producto else '') + f' — {m.motivo}.'
                      for m in lista]
        texto = leeme.read_text(encoding='utf-8') if leeme.exists() else cabecera
        leeme.write_text(texto.rstrip('\n') + f'\n\n## {fecha}\n\n' + '\n'.join(lineas) + '\n', encoding='utf-8')
        # Al índice, como los archivos movidos: un commit a mano (sin `git add -A`) no lo deja fuera.
        subprocess.run(['git', 'add', '--', str(leeme)], cwd=raiz, capture_output=True, text=True, check=False)


def resumen(movimientos, fecha):
    """Texto de «up media/RESUMEN.md», para la dueña: qué pasó con cada archivo."""
    por_estado = {e: [m for m in movimientos if m.estado == e]
                  for e in ('cargado', 'conservado', 'descartado', 'pendiente')}
    excel = [m for m in por_estado['cargado'] if Path(m.archivo).suffix.lower() in EXTENSIONES_EXCEL]
    fotos = [m for m in por_estado['cargado'] if m not in excel]
    lineas = [
        '# up media: qué pasó con lo que subiste',
        '',
        f'Procesado el {fecha} por `scripts/procesar_up_media.py` (lo corre GitHub solo, con cada subida: '
        '`.github/workflows/up-media.yml`; cómo leer esto: `docs/OPERACION.md` › «Cómo subir fotos»).',
        '',
        'Cómo funciona esta carpeta: aquí solo queda lo **pendiente**. Lo que ya se cargó al catálogo está en '
        '`fuentes/<carga>/` y lo que no era de ningún producto, en `descartado/<fecha>/` (con el motivo en su '
        'LEEME.md). El catálogo se escribe a mano: cómo y qué preguntas siguen abiertas, en `docs/CATALOGO.md`.',
        '',
        '## Excel cargados',
        '',
        *([f'- `{m.archivo}` → {m.producto}; ahora en `{m.destino}/`.' for m in excel] or ['- Ninguno.']),
        '',
        '## Fotos cargadas: a qué producto fue cada una',
        '',
        '| Foto | Producto | Cómo se asignó | Ahora está en |',
        '|---|---|---|---|',
        *([f'| `{m.archivo}` | {m.producto} | {m.motivo} | `{m.destino}/` |' for m in fotos]
          or ['| — | — | — | — |']),
        '',
        '## Lo que no se asignó y por qué',
        '',
        '### Se queda aquí, pendiente de alguien',
        '',
        *([f'- `{m.archivo}`: {m.motivo}.' for m in por_estado['pendiente']] or ['- Nada pendiente.']),
        '',
        '### Se guardó sin cargar (no es foto de producto)',
        '',
        *([f'- `{m.archivo}` → `{m.destino}/`: {m.motivo}.' for m in por_estado['conservado']] or ['- Nada.']),
        '',
        '### Descartado',
        '',
        *([f'- `{m.archivo}` → `{m.destino}/`: {m.motivo}.' for m in por_estado['descartado']] or ['- Nada.']),
        '',
        '## Cómo subir más',
        '',
        '- Fotos de los productos: por ahora se ponen a mano en Odoo (Inventario › Productos › la foto del '
        'producto). Si las subes aquí, con el código en el nombre (`NAT-M.jpg`, `NAT-M_2.jpg`…), quedan guardadas y '
        'anotadas como pendientes.',
        '- Un Excel nuevo queda pendiente hasta que el programador registre cómo se lee.',
        '',
    ]
    return '\n'.join(lineas)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Procesa la bandeja «up media/» y escribe RESUMEN.md.')
    parser.add_argument('--simular', action='store_true', help='no mueve nada: imprime lo que haría')
    parser.add_argument('--fecha', default=None, help='fecha de proceso (AAAA-MM-DD); por defecto, hoy en Panamá')
    args = parser.parse_args(argv)
    fecha = args.fecha or hoy()

    resultado = importador.main()
    entradas = [e for e in ORIGEN.iterdir()] if ORIGEN.is_dir() else []
    movimientos = clasificar(entradas, resultado, fecha)
    if args.simular:
        print(resumen(movimientos, fecha))
        return 0
    finales = ejecutar(movimientos, RAIZ, ORIGEN, fecha)
    # El RESUMEN se reescribe siempre: lo pendiente también cambia aunque no se mueva nada.
    ORIGEN.mkdir(parents=True, exist_ok=True)
    (ORIGEN / RESUMEN).write_text(resumen(finales, fecha), encoding='utf-8')
    subprocess.run(['git', 'add', '--', str(ORIGEN / RESUMEN)], cwd=RAIZ,
                   capture_output=True, text=True, check=False)
    conteo = {e: sum(1 for m in finales if m.estado == e) for e in ('cargado', 'conservado', 'descartado', 'pendiente')}
    print(f'up media: {conteo["cargado"]} cargados, {conteo["conservado"]} conservados, '
          f'{conteo["descartado"]} descartados, {conteo["pendiente"]} pendientes.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
