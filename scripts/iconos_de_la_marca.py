"""Íconos de la pantalla de inicio y favicon, hechos del logo de la marca: python scripts/iconos_de_la_marca.py

Pedido de la dueña (2026-10-22): «el ícono que se crea cuando se guarda la página o panel administrativo en los
celulares en pantallas de inicio debe ser estrictamente el logo». Todos salen de
``addons/dcasa_base/static/img/logo.png`` (el de la empresa, el sitio y los correos), tal cual: centrado, entero (sin
recortar) y del mismo tamaño en proporción.

* ``logo-192.png`` y ``logo-512.png``: solo el logo, con fondo transparente (manifiesto «any», favicon).
* ``logo-maskable-192.png`` y ``logo-maskable-512.png``: sobre blanco y dentro de la zona segura (el círculo del 80 %),
  para que Android lo recorte en círculo o en gota sin cortarle nada.
* ``apple-touch-icon.png`` (180 × 180): sobre blanco, sin transparencia (el iPhone pinta de negro lo transparente) y
  con margen para las esquinas redondas del iPhone.
* ``addons/website_dcasa/static/src/img/favicon.png``: el mismo de 512 transparente, del que Odoo saca el favicon del
  sitio.
* ``addons/website_dcasa/static/src/img/logo-200.webp`` y ``logo-400.webp``: el logo de la cabecera del sitio en WebP,
  de 200 y 400 px de ancho (1x y 2x), con su proporción (``website_dcasa.logo_webp_dcasa`` lleva el ancho y el alto).

Si cambia el logo, se vuelve a correr y se suben las imágenes nuevas.
"""
import math
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
LOGO = RAIZ / 'addons/dcasa_base/static/img/logo.png'
CARPETA = RAIZ / 'addons/dcasa_base/static/img/icono'
FAVICON_DEL_SITIO = RAIZ / 'addons/website_dcasa/static/src/img/favicon.png'
LOGO_DE_LA_CABECERA = RAIZ / 'addons/website_dcasa/static/src/img/logo-{ancho}.webp'
BLANCO = (255, 255, 255, 255)

# Zona segura de un ícono «maskable»: un círculo de radio 40 % del lado (Android lo recorta en círculo o en gota).
ZONA_SEGURA = 0.4
# (archivo, lado en píxeles, ancho del logo sobre el lado o ZONA_SEGURA, fondo o None si es transparente)
ICONOS = (
    ('logo-192.png', 192, 0.94, None),
    ('logo-512.png', 512, 0.94, None),
    ('logo-maskable-192.png', 192, ZONA_SEGURA, BLANCO),
    ('logo-maskable-512.png', 512, ZONA_SEGURA, BLANCO),
    ('apple-touch-icon.png', 180, 0.86, BLANCO),
)


def ancho_en_zona_segura(logo):
    """El ancho (sobre el lado) con el que el logo entero cae dentro del círculo de la zona segura: su esquina queda
    a la mitad de su diagonal del centro. Sale de la proporción del logo (con el de D'CASA, 892 × 405, daba 0,72; con
    uno cuadrado, 0,56), con dos decimales hacia abajo."""
    return math.floor(2 * ZONA_SEGURA / math.hypot(1, logo.height / logo.width) * 100) / 100


def componer(logo, lado, ancho_relativo, fondo):
    """El logo, entero y centrado, en un cuadrado de ``lado`` píxeles."""
    ancho = round(lado * ancho_relativo)
    alto = round(ancho * logo.height / logo.width)
    reducido = logo.resize((ancho, alto), Image.LANCZOS)
    lienzo = Image.new('RGBA', (lado, lado), fondo or (0, 0, 0, 0))
    lienzo.alpha_composite(reducido, ((lado - ancho) // 2, (lado - alto) // 2))
    return lienzo.convert('RGB') if fondo else lienzo


def main():
    logo = Image.open(LOGO).convert('RGBA')
    CARPETA.mkdir(exist_ok=True)
    for archivo, lado, ancho, fondo in ICONOS:
        relativo = ancho_en_zona_segura(logo) if ancho == ZONA_SEGURA else ancho
        componer(logo, lado, relativo, fondo).save(CARPETA / archivo, optimize=True)
        print(f'{CARPETA.relative_to(RAIZ) / archivo}')
    componer(logo, 512, 0.94, None).save(FAVICON_DEL_SITIO, optimize=True)
    print(FAVICON_DEL_SITIO.relative_to(RAIZ))
    for ancho in (200, 400):
        destino = Path(str(LOGO_DE_LA_CABECERA).format(ancho=ancho))
        alto = round(ancho * logo.height / logo.width)
        logo.resize((ancho, alto), Image.LANCZOS).save(destino, 'WEBP', quality=90, method=6)
        print(f'{destino.relative_to(RAIZ)} ({ancho} × {alto})')


if __name__ == '__main__':
    main()
