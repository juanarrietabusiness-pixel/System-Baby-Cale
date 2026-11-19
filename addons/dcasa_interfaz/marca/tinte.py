"""El tinte del panel: el CSS ya compilado (y los íconos SVG de las apps) con los colores de una empresa.

Por qué así y no con variables CSS. Los colores de fábrica (el navy de la tinta y el naranja del relleno, la marca de
Baby Caleb) no viven en un solo lugar: están en ``--dc-*`` (tokens propios), pero también escritos a mano en las hojas
de varios módulos y, sobre todo, **calculados al compilar** por Bootstrap y Odoo (``.btn-primary`` y su color al pasar
el puntero, el foco de los campos, la pestaña activa de Ajustes, la barra de estado, el compositor del chat…): cientos
de reglas con el color ya convertido en número. Una variable CSS inyectada no llega a esas. Pintar la hoja compilada
sí: se cambia cada color de la familia del principal y de la del acento por su par con los colores de la empresa
(``colores.Giro`` y ``colores.GiroDelAcento``), **sin recompilar nada**, y la hoja resultante reemplaza a la original en
la página, con la cascada intacta (mismas reglas, mismo orden).

Lo que NO se pinta, a propósito: las paletas de categorías que la persona elige (colores del calendario, de las
etiquetas y de las tarjetas del kanban) y los colores del contenido de la web (``o_cc*``, ``o-color-*``): son datos,
no la marca.
"""
import re

from . import colores as C

_FABRICA_ACENTO = C.a_rgb(C.FABRICA_ACENTO)

# Un color dentro de una declaración: #hex (3, 4, 6 u 8), rgb()/rgba() con comas, %23hex dentro de un SVG en data: y
# el trío «--algo-rgb: r, g, b» con que Bootstrap arma sus transparencias.
_COLOR = re.compile(
    r'(?P<pct>%23)(?P<ph>[0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![0-9a-fA-F])'
    r'|#(?P<h>[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{3})(?![\w-])'
    r'|(?P<fn>rgba?)\(\s*(?P<r>\d{1,3})\s*,\s*(?P<g>\d{1,3})\s*,\s*(?P<b>\d{1,3})\s*(?P<a>,\s*[\d.]+%?\s*)?\)'
    r'|(?P<trio>--[\w-]*rgb\s*:\s*)(?P<tr>\d{1,3})(?P<s1>\s*,\s*)(?P<tg>\d{1,3})(?P<s2>\s*,\s*)(?P<tb>\d{1,3})'
)
# Una regla: lo que va entre la última llave y «{», y su cuerpo. Las de adentro de un @media salen igual (la cabecera
# del @media queda fuera de toda coincidencia y no se toca).
_REGLA = re.compile(r'([^{}]*)\{([^{}]*)\}')
# Paletas de categorías y colores del contenido de la web: no son la marca.
_INTOCABLES = re.compile(
    r'o_calendar_color|o_cw_filter_color|o_colorlist|o_tag_color|o_kanban_color|o_color_\d|o_cc\d|o_colored_level'
    r'|bg-o-color|text-o-color|o_theme_preview|o_configurator|o_website_loader')
_PROTEGIDAS = re.compile(r'--(?:o-color-\d+|o-cc\d[\w-]*)\s*:[^;}]*')


class Tinte:
    """Los colores de una empresa: ``css(texto)`` y ``svg(texto)`` los aplican; con los de fábrica no cambia nada."""

    def __init__(self, principal=None, acento=None):
        self.principal = C.normalizar(principal) or C.FABRICA_PRINCIPAL
        self.acento = C.normalizar(acento) or C.FABRICA_ACENTO
        fabrica = self.principal == C.FABRICA_PRINCIPAL and self.acento == C.FABRICA_ACENTO
        self._giro = C.Giro(self.principal) if self.principal != C.FABRICA_PRINCIPAL else None
        # La familia del acento gira también si solo cambia el principal: sus rellenos llevan la letra del principal.
        self._giro_acento = None if fabrica else C.GiroDelAcento(self.acento, self.principal)
        self._acento = C.a_rgb(self.acento)

    @property
    def de_fabrica(self):
        return not self._giro and not self._giro_acento

    def color(self, rgb):
        """El par de ``rgb`` con estos colores, o ``None`` si se queda igual."""
        rgb = tuple(int(c) for c in rgb[:3])
        if self.de_fabrica:
            return None
        if max(abs(a - b) for a, b in zip(rgb, _FABRICA_ACENTO, strict=True)) <= 2:
            return self._acento
        for giro in (self._giro_acento, self._giro):
            if giro:
                nuevo = giro(rgb)
                if nuevo != rgb:
                    return nuevo
        return None

    # --- Reemplazos ---------------------------------------------------------------------------------------------------

    def _uno(self, hallado):
        if hallado.group('pct'):
            cifras = hallado.group('ph')
            nuevo = self.color(_de_cifras(cifras))
            return hallado.group(0) if nuevo is None else '%23' + C.a_hexa(nuevo)[1:]
        if hallado.group('h'):
            cifras = hallado.group('h')
            nuevo = self.color(_de_cifras(cifras))
            if nuevo is None:
                return hallado.group(0)
            alfa = cifras[6:8] if len(cifras) == 8 else (cifras[3] * 2 if len(cifras) == 4 else '')
            return C.a_hexa(nuevo) + alfa
        if hallado.group('fn'):
            nuevo = self.color((int(hallado.group('r')), int(hallado.group('g')), int(hallado.group('b'))))
            if nuevo is None:
                return hallado.group(0)
            return f'{hallado.group("fn")}({nuevo[0]}, {nuevo[1]}, {nuevo[2]}{hallado.group("a") or ""})'
        nuevo = self.color((int(hallado.group('tr')), int(hallado.group('tg')), int(hallado.group('tb'))))
        if nuevo is None:
            return hallado.group(0)
        return (f'{hallado.group("trio")}{nuevo[0]}{hallado.group("s1")}{nuevo[1]}{hallado.group("s2")}'
                f'{nuevo[2]}')

    def _cuerpo(self, cuerpo):
        protegidas = [(p.start(), p.end()) for p in _PROTEGIDAS.finditer(cuerpo)]

        def cambiar(hallado):
            if any(inicio <= hallado.start() < fin for inicio, fin in protegidas):
                return hallado.group(0)
            return self._uno(hallado)
        return _COLOR.sub(cambiar, cuerpo)

    def css(self, texto):
        """La hoja con estos colores. Cada regla conserva su lugar: la cascada no cambia."""
        if self.de_fabrica:
            return texto

        def regla(hallada):
            selector, cuerpo = hallada.group(1), hallada.group(2)
            if _INTOCABLES.search(selector):
                return hallada.group(0)
            return f'{selector}{{{self._cuerpo(cuerpo)}}}'
        return _REGLA.sub(regla, texto)

    def svg(self, texto):
        """Un dibujo SVG (los íconos de las apps) con estos colores."""
        if self.de_fabrica:
            return texto
        return _COLOR.sub(self._uno, texto)


def _de_cifras(cifras):
    if len(cifras) in (3, 4):
        cifras = ''.join(c * 2 for c in cifras[:3])
    return (int(cifras[0:2], 16), int(cifras[2:4], 16), int(cifras[4:6], 16))
