"""Los pares de color del pago, con la fórmula WCAG (la misma de los informes de Feuxui): texto ≥ 4.5:1, borde de un
campo y ícono ≥ 3:1. Los colores se leen del propio ``pago.scss`` y de los tokens de la marca de ``dcasa.scss`` (no se
copian aquí): si alguien cambia un tono y el par deja de cumplir, esta prueba lo dice. Y la marca de Baby Caleb
(docs/MARCA_BABY_CALEB.md): el pago no usa nada de D'CASA (azul, amarillo, Anton, Oswald, Inter), la letra sobre el
naranja es navy, y no hay degradados ni sombras."""
import re
from pathlib import Path

from odoo.tests import TransactionCase, tagged

SCSS = Path(__file__).resolve().parent.parent / 'static' / 'src' / 'scss'
BLANCO = '#FFFFFF'
NAVY = '#1B3246'
NARANJA = '#EE924A'


def luminancia(color):
    canales = [int(color.lstrip('#')[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    r, g, b = (c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canales)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a, b):
    claro, oscuro = sorted((luminancia(a), luminancia(b)), reverse=True)
    return (claro + 0.05) / (oscuro + 0.05)


def tokens():
    """Las variables de color de dcasa.scss y de pago.scss (con sus alias), ya resueltas a #RRGGBB."""
    brutos = {}
    for archivo in ('dcasa.scss', 'pago.scss'):
        for nombre, valor in re.findall(r'^\$([a-z0-9-]+):\s*([^;/]+?);', (SCSS / archivo).read_text(), re.M):
            brutos[nombre] = valor.strip()
    resueltos = {}
    for nombre, bruto in brutos.items():
        valor = bruto
        while valor.startswith('$') and valor[1:] in brutos:
            valor = brutos[valor[1:]]
        if re.fullmatch(r'#[0-9A-Fa-f]{6}', valor):
            resueltos[nombre] = valor.upper()
    return resueltos


def mezcla(color, sobre, parte):
    """``color`` al ``parte`` (0 a 1) sobre ``sobre``: como el ``mix()`` de SCSS."""
    a = [int(color.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4)]
    b = [int(sobre.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4)]
    return '#' + ''.join(f'{round(x * parte + y * (1 - parte)):02X}' for x, y in zip(a, b, strict=True))


@tagged('post_install', '-at_install')
class TestContrasteDelPago(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.c = tokens()

    def test_los_tokens_del_pago_existen_y_son_los_de_la_marca(self):
        for nombre in ('pago-tinta', 'pago-gris', 'pago-enlace', 'pago-accion', 'pago-en-accion', 'pago-accion-encima',
                       'pago-filo', 'pago-borde', 'pago-borde-campo', 'pago-elegida', 'pago-encima', 'pago-panel',
                       'pago-campo', 'pago-insignia', 'pago-icono', 'pago-apagado', 'pago-apagado-letra',
                       'pago-error', 'pago-error-fondo'):
            self.assertIn(nombre, self.c, '$' + nombre)
        c = self.c
        # Los de MARCA_BABY_CALEB.md, tal cual.
        self.assertEqual((c['pago-tinta'], c['pago-accion'], c['pago-en-accion']), (NAVY, NARANJA, NAVY),
                         'el botón de pagar: naranja con letra navy')
        self.assertEqual((c['pago-enlace'], c['pago-filo'], c['pago-panel'], c['pago-elegida']),
                         ('#985D2F', '#C3783D', '#F2EFE5', '#F9F6ED'))
        # Los ya mezclados son los de la marca: el naranja al pasar el puntero es el `$bc-accent-hover` de dcasa.scss
        # (mix al 88 % con el crema), y `muted`, `line` y `control` son el navy al 70, 12 y 55 % sobre el crema.
        self.assertEqual(c['pago-accion-encima'], mezcla(NARANJA, c['bc-bg'], .88))
        self.assertEqual(c['pago-gris'], mezcla(NAVY, c['bc-bg'], .70))
        self.assertEqual(c['pago-borde'], mezcla(NAVY, c['bc-bg'], .12))
        self.assertEqual(c['pago-borde-campo'], mezcla(NAVY, c['bc-bg'], .55))
        self.assertEqual(c['pago-encima'], mezcla(c['pago-panel'], c['pago-elegida'], .5))

    def test_todo_texto_llega_a_4_5_a_1(self):
        c = self.c
        pares = [
            ('tinta sobre el crema de la página', c['pago-tinta'], c['bc-bg']),
            ('tinta sobre la superficie (lista y resumen)', c['pago-tinta'], c['pago-panel']),
            ('tinta sobre la fila elegida', c['pago-tinta'], c['pago-elegida']),
            ('tinta sobre la fila bajo el puntero', c['pago-tinta'], c['pago-encima']),
            ('gris sobre el crema (líneas del total, ayuda por WhatsApp)', c['pago-gris'], c['bc-bg']),
            ('gris sobre la superficie', c['pago-gris'], c['pago-panel']),
            ('gris sobre la fila elegida (ayuda del método)', c['pago-gris'], c['pago-elegida']),
            ('gris sobre la fila bajo el puntero', c['pago-gris'], c['pago-encima']),
            ('texto de ejemplo de un campo (placeholder)', c['pago-gris'], c['pago-campo']),
            ('enlace sobre el crema', c['pago-enlace'], c['bc-bg']),
            ('enlace sobre la superficie (resumen plegable, «Editar»)', c['pago-enlace'], c['pago-panel']),
            ('«Aplicar» navy sobre el campo', c['pago-tinta'], c['pago-campo']),
            ('«Aplicar» navy sobre la fila elegida', c['pago-tinta'], c['pago-elegida']),
            ('texto del botón de pagar (navy sobre naranja)', c['pago-en-accion'], c['pago-accion']),
            ('texto del botón de pagar bajo el puntero', c['pago-en-accion'], c['pago-accion-encima']),
            ('cantidad navy en la insignia verde', c['pago-tinta'], c['pago-insignia']),
            ('«Modo de prueba» navy sobre el crema', c['pago-tinta'], c['pago-elegida']),
            ('antetítulo de la entrega (salvia fuerte) sobre la superficie', c['pago-icono'], c['pago-panel']),
            ('«El pago no se completó» sobre el crema', c['pago-error'], c['bc-bg']),
            ('«El pago no se completó» sobre la superficie', c['pago-error'], c['pago-panel']),
            ('botón de pagar sin método elegido', c['pago-apagado-letra'], c['pago-apagado']),
        ]
        for nombre, texto, fondo in pares:
            with self.subTest(par=nombre):
                self.assertGreaterEqual(contraste(texto, fondo), 4.5, f'{nombre}: {texto} sobre {fondo}')

    def test_bordes_e_iconos_llegan_a_3_a_1(self):
        c = self.c
        pares = [
            ('borde del campo del código de descuento', c['pago-borde-campo'], c['pago-campo']),
            ('radio sin elegir sobre la superficie', c['pago-borde-campo'], c['pago-panel']),
            ('radio elegido (navy)', c['pago-tinta'], c['pago-campo']),
            ('el filo naranja de la fila elegida sobre la fila', c['pago-filo'], c['pago-elegida']),
            ('el filo naranja sobre la superficie de al lado', c['pago-filo'], c['pago-panel']),
            ('candado e íconos de estado sobre el crema', c['pago-icono'], c['pago-elegida']),
            ('ícono de fallo sobre su recuadro', c['pago-error'], c['pago-error-fondo']),
        ]
        for nombre, trazo, fondo in pares:
            with self.subTest(par=nombre):
                self.assertGreaterEqual(contraste(trazo, fondo), 3.0, f'{nombre}: {trazo} sobre {fondo}')

    def test_la_marca_el_pago_es_de_baby_caleb_plano_y_sin_nada_de_d_casa(self):
        archivos = ('pago.scss', '../../../../dcasa_pago_tilopay/static/src/scss/tilopay.scss',
                    '../../../../dcasa_pago_yappy/static/src/scss/yappy.scss')
        for archivo in archivos:
            ruta = SCSS / archivo
            if not ruta.exists():
                continue
            codigo = ruta.read_text()
            sin_comentarios = re.sub(r'//[^\n]*', '', re.sub(r'/\*.*?\*/', '', codigo, flags=re.S))
            with self.subTest(archivo=ruta.name):
                for de_dcasa in ('#1340B1', '#FED00F', '#0E2A6B', '#0F3591', '#1B2233', '#4A5163', 'ANTON', 'OSWALD',
                                 "'INTER'", '"INTER"'):
                    self.assertNotIn(de_dcasa, sin_comentarios.upper(), f'{ruta.name}: quedó {de_dcasa} de D\'CASA')
                self.assertNotIn('gradient', sin_comentarios, 'sistema plano: sin degradados')
                self.assertNotIn('text-shadow', sin_comentarios)
                self.assertNotIn('drop-shadow', sin_comentarios)
                for sombra in re.findall(r'box-shadow:\s*([^;]+);', sin_comentarios):
                    valor = sombra.replace('!important', '').strip()
                    self.assertTrue(valor == 'none' or re.fullmatch(r'(inset )?0 0 0 \d+px [^,]+', valor),
                                    f'solo anillos planos (sin desenfoque): {sombra}')
        pago = (SCSS / 'pago.scss').read_text()
        # Los titulares van como frase: la única caja alta del pago es el antetítulo de la entrega (12 px, .14em).
        self.assertEqual(pago.count('text-transform: uppercase'), 1)
        # La letra blanca nunca va sobre el naranja: en el pago, lo que va sobre $pago-accion es $pago-en-accion (navy).
        for bloque in re.findall(r'background: \$pago-accion;[^}]*', pago):
            self.assertNotIn('#fff', bloque.lower())
            self.assertNotIn('$bc-blanco', bloque)
