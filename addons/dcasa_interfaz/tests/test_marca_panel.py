"""La marca del panel por empresa (Ajustes › Marca del panel, 2026-11-18).

Pedido del dueño: «en Ajustes cada empresa tiene que poder cargar su logo y customizar su interfaz con los colores de
la empresa; el logo del favicon y el del panel se cargan a mano, y los colores igual. La página web pública se queda
como está». Y desde el 2026-11-19 **la fábrica es la marca de Baby Caleb** (navy de principal, naranja de acento,
docs/MARCA_BABY_CALEB.md). Aquí se cuida:

* **De fábrica, la hoja de Odoo tal cual** (ya compilada en crema, navy y naranja): la página del panel enlaza la
  hoja de Odoo, el logo, favicon, ícono del iPhone y manifiesto de fábrica, y la barra del navegador en el crema.
* **Las bases instaladas con la fábrica de D'CASA** pasan a la de Baby Caleb (la migración 19.0.1.4.0), y «Volver a
  la marca de fábrica» no devuelve el azul.
* **Lo que sube la empresa aparece**: el logo en la barra y en el menú del celular, el favicon, el ícono del iPhone y
  los del manifiesto (hechos de su imagen, en sus tamaños), el color en la barra del navegador y la hoja del panel
  pintada con sus colores, en claro y en oscuro, y los íconos de las apps.
* **La web no cambia** (portada, tienda, acceso del equipo).
* **Los colores se validan y se leen**: formato, contraste del principal con la superficie crema (es la letra) y del
  acento con el principal (es el relleno del botón principal, con la letra del principal encima), con una sugerencia
  que sí sirve; y la hoja pintada no tiene más pares ilegibles que la de fábrica.
* **Permisos**: solo administradores cambian la marca; la hoja de una empresa ajena no se entrega.

Los colores de prueba (un verde oscuro y un amarillo) son solo de prueba: no son la marca de ninguna empresa.
"""
import base64
import importlib.util
import io
import json
import os
import re
from unittest.mock import patch

from PIL import Image, ImageChops, ImageDraw

from odoo.addons.dcasa_interfaz.controllers import marca as rutas
from odoo.addons.dcasa_interfaz.marca import colores as C
from odoo.addons.dcasa_interfaz.marca import tinte as modulo_tinte
from odoo.addons.dcasa_interfaz.marca.tinte import Tinte
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import HttpCase, TransactionCase, new_test_user, tagged
from odoo.tools import file_path

from .test_inicio_por_rol import ESPERAR_JS
from .test_modo_oscuro import pares_que_no_se_leen

PRINCIPAL = '#1F4D3A'
ACENTO = '#F2C14E'
FABRICA_APPLE = '/dcasa_base/static/img/icono/apple-touch-icon.png'
FABRICA_FAVICON = '/dcasa_base/static/img/icono/logo-192.png'
LOGO_DE_FABRICA = '/dcasa_base/static/img/logo.png'
# La escala del navy de tokens.scss (del más oscuro al principal y los dos más claros): lo que gira con el principal.
ESCALA = ('#0C171F', '#101E2A', '#142635', '#172B3D', '#1B3246', '#24405A', '#2B4A66')
# Los tonos del naranja de la marca: el relleno, el del puntero, el apretado, el de letra y el de los bordes.
NARANJAS = ('#EE924A', '#F1A86E', '#E8853A', '#985D2F', '#C3783D')
CREMA = '#F9F6ED'
NAVY = '#1B3246'
NARANJA = '#EE924A'


def imagen(ancho, alto, color=(27, 50, 70, 255), formato='PNG'):
    """Un dibujo de prueba: un rectángulo de color con margen transparente alrededor."""
    lienzo = Image.new('RGBA', (ancho, alto), (0, 0, 0, 0))
    ImageDraw.Draw(lienzo).rectangle((ancho // 10, alto // 10, ancho - ancho // 10 - 1, alto - alto // 10 - 1),
                                     fill=color)
    salida = io.BytesIO()
    (lienzo.convert('RGB') if formato == 'JPEG' else lienzo).save(salida, formato)
    return salida.getvalue()


def b64(datos):
    return base64.b64encode(datos)


def selectores(pares):
    return {par.split(': fondo ')[0] for par in pares}


# --- Los colores, en Python puro --------------------------------------------------------------------------------

@tagged('post_install', '-at_install')
class TestColoresDeLaMarca(TransactionCase):

    def test_un_color_se_escribe_como_numeral_y_seis_cifras(self):
        self.assertEqual(C.normalizar('#1b3246'), '#1B3246')
        self.assertEqual(C.normalizar(' 1B3246 '), '#1B3246')
        self.assertEqual(C.normalizar('#13b'), '#1133BB')
        self.assertIsNone(C.normalizar(''))
        self.assertIsNone(C.normalizar(False))
        for malo in ('azul', '#12345', '#GGGGGG', 'rgb(1,2,3)', '#1B3246FF', '##1B3246'):
            with self.subTest(malo=malo), self.assertRaisesRegex(ValueError, 'no es un color'):
                C.normalizar(malo)

    def test_contraste_segun_wcag(self):
        self.assertAlmostEqual(C.contraste('#FFFFFF', '#000000'), 21, places=1)
        self.assertAlmostEqual(C.contraste('#1B3246', '#1B3246'), 1)
        # Las medidas de Baby-caleb/brand.json (2026-11-09).
        self.assertAlmostEqual(C.contraste(NAVY, CREMA), 12.21, places=2)
        self.assertAlmostEqual(C.contraste(NAVY, NARANJA), 5.56, places=2)
        self.assertAlmostEqual(C.contraste(NARANJA, CREMA), 2.20, places=2)

    def test_la_fabrica_es_baby_caleb_y_se_lee(self):
        """El principal de fábrica es el navy (la tinta) y el acento el naranja (el relleno, con letra navy)."""
        self.assertEqual((C.FABRICA_PRINCIPAL, C.FABRICA_ACENTO), (NAVY, NARANJA))
        self.assertNotIn(C.DCASA_PRINCIPAL, (C.FABRICA_PRINCIPAL, C.FABRICA_ACENTO), 'el azul de D\'CASA ya no es fábrica')
        self.assertIsNone(C.problema_del_principal(C.FABRICA_PRINCIPAL))
        self.assertIsNone(C.problema_del_acento(C.FABRICA_ACENTO, C.FABRICA_PRINCIPAL))
        self.assertEqual(C.oscuro_de(C.FABRICA_PRINCIPAL), C.OSCURO_DE_FABRICA)
        self.assertEqual(C.oscuro_de(PRINCIPAL), PRINCIPAL, 'encima del acento va la letra en el principal')
        self.assertTrue(C.como_se_lee(C.FABRICA_PRINCIPAL, C.FABRICA_ACENTO).startswith('Se lee bien'))
        # Los colores de D'CASA siguen siendo una marca válida para otra empresa (azul de tinta, amarillo de relleno).
        self.assertIsNone(C.problema_del_principal(C.DCASA_PRINCIPAL))
        self.assertIsNone(C.problema_del_acento(C.DCASA_ACENTO, C.DCASA_PRINCIPAL))

    def test_el_color_de_fabrica_va_a_dar_exacto_al_elegido(self):
        for principal in (PRINCIPAL, '#985D2F', '#0F7B3A', '#B00020', '#555555', '#000000', '#6A1B9A', '#1340B1'):
            with self.subTest(principal=principal):
                giro = C.Giro(principal)
                self.assertEqual(C.a_hexa(giro(C.a_rgb(C.FABRICA_PRINCIPAL))), principal)
        for acento in (ACENTO, '#FED00F', '#91C9A2', '#FFB4C8', '#DDDDDD'):
            with self.subTest(acento=acento):
                giro = C.GiroDelAcento(acento, PRINCIPAL)
                self.assertEqual(C.a_hexa(giro(C.a_rgb(C.FABRICA_ACENTO))), acento)

    def test_el_giro_conserva_lo_que_se_leia_sobre_el_crema(self):
        """Lo que en fábrica se leía como letra sobre la superficie crema se sigue leyendo con cualquier principal
        válido, también uno más claro que el navy (el que más aprieta); y los tonos del naranja que eran letra o borde
        siguen siéndolo con cualquier acento."""
        for principal in (PRINCIPAL, '#985D2F', '#0F7B3A', '#C2185B', '#6C6C6C', '#2E7D32', '#000000', '#1340B1'):
            self.assertIsNone(C.problema_del_principal(principal), principal)
            giro = C.Giro(principal)
            for color in ESCALA:
                with self.subTest(principal=principal, color=color):
                    self.assertGreaterEqual(C.contraste(giro(C.a_rgb(color)), C.SUPERFICIE), C.MINIMO_TEXTO)
        for acento, principal in ((ACENTO, PRINCIPAL), ('#FED00F', '#1340B1'), ('#7FD1C1', '#3D1F5C'),
                                  ('#FFFFFF', '#000000')):
            self.assertIsNone(C.problema_del_acento(acento, principal), acento)
            giro = C.GiroDelAcento(acento, principal)
            for color in NARANJAS:
                antes = C.contraste(color, C.SUPERFICIE)
                despues = C.a_rgb(giro(C.a_rgb(color)))
                with self.subTest(acento=acento, color=color):
                    if antes >= C.MINIMO_TEXTO:
                        self.assertGreaterEqual(C.contraste(despues, C.SUPERFICIE), C.MINIMO_TEXTO, 'letra')
                    elif antes >= C.MINIMO_DETALLE:
                        self.assertGreaterEqual(C.contraste(despues, C.SUPERFICIE), C.MINIMO_DETALLE, 'borde')
                    if C.contraste(color, C.FABRICA_PRINCIPAL) >= C.MINIMO_TEXTO:
                        self.assertGreaterEqual(C.contraste(despues, principal), C.MINIMO_TEXTO,
                                                'relleno con la letra del principal encima')

    def test_el_giro_respeta_el_orden_de_claro_a_oscuro(self):
        giro = C.Giro('#985D2F')
        luces = [C.luz(giro(C.a_rgb(c))) for c in ESCALA]
        self.assertEqual(luces, sorted(luces), 'la escala sigue yendo del más oscuro al más claro')

    def test_lo_que_no_es_la_marca_no_cambia(self):
        giro = C.Giro(PRINCIPAL)
        giro_acento = C.GiroDelAcento(ACENTO, PRINCIPAL)
        # la crema, la superficie, las líneas y los bordes, la letra de apoyo, la superficie del modo oscuro, el salvia,
        # el ámbar de los avisos, rojo, verde, blanco y negro
        for color in ('#F9F6ED', '#F2EFE5', '#DEDED9', '#7F8A91', '#475967', '#5E6D78', '#162129', '#0F161C',
                      '#91C9A2', '#53735C', '#FFAC00', '#DC3545', '#28A745', '#FFFFFF', '#000000'):
            with self.subTest(color=color):
                self.assertEqual(C.a_hexa(giro(C.a_rgb(color))), color)
                self.assertEqual(C.a_hexa(giro_acento(C.a_rgb(color))), color)

    def test_un_principal_muy_claro_se_rechaza_con_uno_que_si_sirve(self):
        problema = C.problema_del_principal(ACENTO)
        self.assertIn('muy claro', problema)
        sugerido = re.search(r'Prueba con (#[0-9A-F]{6})', problema).group(1)
        self.assertGreaterEqual(C.contraste(sugerido, C.SUPERFICIE), C.MINIMO_TEXTO)
        self.assertLess(C.distancia_de_tono(C.hsl(sugerido)[0], C.hsl(ACENTO)[0]), 4, 'el mismo tono')
        self.assertIsNone(C.problema_del_principal(sugerido))
        # El naranja de fábrica no sirve de principal: es relleno, no letra (2.1 a 1 sobre la superficie).
        self.assertIn('muy claro', C.problema_del_principal(C.FABRICA_ACENTO))

    def test_un_acento_oscuro_se_rechaza_con_uno_que_si_sirve(self):
        problema = C.problema_del_acento('#6A1B9A', C.FABRICA_PRINCIPAL)
        self.assertIn('no se lee', problema)
        sugerido = re.search(r'Prueba con (#[0-9A-F]{6})', problema).group(1)
        self.assertIsNone(C.problema_del_acento(sugerido, C.FABRICA_PRINCIPAL))
        # El naranja fuerte (el de la letra) tampoco: lleva la letra navy encima y da 2.5 a 1.
        self.assertIn('no se lee', C.problema_del_acento('#985D2F', C.FABRICA_PRINCIPAL))
        # Un acento claro con un principal oscuro: bien.
        self.assertIsNone(C.problema_del_acento(ACENTO, PRINCIPAL))


@tagged('post_install', '-at_install')
class TestTinteDeLaHoja(TransactionCase):

    def test_de_fabrica_no_cambia_ni_un_byte(self):
        hoja = ':root{--dc-azul-600: #1B3246}.btn-primary{--btn-bg: #EE924A; color: #1B3246}'
        for tinte in (Tinte(), Tinte(C.FABRICA_PRINCIPAL, C.FABRICA_ACENTO), Tinte('#1b3246', '')):
            self.assertTrue(tinte.de_fabrica)
            self.assertIs(tinte.css(hoja), hoja)
            self.assertIs(tinte.svg('<svg fill="#1B3246"/>'), '<svg fill="#1B3246"/>')

    def test_pinta_cada_forma_en_que_vienen_el_navy_y_el_naranja(self):
        tinte = Tinte(PRINCIPAL, ACENTO)
        hoja = ('.a{color: #1B3246; border-color: #1b3246}'
                '.b{background: rgba(27, 50, 70, 0.25); box-shadow: 0 0 0 1px rgb(27,50,70)}'
                '.c{background-color: #1B324680}'
                '.d{--primary-rgb: 27, 50, 70; --btn-focus-shadow-rgb: 27, 50, 70}'
                ".e{--fondo: url(\"data:image/svg+xml,%3csvg fill='%231B3246'/%3e\")}"
                '.f{background: #EE924A; color: #1B3246; border-color: rgba(238, 146, 74, .5)}'
                '@media (max-width: 767.98px){.g{color: #1B3246 !important}}')
        pintada = tinte.css(hoja)
        self.assertNotRegex(pintada.lower(), r'1b3246|27, ?50, ?70|ee924a|238, 146, 74')
        self.assertIn('.a{color: #1F4D3A; border-color: #1F4D3A}', pintada)
        self.assertIn('rgba(31, 77, 58, 0.25)', pintada)
        self.assertIn('rgb(31, 77, 58)', pintada)
        self.assertIn('#1F4D3A80', pintada, 'la transparencia del #hex de 8 cifras se queda')
        self.assertIn('--primary-rgb: 31, 77, 58', pintada)
        self.assertIn("fill='%231F4D3A'", pintada)
        self.assertIn('.f{background: #F2C14E; color: #1F4D3A; border-color: rgba(242, 193, 78, .5)}', pintada,
                      'el botón principal: el acento de relleno con la letra del principal')
        self.assertIn('@media (max-width: 767.98px){.g{color: #1F4D3A !important}}', pintada, 'el @media intacto')

    def test_los_tonos_del_naranja_giran_con_el_acento(self):
        """El puntero, lo apretado, la letra naranja y los bordes naranja siguen al acento de la empresa, y cada uno
        sigue haciendo su trabajo: la letra se lee sobre el crema y los rellenos llevan la letra del principal."""
        tinte = Tinte(PRINCIPAL, ACENTO)
        puntero, apretado, letra, borde = (C.a_rgb(tinte.color(C.a_rgb(c))) for c in NARANJAS[1:])
        for color in (puntero, apretado, letra, borde):
            self.assertLess(C.distancia_de_tono(C.hsl(color)[0], C.hsl(ACENTO)[0]), 4, 'el tono del acento')
        self.assertGreaterEqual(C.contraste(letra, C.SUPERFICIE), C.MINIMO_TEXTO)
        self.assertGreaterEqual(C.contraste(borde, C.SUPERFICIE), C.MINIMO_DETALLE)
        for relleno in (puntero, apretado):
            self.assertGreaterEqual(C.contraste(relleno, PRINCIPAL), C.MINIMO_TEXTO)
        # Solo con otro principal (el acento de fábrica): el naranja se queda, sus rellenos siguen leyéndose.
        solo_principal = Tinte(PRINCIPAL, C.FABRICA_ACENTO)
        self.assertFalse(solo_principal.de_fabrica)
        self.assertIn('#EE924A', solo_principal.css('.x{background: #EE924A}').upper())

    def test_no_pinta_las_paletas_ni_el_contenido_de_la_web(self):
        tinte = Tinte(PRINCIPAL, ACENTO)
        hoja = ('.o_calendar_renderer .o_calendar_color_45{background: #1B3246}'
                '.o_kanban_record.o_kanban_color_3::after{background-color: #EE924A}'
                '.o_cc1 a:not(.btn){color: #1B3246}'
                ':root{--o-color-1: #1B3246; --o-cc1-link: #1B3246; --dc-azul-600: #1B3246}')
        pintada = tinte.css(hoja)
        self.assertIn('.o_calendar_color_45{background: #1B3246}', pintada)
        self.assertIn('.o_kanban_color_3::after{background-color: #EE924A}', pintada)
        self.assertIn('.o_cc1 a:not(.btn){color: #1B3246}', pintada)
        self.assertIn(':root{--o-color-1: #1B3246; --o-cc1-link: #1B3246; --dc-azul-600: #1F4D3A}', pintada)

    def test_los_iconos_svg_de_las_apps(self):
        svg = '<svg><rect fill="#1B3246"/><path stroke="#F9F6ED"/><circle fill="#EE924A"/></svg>'
        self.assertEqual(Tinte(PRINCIPAL, ACENTO).svg(svg),
                         '<svg><rect fill="#1F4D3A"/><path stroke="#F9F6ED"/><circle fill="#F2C14E"/></svg>')


# --- La empresa: guardar, validar, permisos ----------------------------------------------------------------------

@tagged('post_install', '-at_install')
class TestMarcaDeLaEmpresa(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.empresa = cls.env.company
        cls.gerencia = new_test_user(cls.env, login='gerencia_marca',
                                     groups='base.group_user,dcasa_base.group_gerencia')
        cls.admin = new_test_user(cls.env, login='admin_marca', groups='base.group_user,base.group_system')

    def test_de_fabrica_el_panel_es_el_de_siempre(self):
        empresa = self.empresa
        self.assertEqual(empresa.dcasa_panel_color_principal, C.FABRICA_PRINCIPAL)
        self.assertEqual(empresa.dcasa_panel_color_acento, C.FABRICA_ACENTO)
        self.assertFalse(empresa.dcasa_panel_logo)
        self.assertFalse(empresa.dcasa_panel_icono)
        self.assertTrue(empresa._dcasa_panel_resumen()['todo_de_fabrica'])
        self.assertEqual(empresa._dcasa_panel_pagina('light'), {})
        self.assertEqual(empresa._dcasa_panel_pagina('dark'), {})
        self.assertEqual(empresa._dcasa_panel_navegador(), {'logo': False, 'nombre': False})
        self.assertEqual(empresa._dcasa_panel_manifiesto(), {'iconos': None})
        self.assertEqual(empresa._dcasa_panel_url_logo(), LOGO_DE_FABRICA)
        nueva = self.env['res.company'].create({'name': 'Empresa nueva de prueba'})
        self.assertEqual((nueva.dcasa_panel_color_principal, nueva.dcasa_panel_color_acento),
                         (C.FABRICA_PRINCIPAL, C.FABRICA_ACENTO), 'una empresa nueva nace con la marca de fábrica')

    def test_el_inicio_saluda_con_el_nombre_de_la_empresa(self):
        """«Así va el día en …»: el nombre de la empresa, no el de la plantilla de origen."""
        self.empresa.name = 'Empresa de Prueba'
        self.assertEqual(self.env['dcasa.tablero'].with_user(self.admin).obtener_datos()['empresa'], 'Empresa de Prueba')
        with open(file_path('dcasa_interfaz/static/src/xml/inicio.xml'), encoding='utf-8') as archivo:
            plantilla = archivo.read()
        self.assertIn('Así va el día en <t t-esc="d.empresa"/>.', plantilla)
        self.assertNotIn("D'CASA", plantilla)

    def test_guardar_normaliza_y_cambia_la_version_solo_si_cambia_algo(self):
        empresa = self.empresa.with_user(self.admin)
        empresa.write({'dcasa_panel_color_principal': '1f4d3a', 'dcasa_panel_color_acento': '#f2c14e'})
        self.assertEqual(empresa.dcasa_panel_color_principal, PRINCIPAL)
        self.assertEqual(empresa.dcasa_panel_color_acento, ACENTO)
        version = empresa.dcasa_panel_version
        self.assertTrue(version)
        empresa.write({'dcasa_panel_color_principal': PRINCIPAL})
        self.assertEqual(empresa.dcasa_panel_version, version, 'lo mismo otra vez no obliga a bajar todo de nuevo')
        empresa.write({'dcasa_panel_color_principal': '', 'dcasa_panel_color_acento': False})
        self.assertEqual((empresa.dcasa_panel_color_principal, empresa.dcasa_panel_color_acento),
                         (C.FABRICA_PRINCIPAL, C.FABRICA_ACENTO), 'vacío es el de fábrica')
        self.assertNotEqual(empresa.dcasa_panel_version, version)

    def rechazado(self, vals, mensaje, error=ValidationError):
        """Un guardado que no pasa. En la pantalla, el error deshace la transacción; aquí, un punto de guardado."""
        with self.assertRaisesRegex(error, mensaje), self.env.cr.savepoint():
            self.empresa.with_user(self.admin).write(vals)
        self.env.invalidate_all()

    def test_un_color_mal_escrito_o_que_no_se_lee_no_se_guarda(self):
        self.rechazado({'dcasa_panel_color_principal': 'azul'}, 'no es un color')
        self.rechazado({'dcasa_panel_color_principal': ACENTO}, r'muy claro.*Prueba con #')
        self.rechazado({'dcasa_panel_color_acento': '#985D2F'}, 'acento .* no se lee')   # el naranja de letra
        self.assertEqual(self.empresa.dcasa_panel_color_principal, C.FABRICA_PRINCIPAL)

    def test_el_logo_tiene_que_ser_una_imagen_que_se_pueda_achicar(self):
        empresa = self.empresa.with_user(self.admin)
        svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10"/></svg>'
        self.rechazado({'dcasa_panel_logo': b64(svg)}, 'El logo del panel .*SVG no sirve')
        self.rechazado({'dcasa_panel_icono': b64(svg)}, 'El ícono del panel .*SVG no sirve')
        # Lo que no es una imagen ya lo frena Odoo al guardar el campo.
        self.rechazado({'dcasa_panel_icono': b64(b'esto no es una imagen')}, '.', error=UserError)
        empresa.write({'dcasa_panel_logo': b64(imagen(300, 120, formato='JPEG'))})
        self.assertTrue(empresa._dcasa_panel_tiene('dcasa_panel_logo'))

    def test_solo_un_administrador_cambia_la_marca(self):
        with self.assertRaises(AccessError):
            self.empresa.with_user(self.gerencia)._dcasa_panel_poner({'dcasa_panel_color_principal': PRINCIPAL})
        with self.assertRaises(AccessError):
            self.empresa.with_user(self.gerencia).write({'dcasa_panel_color_principal': PRINCIPAL})
        with self.assertRaises(AccessError):
            self.empresa.with_user(self.gerencia)._dcasa_panel_fabrica('todo')
        self.assertEqual(self.empresa.dcasa_panel_color_principal, C.FABRICA_PRINCIPAL)
        self.assertTrue(self.empresa.with_user(self.admin)._dcasa_panel_poner(
            {'dcasa_panel_color_principal': PRINCIPAL, 'name': 'Esto no lo cambia'}))
        self.assertEqual(self.empresa.dcasa_panel_color_principal, PRINCIPAL)
        self.assertNotEqual(self.empresa.name, 'Esto no lo cambia', 'solo toca los campos de la marca')

    def test_ajustes_dice_como_se_va_a_leer_y_vuelve_a_fabrica(self):
        Ajustes = self.env['res.config.settings'].with_user(self.admin)
        ajustes = Ajustes.new({'dcasa_panel_color_principal': PRINCIPAL, 'dcasa_panel_color_acento': ACENTO})
        self.assertTrue(ajustes.dcasa_panel_lectura.startswith('Se lee bien'))
        ajustes = Ajustes.new({'dcasa_panel_color_principal': ACENTO})
        self.assertIn('muy claro', ajustes.dcasa_panel_lectura)
        ajustes = Ajustes.new({'dcasa_panel_color_principal': 'rojo'})
        self.assertIn('no es un color', ajustes.dcasa_panel_lectura)

        self.empresa.write({'dcasa_panel_color_principal': PRINCIPAL, 'dcasa_panel_logo': b64(imagen(300, 120))})
        guardados = Ajustes.create({})
        self.assertEqual(guardados.dcasa_panel_color_principal, PRINCIPAL)
        accion = guardados.action_dcasa_panel_fabrica()
        self.assertEqual(accion, {'type': 'ir.actions.client', 'tag': 'reload'}, 'el panel se recarga ya pintado')
        resumen = self.empresa._dcasa_panel_resumen()
        self.assertTrue(resumen['todo_de_fabrica'])
        self.assertEqual((resumen['color_principal'], resumen['color_acento']), (NAVY, NARANJA),
                         'la fábrica es la de Baby Caleb: nada del azul ni del amarillo de D\'CASA')
        with self.assertRaises(AccessError):
            guardados.with_user(self.gerencia).action_dcasa_panel_fabrica()

    def test_ajustes_guarda_en_la_empresa(self):
        ajustes = self.env['res.config.settings'].with_user(self.admin).create({
            'dcasa_panel_color_principal': PRINCIPAL, 'dcasa_panel_color_acento': ACENTO})
        ajustes.execute()
        self.assertEqual((self.empresa.dcasa_panel_color_principal, self.empresa.dcasa_panel_color_acento),
                         (PRINCIPAL, ACENTO))

    def test_la_pantalla_esta_en_ajustes_solo_para_administradores(self):
        menu = self.env.ref('dcasa_interfaz.menu_dcasa_marca_panel')
        self.assertEqual(menu.parent_id, self.env.ref('base.menu_administration'))
        self.assertEqual(menu.action, self.env.ref('dcasa_interfaz.action_dcasa_marca_panel'))
        self.assertEqual(menu.action.context.replace(' ', ''), "{'module':'dcasa_interfaz','bin_size':False}")
        visibles = {usuario: menu.id in self.env['ir.ui.menu'].with_user(usuario)._visible_menu_ids()
                    for usuario in (self.admin, self.gerencia)}
        self.assertEqual(visibles, {self.admin: True, self.gerencia: False})

    def test_los_iconos_de_las_apps_con_los_colores_de_la_empresa(self):
        def iconos(usuario):
            menus = self.env['ir.ui.menu'].with_user(usuario).load_web_menus(False)
            return {m['xmlid']: base64.b64decode(m['webIconData'].split(',', 1)[1]).decode()
                    for m in menus.values()
                    if (m.get('webIconData') or '').startswith('data:image/svg+xml;base64,')}
        antes = iconos(self.admin)
        ventas = antes.get('sale.sale_menu_root')
        self.assertIn(NAVY, ventas, 'de fábrica, el cuadro navy con el punto naranja')
        self.assertIn(NARANJA, ventas)
        self.empresa.write({'dcasa_panel_color_principal': PRINCIPAL, 'dcasa_panel_color_acento': ACENTO})
        despues = iconos(self.admin)
        self.assertNotIn(NAVY, despues['sale.sale_menu_root'])
        self.assertIn(PRINCIPAL, despues['sale.sale_menu_root'])
        self.assertIn(ACENTO, despues['sale.sale_menu_root'])
        self.assertEqual(despues['sale.sale_menu_root'], Tinte(PRINCIPAL, ACENTO).svg(ventas))


# --- Las bases que se instalaron con la fábrica de D'CASA -----------------------------------------------------------

@tagged('post_install', '-at_install')
class TestMigracionDeLaFabrica(TransactionCase):
    """Una base instalada antes del 2026-11-19 (staging) guarda los colores de fábrica de entonces, los de D'CASA: al
    actualizar pasan a los de Baby Caleb sin que nadie toque Ajustes; un color que la empresa sí eligió se queda."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ruta = file_path('dcasa_interfaz/migrations/19.0.1.4.0/post-migrate.py')
        especificacion = importlib.util.spec_from_file_location('dcasa_interfaz_migracion_marca', ruta)
        cls.migracion = importlib.util.module_from_spec(especificacion)
        especificacion.loader.exec_module(cls.migracion)

    def guardado(self, empresa, principal, acento):
        """Como lo dejó la versión anterior: directo en la base, sin las reglas de ahora."""
        self.env.cr.execute('UPDATE res_company SET dcasa_panel_color_principal = %s, dcasa_panel_color_acento = %s, '
                            'dcasa_panel_version = NULL WHERE id = %s', (principal, acento, empresa.id))
        empresa.invalidate_recordset()

    def migrar(self):
        self.migracion.migrate(self.env.cr, '19.0.1.3.0')
        self.env.invalidate_all()

    def test_la_fabrica_de_dcasa_pasa_a_la_de_baby_caleb(self):
        empresa = self.env.company
        self.guardado(empresa, C.DCASA_PRINCIPAL, C.DCASA_ACENTO)
        self.assertFalse(empresa._dcasa_panel_tinte().de_fabrica, 'antes: el panel se pintaría de azul')
        self.migrar()
        self.assertEqual((empresa.dcasa_panel_color_principal, empresa.dcasa_panel_color_acento), (NAVY, NARANJA))
        self.assertTrue(empresa._dcasa_panel_tinte().de_fabrica, 'ahora la hoja de Odoo tal cual: Baby Caleb')
        self.assertTrue(empresa.dcasa_panel_version, 'los navegadores piden lo nuevo')
        self.assertEqual(empresa._dcasa_panel_pagina('light'), {})
        version = empresa.dcasa_panel_version
        self.migrar()
        self.assertEqual(empresa.dcasa_panel_version, version, 'se puede repetir sin cambiar nada')

    def test_lo_que_la_empresa_eligio_se_queda(self):
        empresa = self.env.company
        self.guardado(empresa, PRINCIPAL, C.DCASA_ACENTO)
        self.migrar()
        self.assertEqual((empresa.dcasa_panel_color_principal, empresa.dcasa_panel_color_acento), (PRINCIPAL, NARANJA))
        # Si con el cambio el par dejara de leerse, la empresa vuelve entera a la fábrica.
        self.guardado(empresa, '#985D2F', C.DCASA_ACENTO)
        self.migrar()
        self.assertEqual((empresa.dcasa_panel_color_principal, empresa.dcasa_panel_color_acento), (NAVY, NARANJA))


# --- La página del panel, sus hojas e íconos ------------------------------------------------------------------------

@tagged('post_install', '-at_install')
class TestMarcaEnLaPagina(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.empresa = cls.env.company
        rutas.HOJAS.clear()
        rutas.ICONOS.clear()

    def pagina(self, cookies=None):
        self.authenticate('admin', 'admin')
        return self.url_open('/odoo', cookies=cookies).text

    def info(self, html):
        return json.loads(re.search(r'odoo\.__session_info__ = (\{.*?\});\n', html, re.S).group(1))

    def poner(self, **vals):
        self.empresa.write(vals)

    def test_de_fabrica_la_pagina_es_la_de_siempre(self):
        html = self.pagina()
        self.assertNotIn('/dcasa_interfaz/marca', html)
        self.assertRegex(html, r'href="/web/assets/[^"]*web\.assets_web\.min\.css"')
        self.assertIn(f'<link rel="apple-touch-icon" href="{FABRICA_APPLE}"/>', html)
        self.assertIn(f'href="{FABRICA_FAVICON}"', html)
        self.assertIn(f'<meta name="theme-color" content="{CREMA}"/>', html)
        self.assertEqual(self.info(html)['dcasa_marca'], {'logo': False, 'nombre': False})
        manifiesto = self.url_open('/web/manifest.webmanifest').json()
        self.assertEqual(manifiesto['theme_color'], CREMA)
        self.assertTrue(all(i['src'].startswith('/dcasa_base/static/img/icono/') for i in manifiesto['icons']))

    def test_con_sus_colores_el_panel_enlaza_la_hoja_pintada(self):
        original = re.search(r'href="(/web/assets/[^"]*web\.assets_web\.min\.css)"', self.pagina()).group(1)
        fabrica = self.url_open(original).text
        self.poner(dcasa_panel_color_principal=PRINCIPAL, dcasa_panel_color_acento=ACENTO)
        html = self.pagina()
        self.assertNotIn(original, html, 'no se cargan las dos hojas')
        self.assertIn(f'<meta name="theme-color" content="{CREMA}"/>', html, 'la barra del navegador: el crema')
        enlace = re.search(r'href="(/dcasa_interfaz/marca/hoja/[^"]*web\.assets_web\.min\.css)"', html).group(1)
        self.assertIn(f'/{self.empresa.id}/{self.empresa.dcasa_panel_version}/', enlace)
        respuesta = self.url_open(enlace)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.headers['Content-Type'], 'text/css; charset=utf-8')
        self.assertIn('immutable', respuesta.headers['Cache-Control'])
        pintada = respuesta.text
        self.assertEqual(pintada, Tinte(PRINCIPAL, ACENTO).css(fabrica), 'la hoja de Odoo, solo con otros colores')
        self.assertIn('o_dcasa_inicio', pintada)
        self.assertRegex(pintada, rf'--dc-azul-600: {PRINCIPAL}')
        self.assertRegex(pintada, rf'\.btn-primary\{{[^}}]*--btn-bg: {ACENTO}')
        self.assertRegex(pintada, rf'\.btn-primary\{{[^}}]*--btn-color: {PRINCIPAL}')
        self.assertRegex(pintada, rf'--dc-amarillo: {ACENTO}')
        self.assertRegex(pintada, rf'--dc-naranja: {ACENTO}')
        # El navy y el naranja de fábrica solo quedan en lo que no es la marca: paletas de categorías y colores de la web.
        for regla in re.findall(r'([^{}]*)\{([^{}]*(?:#1B3246|#EE924A)[^{}]*)\}', pintada, re.I):
            with self.subTest(regla=regla[0][-80:]):
                self.assertRegex(regla[0] + regla[1], modulo_tinte._INTOCABLES.pattern + r'|--o-c(?:olor|c)')
        # Con los colores de antes, la página vuelve a la hoja de Odoo.
        self.poner(dcasa_panel_color_principal=C.FABRICA_PRINCIPAL, dcasa_panel_color_acento=C.FABRICA_ACENTO)
        self.assertIn(original, self.pagina())

    def test_la_hoja_pintada_se_lee_como_la_de_fabrica_en_claro_y_en_oscuro(self):
        """La red de pares ilegibles del modo oscuro, sobre las dos hojas pintadas: ninguna regla propia nueva."""
        # Un principal más claro que el navy (el que más aprieta) y un acento muy claro que lleva su letra encima.
        self.poner(dcasa_panel_color_principal='#985D2F', dcasa_panel_color_acento='#FFF0D0')
        for cookies, archivo in ((None, 'web.assets_web.min.css'), ({'color_scheme': 'dark'},
                                                                     'web.assets_web_dark.min.css')):
            with self.subTest(hoja=archivo):
                html = self.pagina(cookies)
                enlace = re.search(rf'href="(/dcasa_interfaz/marca/hoja/[^"]*{re.escape(archivo)})"', html).group(1)
                original = '/web/assets/' + enlace.split('/', 6)[6]
                fabrica = self.url_open(original).text
                pintada = self.url_open(enlace).text
                nuevos = selectores(pares_que_no_se_leen(pintada)) - selectores(pares_que_no_se_leen(fabrica))
                self.assertFalse(nuevos, f'con estos colores dejan de leerse: {sorted(nuevos)[:20]}')
                if archivo.startswith('web.assets_web_dark'):
                    self.assertIn('--dc-relleno', pintada, 'la hoja oscura, pintada')

    def test_la_hoja_de_una_empresa_ajena_no_se_entrega(self):
        self.poner(dcasa_panel_color_principal=PRINCIPAL)
        enlace = re.search(r'href="(/dcasa_interfaz/marca/hoja/[^"]+)"', self.pagina()).group(1)
        ajena = self.env['res.company'].create({'name': 'Otra empresa de prueba'})
        otra = enlace.replace(f'/hoja/{self.empresa.id}/', f'/hoja/{ajena.id}/')
        self.assertEqual(self.url_open(otra).status_code, 404)
        self.assertEqual(self.url_open(enlace.replace('web.assets_web.min.css', 'otra.css')).status_code, 404)
        self.logout()
        respuesta = self.url_open(enlace, allow_redirects=False)
        self.assertIn(respuesta.status_code, (302, 303))
        self.assertIn('/web/login', respuesta.headers['Location'])

    def test_si_pintar_falla_el_panel_usa_la_hoja_de_odoo(self):
        self.poner(dcasa_panel_color_principal=PRINCIPAL)
        enlace = re.search(r'href="(/dcasa_interfaz/marca/hoja/[^"]+)"', self.pagina()).group(1)
        rutas.HOJAS.clear()
        with patch.object(Tinte, 'css', side_effect=RuntimeError('prueba')), \
                self.assertLogs('odoo.addons.dcasa_interfaz.controllers.marca', 'ERROR'):
            respuesta = self.url_open(enlace, allow_redirects=False)
        self.assertIn(respuesta.status_code, (302, 303))
        self.assertRegex(respuesta.headers['Location'], r'/web/assets/[^/]+/web\.assets_web\.min\.css$')

    def test_si_leer_la_marca_falla_el_panel_abre_con_la_de_fabrica(self):
        self.poner(dcasa_panel_color_principal=PRINCIPAL)
        Empresa = type(self.env['res.company'])
        with patch.object(Empresa, '_dcasa_panel_pagina_sin_red', side_effect=RuntimeError('prueba')), \
                self.assertLogs('odoo.addons.dcasa_interfaz.models.marca', 'ERROR'):
            html = self.pagina()
        self.assertRegex(html, r'href="/web/assets/[^"]*web\.assets_web\.min\.css"')
        self.assertNotIn('/dcasa_interfaz/marca/hoja', html)

    def assertIcono(self, url, lado, opaco):
        respuesta = self.url_open(url)
        self.assertEqual(respuesta.status_code, 200, url)
        self.assertEqual(respuesta.headers['Content-Type'], 'image/png', url)
        dibujo = Image.open(io.BytesIO(respuesta.content)).convert('RGBA')
        self.assertEqual(dibujo.size, (lado, lado), url)
        if opaco:
            self.assertEqual(dibujo.getextrema()[3], (255, 255), f'{url}: sin transparencia')
            self.assertEqual(dibujo.getpixel((0, 0)), (255, 255, 255, 255), f'{url}: sobre blanco')
            fondo = Image.new('RGBA', dibujo.size, (255, 255, 255, 255))
            caja = ImageChops.difference(dibujo, fondo).convert('L').point(lambda v: 255 if v > 24 else 0).getbbox()
        else:
            self.assertEqual(dibujo.getpixel((0, 0))[3], 0, f'{url}: fondo transparente')
            caja = dibujo.getchannel('A').point(lambda v: 255 if v > 24 else 0).getbbox()
        izquierda, arriba, derecha, abajo = caja
        self.assertLessEqual(abs(izquierda - (lado - derecha)), 2, f'{url}: centrado a lo ancho')
        self.assertLessEqual(abs(arriba - (lado - abajo)), 2, f'{url}: centrado a lo alto')
        self.assertGreater(izquierda, 0, f'{url}: con margen')
        return dibujo, caja

    def test_el_logo_y_los_iconos_salen_de_lo_que_subio_la_empresa(self):
        self.poner(dcasa_panel_logo=b64(imagen(600, 240)))
        html = self.pagina()
        version = self.empresa.dcasa_panel_version
        marca = self.info(html)['dcasa_marca']
        self.assertEqual(marca, {'logo': f'/web/image/res.company/{self.empresa.id}/dcasa_panel_logo?unique={version}',
                                 'nombre': self.empresa.name})
        logo = self.url_open(marca['logo'])
        self.assertEqual((logo.status_code, logo.headers['Content-Type']), (200, 'image/png'))
        base = f'/dcasa_interfaz/marca/icono/{self.empresa.id}/{version}'
        self.assertIn(f'<link rel="apple-touch-icon" href="{base}/apple-touch-icon.png"/>', html)
        self.assertIn(f'href="{base}/icono-192.png"', html, 'el favicon')
        self.assertNotIn(FABRICA_APPLE, html)
        manifiesto = self.url_open('/web/manifest.webmanifest').json()
        self.assertEqual({(i['sizes'], i['purpose']): i['src'] for i in manifiesto['icons']}, {
            ('192x192', 'any'): f'{base}/icono-192.png', ('512x512', 'any'): f'{base}/icono-512.png',
            ('192x192', 'maskable'): f'{base}/icono-maskable-192.png',
            ('512x512', 'maskable'): f'{base}/icono-maskable-512.png'})
        self.assertEqual(manifiesto['theme_color'], CREMA, 'la barra del navegador, en el crema de la página')
        _dibujo, caja = self.assertIcono(f'{base}/icono-512.png', 512, False)
        ancho, alto = caja[2] - caja[0], caja[3] - caja[1]
        self.assertAlmostEqual(ancho / alto, 480 / 192, delta=0.08, msg='el logo entero, sin deformar')
        self.assertAlmostEqual(ancho, 512 * 0.94, delta=3)
        self.assertIcono(f'{base}/icono-192.png', 192, False)
        _dibujo, caja = self.assertIcono(f'{base}/icono-maskable-512.png', 512, True)
        medio = ((caja[2] - caja[0]) / 2, (caja[3] - caja[1]) / 2)
        self.assertLessEqual((medio[0] ** 2 + medio[1] ** 2) ** 0.5, 0.4 * 512 + 1, 'dentro de la zona segura')
        self.assertIcono(f'{base}/icono-maskable-192.png', 192, True)
        self.assertIcono(f'{base}/apple-touch-icon.png', 180, True)
        respuesta = self.url_open(f'{base}/icono-192.png')
        self.assertIn('immutable', respuesta.headers['Cache-Control'])
        self.assertEqual(self.url_open(f'{base}/otro.png').status_code, 404)

    def test_el_icono_propio_manda_sobre_el_logo(self):
        self.poner(dcasa_panel_logo=b64(imagen(600, 240, color=(27, 50, 70, 255))),
                   dcasa_panel_icono=b64(imagen(300, 300, color=(238, 146, 74, 255))))
        base = f'/dcasa_interfaz/marca/icono/{self.empresa.id}/{self.empresa.dcasa_panel_version}'
        dibujo, _caja = self.assertIcono(f'{base}/icono-192.png', 192, False)
        self.assertEqual(dibujo.getpixel((96, 96))[:3], (238, 146, 74), 'el centro es el ícono, no el logo')

    def test_sin_imagen_propia_los_iconos_son_los_de_fabrica(self):
        respuesta = self.url_open(f'/dcasa_interfaz/marca/icono/{self.empresa.id}/0/apple-touch-icon.png',
                                  allow_redirects=False)
        self.assertIn(respuesta.status_code, (302, 303))
        self.assertTrue(respuesta.headers['Location'].endswith(FABRICA_APPLE))
        self.assertEqual(self.url_open('/dcasa_interfaz/marca/icono/999999/0/icono-192.png').status_code, 404)

    def test_la_web_no_cambia(self):
        """Portada, tienda y acceso del equipo: las mismas hojas y los mismos íconos con o sin la marca del panel."""
        def huella(ruta):
            html = self.url_open(ruta).text
            return (sorted(re.findall(r'href="([^"]+\.css)"', html)),
                    sorted(re.findall(r'<link rel="(?:apple-touch-icon|icon|shortcut icon)"[^>]*>', html)),
                    re.findall(r'<meta name="theme-color"[^>]*>', html))
        rutas_web = ('/', '/shop', '/web/login')
        antes = {ruta: huella(ruta) for ruta in rutas_web}
        self.poner(dcasa_panel_color_principal=PRINCIPAL, dcasa_panel_color_acento=ACENTO,
                   dcasa_panel_logo=b64(imagen(600, 240)), dcasa_panel_icono=b64(imagen(300, 300)))
        for ruta in rutas_web:
            with self.subTest(ruta=ruta):
                html = self.url_open(ruta).text
                self.assertNotIn('/dcasa_interfaz/marca', html)
                self.assertNotIn('dcasa_panel_logo', html)
                self.assertEqual(huella(ruta), antes[ruta])
        self.assertIn(f'href="{FABRICA_APPLE}"', self.url_open('/').text)


# --- Lo que se ve en el navegador ------------------------------------------------------------------------------------

@tagged('post_install', '-at_install')
class TestMarcaEnElNavegador(HttpCase):

    def setUp(self):
        super().setUp()
        if os.environ.get('DCASA_SIN_NAVEGADOR'):
            self.skipTest('sin navegador')

    def probar(self, cuerpo):
        codigo = '(async () => {' + ESPERAR_JS + cuerpo + "console.log('test successful'); })();"
        self.browser_js('/odoo/action-dcasa_interfaz.action_dcasa_inicio', codigo, login='admin')

    def test_de_fabrica_el_logo_de_siempre(self):
        self.probar(f"""
            const logo = await esperar(() => document.querySelector('.o_dcasa_barra_logo'), 'el logo de la barra');
            if (logo.getAttribute('src') !== '{LOGO_DE_FABRICA}' || logo.getAttribute('alt') !== "Baby Caleb") {{
                throw new Error('logo: ' + logo.outerHTML);
            }}
            const marca = document.querySelector('.o_dcasa_barra_marca');
            if (marca.getAttribute('aria-label') !== "Baby Caleb, ir al inicio") {{
                throw new Error('nombre: ' + marca.getAttribute('aria-label'));
            }}
        """)

    def test_el_logo_y_los_colores_de_la_empresa_en_el_panel(self):
        empresa = self.env.company
        empresa.write({'name': 'Empresa de Prueba', 'dcasa_panel_logo': b64(imagen(600, 240)),
                       'dcasa_panel_color_principal': PRINCIPAL, 'dcasa_panel_color_acento': ACENTO})
        self.probar(f"""
            const logo = await esperar(() => document.querySelector('.o_dcasa_barra_logo'), 'el logo de la barra');
            if (!logo.getAttribute('src').startsWith('/web/image/res.company/{empresa.id}/dcasa_panel_logo')
                    || logo.getAttribute('alt') !== 'Empresa de Prueba') {{
                throw new Error('logo: ' + logo.outerHTML);
            }}
            await esperar(() => logo.complete && logo.naturalWidth > 0, 'que el logo cargue');
            const boton = await esperar(() => document.querySelector('.o_dcasa_inicio_accesos .btn-primary'),
                                        'el botón principal del Inicio');
            // El botón principal: el acento de la empresa de relleno, con la letra en su principal.
            const fondo = getComputedStyle(boton).backgroundColor, letra = getComputedStyle(boton).color;
            if (fondo !== 'rgb(242, 193, 78)') {{ throw new Error('el botón principal sale ' + fondo); }}
            if (letra !== 'rgb(31, 77, 58)') {{ throw new Error('la letra del botón principal sale ' + letra); }}
            const hojas = [...document.querySelectorAll('link[rel="stylesheet"]')].map((l) => l.href);
            if (!hojas.some((h) => h.includes('/dcasa_interfaz/marca/hoja/'))) {{
                throw new Error('hojas: ' + JSON.stringify(hojas));
            }}
        """)


@tagged('post_install', '-at_install')
class TestMarcaEnElCelular(HttpCase):
    browser_size = '390x844'
    touch_enabled = True

    def test_el_menu_del_celular_trae_el_logo_de_la_empresa(self):
        if os.environ.get('DCASA_SIN_NAVEGADOR'):
            self.skipTest('sin navegador')
        empresa = self.env.company
        empresa.write({'name': 'Empresa de Prueba', 'dcasa_panel_logo': b64(imagen(600, 240))})
        codigo = '(async () => {' + ESPERAR_JS + f"""
            await esperar(() => document.querySelector('.o_main_navbar .o_menu_toggle'), 'las tres rayas');
            document.querySelector('.o_main_navbar .o_menu_toggle').click();
            const logo = await esperar(() => document.querySelector('.o_app_menu_sidebar .o_dcasa_cajon_titulo img'),
                                       'el logo del menú');
            if (!logo.getAttribute('src').startsWith('/web/image/res.company/{empresa.id}/dcasa_panel_logo')
                    || logo.getAttribute('alt') !== 'Empresa de Prueba') {{
                throw new Error('logo del menú: ' + logo.outerHTML);
            }}
            console.log('test successful');
        }})();"""
        self.browser_js('/odoo/action-dcasa_interfaz.action_dcasa_inicio', codigo, login='admin')
