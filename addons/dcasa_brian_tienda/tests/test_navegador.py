# ruff: noqa: E501  (JavaScript del navegador embebido en texto)
"""La página de verdad en Chrome, con el Worker simulado (tests/worker_simulado.py): la burbuja a 360, 390, 430 y
1366 px, el chat de punta a punta (saludo, tarjetas de Odoo, «te lo puse en el carrito», la ubicación, las estrellas),
la ventana ampliada, Esc, el foco, que no tape la barra de la ficha ni el botón de WhatsApp de la ficha, el movimiento
reducido y el micrófono de las notas de voz (con el micrófono de prueba de Chrome). Y la marca Baby Caleb
(docs/MARCA_BABY_CALEB.md): la burbuja naranja con el globo navy, quieta; la cabecera naranja con todo en navy; el
panel crema; nada del robot ni del azul de D'CASA."""
import contextlib
import os
from datetime import datetime
from unittest.mock import patch

import pytz

from odoo import Command
from odoo.addons.dcasa_envios.tests.common import importar
from odoo.tests import common as comun
from odoo.tests import new_test_user, tagged
from odoo.tests.common import TEST_CURSOR_COOKIE_NAME, ChromeBrowser

from .common import TOKEN_ODOO, TOKEN_WORKER, TiendaCase
from .worker_simulado import WorkerSimulado

ALTO = 800
# Chrome con un micrófono de prueba (un pitido) y el permiso ya dado: MediaRecorder graba de verdad.
MICROFONO_DE_PRUEBA = ('--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream')
# Los colores de la marca, como los devuelve getComputedStyle.
NARANJA = 'rgb(238, 146, 74)'     # accent: relleno
NAVY = 'rgb(27, 50, 70)'          # fg y accent-fg: la letra y los íconos sobre el naranja (5.56)
CREMA = 'rgb(249, 246, 237)'      # bg
SUPERFICIE = 'rgb(242, 239, 229)'  # surface
NARANJA_TEXTO = 'rgb(152, 93, 47)'  # accent-strong
AZUL_DCASA = 'rgb(19, 64, 177)'
COSTA = (8.9415, -79.8415)    # Costa Inventada, del fixture sintético de envíos

ESPERAR = """
    const esperar = (ms) => new Promise((ok) => setTimeout(ok, ms));
    const hasta = async (fn, que, ms = 20000) => {
        const t0 = Date.now();
        while (Date.now() - t0 < ms) { const v = fn(); if (v) { return v; } await esperar(100); }
        throw new Error('No llegó: ' + que);
    };
    const caja = (el) => { const r = el.getBoundingClientRect(); return { x: r.left, y: r.top, ancho: r.width, alto: r.height, derecha: r.right, abajo: r.bottom }; };
    const globos = () => [...document.querySelectorAll('#o_dcbt_panel .o_dcbt_globo')].map((g) => g.textContent);
    const chip = (texto) => [...document.querySelectorAll('#o_dcbt_panel .o_dcbt_chip')].find((c) => c.textContent.includes(texto));
    await hasta(() => document.readyState === 'complete' && document.querySelector('button.o_dcbt_burbuja'), 'la burbuja');
"""

CHAT = """(async () => {
    /*ESPERAR*/
    const res = { errores: [] };
    const burbuja = document.querySelector('button.o_dcbt_burbuja');
    burbuja.click();
    await hasta(() => globos().some((g) => g.includes('Hola, soy Andrés. ¿Qué buscas hoy?')), 'el saludo');
    res.saludos = globos().filter((g) => g.includes('Hola, soy Andrés')).length;
    res.expandido = burbuja.getAttribute('aria-expanded');
    // Las sugerencias dependen del catálogo (las dos categorías con más productos): se escribe «Colchones», que es lo
    // mismo que manda el botón.
    await hasta(() => document.querySelector('#o_dcbt_panel .o_dcbt_chip'), 'las sugerencias del saludo');
    const campo0 = document.querySelector('#o_dcbt_texto');
    campo0.value = 'Colchones';
    campo0.dispatchEvent(new Event('input', { bubbles: true }));
    document.querySelector('#o_dcbt_panel .o_dcbt_composer').requestSubmit();
    const tarjeta = await hasta(() => document.querySelector('#o_dcbt_panel .o_dcbt_tarjeta'), 'las tarjetas');
    res.tarjeta = tarjeta.querySelector('h3').textContent;
    res.precio = tarjeta.querySelector('.o_dcbt_precio').textContent;
    res.imagen = tarjeta.querySelector('img') ? tarjeta.querySelector('img').getAttribute('src') : null;
    res.ver = tarjeta.querySelector('.o_dcbt_btn_ver').getAttribute('href');
    tarjeta.querySelector('[data-paso="1"]').click();          // 2
    tarjeta.querySelector('[data-agregar]').click();
    await hasta(() => document.querySelector('#o_dcbt_panel [data-carrito] .o_dcbt_linea_carrito'), 'el carrito');
    res.listo = globos().filter((g) => g.startsWith('Listo, te puse 2 en el carrito')).length;
    res.navbar = (document.querySelector('.my_cart_quantity') || {}).textContent;
    // Brian propone (el visitante lo pidió) y la página lo aplica en Odoo y le cuenta el resultado.
    const escribir = (texto) => {
        const campo = document.querySelector('#o_dcbt_texto');
        campo.value = texto;
        campo.dispatchEvent(new Event('input', { bubbles: true }));
        document.querySelector('#o_dcbt_panel .o_dcbt_composer').requestSubmit();
    };
    escribir('Ponlo en el carrito, por favor');
    await hasta(() => globos().some((g) => g === 'Listo, te lo puse en el carrito. Gracias por escogernos.'), 'el «listo» de Brian');
    await hasta(() => [...document.querySelectorAll('[data-carrito] .o_dcbt_carrito_total')].some((t) => t.textContent.includes('3 artículos')), 'el carrito con 3');
    res.total = [...document.querySelectorAll('[data-carrito] .o_dcbt_carrito_total strong')].pop().textContent;
    res.pdf = document.querySelector('#o_dcbt_panel a[href$="cotizacion.pdf"]') ? true : false;
    // El envío con la ubicación del teléfono.
    (await hasta(() => chip('envío'), 'la sugerencia del envío')).click();
    await hasta(() => chip('Usar mi ubicación actual'), 'el botón de la ubicación');
    res.privacidad = !!document.querySelector('#o_dcbt_panel .o_dcbt_privacidad');
    chip('Usar mi ubicación actual').click();
    const envio = await hasta(() => document.querySelector('#o_dcbt_panel .o_dcbt_envio_texto'), 'el envío');
    res.envio = envio.textContent;
    res.lugar = envio.parentElement.querySelector('h3').textContent;
    // Las estrellas.
    escribir('Gracias, Brian');
    (await hasta(() => document.querySelector('#o_dcbt_panel .o_dcbt_estrella[data-estrellas="5"]'), 'las estrellas')).click();
    await hasta(() => globos().some((g) => g.includes('Gracias por calificarme')), 'las gracias');
    // La ventana ampliada (en el celular, la cuadrícula) y Esc: primero vuelve al tamaño normal, después cierra.
    document.querySelector('#o_dcbt_panel .o_dcbt_cab_boton[aria-pressed]').click();
    await esperar(500);
    const panel = document.querySelector('#o_dcbt_panel');
    res.ampliado = { clase: panel.classList.contains('o_dcbt_ampliado'), ancho: panel.getBoundingClientRect().width,
                     vitrina: document.querySelectorAll('#o_dcbt_panel .o_dcbt_vitrina_grid .o_dcbt_tarjeta').length };
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    await esperar(400);
    res.trasPrimerEsc = { abierto: !panel.hidden, ampliado: panel.classList.contains('o_dcbt_ampliado') };
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    await hasta(() => panel.hidden, 'que se cierre');
    await esperar(400);
    res.foco = document.activeElement === document.querySelector('button.o_dcbt_burbuja');
    res.sinScrollDeLado = document.documentElement.scrollWidth <= innerWidth;
    return res;
})()""".replace('/*ESPERAR*/', ESPERAR)

BURBUJA = """(async () => {
    /*ESPERAR*/
    const burbuja = document.querySelector('button.o_dcbt_burbuja');
    await esperar(2200);   // la burbuja entra
    const m = window.odoo.loader.modules.get('@dcasa_brian_tienda/js/brian_tienda');
    const pagina = m.tipoDePagina(location.pathname);
    const estilo = getComputedStyle(burbuja);
    const icono = burbuja.querySelector('.o_dcbt_burbuja_ico svg');
    const res = {
        pantalla: innerWidth, alto: innerHeight, burbuja: { ...caja(burbuja), ancho: burbuja.offsetWidth, altoB: burbuja.offsetHeight }, tipo: pagina.tipo,
        aparteAlCargar: burbuja.classList.contains('o_dcbt_aparte'),
        marca: { fondo: estilo.backgroundColor, color: estilo.color, redondo: estilo.borderTopLeftRadius,
                 icono: Boolean(icono), colorIcono: icono ? getComputedStyle(icono).color : null,
                 imagenes: burbuja.querySelectorAll('img').length },
        etiqueta: burbuja.getAttribute('aria-label'), sinScrollDeLado: document.documentElement.scrollWidth <= innerWidth,
    };
    const barra = document.querySelector('#o_wsale_cta_wrapper');
    if (barra && getComputedStyle(barra).position === 'fixed') {
        res.barra = caja(barra);
    }
    const wa = document.querySelector('.o_dcasa_wa_producto');
    if (wa) {
        // Se lleva el botón de WhatsApp de la ficha justo detrás de la burbuja: la burbuja se hace a un lado.
        const b = burbuja.getBoundingClientRect();
        window.scrollBy(0, wa.getBoundingClientRect().top - (b.top + b.height / 2) + wa.getBoundingClientRect().height / 2);
        await esperar(500);
        res.wa = caja(wa);
        res.aparte = burbuja.classList.contains('o_dcbt_aparte');
        const r = burbuja.getBoundingClientRect();
        res.tapaVisible = !res.aparte && r.left < res.wa.derecha && r.right > res.wa.x && r.top < res.wa.abajo && r.bottom > res.wa.y;
        window.scrollBy(0, wa.getBoundingClientRect().bottom + 40);   // el botón ya pasó: la burbuja vuelve
        await esperar(500);
        res.vuelve = !burbuja.classList.contains('o_dcbt_aparte');
    }
    return res;
})()""".replace('/*ESPERAR*/', ESPERAR)

QUIETO = """(async () => {
    /*ESPERAR*/
    document.querySelector('button.o_dcbt_burbuja').click();
    await hasta(() => globos().some((g) => g.includes('Hola, soy Andrés')), 'el saludo');
    await esperar(300);
    const delChat = (a) => a.effect && a.effect.target && a.effect.target.closest && a.effect.target.closest('#o_dcasa_brian');
    return { animaciones: document.getAnimations().filter((a) => a.playState === 'running' && delChat(a)).map((a) => a.animationName || 'waapi'),
             reducido: matchMedia('(prefers-reduced-motion: reduce)').matches };
})()""".replace('/*ESPERAR*/', ESPERAR)

PURAS = """(() => {
    const m = window.odoo.loader.modules.get('@dcasa_brian_tienda/js/brian_tienda');
    return {
        urls: [m.urlPropia('/shop/x-1'), m.urlPropia('javascript:alert(1)'), m.urlPropia('https://malo.example.com/x'),
               m.urlPropia('https://dcasapty.com/shop/x-2'), m.urlPropia('//malo.example.com/x')],
        precio: m.partirPrecio('$278.00 + ITBMS'),
        wa: m.mensajeWhatsApp({ lineas: [{ cantidad: 2, nombre: 'Colchón' }] }),
        tipos: [m.tipoDePagina('/').tipo, m.tipoDePagina('/shop').tipo, m.tipoDePagina('/shop/cart').tipo,
                m.tipoDePagina('/socios').tipo],
        // El robot de D'CASA y sus poses se fueron con la marca (2026-11-19): el JS ya no los trae.
        delRobot: ['POSES', 'poseDePagina', 'SECCIONES', 'posesDeSecciones', 'seccionesDeLaPagina', 'seccionActiva',
                   'esDeNoche', 'MIN_ENTRE_CAMBIOS_MS'].filter((n) => n in m),
    };
})()"""

# Baja por la página deteniéndose donde se le pide y anota cada cambio de la burbuja cerrada: su contenido (el ícono)
# y su fondo. La de Baby Caleb es quieta: no cambia con la página, al bajar ni de noche.
BAJAR = """
    const burbujaB = document.querySelector('button.o_dcbt_burbuja');
    const actual = () => burbujaB.innerHTML + '|' + getComputedStyle(burbujaB).backgroundColor;
    const cambios = [];
    let ultima = actual();
    new MutationObserver(() => { const a = actual(); if (a !== ultima) { ultima = a; cambios.push([Date.now(), a]); } }).observe(burbujaB, { childList: true, subtree: true, attributes: true, attributeFilter: ['src', 'class'] });
    const ir = async (sel, ms) => {
        const el = document.querySelector(sel);
        if (!el) { throw new Error('No está la sección ' + sel); }
        const r = el.getBoundingClientRect();
        window.scrollTo(0, Math.max(1, scrollY + r.top + Math.min(r.height, 200) / 2 - innerHeight * 0.475));
        await esperar(ms);
    };
    const esLaDeLaMarca = () => Boolean(burbujaB.querySelector('.o_dcbt_burbuja_ico svg')) && !burbujaB.querySelector('img')
        && getComputedStyle(burbujaB).backgroundColor === 'NARANJA';
""".replace('NARANJA', NARANJA)

QUIETA_EN_EL_INICIO = """(async () => {
    /*ESPERAR*/
    /*BAJAR*/
    await esperar(3200);
    const res = { quieta: cambios.length, deLaMarca: esLaDeLaMarca() };
    for (const sel of ['.o_dcasa_beneficios', '.o_dcasa_rail .o_dcasa_section_head', '.o_dcasa_socios_band',
                       '.o_dcasa_ayuda .o_dcasa_faq', '.o_dcasa_visita_franja', '#bottom, footer']) {
        if (document.querySelector(sel)) { await ir(sel, 900); }
    }
    await esperar(2600);
    res.cambios = cambios.length;
    res.alFinal = esLaDeLaMarca();
    res.sinScrollDeLado = document.documentElement.scrollWidth <= innerWidth;
    return res;
})()""".replace('/*ESPERAR*/', ESPERAR).replace('/*BAJAR*/', BAJAR)

QUIETA_EN_LA_FICHA = """(async () => {
    /*ESPERAR*/
    /*BAJAR*/
    await esperar(3200);
    const res = { quieta: cambios.length, deLaMarca: esLaDeLaMarca() };
    await ir('.o_wsale_product_details_content_section_price', 1500);
    res.alMoverse = cambios.length;
    // Con el chat abierto y al cerrarlo, la misma burbuja.
    document.querySelector('button.o_dcbt_burbuja').click();
    await hasta(() => !document.querySelector('#o_dcbt_panel').hidden, 'el chat abierto');
    await ir('#bottom, footer', 1500);
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    await hasta(() => document.querySelector('#o_dcbt_panel').hidden, 'que se cierre');
    await esperar(2600);
    res.alCerrar = esLaDeLaMarca();
    return res;
})()""".replace('/*ESPERAR*/', ESPERAR).replace('/*BAJAR*/', BAJAR)

NOCHE_CHAT = """(async () => {
    /*ESPERAR*/
    const burbuja = document.querySelector('button.o_dcbt_burbuja');
    const deLaMarca = Boolean(burbuja.querySelector('.o_dcbt_burbuja_ico svg')) && !burbuja.querySelector('img');
    document.querySelector('button.o_dcbt_burbuja').click();
    await hasta(() => globos().some((g) => g.includes('Hola, soy Andrés')) && globos().length >= 2, 'el saludo');
    let pase = null;
    try { pase = JSON.parse(sessionStorage.getItem('dcasa.brian.pase')); } catch (e) { pase = null; }
    return { deLaMarca, globos: globos(), noche: pase && pase.noche, avisar: pase && pase.avisar_cerrado,
             avatares: document.querySelectorAll('#o_dcbt_panel img').length };
})()""".replace('/*ESPERAR*/', ESPERAR)

NOCHE_BURBUJA = """(async () => {
    /*ESPERAR*/
    /*BAJAR*/
    await esperar(3200);
    const alLlegar = esLaDeLaMarca();
    await ir('.o_wsale_product_details_content_section_price', 1500);
    return { alLlegar, cambios: cambios.length };
})()""".replace('/*ESPERAR*/', ESPERAR).replace('/*BAJAR*/', BAJAR)


class ChromeConMicrofono(ChromeBrowser):
    """El Chrome de las pruebas de Odoo con el micrófono de prueba (las opciones van antes de la página inicial)."""

    def _spawn_chrome(self, cmd):
        return super()._spawn_chrome([*cmd[:-1], *MICROFONO_DE_PRUEBA, cmd[-1]])


class NavegadorCase(TiendaCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        gerencia = new_test_user(cls.env, login='zzbt_ger_nav', name='ZZBT Gerencia Nav',
                                 groups='base.group_user,dcasa_base.group_gerencia')
        importar(cls.env, gerencia)
        cls.env['dcasa.envio.tarifa'].search([], limit=1).with_user(gerencia).action_aprobar()
        # Los colchones del catálogo de ejemplo saldrían antes en «Colchones»: el chat de prueba ve solo los suyos.
        cls.env['product.template'].search([('name', 'ilike', 'colch'), ('id', '!=', cls.colchon.id)]).write(
            {'is_published': False})

    def setUp(self):
        super().setUp()
        if comun.websocket is None:
            # Sin websocket-client (el CI) Odoo salta cada navegador; sin esto, lo que se afirma después de los subtests
            # (p. ej. cuántas ubicaciones recibió el Worker) fallaría sin que el navegador haya corrido.
            self.skipTest('websocket-client module is not installed')
        self.worker = WorkerSimulado(TOKEN_WORKER, self.base_url(), TOKEN_ODOO,
                                     cookie_odoo=lambda: f'{TEST_CURSOR_COOKIE_NAME}={self.http_request_key}')
        puerto = self.worker.iniciar()
        self.addCleanup(self.worker.detener)
        entorno = patch.dict(os.environ, {'JUAN_URL': f'http://127.0.0.1:{puerto}'})
        entorno.start()
        self.addCleanup(entorno.stop)

    @contextlib.contextmanager
    def chrome(self, ancho, alto=ALTO, movil=True, reducido=False, microfono=False):
        self.browser_size = f'{ancho}x{alto}'
        browser = (ChromeConMicrofono if microfono else ChromeBrowser)(self, headless=True)
        with self.allow_requests(browser=browser), contextlib.ExitStack() as atexit:
            atexit.callback(self._wait_remaining_requests)
            atexit.enter_context(browser.cleanup)
            self.authenticate(None, None, browser=browser)
            self.cr.flush()
            self.cr.clear()
            browser._websocket_request('Emulation.setDeviceMetricsOverride', params={
                'width': ancho, 'height': alto, 'deviceScaleFactor': 2 if movil else 1, 'mobile': movil})
            if movil:
                browser._websocket_request('Emulation.setTouchEmulationEnabled', params={'enabled': True})
            if reducido:
                browser._websocket_request('Emulation.setEmulatedMedia', params={
                    'features': [{'name': 'prefers-reduced-motion', 'value': 'reduce'}]})
            browser._websocket_request('Browser.grantPermissions', params={
                'permissions': ['geolocation'], 'origin': self.base_url()})
            browser._websocket_request('Emulation.setGeolocationOverride', params={
                'latitude': COSTA[0], 'longitude': COSTA[1], 'accuracy': 30})
            yield browser

    def evaluar(self, browser, expresion, timeout=120):
        res = browser._websocket_request('Runtime.evaluate', params={
            'expression': expresion, 'awaitPromise': True, 'returnByValue': True}, timeout=timeout)
        resultado = res['result']
        self.assertFalse(res.get('exceptionDetails'), f'JavaScript falló: {res}')
        self.assertNotEqual(resultado.get('subtype'), 'error', f'JavaScript falló: {res}')
        return resultado.get('value')


@tagged('post_install', '-at_install')
class TestChatEnElNavegador(NavegadorCase):

    def revisar_chat(self, r, ancho):
        self.assertEqual(r['saludos'], 1, 'Brian se presenta una sola vez')
        self.assertEqual(r['expandido'], 'true')
        self.assertEqual(r['tarjeta'], 'ZZBT Colchón Queen', 'la tarjeta sale de buscar_productos de Odoo')
        self.assertEqual(r['precio'], '$278.00+ ITBMS')
        self.assertEqual(r['ver'], self.colchon.website_url)
        self.assertEqual(r['listo'], 1)
        self.assertEqual(r['navbar'], '2', 'el globo del carrito de la cabecera se pone al día')
        self.assertEqual(r['total'], '$834.00')
        self.assertTrue(r['pdf'])
        self.assertTrue(r['privacidad'])
        self.assertEqual(r['lugar'], 'Costa Inventada')
        self.assertIn('Costa Inventada', r['envio'])
        self.assertTrue(r['ampliado']['clase'])
        self.assertGreaterEqual(r['ampliado']['vitrina'], 1, 'la cuadrícula con los productos de la conversación')
        if ancho >= 1000:
            self.assertGreater(r['ampliado']['ancho'], 900)
        self.assertEqual(r['trasPrimerEsc'], {'abierto': True, 'ampliado': False})
        self.assertTrue(r['foco'], 'al cerrar, el foco vuelve a la burbuja')
        self.assertTrue(r['sinScrollDeLado'])

    def test_el_chat_de_punta_a_punta_en_el_celular_y_la_computadora(self):
        for ancho, movil in ((390, True), (1366, False)):
            with self.subTest(ancho=ancho), self.chrome(ancho, 844 if movil else 768, movil=movil) as browser:
                antes = self.env['dcasa.brian.tienda.calificacion'].sudo().search_count([])
                ubicaciones = self.worker.ubicaciones
                browser.navigate_to(self.base_url() + '/', wait_stop=True)
                r = self.evaluar(browser, CHAT)
                self.revisar_chat(r, ancho)
                self.assertEqual(self.env['dcasa.brian.tienda.calificacion'].sudo().search_count([]), antes + 1)
                self.assertEqual(self.worker.ubicaciones, ubicaciones + 1, 'la ubicación llegó al Worker una vez')
        # La ubicación nunca llegó a guardarse, y lo que preguntó el chat no queda en la auditoría de Brian.
        self.assertFalse(self.env['brian.accion'].sudo().search([('herramienta', '=', 'juan_cotizar_envio')]))
        self.assertFalse([c for c in self.worker.recibidos if 'ubicacion' in c])

    def test_las_funciones_de_la_pagina(self):
        with self.chrome(390) as browser:
            browser.navigate_to(self.base_url() + '/', wait_stop=True)
            self.evaluar(browser, '(async () => { ' + ESPERAR + ' return true; })()')
            r = self.evaluar(browser, PURAS)
        self.assertEqual(r['urls'], ['/shop/x-1', None, None, '/shop/x-2', None])
        self.assertEqual(r['precio'], ['$278.00', '+ ITBMS'])
        # El mensaje de WhatsApp no lleva el nombre de la tienda de origen (lo recibe la tienda: sabe quién es).
        self.assertEqual(r['wa'], 'Hola, vengo del chat de la web. Tengo en el carrito: 2 × Colchón.')
        self.assertEqual(r['tipos'], ['inicio', 'catalogo', 'carrito', 'socios'], 'el tipo de página sigue yendo al Worker')
        self.assertEqual(r['delRobot'], [], 'nada del robot de D’CASA en el JS')


@tagged('post_install', '-at_install')
class TestBurbujaEnLaPagina(NavegadorCase):

    def test_la_burbuja_a_360_390_430_y_1366(self):
        rutas = ('/', '/shop', self.colchon.website_url, '/shop/cart')
        for ancho, movil in ((360, True), (390, True), (430, True), (1366, False)):
            for ruta in rutas:
                with self.subTest(ancho=ancho, ruta=ruta), self.chrome(ancho, movil=movil) as browser:
                    browser.navigate_to(self.base_url() + ruta, wait_stop=True)
                    m = self.evaluar(browser, BURBUJA)
                    b = m['burbuja']
                    # La de Baby Caleb (Chatbot.tsx): 56 px, naranja, redonda, con el globo de chat en navy y sin robot.
                    self.assertEqual(m['marca']['fondo'], NARANJA, 'la burbuja, naranja')
                    self.assertEqual(m['marca']['color'], NAVY, 'el ícono navy (5.56), nunca blanco')
                    self.assertEqual(m['marca']['colorIcono'], NAVY)
                    self.assertTrue(m['marca']['icono'], 'el globo de chat')
                    self.assertEqual(m['marca']['imagenes'], 0, 'sin el robot de D’CASA')
                    self.assertEqual(m['marca']['redondo'], '50%')
                    self.assertEqual(m['etiqueta'], 'Abrir el chat de la tienda')
                    self.assertEqual((b['ancho'], b['altoB']), (56, 56), 'la medida de Baby Caleb, y más de 44 para el dedo')
                    if not m['aparteAlCargar']:   # apartada (un botón de la página quedaría debajo) no cuenta
                        self.assertGreaterEqual(b['x'], 0)
                        self.assertLessEqual(b['derecha'], m['pantalla'])
                        self.assertLessEqual(b['abajo'], m['alto'])
                    self.assertTrue(m['sinScrollDeLado'])
                    if m.get('barra'):
                        self.assertLessEqual(b['abajo'], m['barra']['y'] - 4,
                                             'no tapa la barra de «Agregar al carrito» de la ficha')
                    if 'aparte' in m:
                        self.assertFalse(m['tapaVisible'], 'nunca tapa el botón de WhatsApp de la ficha')
                        if movil:
                            self.assertTrue(m['aparte'])
                            self.assertTrue(m['vuelve'])

    def test_con_movimiento_reducido_quieto(self):
        with self.chrome(390, reducido=True) as browser:
            browser.navigate_to(self.base_url() + '/', wait_stop=True)
            r = self.evaluar(browser, QUIETO)
        self.assertTrue(r['reducido'])
        self.assertEqual(r['animaciones'], [], 'nada del chat se mueve')


@tagged('post_install', '-at_install')
class TestConElEditor(TiendaCase):
    """La administradora con el editor del sitio (la trampa del error 500 del lote 1). En producción nadie tiene el
    editor (dcasa_interfaz se lo quita a todos): aquí se le da a propósito para abrir el modo edición."""

    def test_la_administradora_abre_el_sitio_en_modo_edicion(self):
        admin = self.env.ref('base.user_admin')
        admin.group_ids = [Command.link(self.env.ref('website.group_website_designer').id)]
        self.start_tour(self.env['website'].get_client_action_url('/'), 'dcasa_brian_tienda_editor', login='admin',
                        timeout=180)


@tagged('post_install', '-at_install')
class TestBurbujaQuieta(NavegadorCase):
    """La burbuja de Baby Caleb es quieta (docs/MARCA_BABY_CALEB.md): la misma en todas las páginas, al bajar, con el
    chat abierto y al cerrarlo. Antes el robot de D'CASA cambiaba de pose con cada sección; se fue con su marca."""

    def setUp(self):
        super().setUp()
        # De día a cualquier hora, para que la prueba no dependa de la hora (la de noche va en TestBrianDeNoche).
        self.env['dcasa.juan.ajustes'].obtener().write({
            'horario_inicio': 0.0, 'horario_fin': 23.98, 'horario_fin_domingo': 0.0, 'dia_domingo': True,
            'dia_lunes': True, 'dia_martes': True, 'dia_miercoles': True, 'dia_jueves': True, 'dia_viernes': True,
            'dia_sabado': True})
        self.env.registry.clear_cache('templates')   # Odoo guarda la portada (con el horario) una hora

    def test_en_el_inicio_no_cambia_al_bajar(self):
        with self.chrome(390) as browser:
            browser.navigate_to(self.base_url() + '/', wait_stop=True)
            r = self.evaluar(browser, QUIETA_EN_EL_INICIO)
        self.assertEqual((r['quieta'], r['deLaMarca']), (0, True), 'al llegar, la burbuja de la marca')
        self.assertEqual(r['cambios'], 0, 'al bajar por las secciones no cambia')
        self.assertTrue(r['alFinal'])
        self.assertTrue(r['sinScrollDeLado'])

    def test_en_la_ficha_y_con_el_chat_abierto(self):
        with self.chrome(1366, 768, movil=False) as browser:
            browser.navigate_to(self.base_url() + self.colchon.website_url, wait_stop=True)
            r = self.evaluar(browser, QUIETA_EN_LA_FICHA)
        self.assertEqual((r['quieta'], r['deLaMarca']), (0, True))
        self.assertEqual(r['alMoverse'], 0, 'en el precio y «Agregar al carrito», la misma')
        self.assertTrue(r['alCerrar'], 'al cerrar el chat vuelve la misma burbuja')

    def test_con_movimiento_reducido_tambien(self):
        with self.chrome(390, reducido=True) as browser:
            browser.navigate_to(self.base_url() + self.colchon.website_url, wait_stop=True)
            r = self.evaluar(browser, NOCHE_BURBUJA)
        self.assertEqual((r['alLlegar'], r['cambios']), (True, 0))


@tagged('post_install', '-at_install')
class TestBrianDeNoche(NavegadorCase):
    """De noche (Sitio web › Brian de la tienda; pedido de la dueña, 2026-11-15): de fábrica, Brian saluda como de día
    (no dice que no hay vendedoras); con el aviso encendido, dice que la tienda está cerrada. La burbuja es la misma de
    día: el robot que dormía de noche era de D'CASA y se fue con su marca (y su interruptor con él)."""

    def setUp(self):
        super().setUp()
        # Hoy (hora de Panamá) cerrado. Se prueba en la ficha: Odoo no la guarda en su memoria de páginas.
        hoy = datetime.now(pytz.timezone('America/Panama')).isoweekday() % 7   # 0 = domingo, como el JS
        campos = ['dia_domingo', 'dia_lunes', 'dia_martes', 'dia_miercoles', 'dia_jueves', 'dia_viernes', 'dia_sabado']
        self.env['dcasa.juan.ajustes'].obtener().write({c: i != hoy for i, c in enumerate(campos)})

    def test_el_saludo_de_noche_con_y_sin_aviso(self):
        cerrada = 'Ahora la tienda está cerrada'
        with self.chrome(1366, 768, movil=False) as browser:
            browser.navigate_to(self.base_url() + self.colchon.website_url, wait_stop=True)
            r = self.evaluar(browser, NOCHE_CHAT)
        self.assertEqual((r['noche'], r['avisar']), (True, False), 'el pase dice la verdad y que no hay que avisar')
        self.assertTrue(r['deLaMarca'], 'de noche, la misma burbuja de la marca')
        self.assertEqual(r['avatares'], 0, 'en el chat no hay robot (ni dormido)')
        self.assertEqual(r['globos'][:2], ['Hola, soy Andrés. ¿Qué buscas hoy?', 'Con gusto te ayudo a encontrar lo '
                         'que buscas, ver precios, calcular el envío o dejarte el carrito listo.'], 'saluda como de día')
        self.assertFalse([g for g in r['globos'] if cerrada in g])
        self.env['ir.config_parameter'].sudo().set_param('dcasa_brian_tienda.avisar_cerrado', 'True')
        with self.chrome(1366, 768, movil=False) as browser:
            browser.navigate_to(self.base_url() + self.colchon.website_url, wait_stop=True)
            r = self.evaluar(browser, NOCHE_CHAT)
        self.assertEqual((r['noche'], r['avisar']), (True, True))
        self.assertTrue(r['globos'][1].startswith(cerrada), r['globos'])
        self.assertTrue(r['deLaMarca'])

    def test_la_burbuja_de_noche_es_la_de_dia(self):
        with self.chrome(1366, 768, movil=False) as browser:
            browser.navigate_to(self.base_url() + self.colchon.website_url, wait_stop=True)
            r = self.evaluar(browser, NOCHE_BURBUJA)
        self.assertEqual((r['alLlegar'], r['cambios']), (True, 0), 'naranja con el globo navy, y no cambia al bajar')


# La cabecera del chat con la marca Baby Caleb (Chatbot.tsx): naranja, con el nombre de la tienda, el estado y los íconos
# en navy (5.56), y el corazón en un círculo crema. El panel en `surface` y la conversación en crema. Se mide normal y
# ampliada.
CABECERA = """(async () => {
    /*ESPERAR*/
    document.querySelector('button.o_dcbt_burbuja').click();
    await hasta(() => document.querySelector('#o_dcbt_panel:not([hidden]) .o_dcbt_cab'), 'el panel abierto');
    await esperar(500);
    // Sin foco y sin el puntero encima: se mide el color de reposo, después de su transición.
    const medir = async () => {
        if (document.activeElement) { document.activeElement.blur(); }
        await esperar(400);
        const panel = document.querySelector('#o_dcbt_panel');
        const cab = panel.querySelector('.o_dcbt_cab');
        const punto = cab.querySelector('.o_dcbt_punto');
        const avatar = cab.querySelector('.o_dcbt_avatar_marca');
        const h2 = cab.querySelector('h2');
        return {
            cabecera: getComputedStyle(cab).backgroundColor, panel: getComputedStyle(panel).backgroundColor,
            cuerpo: getComputedStyle(panel.querySelector('.o_dcbt_panel_cuerpo')).backgroundColor,
            titulo: h2.textContent, colorTitulo: getComputedStyle(h2).color, letra: getComputedStyle(h2).fontFamily,
            caja: getComputedStyle(h2).textTransform,
            estado: getComputedStyle(cab.querySelector('.o_dcbt_cab_estado')).color,
            iconos: [...cab.querySelectorAll('.o_dcbt_cab_boton')].map((b) => getComputedStyle(b).color),
            avatar: avatar ? { fondo: getComputedStyle(avatar).backgroundColor, color: getComputedStyle(avatar).color,
                               redondo: getComputedStyle(avatar).borderTopLeftRadius } : null,
            punto: { aro: getComputedStyle(punto).borderTopColor, apagado: punto.classList.contains('o_dcbt_apagado') },
            imagenes: panel.querySelectorAll('img.o_dcbt_img_pose, .o_dcbt_pose').length,
        };
    };
    const normal = await medir();
    document.querySelector('#o_dcbt_panel .o_dcbt_cab_boton[aria-pressed]').click();
    await esperar(500);
    return { normal, ampliado: await medir(), esAmpliado: document.querySelector('#o_dcbt_panel').classList.contains('o_dcbt_ampliado') };
})()""".replace('/*ESPERAR*/', ESPERAR)


@tagged('post_install', '-at_install')
class TestCabeceraDeLaMarca(NavegadorCase):

    def test_la_cabecera_es_la_del_chat_de_baby_caleb_normal_y_ampliada(self):
        empresa = self.env['website'].browse(self.website.id).company_id.name
        with self.chrome(1366, 768, movil=False) as browser:
            browser.navigate_to(self.base_url() + '/', wait_stop=True)
            r = self.evaluar(browser, CABECERA)
        self.assertTrue(r['esAmpliado'])
        for tamano in ('normal', 'ampliado'):
            m = r[tamano]
            with self.subTest(tamano=tamano):
                self.assertEqual(m['cabecera'], NARANJA, 'la cabecera naranja de Baby Caleb')
                self.assertEqual(m['titulo'], empresa, 'el nombre de la tienda (la empresa del sitio), no D’CASA')
                self.assertEqual((m['colorTitulo'], m['estado']), (NAVY, NAVY), 'en navy sobre el naranja (5.56)')
                self.assertTrue(m['letra'].startswith('Montserrat'), m['letra'])
                self.assertEqual(m['caja'], 'none', 'el titular como frase, nunca en caja alta')
                self.assertEqual(set(m['iconos']), {NAVY}, 'los íconos navy')
                self.assertEqual(m['avatar'], {'fondo': CREMA, 'color': NARANJA_TEXTO, 'redondo': '50%'},
                                 'el corazón en su círculo crema')
                self.assertEqual(m['punto']['aro'], NAVY)
                self.assertEqual(m['panel'], SUPERFICIE)
                self.assertEqual(m['cuerpo'], CREMA, 'la conversación sobre crema')
                self.assertEqual(m['imagenes'], 0, 'sin el robot de D’CASA')
                self.assertNotIn(AZUL_DCASA, (m['cabecera'], m['colorTitulo'], *m['iconos']))


# El carrito en la barra del chat (pedido de la dueña, 2026-11-15): con algo en el carrito, el ícono de WhatsApp pasa a
# ser el carrito con su cantidad; vacío, vuelve WhatsApp. Y el chat al día con el carrito que cambia la PÁGINA (el
# «Agregar» de la ficha: Odoo y después el número del menú), también al seguir la conversación en otra página (el chat
# decía «Tu carrito está vacío» con la cama ya puesta).
BARRA = """
    const barra = () => {
        const cab = document.querySelector('#o_dcbt_panel .o_dcbt_cab');
        const wa = cab && cab.querySelector('a[target="_blank"]');
        const carrito = cab && cab.querySelector('.o_dcbt_cab_carrito');
        const globo = carrito && getComputedStyle(carrito.querySelector('.o_dcbt_cab_cuenta'));
        const menu = document.querySelector('.my_cart_quantity');
        const deMenu = menu && getComputedStyle(menu);
        return { wa: wa ? !wa.hidden : null, carrito: carrito ? !carrito.hidden : null,
                 colores: globo ? [globo.backgroundColor, globo.color, globo.boxShadow] : null,
                 coloresMenu: deMenu ? [deMenu.backgroundColor, deMenu.color, deMenu.boxShadow] : null,
                 cuenta: carrito ? carrito.querySelector('.o_dcbt_cab_cuenta').textContent : null,
                 etiqueta: carrito ? carrito.getAttribute('aria-label') : null, href: carrito ? carrito.getAttribute('href') : null };
    };
    const agregarDesdeLaPagina = async (cantidad, menu) => {
        await fetch('/shop/cart/add', { method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ jsonrpc: '2.0', method: 'call', params: { product_template_id: TMPL, product_id: PROD, quantity: cantidad } }) });
        if (menu !== null) { document.querySelectorAll('.my_cart_quantity').forEach((g) => { g.textContent = String(menu); }); }
    };
"""

CARRITO_EN_LA_BARRA = """(async () => {
    /*ESPERAR*/ /*BARRA*/
    const r = {};
    document.querySelector('button.o_dcbt_burbuja').click();
    await hasta(() => globos().some((g) => g.includes('Hola, soy Andrés')), 'el saludo');
    await esperar(600);
    r.vacio = barra();
    const primeras = document.querySelector('#o_dcbt_panel .o_dcbt_chips');
    r.chips = primeras ? [...primeras.querySelectorAll('.o_dcbt_chip')].map((c) => c.textContent) : [];
    r.sugerencias = JSON.parse(sessionStorage.getItem('dcasa.brian.pase') || '{}').sugerencias || null;
    r.hayMenu = document.querySelectorAll('.my_cart_quantity').length;
    await agregarDesdeLaPagina(2, 2);
    await hasta(() => barra().carrito, 'el carrito en la barra');
    r.lleno = barra();
    await window.__dcasaBrian.odoo('POST', '/dcasa/brian/v1/carrito/cantidad', { producto_id: PROD, cantidad: 0 });
    document.querySelectorAll('.my_cart_quantity').forEach((g) => { g.textContent = '0'; });
    await hasta(() => barra().wa && !barra().carrito, 'WhatsApp de vuelta');
    r.otraVez = barra();
    return r;
})()"""

SIGUE_EN_OTRA_PAGINA_1 = """(async () => {
    /*ESPERAR*/ /*BARRA*/
    document.querySelector('button.o_dcbt_burbuja').click();
    await hasta(() => globos().some((g) => g.includes('Hola, soy Andrés')), 'el saludo');
    await esperar(600);
    const antes = barra();
    await agregarDesdeLaPagina(1, null);   // sin tocar el menú: como la página que agrega y se va a otra
    await esperar(300);
    return antes;
})()"""

SIGUE_EN_OTRA_PAGINA_2 = """(async () => {
    /*ESPERAR*/ /*BARRA*/
    await hasta(() => document.querySelector('#o_dcbt_panel:not([hidden])'), 'el chat abierto otra vez');
    await hasta(() => barra().carrito, 'el carrito en la barra');
    const pie = document.querySelector('#o_dcbt_panel .o_dcbt_vitrina_pie');
    return { barra: barra(), pie: pie ? pie.textContent : null, historial: globos().filter((g) => g.includes('Hola, soy Andrés')).length };
})()"""


@tagged('post_install', '-at_install')
class TestCarritoEnLaBarra(NavegadorCase):

    def setUp(self):
        super().setUp()
        # Los ids se leen ANTES de abrir el navegador: con la página abierta, sus pedidos (las fotos, el pase) usan el
        # mismo cursor de la prueba y leer el ORM a la vez daba, a veces, una variante vacía (2026-11-16).
        self.ids = (self.colchon.id, self.colchon.product_variant_id.id)

    def _js(self, codigo):
        plantilla, variante = self.ids
        return (codigo.replace('/*ESPERAR*/', ESPERAR).replace('/*BARRA*/', BARRA)
                .replace('TMPL', str(plantilla)).replace('PROD', str(variante)))

    def test_whatsapp_o_el_carrito_con_su_cantidad_al_dia_con_la_pagina(self):
        with self.chrome(1366, 768, movil=False) as browser:
            browser.navigate_to(self.base_url() + '/', wait_stop=True)
            r = self.evaluar(browser, self._js(CARRITO_EN_LA_BARRA))
        self.assertEqual((r['vacio']['wa'], r['vacio']['carrito']), (True, False), 'carrito vacío: WhatsApp')
        self.assertTrue(r['sugerencias'] is not None, 'el pase trae las sugerencias')
        self.assertEqual(r['chips'][-2:], ['¿Cuánto cuesta el envío?', 'Formas de pago'])
        if r['sugerencias']:
            self.assertEqual(r['chips'][:-2], r['sugerencias'], 'las primeras, las del catálogo')
        self.assertGreater(r['hayMenu'], 0, 'el menú del sitio tiene el número del carrito')
        self.assertEqual((r['lleno']['wa'], r['lleno']['carrito']), (False, True), 'con algo: el carrito')
        self.assertEqual(r['lleno']['cuenta'], '2')
        self.assertEqual(r['lleno']['etiqueta'], 'Ver tu carrito: 2 artículos')
        self.assertEqual(r['lleno']['href'], '/shop/cart')
        # El color de la cantidad en la cabecera naranja del chat (marca Baby Caleb): la pastilla navy con el número
        # crema (12.21) y un filo naranja que la despega del círculo. (La del menú del sitio la pinta website_dcasa.)
        fondo, texto, aro = r['lleno']['colores']
        self.assertEqual((fondo, texto), (NAVY, CREMA), 'la cantidad, navy con número crema')
        self.assertIn(NARANJA, aro, 'el filo naranja la despega del círculo')
        self.assertNotIn(AZUL_DCASA, (fondo, texto, aro))
        self.assertEqual((r['otraVez']['wa'], r['otraVez']['carrito']), (True, False), 'vacío otra vez: WhatsApp')

    def test_la_conversacion_que_sigue_en_otra_pagina_lee_el_carrito(self):
        with self.chrome(1366, 768, movil=False) as browser:
            browser.navigate_to(self.base_url() + '/', wait_stop=True)
            antes = self.evaluar(browser, self._js(SIGUE_EN_OTRA_PAGINA_1))
            browser.navigate_to(self.base_url() + '/shop', wait_stop=True)
            r = self.evaluar(browser, self._js(SIGUE_EN_OTRA_PAGINA_2))
        self.assertFalse(antes['carrito'])
        self.assertTrue(r['barra']['carrito'], 'el chat lee el carrito al seguir en otra página')
        self.assertEqual(r['barra']['cuenta'], '1')
        self.assertEqual(r['historial'], 1, 'la conversación sigue: no se vuelve a presentar')
        self.assertNotIn('vacío', r['pie'] or '', 'la vitrina tampoco dice «vacío»')


# Andrés como buen vendedor (docs/PLAN_ANDRES_VOZ_PORTADA.md, A1 a A5; pedido de la dueña, 2026-11-16): la barra del
# carrito siempre a mano, el envío sumado a la cotización con la línea de Odoo, la reacción al quitar (una vez), cambiar
# el carrito conversando y la vitrina ordenada por pedidos. Con el Worker simulado, que habla el contrato nuevo.
VENDEDOR = """(async () => {
    /*ESPERAR*/
    const r = { errores: [] };
    const escribir = (texto) => {
        const campo = document.querySelector('#o_dcbt_texto');
        campo.value = texto;
        campo.dispatchEvent(new Event('input', { bubbles: true }));
        document.querySelector('#o_dcbt_panel .o_dcbt_composer').requestSubmit();
    };
    const visible = (el) => !!el && !el.closest('[hidden]') && el.getBoundingClientRect().height > 0;
    const barra = () => {
        const b = document.querySelector('#o_dcbt_panel .o_dcbt_barra');
        return b && !b.hidden ? { texto: b.querySelector('.o_dcbt_barra_ver').textContent, expandida: b.querySelector('.o_dcbt_barra_ver').getAttribute('aria-expanded'),
                                  pdf: b.querySelector('a.o_dcbt_barra_pdf').getAttribute('href'), caja: caja(b) } : null;
    };
    const cuantos = (t) => globos().filter((g) => g.includes(t)).length;
    document.querySelector('button.o_dcbt_burbuja').click();
    await hasta(() => globos().some((g) => g.includes('Hola, soy Andrés')) && document.querySelector('#o_dcbt_panel .o_dcbt_chip'), 'el saludo');
    r.barraVacia = barra();
    // Camas: tres de la base (desde su tarjeta).
    escribir('Muéstrame camas');
    const base = await hasta(() => [...document.querySelectorAll('#o_dcbt_panel .o_dcbt_carrusel .o_dcbt_tarjeta')].find((t) => /Base de Cama/i.test(t.textContent) && t.querySelector('[data-agregar]')), 'la base de cama');
    base.querySelector('[data-paso="1"]').click();
    base.querySelector('[data-paso="1"]').click();
    base.querySelector('[data-agregar]').click();
    await hasta(() => barra(), 'la barra del carrito');
    r.barra = barra();
    r.composer = caja(document.querySelector('#o_dcbt_panel .o_dcbt_composer'));
    // Colchones: uno.
    escribir('Ahora colchones');
    const colchon = await hasta(() => document.querySelectorAll('#o_dcbt_panel .o_dcbt_carrusel').length >= 2 && [...document.querySelectorAll('#o_dcbt_panel .o_dcbt_carrusel')].pop().querySelector('.o_dcbt_tarjeta [data-agregar]'), 'los colchones');
    colchon.click();
    await hasta(() => (barra() || {}).texto && barra().texto.includes('4 artículos'), 'cuatro artículos');
    // A5: la vitrina, con «En tu carrito» arriba y un grupo por pedido (el más reciente primero, abierto).
    document.querySelector('#o_dcbt_panel .o_dcbt_cab_boton[aria-pressed]').click();
    await esperar(600);
    const vitrina = document.querySelector('#o_dcbt_panel .o_dcbt_vitrina_grid');
    r.vitrina = { primero: vitrina.firstElementChild.className, lineas: vitrina.querySelectorAll('.o_dcbt_seccion_carrito .o_dcbt_linea_carrito').length,
                  grupos: [...vitrina.querySelectorAll('.o_dcbt_grupo')].map((g) => [g.querySelector('.o_dcbt_grupo_titulo').textContent, g.open, g.querySelectorAll('.o_dcbt_tarjeta').length]) };
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    await esperar(400);
    // A2: el envío; Andrés ofrece sumarlo y, con el sí, la página se lo pide a Odoo.
    escribir('¿Cuánto cuesta el envío a Costa Inventada?');
    await hasta(() => globos().includes('¿Te lo sumo a la cotización?'), 'la oferta del envío');
    (await hasta(() => chip('Sí, súmalo'), 'el chip de sumar')).click();
    await hasta(() => globos().includes('Listo, te lo sumé: el total lo ves en tu carrito y en la cotización.'), 'el «te lo sumé»');
    await hasta(() => (barra() || {}).texto && barra().texto.includes('+ envío'), 'la barra con el envío');
    const tarjetas = [...document.querySelectorAll('#o_dcbt_panel [data-carrito]')];
    r.envioEnLaTarjeta = tarjetas.pop().textContent;
    r.barraConEnvio = barra();
    // A1: la hoja del carrito, editable, sin salir del chat.
    document.querySelector('#o_dcbt_panel .o_dcbt_barra_ver').click();
    await hasta(() => visible(document.querySelector('#o_dcbt_hoja')), 'la hoja abierta');
    const hoja = document.querySelector('#o_dcbt_hoja');
    r.hoja = { expandida: barra().expandida, foco: document.activeElement === hoja.querySelector('.o_dcbt_hoja_cerrar'), lineas: hoja.querySelectorAll('.o_dcbt_linea_carrito').length,
               envio: hoja.querySelectorAll('.o_dcbt_linea_envio').length, texto: hoja.textContent, caja: caja(hoja), panel: caja(document.querySelector('#o_dcbt_panel')) };
    // A3: quitar el colchón desde la hoja → Andrés reacciona UNA vez.
    [...hoja.querySelectorAll('.o_dcbt_linea_carrito')].find((l) => /Colch/i.test(l.textContent)).querySelector('[data-quitar]').click();
    await hasta(() => cuantos('Vi que quitaste') === 1, 'la reacción al quitar');
    r.reaccion = globos().find((g) => g.includes('Vi que quitaste'));
    r.chipsReaccion = [...document.querySelectorAll('#o_dcbt_panel .o_dcbt_chips')].pop().textContent;
    await esperar(300);
    // Bajar otra cantidad: ya no reacciona (nunca insiste).
    const enHoja = document.querySelector('#o_dcbt_hoja:not([hidden]) .o_dcbt_linea_carrito [data-paso="-1"]');
    if (enHoja) { enHoja.click(); } else {
        document.querySelector('#o_dcbt_panel .o_dcbt_barra_ver').click();
        (await hasta(() => document.querySelector('#o_dcbt_hoja:not([hidden]) .o_dcbt_linea_carrito [data-paso="-1"]'), 'el menos')).click();
    }
    await hasta(() => (barra() || {}).texto && barra().texto.includes('2 artículos'), 'dos artículos');
    await esperar(1200);
    r.reacciones = cuantos('Vi que');
    r.marca = sessionStorage.getItem('dcasa.brian.reaccion');
    // Esc cierra primero la hoja (el chat sigue abierto).
    if (!document.querySelector('#o_dcbt_hoja').hidden) {
        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
        await esperar(300);
    }
    r.trasEsc = { hoja: !document.querySelector('#o_dcbt_hoja').hidden, chat: !document.querySelector('#o_dcbt_panel').hidden };
    // A4: cambiar el carrito conversando: Andrés propone, la página lo aplica en Odoo y Andrés confirma.
    escribir('Quita la base de cama, por favor');
    await hasta(() => globos().some((g) => g.startsWith('Listo, quité')), 'el «listo, quité»');
    await hasta(() => !barra(), 'la barra se va con el carrito vacío');
    r.quite = globos().find((g) => g.startsWith('Listo, quité'));
    r.reaccionesAlFinal = cuantos('Vi que');
    r.sinScrollDeLado = document.documentElement.scrollWidth <= innerWidth;
    return r;
})()""".replace('/*ESPERAR*/', ESPERAR)


@tagged('post_install', '-at_install')
class TestAndresVendedor(NavegadorCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.costa = cls.env['dcasa.envio.lugar'].search([('name', '=', 'Costa Inventada')])
        # Las camas del catálogo de ejemplo saldrían antes en «camas»: el chat de prueba ve solo las suyas.
        cls.env['product.template'].search([('name', 'ilike', 'cama'), ('name', 'not ilike', 'ZZBT')]).write(
            {'is_published': False})

    def test_la_barra_el_envio_la_reaccion_cambiar_conversando_y_la_vitrina(self):
        for ancho, movil in ((390, True), (1366, False)):
            recibidos = len(self.worker.recibidos)
            with self.subTest(ancho=ancho), self.chrome(ancho, 844 if movil else 768, movil=movil) as browser:
                browser.navigate_to(self.base_url() + '/', wait_stop=True)
                r = self.evaluar(browser, VENDEDOR, timeout=240)
            # A1: sin carrito no hay barra; con algo, encima del campo de texto, con los números de Odoo y el PDF.
            self.assertIsNone(r['barraVacia'])
            self.assertIn('3 artículos', r['barra']['texto'])
            self.assertIn('$209.97', r['barra']['texto'])
            self.assertIn('+ ITBMS', r['barra']['texto'])
            self.assertEqual(r['barra']['pdf'], '/dcasa/brian/v1/carrito/cotizacion.pdf')
            self.assertEqual(r['barra']['expandida'], 'false')
            self.assertLessEqual(r['barra']['caja']['abajo'], r['composer']['y'] + 1, 'encima del campo de texto')
            # A5: «En tu carrito» arriba; Colchones (lo último) abierto, Camas plegado.
            self.assertIn('o_dcbt_seccion_carrito', r['vitrina']['primero'])
            self.assertEqual(r['vitrina']['lineas'], 2)
            self.assertEqual([g[:2] for g in r['vitrina']['grupos']], [['Colchones', True], ['Camas', False]])
            # A2: la línea del envío de Odoo en la tarjeta y la barra; Andrés no dijo ninguna cifra al sumarlo.
            self.assertIn('Envío a domicilio: Costa Inventada', r['envioEnLaTarjeta'])
            self.assertIn('+ envío', r['barraConEnvio']['texto'])
            # La hoja: editable, con el envío y los totales de Odoo, dentro del panel; el foco en «Cerrar».
            self.assertEqual(r['hoja']['expandida'], 'true')
            self.assertTrue(r['hoja']['foco'])
            self.assertEqual((r['hoja']['lineas'], r['hoja']['envio'] >= 1), (2, True))
            self.assertIn('Total con ITBMS', r['hoja']['texto'])
            self.assertGreaterEqual(r['hoja']['caja']['y'], r['hoja']['panel']['y'])
            # A3: una sola reacción, amable y con alternativas; la segunda baja no la repite.
            self.assertTrue(r['reaccion'].startswith('Vi que quitaste ZZBT Colchón Queen'), r['reaccion'])
            self.assertIn('Una más económica', r['chipsReaccion'])
            self.assertEqual((r['reacciones'], r['marca']), (1, '1'))
            self.assertEqual(r['trasEsc'], {'hoja': False, 'chat': True})
            # A4: lo propuso Andrés, lo aplicó la página en Odoo y lo confirmó con el carrito que quedó.
            self.assertTrue(r['quite'].startswith('Listo, quité'), r['quite'])
            self.assertEqual(r['reaccionesAlFinal'], 1, 'quitar a pedido del visitante no es «vi que quitaste»')
            self.assertTrue(r['sinScrollDeLado'])
            # Lo que llegó al Worker: el envío solo con el lugar (nunca un precio), el aviso de A3 una vez.
            nuevos = self.worker.recibidos[recibidos:]
            acciones = [c['accion'] for c in nuevos if c.get('accion')]
            envios = [a for a in acciones if a['tipo'] == 'confirmar_envio']
            self.assertEqual(envios, [{'tipo': 'confirmar_envio', 'lugar_id': self.costa.id, 'resultado': 'ok'}])
            self.assertEqual(len([a for a in acciones if a['tipo'] == 'carrito_bajo']), 1)
            (cambio,) = [c for c in nuevos if (c.get('accion') or {}).get('tipo') == 'confirmar_cambio']
            self.assertEqual((cambio['accion']['cantidad'], cambio['accion']['resultado'], cambio['carrito']), (0, 'ok', None),
                             'el carrito que quedó (vacío), el de Odoo')


# Las notas de voz en el chat de la tienda (docs/JUAN.md §12a; docs/BRIAN_TIENDA.md › «Notas de voz»): el micrófono sale
# solo si el Worker lo ofrece; graba con el micrófono de prueba de Chrome, manda el audio crudo con el pase y, con el texto,
# lo pinta en el globo del visitante y lo manda como un mensaje normal. Cancelar no manda nada; los errores, amables.
VOZ = """
    const panel = () => document.querySelector('#o_dcbt_panel');
    const voz = () => {
        const p = panel();
        const b = p && p.querySelector('button.o_dcbt_voz');
        const g = p && p.querySelector('.o_dcbt_voz_grabando');
        const pista = p && p.querySelector('.o_dcbt_voz_pista');
        return { boton: !!b && !b.hidden && b.getBoundingClientRect().width > 0, estado: g && !g.hidden ? g.dataset.estado : null,
                 campo: !!p && !p.querySelector('#o_dcbt_texto').hidden, enviar: !!p && !p.querySelector('.o_dcbt_enviar[type="submit"]').hidden,
                 pista: !!pista && !pista.hidden ? pista.textContent : null,
                 tiempo: p ? (p.querySelector('.o_dcbt_voz_tiempo') || {}).textContent : null,
                 anuncio: p ? (p.querySelector('.o_dcbt_composer [role="status"]') || {}).textContent : null };
    };
    // Los pedidos del micrófono (el permiso solo se pide al tocar el botón) y sus pistas, para ver que se apagan.
    window.__microfono = window.__microfono || { pedidos: 0, flujos: [] };
    const microfono = window.__microfono;
    if (navigator.mediaDevices && !microfono.contado) {
        const original = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
        navigator.mediaDevices.getUserMedia = async (c) => { microfono.pedidos++; const f = await original(c); microfono.flujos.push(f); return f; };
        microfono.contado = true;
    }
    const apagados = () => microfono.flujos.every((f) => f.getTracks().every((t) => t.readyState === 'ended'));
    const escribir = (texto) => {
        const campo = document.querySelector('#o_dcbt_texto');
        campo.value = texto;
        campo.dispatchEvent(new Event('input', { bubbles: true }));
        document.querySelector('#o_dcbt_panel .o_dcbt_composer').requestSubmit();
    };
    const preguntoPorLaVoz = () => performance.getEntriesByType('resource').some((e) => e.name.includes('/tienda/v1/voz'));
    const abrirChat = async () => {
        document.querySelector('button.o_dcbt_burbuja').click();
        await hasta(() => globos().some((g) => g.includes('Hola, soy Andrés')) && document.querySelector('#o_dcbt_panel .o_dcbt_chip'), 'el saludo');
        await hasta(preguntoPorLaVoz, 'la pregunta al Worker por el micrófono');
        await esperar(400);
    };
    const tocar = (sel) => document.querySelector('#o_dcbt_panel ' + sel).click();
    const grabar = async () => {
        tocar('button.o_dcbt_voz');
        await hasta(() => voz().estado === 'grabando', 'grabando');
    };
    const delCliente = () => [...document.querySelectorAll('#o_dcbt_panel .o_dcbt_del_cliente .o_dcbt_globo')].map((g) => g.textContent);
"""

VOZ_NO_DISPONIBLE = """(async () => {
    /*ESPERAR*/ /*VOZ*/
    await abrirChat();
    return { voz: voz(), pedidos: microfono.pedidos };
})()"""

VOZ_GRABAR = """(async () => {
    /*ESPERAR*/ /*VOZ*/
    const r = {};
    await abrirChat();
    await hasta(() => voz().boton, 'el micrófono');
    const boton = panel().querySelector('button.o_dcbt_voz');
    r.antes = { voz: voz(), pedidos: microfono.pedidos, etiqueta: boton.getAttribute('aria-label'),
                lado: boton.nextElementSibling === panel().querySelector('.o_dcbt_enviar[type="submit"]') };
    // Algo en el carrito: con la barra de A1 a la vista, la nota no tapa nada.
    escribir('Colchones');
    const tarjeta = await hasta(() => panel().querySelector('.o_dcbt_carrusel .o_dcbt_tarjeta [data-agregar]'), 'las tarjetas');
    tarjeta.click();
    await hasta(() => !panel().querySelector('.o_dcbt_barra').hidden, 'la barra del carrito');
    r.pistaTrasEscribir = voz().pista;
    const respuestas = globos().filter((g) => g.startsWith('Encontré estos')).length;
    await grabar();
    r.grabando = { voz: voz(), pedidos: microfono.pedidos, foco: document.activeElement === panel().querySelector('.o_dcbt_voz_listo'),
                   etiquetaListo: panel().querySelector('.o_dcbt_voz_listo').getAttribute('aria-label') };
    await hasta(() => /^0:0[2-9]/.test(voz().tiempo || ''), 'dos segundos de grabación');
    r.tiempo = voz().tiempo;
    r.cajas = { barra: caja(panel().querySelector('.o_dcbt_barra')), composer: caja(panel().querySelector('.o_dcbt_composer')),
                nota: caja(panel().querySelector('.o_dcbt_voz_grabando')), mensajes: caja(panel().querySelector('.o_dcbt_mensajes')),
                panel: caja(panel()), alto: innerHeight, ancho: innerWidth };
    tocar('.o_dcbt_voz_listo');
    await hasta(() => delCliente().includes('Busco un colchón queen'), 'el texto en el globo del visitante');
    await hasta(() => globos().filter((g) => g.startsWith('Encontré estos')).length > respuestas, 'la respuesta de Andrés al texto');
    r.despues = { voz: voz(), apagados: apagados(), grabacion: window.__dcasaBrian.grabacion,
                  guardado: sessionStorage.getItem('dcasa.brian.chat') || '' };
    r.sinScrollDeLado = document.documentElement.scrollWidth <= innerWidth;
    return r;
})()"""

VOZ_CANCELAR = """(async () => {
    /*ESPERAR*/ /*VOZ*/
    const r = {};
    await abrirChat();
    await hasta(() => voz().boton, 'el micrófono');
    const antes = delCliente().length;
    // Esc: se tira la nota y el micrófono se apaga; el chat sigue abierto.
    await grabar();
    await esperar(1200);
    const delChat = (a) => a.effect && a.effect.target && a.effect.target.closest && a.effect.target.closest('#o_dcasa_brian');
    r.animaciones = document.getAnimations().filter((a) => a.playState === 'running' && delChat(a)).length;
    r.reducido = matchMedia('(prefers-reduced-motion: reduce)').matches;
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    await hasta(() => voz().estado === null, 'cancelada con Esc');
    await esperar(300);
    r.esc = { voz: voz(), apagados: apagados(), abierto: !panel().hidden, foco: document.activeElement === panel().querySelector('button.o_dcbt_voz') };
    // La X: lo mismo.
    await grabar();
    await esperar(800);
    tocar('.o_dcbt_voz_cancelar');
    await hasta(() => voz().estado === null, 'cancelada con la X');
    await esperar(1500);
    r.x = { voz: voz(), apagados: apagados(), pedidos: microfono.pedidos, nuevos: delCliente().length - antes };
    return r;
})()"""

# Cada paso después del primero (el chat ya abierto): graba, toca «Listo» y espera lo que diga ``hasta``.
VOZ_PASO = """(async () => {
    /*ESPERAR*/ /*VOZ*/
    if (!panel() || panel().hidden || !globos().length) { await abrirChat(); }   // el panel se arma al abrir el chat
    await hasta(() => voz().boton, 'el micrófono');
    const antes = { cliente: delCliente().length, globos: globos().length };
    const r = {};
    MODO
    r.voz = voz();
    r.nuevosDelCliente = delCliente().slice(antes.cliente);
    r.nuevosDeAndres = globos().slice(antes.globos).filter((g) => !delCliente().includes(g));
    r.campo = document.querySelector('#o_dcbt_texto').value;
    r.apagados = apagados();
    return r;
})()"""

LISTO_Y_ERROR = """
    await grabar();
    await esperar(1200);
    tocar('.o_dcbt_voz_listo');
    await hasta(() => voz().estado === null && globos().length > antes.globos, 'la respuesta a la nota');
    await esperar(300);
"""

LISTO_Y_CAJA = """
    await grabar();
    await esperar(1200);
    tocar('.o_dcbt_voz_listo');
    await hasta(() => voz().estado === null && document.querySelector('#o_dcbt_texto').value, 'el texto en la caja');
    await esperar(600);
    r.foco = document.activeElement === document.querySelector('#o_dcbt_texto');
"""

SOLA_AL_TOPE = """
    await grabar();
    r.tope = voz().tiempo;
    await hasta(() => delCliente().length > antes.cliente, 'la nota que paró sola al tope', 15000);
"""

SIN_PERMISO = """
    const real = navigator.mediaDevices.getUserMedia;
    navigator.mediaDevices.getUserMedia = async () => { throw new DOMException('negado', 'NotAllowedError'); };
    tocar('button.o_dcbt_voz');
    await hasta(() => globos().length > antes.globos, 'el aviso del permiso');
    await esperar(300);
    navigator.mediaDevices.getUserMedia = real;
"""


@tagged('post_install', '-at_install')
class TestNotaDeVoz(NavegadorCase):

    def _js(self, codigo, modo=''):
        return codigo.replace('/*ESPERAR*/', ESPERAR).replace('/*VOZ*/', VOZ).replace('MODO', modo)

    def test_el_microfono_sale_solo_si_el_worker_lo_ofrece(self):
        self.worker.voz['disponible'] = False
        with self.chrome(1366, 768, movil=False, microfono=True) as browser:
            browser.navigate_to(self.base_url() + '/', wait_stop=True)
            r = self.evaluar(browser, self._js(VOZ_NO_DISPONIBLE))
        self.assertGreaterEqual(self.worker.consultas_voz, 1, 'la página le preguntó al Worker')
        self.assertFalse(r['voz']['boton'], 'sin notas de voz en el Worker, no hay micrófono')
        self.assertIsNone(r['voz']['pista'], 'ni la sugerencia de mandar una nota')
        self.assertTrue(r['voz']['campo'] and r['voz']['enviar'])
        self.assertEqual(r['pedidos'], 0)

    def test_graba_manda_pinta_el_texto_y_lo_envia(self):
        for ancho, movil in ((390, True), (1440, False)):
            voces, recibidos = len(self.worker.voces), len(self.worker.recibidos)
            with self.subTest(ancho=ancho), self.chrome(ancho, 844 if movil else 900, movil=movil, microfono=True) as browser:
                browser.navigate_to(self.base_url() + '/', wait_stop=True)
                r = self.evaluar(browser, self._js(VOZ_GRABAR), timeout=180)
            # Antes de tocarlo: el micrófono junto a «Enviar», la sugerencia una vez y el permiso sin pedir.
            self.assertTrue(r['antes']['voz']['boton'])
            self.assertTrue(r['antes']['lado'], 'el micrófono va junto a «Enviar»')
            self.assertEqual(r['antes']['etiqueta'], 'Mandar una nota de voz')
            self.assertEqual(r['antes']['voz']['pista'], 'Si prefieres, mándame una nota de voz.')
            self.assertEqual(r['antes']['pedidos'], 0, 'el permiso del micrófono solo se pide al tocarlo')
            self.assertIsNone(r['pistaTrasEscribir'], 'la sugerencia no insiste: se va con el primer mensaje')
            # Grabando: el tiempo, cancelar y «Listo» en el renglón del campo; el foco en «Listo».
            g = r['grabando']
            self.assertEqual(g['pedidos'], 1)
            self.assertEqual((g['voz']['campo'], g['voz']['enviar'], g['voz']['boton']), (False, False, False))
            self.assertTrue(g['foco'], 'el foco va a «Listo»')
            self.assertEqual(g['etiquetaListo'], 'Listo: mandar la nota de voz')
            self.assertIn('Grabando', g['voz']['anuncio'])
            self.assertTrue(r['tiempo'].endswith('/ 1:00'), r['tiempo'])
            # No tapa nada: la nota va dentro del renglón de escribir, debajo de la barra del carrito y en la pantalla.
            c = r['cajas']
            self.assertLessEqual(c['barra']['abajo'], c['composer']['y'] + 1, 'la barra del carrito, encima')
            self.assertLessEqual(c['mensajes']['abajo'], c['barra']['y'] + 1, 'la conversación, encima de la barra')
            self.assertGreaterEqual(c['nota']['y'], c['composer']['y'] - 1)
            self.assertLessEqual(c['nota']['abajo'], c['composer']['abajo'] + 1)
            self.assertLessEqual(c['nota']['derecha'], c['ancho'])
            self.assertLessEqual(c['composer']['abajo'], c['alto'] + 1)
            # Mandada: el texto como globo del visitante y como mensaje normal; el micrófono, apagado.
            d = r['despues']
            self.assertTrue(d['voz']['boton'] and d['voz']['campo'])
            self.assertTrue(d['apagados'], 'el micrófono se apaga al terminar')
            self.assertIsNone(d['grabacion'])
            self.assertNotIn('audio', d['guardado'].lower(), 'en el navegador queda solo el texto')
            self.assertTrue(r['sinScrollDeLado'])
            (nota,) = self.worker.voces[voces:]
            self.assertEqual(nota['tipo'], 'audio/webm', 'el WebM con Opus que graba Chrome')
            self.assertGreater(nota['kb'], 0)
            self.assertGreaterEqual(nota['duracion_ms'], 1800)
            self.assertLess(nota['duracion_ms'], 30000)
            self.assertIsNone(nota['motivo'])
            textos = [c.get('texto') for c in self.worker.recibidos[recibidos:]]
            self.assertIn('Busco un colchón queen', textos, 'el texto llegó por /tienda/v1/mensaje como un mensaje')

    def test_cancelar_no_manda_nada_y_con_movimiento_reducido_quieto(self):
        voces, recibidos = len(self.worker.voces), len(self.worker.recibidos)
        with self.chrome(390, 844, reducido=True, microfono=True) as browser:
            browser.navigate_to(self.base_url() + '/', wait_stop=True)
            r = self.evaluar(browser, self._js(VOZ_CANCELAR), timeout=120)
        self.assertTrue(r['reducido'])
        self.assertEqual(r['animaciones'], 0, 'grabando, nada se mueve con movimiento reducido')
        for como in ('esc', 'x'):
            with self.subTest(como=como):
                self.assertIsNone(r[como]['voz']['estado'])
                self.assertTrue(r[como]['voz']['campo'] and r[como]['voz']['boton'])
                self.assertTrue(r[como]['apagados'], 'el micrófono se apaga')
                self.assertIn('no se mandó nada', r[como]['voz']['anuncio'])
        self.assertTrue(r['esc']['abierto'], 'Esc tira la nota, no cierra el chat')
        self.assertTrue(r['esc']['foco'], 'el foco vuelve al micrófono')
        self.assertEqual(r['x']['pedidos'], 2)
        self.assertEqual(r['x']['nuevos'], 0)
        self.assertEqual(len(self.worker.voces), voces, 'al Worker no llegó ninguna nota')
        self.assertEqual(len(self.worker.recibidos), recibidos, 'ni un mensaje')

    def test_el_tope_lo_recortado_y_los_errores_amables(self):
        with self.chrome(1366, 768, movil=False, microfono=True) as browser:
            browser.navigate_to(self.base_url() + '/', wait_stop=True)
            # Corta sola al llegar al tope del Worker (aquí 3 s) y se manda.
            self.worker.voz.update(max_segundos=3, texto='Busco una cama matrimonial')
            r = self.evaluar(browser, self._js(VOZ_PASO, SOLA_AL_TOPE), timeout=120)
            self.assertTrue(r['tope'].endswith('/ 0:03'), r['tope'])
            self.assertEqual(r['nuevosDelCliente'], ['Busco una cama matrimonial'])
            self.assertLessEqual(self.worker.voces[-1]['duracion_ms'], 3000)
            self.assertGreaterEqual(self.worker.voces[-1]['duracion_ms'], 2500)
            self.assertTrue(r['apagados'])
            self.worker.voz['max_segundos'] = 60
            # Recortado: el texto queda en la caja para que el visitante lo revise y lo mande él.
            recibidos = len(self.worker.recibidos)
            self.worker.voz.update(texto='Quiero ver salas', recortado=True)
            r = self.evaluar(browser, self._js(VOZ_PASO, LISTO_Y_CAJA), timeout=120)
            self.assertEqual(r['campo'], 'Quiero ver salas')
            self.assertTrue(r['foco'])
            self.assertEqual(r['nuevosDelCliente'], [], 'no se mandó solo')
            self.assertEqual(len(self.worker.recibidos), recibidos)
            self.assertIn('tomé la primera parte', r['voz']['anuncio'])
            self.worker.voz['recortado'] = False
            self.evaluar(browser, "(() => { const c = document.querySelector('#o_dcbt_texto'); c.value = ''; c.dispatchEvent(new Event('input', { bubbles: true })); return true; })()")
            # Los errores del Worker, en palabras amables (y nada llega como mensaje).
            esperados = {
                'no_se_entendio': 'No te entendí bien. ¿Me lo repites un poco más cerca del micrófono? O escríbelo, por favor.',
                'tope_sesion': 'Por ahora no puedo escuchar más notas de voz. Escríbelo, por favor.',
                'muy_larga': 'Tu nota quedó muy larga (hasta un minuto). Mándame una más corta o escríbelo, por favor.',
                'fallo': 'No pude escuchar tu nota ahora. Inténtalo otra vez o escríbelo, por favor.',
            }
            for motivo, frase in esperados.items():
                with self.subTest(motivo=motivo):
                    recibidos = len(self.worker.recibidos)
                    self.worker.voz['motivo'] = motivo
                    r = self.evaluar(browser, self._js(VOZ_PASO, LISTO_Y_ERROR), timeout=120)
                    self.assertEqual(r['nuevosDeAndres'], [frase])
                    self.assertEqual(r['nuevosDelCliente'], [])
                    self.assertEqual(len(self.worker.recibidos), recibidos)
                    self.assertTrue(r['voz']['boton'], 'el micrófono sigue')
            # Sin permiso del micrófono: lo dice y ofrece escribirlo; no llega nada al Worker.
            voces = len(self.worker.voces)
            r = self.evaluar(browser, self._js(VOZ_PASO, SIN_PERMISO), timeout=60)
            self.assertEqual(r['nuevosDeAndres'], ['Para mandarme una nota de voz, permite el micrófono en tu navegador. Si no, '
                                                   'escríbelo, por favor.'])
            self.assertEqual(len(self.worker.voces), voces)
            self.assertTrue(r['voz']['boton'])
            # El Worker dejó de transcribir: lo dice y el micrófono se va.
            self.worker.voz['motivo'] = 'no_disponible'
            r = self.evaluar(browser, self._js(VOZ_PASO, LISTO_Y_ERROR), timeout=120)
            self.assertEqual(r['nuevosDeAndres'], ['Ahora no puedo escuchar notas de voz. Escríbelo, por favor.'])
            self.assertFalse(r['voz']['boton'], 'sin transcripción en el Worker, el micrófono se va')
            self.assertTrue(r['voz']['campo'], 'escribir sigue igual')
            self.assertTrue(r['apagados'], 'el micrófono de prueba quedó apagado en cada nota')

    def test_las_funciones_de_la_voz(self):
        with self.chrome(390) as browser:
            browser.navigate_to(self.base_url() + '/', wait_stop=True)
            self.evaluar(browser, '(async () => { ' + ESPERAR + ' return true; })()')
            r = self.evaluar(browser, """(() => {
                const m = window.odoo.loader.modules.get('@dcasa_brian_tienda/js/brian_tienda');
                const todo = () => true;
                return {
                    reloj: [m.relojVoz(0), m.relojVoz(7.9), m.relojVoz(60), m.relojVoz(-3)],
                    tipo: [m.tipoDeVoz(['audio/webm', 'audio/ogg', 'audio/mp4'], todo), m.tipoDeVoz(['audio/mp4'], todo),
                           m.tipoDeVoz(['audio/ogg'], (t) => t !== 'audio/ogg;codecs=opus'), m.tipoDeVoz(['audio/wav'], todo), m.tipoDeVoz(null, todo)],
                    ofrecida: [m.vozOfrecida({ disponible: false, tipos: ['audio/webm'] }), m.vozOfrecida({ disponible: true, tipos: [] }),
                               m.vozOfrecida({ disponible: true, max_segundos: 60, max_bytes: 1048576, tipos: ['audio/webm'] }),
                               m.vozOfrecida({ disponible: true, max_segundos: 'x', max_bytes: -1, tipos: ['audio/webm'] })],
                    textos: ['permiso', 'sin_microfono', 'corta', 'muy_pesada', 'audio', 'tope_red', 'tope_dia', 'presupuesto', 'ocupado', 'no_disponible', 'tardo', 'raro'].map(m.textoErrorVoz),
                };
            })()""")
        self.assertEqual(r['reloj'], ['0:00', '0:07', '1:00', '0:00'])
        self.assertEqual(r['tipo'], ['audio/webm;codecs=opus', 'audio/mp4', 'audio/ogg', '', ''])
        self.assertEqual(r['ofrecida'][:2], [None, None])
        self.assertEqual(r['ofrecida'][2], {'max_segundos': 60, 'max_bytes': 1048576, 'tipos': ['audio/webm']})
        self.assertEqual(r['ofrecida'][3], {'max_segundos': 60, 'max_bytes': 1048576, 'tipos': ['audio/webm']})
        for texto in r['textos']:
            self.assertTrue(texto.endswith(('escríbelo, por favor.', 'Escríbelo, por favor.', 'en un ratito.')), texto)
        self.assertNotIn('¡', ''.join(r['textos']))
