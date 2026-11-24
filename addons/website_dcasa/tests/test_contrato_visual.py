# ruff: noqa: E501  (JavaScript del navegador embebido en texto)
"""Contrato visual de la cabecera y del hero (pedido de la dueña de la plantilla: «que este navbar nunca más se vuelva a
dañar»), con la marca de Baby Caleb (docs/MARCA_BABY_CALEB.md, 2026-11-19). Fija, medido en Chrome y a dos anchos
(1440 y 390), el diseño de babycaleb.com:

* La pastilla flotante de vidrio crema (`.bc-vidrio` de Baby-caleb/src/styles/tokens.css, `.o_main_nav::before`):
  desenfoque, saturación y brillo (o la refracción), tinte `surface` al 50 %, un filo casi invisible, la sombra larga
  de su web y esquinas de 16 px; LA MISMA en todas las páginas (ya no hay vidrio ahumado: no hay fotos oscuras). La
  marca «Baby Caleb» escrita en Montserrat 700 navy y el sello del logo al lado; los enlaces navy en 500, como frase;
  la hamburguesa navy en el celular. Sin barra de anuncios encima.
* La portada (S02Hero.tsx): crema, con las dos manchas suaves detrás; el antetítulo en píldora, el titular navy, el
  subtítulo en `muted` y el botón naranja con letra navy; la foto del bebé con esquinas de 24 px, AL LADO del texto
  (debajo en el celular), sin velo ni filtro.
* La portada con los productos que elige Gerencia (models/portada.py): el mismo hero crema; las fotos se funden en el
  marco redondeado de la derecha, sin velo, sin degradado y sin nada que el visitante maneje.
* Capturas de referencia («golden») en tests/referencia/, comparadas con tolerancia.

Dos niveles:
1. Estilos computados (bloqueante): no dependen del motor de dibujo ni de las fuentes del sistema.
2. Píxeles contra las referencias (tolerancia `DCASA_TOLERANCIA_VISUAL`, 1.5 % por defecto, de píxeles
   con una diferencia > 40/255). Las referencias se regeneran A PROPÓSITO con
   `scripts/actualizar_referencias_visuales.sh` (ver docs/OPERACION.md). Si la comparación resulta
   frágil en CI (otra versión de Chrome, otro rasterizado), se sube la tolerancia por variable de
   entorno sin tocar el contrato de estilos.
"""
import base64
import contextlib
import io
import json
import logging
import os
import pathlib
from unittest.mock import patch

from PIL import Image, ImageChops, ImageDraw

from odoo.addons.website_dcasa.models.black_weekend import PARAM_ACTIVO, PARAM_FIN, PARAM_INICIO
from odoo.tests import HttpCase, tagged
from odoo.tests.common import ChromeBrowser, save_test_file

_logger = logging.getLogger(__name__)

REFERENCIAS = pathlib.Path(__file__).parent / 'referencia'
VAR_REGENERAR = 'DCASA_REFERENCIAS_VISUALES'       # =regenerar → reescribe las referencias
VAR_TOLERANCIA = 'DCASA_TOLERANCIA_VISUAL'         # % de píxeles distintos tolerado (manda sobre los defectos)
UMBRAL_PIXEL = 40                                  # diferencia por canal (0-255) que cuenta como distinto
# Tolerancias por defecto: 1.5 % en local (mismo Chromium que generó las referencias). En CI (variable
# CI=true, GitHub Actions) el Chrome del runner rasteriza texto y desenfoque distinto: el borde de cada
# letra ya suma 1-2 % de la cabecera sin cambio de diseño, así que ahí se afloja y el contrato de
# estilos computados (test_01/test_02, bloqueante) es el que garantiza el diseño.
TOLERANCIA_LOCAL, TOLERANCIA_CI = 1.5, 6.0


def modulos_propios_sin_instalar(env):
    """Los módulos de este sistema (``dcasa_*``) que no están instalados en la base de la prueba.

    Las referencias son las del sistema entero, como lo ven las clientas en staging: Mi cuenta pone su ícono en la
    cabecera, el catálogo publica los productos con su foto (la tarjetita del hero) y el chat de la tienda deja su
    burbuja en la esquina. Con solo una parte instalada la página es otra, y compararla daría diferencias falsas.
    """
    return env['ir.module.module'].search([('name', '=like', 'dcasa_%'), ('state', '=', 'uninstalled')]).mapped('name')
# Las referencias van SIN pérdida (la compresión con pérdida sola ya movía el 3 % de los píxeles de
# los bordes del texto por encima del umbral). El hero (una foto grande) se guarda y compara a la
# mitad de resolución: basta para ver una placa, un velo distinto o un texto movido, y pesa 4 veces menos.
REDUCCION = {'cabecera': 1, 'hero': 2}

# Anchos: escritorio y celular (iPhone 12/13/14).
VENTANAS = ((1440, 900), (390, 844))

# El contrato: la pastilla de babycaleb.com (tokens.css, `.bc-vidrio` y S01Nav.tsx).
VIDRIO = {'fondo': 'rgba(242, 239, 229, 0.5)', 'borde': 'rgba(27, 50, 70, 0.04)', 'texto': 'rgb(27, 50, 70)',
          'sombra': 'rgba(27, 50, 70, 0.1) 0px 8px 32px 0px'}
RADIO_PILDORA = '16px'                             # rounded-2xl
FILTRO_MATE = 'blur(16px) saturate(2.1) brightness(1.06)'
CREMA, NAVY, MUTED = 'rgb(249, 246, 237)', 'rgb(27, 50, 70)', 'rgba(27, 50, 70, 0.7)'
NARANJA, SAGE_STRONG = 'rgb(238, 146, 74)', 'rgb(83, 115, 92)'

# Deja la página quieta y determinista antes de medir o capturar: sin animaciones ni transiciones,
# entradas ya terminadas, barra de scroll oculta, fuentes e imágenes cargadas.
PREPARAR = """
    (async () => {
        const estilo = document.createElement('style');
        estilo.setAttribute('data-dcasa-contrato-visual', '');
        estilo.textContent = `
            *, *::before, *::after { animation: none !important; transition: none !important;
                                     caret-color: transparent !important; }
            [data-anim-entrada] > *, .o_dcasa_anim [data-anim], .o_dcasa_anim [data-anim-cascada] > *,
            .o_dcasa_anim [data-titular] .o_dcasa_palabra > span { opacity: 1 !important; transform: none !important; }
            html { scrollbar-width: none; }
            ::-webkit-scrollbar { display: none; }
        `;
        document.head.appendChild(estilo);
        const modulo = '@website_dcasa/js/animaciones';
        const listo = () => odoo.loader?.modules?.has(modulo) && document.body.getAttribute('is-ready') === 'true';
        for (let i = 0; i < 600 && !listo(); i++) {
            await new Promise((ok) => setTimeout(ok, 50));
        }
        // Fuentes propias y las fotos de lo que se captura (las imágenes diferidas de más abajo no
        // cargan sin desplazar la página: no se esperan). Tope de 15 s por si una no termina.
        const fotos = [...document.querySelectorAll(
            'header#top img, .o_dcasa_hero img, .o_dcasa_hero_vitrina .is-activa img')];
        await Promise.race([
            Promise.all([document.fonts.ready, ...fotos.filter((img) => !img.complete).map(
                (img) => new Promise((ok) => { img.onload = ok; img.onerror = ok; }))]),
            new Promise((ok) => setTimeout(ok, 15000)),
        ]);
        document.querySelector('.o_dcasa_filtros')?.pauseAnimations?.();
        window.scrollTo(0, 0);
        await new Promise((ok) => requestAnimationFrame(() => requestAnimationFrame(ok)));
        return listo();
    })()
"""

# Lo que se mide. Devuelve un objeto plano (se evalúa con returnByValue).
MEDIR = """
    (() => {
        const cs = (el, pseudo) => getComputedStyle(el, pseudo);
        const rect = (el) => {
            const r = el.getBoundingClientRect();
            return { x: r.left, y: r.top, width: r.width, height: r.height };
        };
        const visible = (el) => !!el && cs(el).display !== 'none' && cs(el).visibility !== 'hidden'
            && el.getBoundingClientRect().width > 0 && el.getBoundingClientRect().height > 0;
        const solapan = (a, b) => a.left < b.right - 1 && a.right > b.left + 1 && a.top < b.bottom - 1 && a.bottom > b.top + 1;
        const html = document.documentElement.classList;
        const cabecera = document.querySelector('header#top');
        // Odoo pinta dos barras (escritorio y celular, .o_header_mobile): se mide la visible.
        const nav = [...cabecera.querySelectorAll('.o_main_nav')].find(visible);
        const antes = cs(nav, '::before');
        const enlace = document.querySelector('#top_menu .nav-link:not(.active)');
        const menu = document.querySelector('#top_menu');
        // Hamburguesa: en Odoo 19 es un button.nav-link con el icono .navbar-toggler-icon.
        const icono = nav.querySelector('.navbar-toggler-icon');
        const hamburguesa = icono && icono.closest('button');
        const marca = nav.querySelector('.o_dcasa_marca');
        const res = {
            ancho: innerWidth,
            html: { refraccion: html.contains('o_dcasa_refraccion') },
            anuncios: !!cabecera.querySelector('.o_dcasa_anuncios'),
            pildora: {
                content: antes.content,
                backdropFilter: antes.backdropFilter || antes.webkitBackdropFilter || 'none',
                fondo: antes.backgroundColor,
                fondoImagen: antes.backgroundImage,
                borde: antes.borderTopColor,
                bordeAncho: antes.borderTopWidth,
                radio: antes.borderTopLeftRadius,
                radioNav: cs(nav).borderTopLeftRadius,
                sombra: antes.boxShadow,
                position: antes.position,
                alto: Math.round(rect(nav).height),
                ancho: Math.round(rect(nav).width),
            },
            marca: marca ? { texto: marca.textContent.trim(), color: cs(marca).color, peso: cs(marca).fontWeight,
                             fuente: cs(marca).fontFamily, unaLinea: marca.getBoundingClientRect().height < 40 } : null,
            menu: { visible: visible(menu), color: enlace ? cs(enlace).color : null,
                    fuente: enlace ? cs(enlace).fontFamily : null, peso: enlace ? cs(enlace).fontWeight : null,
                    mayusculas: enlace ? cs(enlace).textTransform : null },
            hamburguesa: { visible: visible(hamburguesa), icono: icono ? cs(icono).backgroundImage : null,
                           filtroIcono: icono ? cs(icono).filter : null },
            cta: nav.querySelector('.btn_cta') ? true : null,
            logo: !!nav.querySelector('.navbar-brand img'),
            cabecera: rect(cabecera),
        };
        const hero = document.querySelector('.o_dcasa_hero:not(.o_dcasa_hero_compacto)');
        const vitrina = document.querySelector('.o_dcasa_hero_vitrina');
        const textoDelHero = (raiz) => {
            const titulo = raiz.querySelector('.o_dcasa_display');
            const sub = raiz.querySelector('.o_dcasa_hero_sub');
            const kicker = raiz.querySelector('.o_dcasa_hero_texto > .o_dcasa_kicker');
            const boton = raiz.querySelector('.o_dcasa_hero_texto .btn-primary');
            return {
                colores: { titulo: cs(titulo).color, sub: cs(sub).color, kicker: cs(kicker).color },
                titulo: { mayusculas: cs(titulo).textTransform, peso: cs(titulo).fontWeight, fuente: cs(titulo).fontFamily,
                          espaciado: cs(titulo).letterSpacing, tamano: parseFloat(cs(titulo).fontSize) },
                pildora: { radio: cs(kicker).borderTopLeftRadius, borde: cs(kicker).borderTopStyle,
                           mayusculas: cs(kicker).textTransform, tamano: cs(kicker).fontSize },
                boton: { fondo: cs(boton).backgroundColor, color: cs(boton).color, peso: cs(boton).fontWeight,
                         pastilla: parseFloat(cs(boton).borderTopLeftRadius) >= boton.getBoundingClientRect().height / 2 - 1,
                         brillo: cs(boton).boxShadow, href: boton.getAttribute('href') },
                halo: cs(titulo).textShadow,
                manchas: [...raiz.querySelectorAll('.o_dcasa_hero_mancha')].map((m) => cs(m).filter),
                fondo: cs(raiz).backgroundColor,
                texto: titulo.closest('.o_dcasa_hero_texto').getBoundingClientRect(),
            };
        };
        if (vitrina) {
            const marco = vitrina.querySelector('.o_dcasa_vitrina_fotos');
            const img = vitrina.querySelector('.o_dcasa_vitrina_foto.is-activa img');
            const panel = vitrina.querySelector('.o_dcasa_vitrina_panel');
            const t = textoDelHero(vitrina);
            const b = marco.getBoundingClientRect();
            res.vitrina = {
                ...t,
                rect: rect(vitrina),
                panelFondo: cs(panel).backgroundColor,
                panelImagen: cs(panel).backgroundImage,
                marcoRadio: cs(marco).borderTopLeftRadius,
                marcoFondoImagen: cs(marco).backgroundImage,
                opacidadFoto: parseFloat(cs(img).opacity),
                opacidadDiapositiva: parseFloat(cs(img.closest('.o_dcasa_vitrina_foto')).opacity),
                filtroFoto: cs(img).filter,
                mezclaFoto: cs(img).mixBlendMode,
                capas: ['::before', '::after'].flatMap((p) => [cs(marco, p).content, cs(panel, p).content,
                                                             cs(vitrina.querySelector('.o_dcasa_vitrina'), p).content]),
                imagenCubreElMarco: (() => {
                    const i = img.getBoundingClientRect();
                    return i.left <= b.left + 1 && i.right >= b.right - 1 && i.top <= b.top + 1 && i.bottom >= b.bottom - 1;
                })(),
                textoSobreFoto: solapan(t.texto, b),
                mandos: vitrina.querySelectorAll('.o_dcasa_vitrina_barra, .o_dcasa_vitrina_boton,'
                    + ' .o_dcasa_vitrina_nombre, .o_dcasa_vitrina_fotos a').length,
            };
            delete res.vitrina.texto;
        }
        if (hero) {
            const img = hero.querySelector('.o_dcasa_hero_media img');
            const t = textoDelHero(hero);
            const b = img.getBoundingClientRect();
            res.hero = {
                ...t,
                rect: rect(hero),
                fondoImagen: cs(hero).backgroundImage,
                opacidadFoto: parseFloat(cs(img).opacity),
                filtroFoto: cs(img).filter,
                mezclaFoto: cs(img).mixBlendMode,
                radioFoto: cs(img).borderTopLeftRadius,
                pildoraVerde: (() => { const p = hero.querySelector('.o_dcasa_hero_pildora');
                    return p ? { fondo: cs(p).backgroundColor, color: cs(p).color, texto: p.textContent.trim() } : null; })(),
                capas: ['::before', '::after'].flatMap((p) => [cs(img.parentElement, p).content]),
                textoSobreFoto: solapan(t.texto, b),
                fotoDebajo: b.top >= t.texto.bottom - 1,
                fotoAlLado: b.left >= t.texto.right - 1,
            };
            delete res.hero.texto;
        }
        return res;
    })()
"""


def _caja_de_estudio(color):
    """Foto 3:4 de una caja de pañales sobre un fondo de estudio claro, dibujada: el contrato no depende del catálogo
    real."""
    imagen = Image.new('RGB', (900, 1200), (226, 232, 224))
    dibujo = ImageDraw.Draw(imagen)
    dibujo.rectangle((0, 960, 900, 1200), fill=(206, 214, 204))           # mesa
    dibujo.rectangle((220, 300, 680, 980), fill=color)                     # caja
    dibujo.rectangle((300, 620, 600, 900), fill=(245, 245, 243))           # paquete
    dibujo.rectangle((360, 680, 540, 800), fill=(150, 190, 210))           # la foto del paquete
    salida = io.BytesIO()
    imagen.save(salida, 'JPEG', quality=92)
    return base64.b64encode(salida.getvalue())


def _comparar(referencia, actual, umbral=UMBRAL_PIXEL):
    """% de píxeles cuya diferencia máxima por canal supera `umbral`, y la máscara de esos píxeles."""
    diff = ImageChops.difference(referencia.convert('RGB'), actual.convert('RGB'))
    r, g, b = diff.split()
    maximo = ImageChops.lighter(ImageChops.lighter(r, g), b)
    mascara = maximo.point(lambda v: 255 if v > umbral else 0)
    distintos = mascara.histogram()[255]
    return 100.0 * distintos / (mascara.width * mascara.height), mascara


@tagged('post_install', '-at_install')
class TestContratoVisual(HttpCase):
    # Medidas y capturas por (página, ancho): se toman una sola vez por clase (cada apertura de
    # Chrome cuesta segundos) y las comparten los tres tests.
    _medido = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        param = cls.env['ir.config_parameter'].sudo()
        param.set_param(PARAM_ACTIVO, '1')
        param.set_param(PARAM_INICIO, '')
        param.set_param(PARAM_FIN, '')
        cls.producto = cls.env['product.template'].create({
            'name': 'Pañal del contrato visual', 'list_price': 45.0, 'is_published': True,
            'dcasa_black_weekend': True,
        })
        cls.paginas = {'portada': '/', 'portada-carrusel': '/', 'tienda': '/shop', 'ficha': cls.producto.website_url,
                       'socios': '/socios', 'black-weekend': '/promociones'}
        # Dos cajas «de estudio» dibujadas para las fotos del hero.
        cls.Diapositiva = cls.env['dcasa.portada.diapositiva']
        cls.cajas_carrusel = cls.env['product.template'].browse()
        for nombre, color in (('Caja verde del contrato visual', (170, 205, 170)),
                              ('Caja café del contrato visual', (190, 150, 110))):
            cls.cajas_carrusel |= cls.env['product.template'].create({
                'name': nombre, 'list_price': 45.0, 'is_published': True, 'image_1920': _caja_de_estudio(color),
            })

    # ------------------------------------------------------------------ Chrome
    @contextlib.contextmanager
    def _chrome(self, ancho, alto):
        """Chrome headless como en HttpCase.browser_js, pero devolviendo el navegador para evaluar
        código con resultado y pedir capturas. Viewport fijo y prefers-reduced-motion: reduce
        (emulado por el protocolo) para que la página sea determinista."""
        self.browser_size = f'{ancho}x{alto}'
        browser = ChromeBrowser(self, headless=True)
        with self.allow_requests(browser=browser), contextlib.ExitStack() as atexit:
            atexit.callback(self._wait_remaining_requests)
            atexit.enter_context(browser.cleanup)
            if 'bus.bus' in self.env.registry:    # igual que browser_js: el websocket del bus en tests
                from odoo.addons.bus.websocket import CloseCode, WebsocketConnectionHandler, _kick_all  # noqa: PLC0415
                atexit.callback(_kick_all, CloseCode.KILL_NOW)
                atexit.enter_context(patch.object(
                    WebsocketConnectionHandler, 'websocket_allowed', return_value=True))
            self.authenticate(None, None, browser=browser)
            self.cr.flush()
            self.cr.clear()
            browser._websocket_request('Emulation.setEmulatedMedia', params={
                'features': [{'name': 'prefers-reduced-motion', 'value': 'reduce'}]})
            yield browser

    def _evaluar(self, browser, expresion, timeout=60):
        res = browser._websocket_request('Runtime.evaluate', params={
            'expression': expresion, 'awaitPromise': True, 'returnByValue': True}, timeout=timeout)
        resultado = res['result']
        self.assertNotEqual(resultado.get('subtype'), 'error', f'JavaScript falló: {res}')
        return resultado.get('value')

    def _capturar(self, browser, caja, alto_ventana):
        """PNG del recorte `caja` (px CSS), acotado a la ventana."""
        alto = min(caja['height'], alto_ventana - caja['y'])
        datos = browser._websocket_request('Page.captureScreenshot', params={
            'format': 'png', 'captureBeyondViewport': False,
            'clip': {'x': caja['x'], 'y': caja['y'], 'width': caja['width'], 'height': alto, 'scale': 1},
        }, timeout=60)['data']
        return Image.open(io.BytesIO(base64.b64decode(datos))).convert('RGB')

    def _medir_todo(self):
        if TestContratoVisual._medido is not None:
            return TestContratoVisual._medido
        medido = {}
        for ancho, alto in VENTANAS:
            for nombre, ruta in self.paginas.items():
                # La campaña encendida solo para su página: con campaña, el menú suma «Promociones» en todas, y el
                # contrato de las demás es la cabecera de todos los días (campaña del sitio, 2026-11-15).
                encendida = '1' if nombre == 'black-weekend' else '0'
                self.env['ir.config_parameter'].sudo().set_param(PARAM_ACTIVO, encendida)
                # El carrusel de la portada solo para su página; las demás, con el hero de siempre.
                self.Diapositiva.search([]).unlink()
                if nombre == 'portada-carrusel':
                    for orden, producto in enumerate(self.cajas_carrusel, start=1):
                        self.Diapositiva.create({'product_tmpl_id': producto.id, 'sequence': orden})
                self.env.flush_all()
                with self._chrome(ancho, alto) as browser:
                    browser.navigate_to(self.base_url() + ruta, wait_stop=True)
                    self.assertTrue(browser._wait_ready(), f'{ruta} no terminó de cargar')
                    self.assertTrue(self._evaluar(browser, PREPARAR, timeout=90),
                                    f'{ruta} a {ancho}px: el JavaScript del sitio no llegó a cargar')
                    medidas = self._evaluar(browser, MEDIR)
                    capturas = {'cabecera': self._capturar(browser, medidas['cabecera'], alto)}
                    if medidas.get('hero') or medidas.get('vitrina'):
                        caja = (medidas.get('hero') or medidas['vitrina'])['rect']
                        capturas['hero'] = self._capturar(browser, caja, alto)
                    capturas = {parte: img.reduce(REDUCCION[parte]) for parte, img in capturas.items()}
                    excepcion = browser._result.done() and browser._result.exception()
                    self.assertFalse(excepcion, f'{ruta} a {ancho}px: error de JavaScript en la página: {excepcion}')
                    self.assertFalse(browser.had_failure, f'{ruta} a {ancho}px: console.error en la página')
                    _logger.info('Contrato visual %s @%s: %s', nombre, ancho, json.dumps(medidas['pildora']))
                    medido[nombre, ancho] = {'medidas': medidas, 'capturas': capturas}
        TestContratoVisual._medido = medido
        return medido

    # ------------------------------------------------------------------ 1. estilos (bloqueante)
    def test_01_pastilla_de_vidrio_crema_en_todas_las_paginas(self):
        medido = self._medir_todo()
        for ancho, _alto in VENTANAS:
            firmas, tintes = {}, {}
            for nombre in self.paginas:
                m = medido[nombre, ancho]['medidas']
                p = m['pildora']
                with self.subTest(pagina=nombre, ancho=ancho):
                    self._revisar_pildora(m, ancho)
                # Firma común a todo el sitio: geometría, filtro y tinte (la misma pastilla en todas las páginas).
                firmas[nombre] = {k: v for k, v in p.items()}
                tintes[nombre] = {'texto': m['menu']['color'], 'hamburguesa': m['hamburguesa']['icono'],
                                  'refraccion': m['html']['refraccion'], 'marca': m['marca']}
            with self.subTest(ancho=ancho, regla='la misma pastilla en todas las páginas'):
                base, tinte = firmas['tienda'], tintes['tienda']
                for nombre, firma in firmas.items():
                    self.assertEqual(firma, base, f'la pastilla de {nombre} difiere de la tienda a {ancho}px')
                    self.assertEqual(tintes[nombre], tinte, f'el vidrio de {nombre} difiere a {ancho}px')

    def _revisar_pildora(self, m, ancho):
        """El contrato de la pastilla en una página, a un ancho."""
        p = m['pildora']
        self.assertEqual(m['ancho'], ancho, 'viewport fijo')
        self.assertFalse(m['anuncios'], 'sin barra de anuncios encima (docs/MARCA_BABY_CALEB.md)')
        self.assertNotIn(p['content'], ('none', 'normal'), 'la pastilla (::before) existe')
        self.assertEqual(p['position'], 'absolute')
        filtro = p['backdropFilter']
        self.assertIn('blur(', filtro, f'sin desenfoque: {filtro}')
        self.assertIn('saturate(', filtro, f'sin saturación: {filtro}')
        if m['html']['refraccion']:
            self.assertIn('url(', filtro, 'con o_dcasa_refraccion el filtro lleva url(#dcasa-liquido)')
            self.assertIn('blur(3px)', filtro)
        else:
            self.assertEqual(filtro, FILTRO_MATE)
        self.assertEqual(p['fondo'], VIDRIO['fondo'], 'el vidrio crema de su web: surface al 50 %')
        self.assertEqual(p['fondoImagen'], 'none', 'sin degradados')
        self.assertEqual(p['borde'], VIDRIO['borde'])
        self.assertEqual(p['bordeAncho'], '1px')
        self.assertEqual(p['sombra'], VIDRIO['sombra'], 'la sombra larga de su pastilla')
        self.assertEqual(p['radio'], RADIO_PILDORA, 'esquinas del vidrio')
        self.assertEqual(p['radioNav'], RADIO_PILDORA, 'esquinas del nav')
        self.assertFalse(m['logo'], 'solo el nombre escrito, sin el sello (S01Nav.tsx, 2026-11-24)')
        self.assertIsNone(m['cta'], 'sin botón «Escríbenos» en la pastilla')
        marca = m['marca']
        self.assertTrue(marca, 'la marca escrita en la pastilla')
        self.assertEqual(marca['texto'], 'Baby Caleb')
        self.assertEqual((marca['color'], marca['peso']), (NAVY, '700'), 'Montserrat 700 navy')
        self.assertIn('Montserrat', marca['fuente'])
        self.assertTrue(marca['unaLinea'], 'el nombre de la marca no se parte en dos líneas')
        if ancho >= 992:
            self.assertTrue(m['menu']['visible'], 'menú visible en escritorio')
            self.assertFalse(m['hamburguesa']['visible'], 'sin hamburguesa en escritorio')
            self.assertEqual(m['menu']['color'], VIDRIO['texto'], 'enlaces navy')
            self.assertIn('Montserrat', m['menu']['fuente'])
            self.assertEqual(m['menu']['peso'], '500')
            self.assertEqual(m['menu']['mayusculas'], 'none', 'los enlaces como frase, no en caja alta')
        else:
            self.assertTrue(m['hamburguesa']['visible'], 'hamburguesa visible en el celular')
            self.assertFalse(m['menu']['visible'], 'en el celular el menú va plegado')
            self.assertIn('1B3246', m['hamburguesa']['icono'] or '', 'la hamburguesa en navy')
            self.assertEqual(m['hamburguesa']['filtroIcono'], 'none')

    def _revisar_texto_del_hero(self, h, ancho):
        for cual, color in h['colores'].items():
            esperado = {'titulo': NAVY, 'sub': MUTED, 'kicker': SAGE_STRONG}[cual]
            self.assertEqual(color, esperado, f'{cual} a {ancho}px')
        self.assertEqual(h['fondo'], CREMA, 'el hero en crema, nunca negro ni azul')
        self.assertEqual(h['titulo']['mayusculas'], 'none', 'el titular como frase')
        self.assertEqual(h['titulo']['peso'], '700')
        self.assertIn('Montserrat', h['titulo']['fuente'])
        self.assertTrue(h['titulo']['espaciado'].startswith('-'), 'letter-spacing negativo (-0.03em)')
        self.assertEqual(h['halo'], 'none', 'sin halo: la letra va sobre el crema, no sobre una foto')
        self.assertEqual(h['pildora']['radio'], '999px', 'el antetítulo en píldora')
        self.assertEqual(h['pildora']['borde'], 'solid')
        self.assertEqual(h['pildora']['mayusculas'], 'uppercase')
        self.assertEqual(h['pildora']['tamano'], '12px')
        self.assertEqual((h['boton']['fondo'], h['boton']['color'], h['boton']['peso']), (NARANJA, NAVY, '700'),
                         'el botón principal: naranja con letra navy, en 700')
        self.assertTrue(h['boton']['pastilla'], 'en pastilla')
        self.assertIn('rgb(238, 146, 74)', h['boton']['brillo'], 'con el resplandor suave del mismo naranja')
        self.assertEqual(h['boton']['href'], '/shop')
        self.assertEqual(len(h['manchas']), 2, 'las dos manchas suaves de su hero')
        for filtro in h['manchas']:
            self.assertIn('blur(', filtro)

    def test_02_hero_de_la_portada_en_crema_con_la_foto_del_bebe(self):
        medido = self._medir_todo()
        for ancho, _alto in VENTANAS:
            h = medido['portada', ancho]['medidas'].get('hero')
            with self.subTest(ancho=ancho):
                self.assertTrue(h, 'la portada abre con el hero (.o_dcasa_hero)')
                self._revisar_texto_del_hero(h, ancho)
                self.assertEqual(h['fondoImagen'], 'none', 'sin foto de fondo ni degradado detrás del texto')
                self.assertEqual(h['opacidadFoto'], 1.0, 'la foto sin velo')
                self.assertEqual(h['filtroFoto'], 'none')
                self.assertEqual(h['mezclaFoto'], 'normal')
                self.assertEqual(h['radioFoto'], '24px', 'la foto con esquinas redondeadas (rounded-3xl)')
                for capa in h['capas']:
                    self.assertIn(capa, ('none', 'normal'), 'ninguna capa encima de la foto')
                self.assertFalse(h['textoSobreFoto'], 'el texto va sobre el crema, no encima de la foto')
                if ancho >= 768:
                    self.assertTrue(h['fotoAlLado'], 'en la computadora la foto va a la derecha del texto')
                else:
                    self.assertTrue(h['fotoDebajo'], 'en el celular la foto va debajo del texto')
                self.assertEqual(h['pildoraVerde'], {'fondo': 'rgb(145, 201, 162)', 'color': NAVY,
                                                     'texto': 'Sin cloro · Sin perfumes'}, 'la píldora verde sobre la foto')

    def test_02b_el_hero_con_productos_es_el_mismo_hero_crema(self):
        """Con productos elegidos (Sitio web › Carrusel de la portada) el hero es el mismo: el texto sobre el crema y las
        fotos fundiéndose en el marco redondeado, sin velo, sin degradado y sin nada que el visitante maneje."""
        medido = self._medir_todo()
        for ancho, _alto in VENTANAS:
            v = medido['portada-carrusel', ancho]['medidas'].get('vitrina')
            with self.subTest(ancho=ancho):
                self.assertTrue(v, 'con productos elegidos, la portada abre con sus fotos (.o_dcasa_hero_vitrina)')
                self._revisar_texto_del_hero(v, ancho)
                self.assertEqual(v['opacidadFoto'], 1.0, 'la foto sin velo')
                self.assertEqual(v['opacidadDiapositiva'], 1.0)
                self.assertEqual(v['filtroFoto'], 'none')
                self.assertEqual(v['mezclaFoto'], 'normal')
                self.assertEqual(v['marcoFondoImagen'], 'none', 'sin degradado sobre las fotos')
                for capa in v['capas']:
                    self.assertIn(capa, ('none', 'normal'), 'ninguna capa ::before/::after sobre la foto o el texto')
                self.assertEqual(v['panelFondo'], 'rgba(0, 0, 0, 0)', 'sin placa detrás del texto')
                self.assertEqual(v['panelImagen'], 'none')
                self.assertEqual(v['marcoRadio'], '24px', 'el marco con las esquinas de la foto del hero')
                self.assertTrue(v['imagenCubreElMarco'], 'la foto llena su marco')
                self.assertFalse(v['textoSobreFoto'], 'el texto va al lado de las fotos, no encima')
                self.assertEqual(v['mandos'], 0, 'sin flechas, barras, nombres ni enlaces')

    # ------------------------------------------------------------------ 2. píxeles (tolerancia)
    def test_03_capturas_de_referencia(self):
        regenerar = os.environ.get(VAR_REGENERAR, '').lower() == 'regenerar'
        faltan = modulos_propios_sin_instalar(self.env)
        if faltan:
            aviso = (f'Las referencias son del sistema entero y faltan {len(faltan)} módulos propios '
                     f'({", ".join(faltan[:5])}…): los píxeles se comparan con scripts/test.sh sin módulos (todos) o '
                     'se regeneran con scripts/actualizar_referencias_visuales.sh.')
            if regenerar:
                self.fail(aviso)
            self.skipTest(aviso)
        medido = self._medir_todo()
        tolerancia = float(os.environ.get(VAR_TOLERANCIA)
                           or (TOLERANCIA_CI if os.environ.get('CI') else TOLERANCIA_LOCAL))
        if regenerar:
            REFERENCIAS.mkdir(exist_ok=True)
        for (nombre, ancho), datos in medido.items():
            for parte, imagen in datos['capturas'].items():
                archivo = REFERENCIAS / f'{parte}-{nombre}-{ancho}.webp'
                if regenerar:
                    imagen.save(archivo, 'WEBP', lossless=True, method=6)
                    _logger.info('Referencia visual escrita: %s (%sx%s)', archivo, *imagen.size)
                    continue
                with self.subTest(parte=parte, pagina=nombre, ancho=ancho):
                    self.assertTrue(archivo.exists(), f'falta {archivo.name}: córrela con '
                                    'scripts/actualizar_referencias_visuales.sh y súbela en el mismo commit')
                    referencia = Image.open(archivo).convert('RGB')
                    if referencia.size != imagen.size:
                        self._guardar(nombre, ancho, parte, imagen)
                        self.fail(f'{archivo.name}: la {parte} cambió de tamaño: referencia {referencia.size}, '
                                  f'ahora {imagen.size}. Si es a propósito, regenera las referencias.')
                    distintos, mascara = _comparar(referencia, imagen)
                    _logger.info('Contrato visual %s/%s @%s: %.2f %% de píxeles distintos',
                                 parte, nombre, ancho, distintos)
                    if distintos > tolerancia:
                        self._guardar(nombre, ancho, parte, imagen, mascara)
                    self.assertLessEqual(distintos, tolerancia, f'{archivo.name}: {distintos:.2f} % de píxeles '
                                         f'distintos (> {tolerancia} %). Si el cambio es a propósito, regenera '
                                         'las referencias en el mismo commit (docs/OPERACION.md).')
        if regenerar:
            _logger.info('Referencias visuales regeneradas: %s',
                         ', '.join(sorted(p.name for p in REFERENCIAS.glob('*.webp'))))

    def _guardar(self, nombre, ancho, parte, imagen, mascara=None):
        """Deja la captura actual (y la máscara de diferencias) junto a las capturas de Odoo."""
        for sufijo, img in (('actual', imagen), ('diff', mascara)):
            if img is None:
                continue
            buf = io.BytesIO()
            img.save(buf, 'PNG')
            save_test_file(f'{parte}_{nombre}_{ancho}_{sufijo}'.replace('-', '_'), buf.getvalue(),
                           'visual_', logger=_logger, document_type='Contrato visual', directory='contrato_visual')
