"""El favicon y los íconos de la app instalable, hechos de la imagen que subió la empresa.

La misma geometría que ``scripts/iconos_de_la_marca.py`` usa con el logo de fábrica (2026-10-22: «estrictamente el
logo»), pero para cualquier forma (cuadrada o alargada): el dibujo entero, centrado y sin deformar.

* ``any`` (favicon y manifiesto): fondo transparente, el dibujo ocupa el 94 % del lado.
* ``maskable`` (Android lo recorta en círculo o en gota): sobre blanco y dentro del círculo de radio 40 %.
* ``apple`` (iPhone, que pinta de negro lo transparente): sobre blanco, sin transparencia, al 86 %.

La imagen se abre con las herramientas de Odoo (``ImageProcess``: tope de megapíxeles y la orientación de la foto);
lo transparente de los bordes se recorta antes de medir.
"""
import io
import math

from PIL import Image

from odoo.tools.image import ImageProcess

BLANCO = (255, 255, 255, 255)
TRANSPARENTE = (0, 0, 0, 0)

# nombre → (lado, uso)
ICONOS = {
    'icono-192.png': (192, 'any'),
    'icono-512.png': (512, 'any'),
    'icono-maskable-192.png': (192, 'maskable'),
    'icono-maskable-512.png': (512, 'maskable'),
    'apple-touch-icon.png': (180, 'apple'),
}


def abrir(fuente):
    """La imagen (``bytes``) como RGBA, derecha y sin bordes transparentes. ``ValueError`` si no es una imagen que se
    pueda achicar (por ejemplo, un SVG)."""
    if not fuente or fuente[:1] == b'<' or fuente.lstrip()[:1] == b'<':
        raise ValueError('svg')
    imagen = ImageProcess(fuente).image
    if not imagen:   # Odoo no procesa WebP: se abre aquí mismo
        imagen = Image.open(io.BytesIO(fuente))
    imagen = imagen.convert('RGBA')
    caja = imagen.getchannel('A').getbbox()
    return imagen.crop(caja) if caja else imagen


def componer(imagen, lado, uso):
    """``imagen`` (RGBA) entera y centrada en un cuadrado de ``lado`` píxeles, según su ``uso``. Devuelve PNG."""
    ancho, alto = imagen.size
    if uso == 'maskable':
        escala = 0.8 * lado / math.hypot(ancho, alto)
    else:
        escala = (0.94 if uso == 'any' else 0.86) * lado / max(ancho, alto)
    medida = (max(1, round(ancho * escala)), max(1, round(alto * escala)))
    reducida = imagen.resize(medida, Image.LANCZOS)
    lienzo = Image.new('RGBA', (lado, lado), TRANSPARENTE if uso == 'any' else BLANCO)
    lienzo.alpha_composite(reducida, ((lado - medida[0]) // 2, (lado - medida[1]) // 2))
    if uso != 'any':
        lienzo = lienzo.convert('RGB')
    salida = io.BytesIO()
    lienzo.save(salida, format='PNG', optimize=True)
    return salida.getvalue()


def icono(fuente, nombre):
    """El PNG ``nombre`` (uno de ``ICONOS``) hecho de ``fuente``."""
    lado, uso = ICONOS[nombre]
    return componer(abrir(fuente), lado, uso)
