"""Colores de la marca del panel: leerlos, medir su contraste, comprobar que se leen y girar la paleta.

Python puro. Contraste y luz según WCAG 2.1 (la luz relativa va de 0, negro, a 1, blanco).

**La fábrica es Baby Caleb** (pedido del dueño, 2026-11-19, ``docs/MARCA_BABY_CALEB.md``): el panel sale de fábrica en
crema, navy, naranja y verde salvia. Hay dos colores de marca, y cada uno arrastra a su familia:

* **El principal es la tinta** (navy ``#1B3246``, el ``fg`` de Baby Caleb): la letra, los títulos, los enlaces, los
  íconos, el aro de foco y lo oscuro de la marca, con toda su escala (``--dc-azul-600…950`` de ``tokens.scss``: los
  nombres vienen de la plantilla de D'CASA y se quedan). Va como letra sobre el crema y lleva letra clara encima.
* **El acento es el relleno** (naranja ``#EE924A``, el ``accent``): el botón principal, lo elegido, las barras y los
  puntos, con sus tonos para letra (``#985D2F``) y para bordes (``#C3783D``). **Nunca es letra ni borde**: encima lleva
  la letra en el principal (``accent-fg`` es el navy).

**El giro de la paleta** (``Giro`` y ``GiroDelAcento``). Para pintar el panel con los colores de una empresa, cada
color de la familia del principal de fábrica se lleva a la familia del principal de la empresa, y lo mismo con el
acento, con la misma regla:

* el **tono** gira lo mismo que gira el color de fábrica hasta el de la empresa;
* la **saturación** se escala en la misma proporción (un principal gris deja todo gris);
* la **luz**: lo más oscuro que el color de fábrica se escala en proporción; lo más claro se reparte entre ese color y
  el blanco (los tonos suaves siguen siendo suaves);
* y unas redes: lo que en fábrica se leía como letra sobre la superficie crema se sigue leyendo (4.5:1), lo que se veía
  como borde o ícono se sigue viendo (3:1) y los rellenos que llevaban la letra del principal encima la siguen llevando
  (4.5:1 con el principal nuevo).

Con los colores de fábrica el giro es la identidad; y el color de fábrica va a dar exactamente al elegido.

**Lo que no es de la marca no gira**: los neutros (las líneas, la letra de apoyo, los bordes de los campos) se escriben
en tonos casi grises a propósito, y la superficie del modo oscuro también: con otro principal, el oscuro sigue siendo
oscuro y la letra de apoyo sigue siendo gris.
"""
import colorsys
import re

FABRICA_PRINCIPAL = '#1B3246'   # navy: la tinta
FABRICA_ACENTO = '#EE924A'      # naranja: el relleno
BLANCO = '#FFFFFF'
CREMA = '#F9F6ED'               # el fondo de la página (bg)
SUPERFICIE = '#F2EFE5'          # tarjetas, barras y hojas (surface): el claro más oscuro sobre el que va letra
# Lo que va escrito encima del acento: la letra en el principal (en Baby Caleb, `accent-fg` es el mismo navy).
OSCURO_DE_FABRICA = FABRICA_PRINCIPAL
# Los de la plantilla de origen (D'CASA). Una base instalada antes del 2026-11-19 los tiene guardados como «de
# fábrica»; la migración de dcasa_interfaz 19.0.1.4.0 los pasa a los de ahora (si no, el panel se pintaría de azul).
DCASA_PRINCIPAL = '#1340B1'
DCASA_ACENTO = '#FED00F'

MINIMO_TEXTO = 4.5      # WCAG AA, letra normal
MINIMO_DETALLE = 3.0    # WCAG 1.4.11: puntos, íconos y bordes que no son letra

# Qué colores son «de la familia» de cada uno: tono a menos de VENTANA grados del de fábrica y saturación (HSL) de al
# menos SATURACION. Medido sobre el CSS compilado del panel (2026-11-19): el navy y sus sombras tienen 41–45 %; los
# grises de Bootstrap y de Odoo, la letra de apoyo (#475967, #5E6D78), los bordes de los campos (#7F8A91) y las
# superficies del modo oscuro (#0F161C, #162129…), 7–30 %, y esos se quedan como están. Los naranjas de la marca tienen
# 53–83 %; el ámbar de los avisos (#FFAC00) está a 14° y tampoco se toca.
VENTANA = 12
SATURACION = 0.36
VENTANA_ACENTO = 10
SATURACION_ACENTO = 0.45

_HEXA = re.compile(r'#?([0-9a-fA-F]{6}|[0-9a-fA-F]{3})')


def normalizar(texto):
    """``'#1b3246'``, ``'1B3246'`` o ``'#13b'`` → ``'#1B3246'``; vacío → ``None``. Si no es un color: ``ValueError``."""
    if texto is None or texto is False:
        return None
    texto = str(texto).strip()
    if not texto:
        return None
    hallado = _HEXA.fullmatch(texto)
    if not hallado:
        raise ValueError(f'«{texto}» no es un color. Escríbelo como #1B3246: un numeral y seis cifras o letras '
                         'de la A a la F.')
    cifras = hallado.group(1)
    if len(cifras) == 3:
        cifras = ''.join(c * 2 for c in cifras)
    return '#' + cifras.upper()


def a_rgb(color):
    """``'#1B3246'`` → ``(27, 50, 70)``. Acepta también una tupla (la devuelve tal cual, en enteros)."""
    if isinstance(color, (tuple, list)):
        return tuple(int(round(c)) for c in color[:3])
    color = normalizar(color)
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


def a_hexa(rgb):
    return '#' + ''.join(f'{max(0, min(255, int(round(c)))):02X}' for c in rgb[:3])


def luz(color):
    """La luz relativa (WCAG): 0 el negro, 1 el blanco."""
    def canal(valor):
        valor /= 255
        return valor / 12.92 if valor <= 0.03928 else ((valor + 0.055) / 1.055) ** 2.4
    r, g, b = a_rgb(color)
    return 0.2126 * canal(r) + 0.7152 * canal(g) + 0.0722 * canal(b)


def contraste(uno, otro):
    """De 1 (iguales) a 21 (blanco y negro)."""
    a, b = luz(uno), luz(otro)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def hsl(color):
    """(tono en grados, saturación 0–1, luminosidad 0–1)."""
    r, g, b = (c / 255 for c in a_rgb(color))
    tono, luminosidad, saturacion = colorsys.rgb_to_hls(r, g, b)
    return tono * 360, saturacion, luminosidad


def distancia_de_tono(uno, otro):
    diferencia = abs(uno - otro) % 360
    return min(diferencia, 360 - diferencia)


def con_luz(tono, saturacion, objetivo, como_mucho=False, como_poco=False):
    """El color de ese tono y esa saturación cuya luz relativa es ``objetivo`` (la luminosidad se busca a tientas: la
    luz crece con ella). Con ``como_mucho``, el más cercano que no la pasa; con ``como_poco``, el más cercano que llega
    (para no perder contraste al redondear)."""
    def color(luminosidad):
        r, g, b = colorsys.hls_to_rgb((tono % 360) / 360, luminosidad, saturacion)
        return tuple(int(round(c * 255)) for c in (r, g, b))
    abajo, arriba = 0.0, 1.0
    for _vuelta in range(32):
        medio = (abajo + arriba) / 2
        if luz(color(medio)) <= objetivo:
            abajo = medio
        else:
            arriba = medio
    debajo, encima = color(abajo), color(arriba)
    if como_mucho:
        return debajo
    if como_poco:
        return encima
    if abs(luz(debajo) - objetivo) <= abs(luz(encima) - objetivo):
        return debajo
    return encima


def oscurecer_hasta(color, contra=SUPERFICIE, minimo=MINIMO_TEXTO):
    """El mismo tono, más oscuro, hasta llegar a ``minimo``:1 contra ``contra`` (que es el más claro de los dos)."""
    tono, saturacion, _luminosidad = hsl(color)
    objetivo = (luz(contra) + 0.05) / minimo - 0.05
    for _vuelta in range(50):
        candidato = con_luz(tono, saturacion, max(0.0, objetivo))
        if contraste(candidato, contra) >= minimo:
            return a_hexa(candidato)
        objetivo -= 0.002
    return '#000000'


def aclarar_hasta(color, contra, minimo=MINIMO_TEXTO):
    """El mismo tono, más claro, hasta llegar a ``minimo``:1 contra ``contra`` (que es el más oscuro). ``None`` si ni el
    más claro de ese tono llega."""
    tono, saturacion, _luminosidad = hsl(color)
    objetivo = minimo * (luz(contra) + 0.05) - 0.05
    for _vuelta in range(50):
        if objetivo > 1:
            return None
        candidato = con_luz(tono, saturacion, objetivo)
        if contraste(candidato, contra) >= minimo:
            return a_hexa(candidato)
        objetivo += 0.002
    return None


def _luz_maxima(contra, minimo):
    """La luz más alta que todavía se distingue a ``minimo``:1 de ``contra`` (más claro), con margen para el redondeo."""
    return (luz(contra) + 0.05) / minimo - 0.05 - 0.002


def _luz_minima(contra, minimo):
    """La luz más baja que todavía se distingue a ``minimo``:1 de ``contra`` (más oscuro), con margen para el redondeo."""
    return minimo * (luz(contra) + 0.05) - 0.05 + 0.002


# La luz más alta que todavía se lee como letra sobre la superficie crema (4.5:1) y la de un borde o ícono (3:1).
LUZ_DE_LETRA = _luz_maxima(SUPERFICIE, MINIMO_TEXTO)
LUZ_DE_DETALLE = _luz_maxima(SUPERFICIE, MINIMO_DETALLE)


def _en_familia(color, de, ventana, saturacion_minima):
    tono, saturacion, _luminosidad = hsl(color)
    return saturacion >= saturacion_minima and distancia_de_tono(tono, hsl(de)[0]) <= ventana


def es_de_la_familia(color):
    """¿Es el principal de fábrica (el navy) o algo que sale de él (más oscuro, más claro, más o menos vivo)?"""
    return _en_familia(color, FABRICA_PRINCIPAL, VENTANA, SATURACION)


def es_de_la_familia_del_acento(color):
    """¿Es el acento de fábrica (el naranja) o uno de sus tonos (el de letra, el de los bordes, el del puntero)?"""
    return _en_familia(color, FABRICA_ACENTO, VENTANA_ACENTO, SATURACION_ACENTO)


class Giro:
    """Lleva cada color de la familia del principal de fábrica a la familia del ``principal`` (ver el docstring del
    módulo).

    Se llama con un ``(r, g, b)`` y devuelve el ``(r, g, b)`` nuevo; lo que no es de la familia vuelve igual."""

    FABRICA = FABRICA_PRINCIPAL

    def __init__(self, principal):
        self.principal = a_rgb(principal)
        self._fabrica = a_rgb(self.FABRICA)
        tono_fabrica, saturacion_fabrica, _luminosidad = hsl(self._fabrica)
        tono, saturacion, _luminosidad = hsl(self.principal)
        self.giro = tono - tono_fabrica
        self.factor = saturacion / saturacion_fabrica
        self.luz = luz(self.principal)
        self._luz_fabrica = luz(self._fabrica)
        self._hechos = {}

    def es_de_la_familia(self, rgb):
        return es_de_la_familia(rgb)

    def limites(self, rgb):
        """``(techo, piso)`` de la luz del color nuevo (``None`` = sin límite): las redes de lectura."""
        # Lo que se leía como letra sobre la superficie crema (o se veía como borde) se sigue leyendo.
        if contraste(rgb, SUPERFICIE) >= MINIMO_TEXTO:
            return LUZ_DE_LETRA, None
        if contraste(rgb, SUPERFICIE) >= MINIMO_DETALLE:
            return LUZ_DE_DETALLE, None
        return None, None

    def __call__(self, rgb):
        rgb = tuple(int(c) for c in rgb[:3])
        if rgb in self._hechos:
            return self._hechos[rgb]
        if rgb == self._fabrica:
            nuevo = self.principal
        elif not self.es_de_la_familia(rgb):
            nuevo = rgb
        else:
            tono, saturacion, _luminosidad = hsl(rgb)
            antes = luz(rgb)
            if antes <= self._luz_fabrica:
                despues = antes * self.luz / self._luz_fabrica
            else:
                despues = self.luz + (antes - self._luz_fabrica) * (1 - self.luz) / (1 - self._luz_fabrica)
            techo, piso = self.limites(rgb)
            como_mucho = como_poco = False
            if techo is not None and despues >= techo:
                despues, como_mucho = techo, True
            if piso is not None and despues <= piso:
                despues, como_poco, como_mucho = piso, True, False
            nuevo = con_luz(tono + self.giro, min(1.0, saturacion * self.factor), despues,
                            como_mucho=como_mucho, como_poco=como_poco)
        self._hechos[rgb] = nuevo
        return nuevo


class GiroDelAcento(Giro):
    """Lo mismo para la familia del acento (el naranja y sus tonos), hacia el ``acento`` de la empresa. Además de las
    redes del principal, los rellenos que llevaban la letra del principal de fábrica encima (4.5:1) la siguen llevando
    con el ``principal`` de la empresa."""

    FABRICA = FABRICA_ACENTO

    def __init__(self, acento, principal=FABRICA_PRINCIPAL):
        super().__init__(acento)
        self._letra = a_rgb(principal)

    def es_de_la_familia(self, rgb):
        return es_de_la_familia_del_acento(rgb)

    def limites(self, rgb):
        techo, piso = super().limites(rgb)
        if contraste(rgb, FABRICA_PRINCIPAL) >= MINIMO_TEXTO:
            piso = _luz_minima(self._letra, MINIMO_TEXTO)
        return techo, piso


# --- Lo que se exige a cada color (lo mismo en Ajustes, al guardar y en Brian) ---------------------------------------

def problema_del_principal(principal):
    """``None`` si el principal se lee; si no, el porqué en palabras sencillas y un color que sí sirve."""
    principal = normalizar(principal)
    if not principal:
        return None
    razon = contraste(principal, SUPERFICIE)
    if razon >= MINIMO_TEXTO:
        return None
    sugerido = oscurecer_hasta(principal)
    return (f'El color principal {principal} es muy claro: es la letra de los títulos y los enlaces sobre el crema del '
            f'panel, y así da {razon:.1f} a 1 (hace falta {MINIMO_TEXTO:g} a 1 para que se lea). Prueba con '
            f'{sugerido}, el mismo tono más oscuro.')


def oscuro_de(principal):
    """El oscuro de la marca con ese principal: la letra que va encima del acento (en Baby Caleb, el principal)."""
    principal = normalizar(principal) or FABRICA_PRINCIPAL
    return a_hexa(Giro(principal)(a_rgb(OSCURO_DE_FABRICA)))


def problema_del_acento(acento, principal):
    """``None`` si el acento lleva bien la letra del principal encima (4.5:1: es el botón principal); si no, el porqué
    y uno que sí sirve."""
    acento = normalizar(acento)
    if not acento:
        return None
    principal = normalizar(principal) or FABRICA_PRINCIPAL
    oscuro = oscuro_de(principal)
    razon = contraste(acento, oscuro)
    if razon >= MINIMO_TEXTO:
        return None
    sugerido = aclarar_hasta(acento, oscuro)
    texto = (f'El color de acento {acento} no se lee: es el relleno del botón principal y lleva encima la letra en el '
             f'color principal ({oscuro}), y da {razon:.1f} a 1 (hace falta {MINIMO_TEXTO:g} a 1). El acento tiene que '
             'ser un color claro y vivo, como el naranja de fábrica.')
    return texto + (f' Prueba con {sugerido}, el mismo tono más claro.' if sugerido else '')


def como_se_lee(principal, acento):
    """Para Ajustes y Brian: cómo van a quedar los pares de letra y fondo con estos colores (o qué falla)."""
    principal = normalizar(principal) or FABRICA_PRINCIPAL
    acento = normalizar(acento) or FABRICA_ACENTO
    problemas = [p for p in (problema_del_principal(principal), problema_del_acento(acento, principal)) if p]
    if problemas:
        return ' '.join(problemas)
    oscuro = oscuro_de(principal)
    return (f'Se lee bien. Títulos, letra y enlaces: el principal sobre el crema del panel, '
            f'{contraste(principal, SUPERFICIE):.1f} a 1. Botón principal: la letra en el principal sobre el acento, '
            f'{contraste(acento, oscuro):.1f} a 1. (Para que se lea hace falta {MINIMO_TEXTO:g} a 1.)')
