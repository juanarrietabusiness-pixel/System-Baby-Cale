"""Colores de la marca del panel: leerlos, medir su contraste, comprobar que se leen y girar la paleta.

Python puro. Contraste y luz según WCAG 2.1 (la luz relativa va de 0, negro, a 1, blanco).

**El giro de la paleta** (``Giro``). El panel de fábrica está hecho con UN azul (``#1340B1``) y todo lo que sale de él:
la escala ``--dc-azul-50…950`` de ``tokens.scss``, los botones, enlaces, focos y fondos suaves que Bootstrap y Odoo
calculan del azul al compilar, los celestes y el azul de los botones del modo oscuro. Para pintar el panel con el
color de una empresa, cada color de esa familia se lleva al color nuevo con la misma regla:

* el **tono** gira lo mismo que gira el principal (de 223° al tono de la empresa);
* la **saturación** se escala en la misma proporción (un principal gris deja todo gris);
* la **luz**: lo más oscuro que el azul se escala en proporción (el marino sigue siendo «más oscuro que el
  principal»); lo más claro se reparte entre el principal y el blanco (los fondos suaves siguen siendo suaves).
* y una red: lo que en fábrica se leía con letra blanca encima (o como letra sobre blanco: es lo mismo, el contraste
  es simétrico) se sigue leyendo, aunque el principal sea más claro que el azul.

Con el principal de fábrica el giro es la identidad; y el azul de fábrica va a dar exactamente al principal elegido.
"""
import colorsys
import re

FABRICA_PRINCIPAL = '#1340B1'
FABRICA_ACENTO = '#FED00F'
BLANCO = '#FFFFFF'
# El oscuro de la marca que lleva el acento encima (insignias, números en amarillo sobre marino) y que va de letra sobre
# el acento: el azul-800 de tokens.scss, el más claro de los oscuros que se usan con el acento.
OSCURO_DE_FABRICA = '#0E2A6B'

MINIMO_TEXTO = 4.5      # WCAG AA, letra normal
MINIMO_DETALLE = 3.0    # WCAG 1.4.11: puntos, íconos y bordes que no son letra

# Qué colores son «de la familia» del azul: tono a menos de VENTANA grados de 223° y saturación (HSL) de al menos
# SATURACION. Medido sobre el CSS compilado del panel (2026-11-18): la escala de la marca tiene 73–86 %, los grises
# fríos de Odoo y de D'CASA (líneas, niebla, la letra gris) 14–43 %, y esos se quedan como están.
VENTANA = 12
SATURACION = 0.45

_HEXA = re.compile(r'#?([0-9a-fA-F]{6}|[0-9a-fA-F]{3})')


def normalizar(texto):
    """``'#1340b1'``, ``'1340B1'`` o ``'#13b'`` → ``'#1340B1'``; vacío → ``None``. Si no es un color: ``ValueError``."""
    if texto is None or texto is False:
        return None
    texto = str(texto).strip()
    if not texto:
        return None
    hallado = _HEXA.fullmatch(texto)
    if not hallado:
        raise ValueError(f'«{texto}» no es un color. Escríbelo como #1340B1: un numeral y seis cifras o letras '
                         'de la A a la F.')
    cifras = hallado.group(1)
    if len(cifras) == 3:
        cifras = ''.join(c * 2 for c in cifras)
    return '#' + cifras.upper()


def a_rgb(color):
    """``'#1340B1'`` → ``(19, 64, 177)``. Acepta también una tupla (la devuelve tal cual, en enteros)."""
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


def con_luz(tono, saturacion, objetivo, como_mucho=False):
    """El color de ese tono y esa saturación cuya luz relativa es ``objetivo`` (la luminosidad se busca a tientas: la
    luz crece con ella). Con ``como_mucho``, el más cercano que no la pasa (para no perder contraste al redondear)."""
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
    if como_mucho or abs(luz(debajo) - objetivo) <= abs(luz(encima) - objetivo):
        return debajo
    return encima


def oscurecer_hasta(color, contra=BLANCO, minimo=MINIMO_TEXTO):
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


_FABRICA = a_rgb(FABRICA_PRINCIPAL)
_FABRICA_HSL = hsl(_FABRICA)
_FABRICA_LUZ = luz(_FABRICA)
# La luz más alta que todavía se lee con letra blanca encima (o como letra sobre blanco) a 4.5:1, con un margen para el
# redondeo a enteros.
LUZ_CON_BLANCO = 1.05 / MINIMO_TEXTO - 0.05 - 0.002


def es_de_la_familia(color):
    """¿Es el azul de la marca o algo que sale de él (más claro, más oscuro, más o menos vivo)?"""
    tono, saturacion, _luminosidad = hsl(color)
    return saturacion >= SATURACION and distancia_de_tono(tono, _FABRICA_HSL[0]) <= VENTANA


class Giro:
    """Lleva cada color de la familia del azul de fábrica a la familia del ``principal`` (ver el docstring del módulo).

    Se llama con un ``(r, g, b)`` y devuelve el ``(r, g, b)`` nuevo; lo que no es de la familia vuelve igual."""

    def __init__(self, principal):
        self.principal = a_rgb(principal)
        tono, saturacion, _luminosidad = hsl(self.principal)
        self.giro = tono - _FABRICA_HSL[0]
        self.factor = saturacion / _FABRICA_HSL[1]
        self.luz = luz(self.principal)
        self._hechos = {}

    def __call__(self, rgb):
        rgb = tuple(int(c) for c in rgb[:3])
        if rgb in self._hechos:
            return self._hechos[rgb]
        if rgb == _FABRICA:
            nuevo = self.principal
        elif not es_de_la_familia(rgb):
            nuevo = rgb
        else:
            tono, saturacion, _luminosidad = hsl(rgb)
            antes = luz(rgb)
            if antes <= _FABRICA_LUZ:
                despues = antes * self.luz / _FABRICA_LUZ
            else:
                despues = self.luz + (antes - _FABRICA_LUZ) * (1 - self.luz) / (1 - _FABRICA_LUZ)
            # Lo que se leía con letra blanca (o sobre blanco) se sigue leyendo.
            se_leia = antes <= LUZ_CON_BLANCO
            if se_leia:
                despues = min(despues, LUZ_CON_BLANCO)
            nuevo = con_luz(tono + self.giro, min(1.0, saturacion * self.factor), despues, como_mucho=se_leia)
        self._hechos[rgb] = nuevo
        return nuevo


# --- Lo que se exige a cada color (lo mismo en Ajustes, al guardar y en Brian) ---------------------------------------

def problema_del_principal(principal):
    """``None`` si el principal se lee; si no, el porqué en palabras sencillas y un color que sí sirve."""
    principal = normalizar(principal)
    if not principal:
        return None
    razon = contraste(principal, BLANCO)
    if razon >= MINIMO_TEXTO:
        return None
    sugerido = oscurecer_hasta(principal)
    return (f'El color principal {principal} es muy claro: va en los botones con letra blanca encima y en los enlaces '
            f'sobre blanco, y así da {razon:.1f} a 1 (hace falta {MINIMO_TEXTO:g} a 1 para que se lea). Prueba con '
            f'{sugerido}, el mismo tono más oscuro.')


def oscuro_de(principal):
    """El oscuro de la marca con ese principal: el que lleva el acento encima y va de letra sobre el acento."""
    principal = normalizar(principal) or FABRICA_PRINCIPAL
    return a_hexa(Giro(principal)(a_rgb(OSCURO_DE_FABRICA)))


def problema_del_acento(acento, principal):
    """``None`` si el acento se lee sobre el oscuro de la marca (4.5:1, va de letra y lleva letra oscura) y se distingue
    sobre el principal (3:1, puntos y detalles); si no, el porqué y uno que sí sirve."""
    acento = normalizar(acento)
    if not acento:
        return None
    principal = normalizar(principal) or FABRICA_PRINCIPAL
    oscuro = oscuro_de(principal)
    sobre_oscuro = contraste(acento, oscuro)
    sobre_principal = contraste(acento, principal)
    if sobre_oscuro >= MINIMO_TEXTO and sobre_principal >= MINIMO_DETALLE:
        return None
    sugerido = aclarar_hasta(acento, oscuro)
    if sugerido and contraste(sugerido, principal) < MINIMO_DETALLE:
        sugerido = aclarar_hasta(acento, principal, MINIMO_DETALLE)
    texto = (f'El color de acento {acento} no se lee: el acento va sobre el oscuro de tu marca ({oscuro}) y con letra '
             f'oscura encima, y da {sobre_oscuro:.1f} a 1 (hace falta {MINIMO_TEXTO:g} a 1); sobre el principal da '
             f'{sobre_principal:.1f} a 1 (hace falta {MINIMO_DETALLE:g} a 1). El acento tiene que ser un color claro y '
             'vivo, como el amarillo de fábrica.')
    return texto + (f' Prueba con {sugerido}, el mismo tono más claro.' if sugerido else '')


def como_se_lee(principal, acento):
    """Para Ajustes y Brian: cómo van a quedar los pares de letra y fondo con estos colores (o qué falla)."""
    principal = normalizar(principal) or FABRICA_PRINCIPAL
    acento = normalizar(acento) or FABRICA_ACENTO
    problemas = [p for p in (problema_del_principal(principal), problema_del_acento(acento, principal)) if p]
    if problemas:
        return ' '.join(problemas)
    oscuro = oscuro_de(principal)
    return (f'Se lee bien. Botones y enlaces: letra blanca sobre el principal y el principal sobre blanco, '
            f'{contraste(principal, BLANCO):.1f} a 1. Acento: sobre el oscuro de tu marca ({oscuro}) y con letra '
            f'oscura encima, {contraste(acento, oscuro):.1f} a 1. (Para que se lea hace falta {MINIMO_TEXTO:g} a 1.)')
