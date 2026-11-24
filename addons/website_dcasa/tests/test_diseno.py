# ruff: noqa: E501  (JavaScript del navegador embebido en texto)
"""La marca de Baby Caleb en el sitio (docs/MARCA_BABY_CALEB.md, pedido del dueño del 2026-11-19: «el branding de la
web de Baby Caleb tal cual»). Lo que se fija aquí:

* La pastilla de vidrio crema de babycaleb.com (la marca «Baby Caleb» escrita, el menú, el carrito, la búsqueda y la
  cuenta) es la misma en todas las páginas, también en la tienda, la ficha, el carrito, las legales, la cuenta y la
  campaña. Sin barra de anuncios encima.
* El pie es el de su web: crema, sin fotos ni velos, con la marca, el lema, los enlaces, el contacto y los legales.
* En Chrome: el crema de fondo, el navy de la letra, Montserrat en todo, los titulares como frase, el botón principal
  naranja con letra navy y en pastilla, y las reglas que no se rompen: el naranja y el verde son relleno (nunca texto
  ni borde) y no queda nada del azul, el amarillo ni el navy de D'CASA.
"""
import re

from odoo.addons.website_dcasa.models.black_weekend import PARAM_ACTIVO, PARAM_FIN, PARAM_INICIO
from odoo.tests import HttpCase, tagged

# Páginas con su cabecera de página (o el hero de la portada): la pastilla va encima (o_header_overlay).
CON_CABECERA_ENCIMA = ('/', '/socios', '/visitanos', '/contactus', '/privacidad', '/terminos', '/web/login')

# Los colores de la marca, como los dice el navegador (getComputedStyle).
CREMA, SURFACE, NAVY = 'rgb(249, 246, 237)', 'rgb(242, 239, 229)', 'rgb(27, 50, 70)'
NARANJA, VERDE = 'rgb(238, 146, 74)', 'rgb(145, 201, 162)'
DE_DCASA = ('rgb(19, 64, 177)', 'rgb(254, 208, 15)', 'rgb(14, 42, 107)', 'rgb(15, 53, 145)')


def _cabecera(html):
    return re.search(r'<header id="top".*?</header>', html, re.S).group(0)


def _clases_wrapwrap(html):
    return re.search(r'<div id="wrapwrap" class="([^"]*)"', html).group(1).split()


# Lo que se mide en cada página (devuelve la lista de fallas; vacía = bien). Se recorren todos los elementos visibles.
REVISAR_MARCA = r"""
    (async () => {
        const esperar = (ms) => new Promise((ok) => setTimeout(ok, ms));
        for (let i = 0; i < 200 && document.body.getAttribute('is-ready') !== 'true'; i++) { await esperar(50); }
        await document.fonts.ready;
        const fallas = [];
        const fallar = (m) => fallas.push(m);
        const cs = (el, p) => getComputedStyle(el, p);
        const nombre = (el) => el.tagName.toLowerCase() + (typeof el.className === 'string' && el.className.trim()
            ? '.' + el.className.trim().split(/\s+/).slice(0, 3).join('.') : '');
        const visible = (el) => { const r = el.getBoundingClientRect(); const e = cs(el);
            return r.width > 0 && r.height > 0 && e.visibility !== 'hidden' && e.display !== 'none'
                && parseFloat(e.opacity) > 0; };
        const tieneTexto = (el) => [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
        if (cs(document.body).backgroundColor !== '%(crema)s') fallar('el fondo no es crema: ' + cs(document.body).backgroundColor);
        // La burbuja de Brian (dcasa_brian_tienda) es de otro módulo y tiene su propia marca.
        const todos = [...document.querySelectorAll('#wrapwrap *')].filter((el) => visible(el)
            && !el.closest('[class*="o_dcbt"], [id^="o_dcbt"]'));
        for (const el of todos) {
            const e = cs(el);
            // El naranja y el verde son RELLENO: nunca color de letra (de un texto visible) ni de borde.
            if (tieneTexto(el) && ['%(naranja)s', '%(verde)s'].includes(e.color)) {
                fallar('texto en naranja o verde: ' + nombre(el) + ' «' + el.textContent.trim().slice(0, 30) + '»');
            }
            for (const lado of ['Top', 'Right', 'Bottom', 'Left']) {
                if (parseFloat(e['border' + lado + 'Width']) > 0 && e['border' + lado + 'Style'] !== 'none'
                        && ['%(naranja)s', '%(verde)s'].includes(e['border' + lado + 'Color'])
                        && e.backgroundColor !== e['border' + lado + 'Color']) {
                    fallar('borde naranja o verde: ' + nombre(el));
                    break;
                }
            }
            // Nada del azul, el amarillo ni el navy de D'CASA.
            for (const valor of [e.color, e.backgroundColor, e.borderTopColor, e.outlineColor]) {
                if (%(de_dcasa)s.includes(valor)) { fallar('color de D\'CASA (' + valor + ') en ' + nombre(el)); break; }
            }
            // Letra: Montserrat y nada de Anton ni Oswald. Los titulares, como frase.
            if (tieneTexto(el) && !/Montserrat/.test(e.fontFamily) && !el.closest('.fa, .oi, svg, code, pre, .o_dcbt_burbuja, #o_dcbt_panel')) {
                fallar('letra que no es Montserrat: ' + nombre(el) + ' (' + e.fontFamily + ')');
            }
            if (/Anton|Oswald/.test(e.fontFamily)) fallar('Anton u Oswald en ' + nombre(el));
            // (Los antetítulos sí van en caja alta: 12 px, 700 y .14em, aunque sean un <h2>.)
            if (/^H[1-3]$/.test(el.tagName) && e.textTransform === 'uppercase' && !el.matches('.o_dcasa_kicker')) {
                fallar('titular en caja alta: ' + nombre(el));
            }
            // El piso de 12 px.
            if (tieneTexto(el) && parseFloat(e.fontSize) < 12 && !el.closest('.visually-hidden, .sr-only')) {
                fallar('letra de ' + e.fontSize + ' (menos de 12 px): ' + nombre(el));
            }
        }
        // El botón principal: relleno naranja, letra navy, pastilla. (En la ficha «Agregar al carrito» es de contorno a
        // propósito: el principal es «Pregunta por este producto por WhatsApp».)
        for (const boton of [...document.querySelectorAll('#wrapwrap .btn-primary:not(#add_to_cart)')].filter(visible)) {
            const e = cs(boton);
            if (e.backgroundColor !== '%(naranja)s') fallar('botón principal sin el naranja: ' + nombre(boton) + ' ' + e.backgroundColor);
            if (e.color !== '%(navy)s') fallar('botón principal sin letra navy: ' + nombre(boton) + ' ' + e.color);
            const alto = boton.getBoundingClientRect().height;
            if (parseFloat(e.borderTopLeftRadius) < alto / 2 - 1) fallar('botón principal sin pastilla: ' + nombre(boton));
            if (e.fontWeight !== '700') fallar('botón principal sin 700: ' + nombre(boton));
        }
        // El aro de foco: 2 px navy (tokens de su web).
        const enlace = document.querySelector('#wrapwrap main a, #wrapwrap #wrap a');
        if (enlace) {
            enlace.focus({ focusVisible: true });
            const e = cs(enlace);
            if (document.activeElement === enlace && e.outlineStyle !== 'none'
                    && (e.outlineColor !== '%(navy)s' || e.outlineWidth !== '2px')) {
                fallar('aro de foco que no es el navy de 2 px: ' + e.outlineWidth + ' ' + e.outlineColor);
            }
            enlace.blur();
        }
        // El pie: crema, sin imágenes, filtros ni velos.
        const pie = document.querySelector('footer#bottom');
        if (cs(pie).backgroundColor !== '%(crema)s') fallar('el pie no es crema: ' + cs(pie).backgroundColor);
        for (const el of [pie, ...pie.querySelectorAll('*')]) {
            const e = cs(el);
            if (e.backgroundImage !== 'none' || e.filter !== 'none' || parseFloat(e.opacity) < 1) {
                fallar('el pie tiene imagen, filtro u opacidad en ' + nombre(el));
                break;
            }
        }
        if (document.documentElement.scrollWidth > innerWidth) fallar('la página se sale de lado: ' + document.documentElement.scrollWidth);
        return fallas;
    })()
""".replace('%(crema)s', CREMA).replace('%(naranja)s', NARANJA).replace('%(verde)s', VERDE).replace(
    '%(navy)s', NAVY).replace('%(de_dcasa)s', str(list(DE_DCASA)))


@tagged('post_install', '-at_install')
class TestDisenoUniforme(HttpCase):

    def setUp(self):
        super().setUp()
        self.website = self.env.ref('website.default_website')
        param = self.env['ir.config_parameter'].sudo()
        param.set_param(PARAM_ACTIVO, '1')
        param.set_param(PARAM_INICIO, '')
        param.set_param(PARAM_FIN, '')
        self.producto = self.env['product.template'].create({
            'name': 'Pañal de prueba de diseño', 'list_price': 45.0, 'is_published': True,
            'dcasa_black_weekend': True,
        })
        self.paginas = [
            '/', '/shop', self.producto.website_url, '/shop/cart', '/black-weekend', '/socios', '/visitanos',
            '/contactus', '/privacidad', '/terminos', '/web/login',
        ]

    def test_la_pildora_es_la_misma_en_todas_las_paginas(self):
        for ruta in self.paginas:
            with self.subTest(ruta=ruta):
                respuesta = self.url_open(ruta)
                self.assertEqual(respuesta.status_code, 200)
                html = respuesta.text
                cabecera = _cabecera(html)
                self.assertNotIn('o_dcasa_anuncios', cabecera, 'sin la barra de anuncios encima (S01Nav.tsx)')
                self.assertIn('o_main_nav', cabecera)
                # Solo la marca escrita (Montserrat 700 navy), sin el sello: como en S01Nav.tsx.
                self.assertRegex(cabecera, r'<span class="o_dcasa_marca" translate="no">Baby Caleb</span>')
                self.assertNotIn('logo-200.webp', cabecera)
                self.assertNotIn('/web/image/website/1/logo', cabecera)
                menu = re.search(r'id="top_menu".*?</ul>', cabecera, re.S).group(0)
                for enlace, texto in (('/shop', 'Productos'), ('/beneficios', 'Beneficios'), ('/historia', 'Historia'),
                                      ('/tips', 'Tips'), ('/como-comprar', 'Cómo comprar'), ('/faq', 'FAQ')):
                    self.assertRegex(menu, rf'href="{re.escape(enlace)}"[^>]*>\s*<span>{texto}</span>')
                # Los íconos de lucide (bolsa, lupa y persona), no los de FontAwesome, todos con la misma clase.
                self.assertNotIn('fa-shopping-cart', cabecera)
                self.assertNotIn('oi-search', cabecera)
                self.assertGreaterEqual(cabecera.count('class="o_dcasa_icono"'), 3)
                self.assertIn('o_wsale_my_cart', cabecera, 'Carrito')
                self.assertIn('o_search_modal', cabecera, 'Búsqueda')
                # «Inicia sesión» de Odoo, o «Mi cuenta» (/mi-cuenta) si dcasa_mi_cuenta está instalado.
                self.assertRegex(cabecera, r'href="/(?:web/login|mi-cuenta)"', 'Cuenta')
                # Sin «Escríbenos» en el menú (decisión de la dueña, 2026-11-15): WhatsApp sigue en la portada y el pie.
                self.assertNotIn('btn_cta', cabecera, 'el menú ya no lleva «Escríbenos»')
                self.assertEqual(cabecera.count('id="top_menu"'), 1)
                # El menú del celular es un diálogo que recibe el foco (website_dcasa.menu_movil_accesible).
                self.assertRegex(cabecera, r'id="top_menu_collapse_mobile"[^>]*tabindex="-1"')
                self.assertIn('aria-label="Abrir menú"', cabecera)

    def test_paginas_con_cabecera_de_pagina_llevan_la_pastilla_encima(self):
        for ruta in CON_CABECERA_ENCIMA:
            with self.subTest(ruta=ruta):
                html = self.url_open(ruta).text
                self.assertIn('o_header_overlay', _clases_wrapwrap(html))
                self.assertRegex(html, r'class="[^"]*o_dcasa_hero', 'con la pastilla encima, la página abre con su cabecera')
        for ruta in ('/shop', self.producto.website_url, '/shop/cart', '/black-weekend'):
            with self.subTest(ruta=ruta):
                self.assertNotIn('o_header_overlay', _clases_wrapwrap(self.url_open(ruta).text))

    def test_pie_como_el_de_babycaleb(self):
        for ruta in ('/', '/shop', '/socios', '/privacidad'):
            with self.subTest(ruta=ruta):
                html = self.url_open(ruta).text
                pie = re.search(r'<footer.*?</footer>', html, re.S).group(0)
                self.assertIn('o_dcasa_footer', pie)
                self.assertIn('babycalebpanama@gmail.com', pie)
                self.assertIn('Esenciales de bebé hipoalergénicos y biodegradables', pie, 'el lema de su web')
                self.assertIn('Venta 100% online con entrega a domicilio en Ciudad de Panamá.', pie)
                self.assertIn('href="https://www.instagram.com/babycalebpanama"', pie)
                self.assertIn('href="/whatsapp"', pie)
                self.assertIn('href="/privacidad"', pie)
                self.assertIn('href="/terminos"', pie)
                self.assertIn('Baby Caleb Panamá</span>. Todos los derechos reservados.', pie)
                self.assertNotIn('dcasapty', pie)
                for prohibido in ('<img', '<picture', 'background-image', 'opacity', 'filter:',
                                  'o_dcasa_hero', 'o_we_bg_filter', 'o_bg_img'):
                    self.assertNotIn(prohibido, pie)

    def test_fotos_principales_a_tiempo(self):
        """Rendimiento (ronda 6): la foto LCP de cada página se pide pronto y al ancho justo."""
        portada = self.url_open('/').text
        precarga = re.search(r'<link[^>]*rel="preload"[^>]*as="image"[^>]*>', portada)
        self.assertTrue(precarga, 'la foto del hero se pide desde la cabecera')
        self.assertIn('hero-bebe-800.webp 800w', precarga.group(0))
        self.assertIn('fetchpriority="high"', precarga.group(0))
        self.assertNotIn('fontawesome-webfont.woff2?v=4.7.0" as="font"', portada)
        self.assertNotRegex(self.url_open('/shop').text, r'rel="preload"[^>]*as="image"')
        ficha = self.url_open(self.producto.website_url).text
        foto = re.search(r'<img[^>]*product_detail_img[^>]*>', ficha)
        if foto:   # sin foto propia, Odoo dibuja el marcador y no hay LCP de producto
            self.assertIn('loading="eager"', foto.group(0))
            self.assertIn('fetchpriority="high"', foto.group(0))

    def test_la_marca_es_el_nombre_aunque_haya_otro_logo(self):
        """Como en babycaleb.com, la pastilla lleva el nombre escrito y no una imagen: aunque se suba otro logo desde
        el editor (que sigue sirviendo para el editor, el favicon y los datos para Google)."""
        self.website.logo = self.env['website']._default_logo()
        cabecera = _cabecera(self.url_open('/shop').text)
        self.assertNotIn('/web/image/website/', cabecera)
        self.assertRegex(cabecera, r'<span class="o_dcasa_marca" translate="no">Baby Caleb</span>')

    def test_la_marca_en_el_navegador(self):
        """Medido en Chrome, elemento por elemento, en la portada, la tienda, la ficha, el contacto, la cuenta y una
        legal: el crema, el navy, Montserrat, el botón principal naranja con letra navy en pastilla, el aro de foco
        navy, el piso de 12 px, y que el naranja y el verde nunca sean texto ni borde ni quede color de D'CASA."""
        for ruta in ('/', '/shop', self.producto.website_url, '/visitanos', '/web/login', '/privacidad'):
            for ancho in (1440, 390):
                with self.subTest(ruta=ruta, ancho=ancho):
                    self.browser_size = f'{ancho}x900'
                    codigo = f"""
                        (async () => {{
                            const fallas = await {REVISAR_MARCA.strip()};
                            if (fallas.length) {{ console.error('Marca a {ancho}px: ' + fallas.slice(0, 12).join(' · ')); }}
                            else {{ console.log('test successful'); }}
                        }})();
                    """
                    self.browser_js(ruta, codigo, timeout=120)

    def test_la_pastilla_de_vidrio_crema_en_el_navegador(self):
        """La pastilla de babycaleb.com (`.bc-vidrio` de tokens.css): vidrio crema (surface al 50 %; al bajar, al 80 %),
        desenfoque y saturación (o la refracción), esquinas de 16 px, la marca en Montserrat 700 navy y los enlaces
        navy en 500. La misma en la tienda y en /socios: ya no hay vidrio ahumado."""
        codigo = """
            (async () => {
            const fallar = (m) => console.error('Pastilla: ' + m);
            for (let i = 0; i < 200 && document.body.getAttribute('is-ready') !== 'true'; i++) {
                await new Promise((ok) => setTimeout(ok, 50));
            }
            const nav = [...document.querySelectorAll('header#top .o_main_nav')].find((n) => n.getBoundingClientRect().width > 0);
            const vidrio = getComputedStyle(nav, '::before');
            const filtro = vidrio.backdropFilter || vidrio.webkitBackdropFilter || 'none';
            if (!/^blur\\(16px\\) saturate\\(2\\.1\\) brightness\\(1\\.06\\)$|^url\\(/.test(filtro)) {
                fallar('la pastilla no es de vidrio: ' + filtro);
            }
            if (vidrio.backgroundColor !== 'rgba(242, 239, 229, 0.5)') fallar('tinte del vidrio: ' + vidrio.backgroundColor);
            if (vidrio.backgroundImage !== 'none') fallar('degradado en el vidrio');
            if (vidrio.borderTopLeftRadius !== '16px') fallar('esquinas: ' + vidrio.borderTopLeftRadius);
            const marca = nav.querySelector('.o_dcasa_marca');
            const m = getComputedStyle(marca);
            if (m.color !== 'rgb(27, 50, 70)' || m.fontWeight !== '700' || !/Montserrat/.test(m.fontFamily)) {
                fallar('la marca no es Montserrat 700 navy: ' + m.color + ' ' + m.fontWeight + ' ' + m.fontFamily);
            }
            if (marca.getBoundingClientRect().height > 40) fallar('la marca se partió en dos líneas');
            const enlace = document.querySelector('#top_menu .nav-link:not(.active)');
            if (enlace && enlace.getBoundingClientRect().width > 0) {
                const e = getComputedStyle(enlace);
                if (e.color !== 'rgb(27, 50, 70)' || e.fontWeight !== '500' || e.textTransform !== 'none') {
                    fallar('enlace del menú: ' + e.color + ' ' + e.fontWeight + ' ' + e.textTransform);
                }
            }
            // Al bajar, el vidrio se tiñe más (Odoo marca la cabecera con o_header_is_scrolled).
            window.scrollTo(0, 600);
            await new Promise((ok) => setTimeout(ok, 700));
            const abajo = getComputedStyle(nav, '::before').backgroundColor;
            if (document.querySelector('header#top').classList.contains('o_header_is_scrolled')
                    && abajo !== 'rgba(242, 239, 229, 0.8)') {
                fallar('al bajar el vidrio no se tiñe: ' + abajo);
            }
            console.log('test successful');
            })();
        """
        for ruta in ('/shop', '/socios', '/'):
            for ancho in (1440, 390):
                with self.subTest(ruta=ruta, ancho=ancho):
                    self.browser_size = f'{ancho}x900'
                    self.browser_js(ruta, codigo, timeout=120)

    def test_cabecera_con_la_pagina_abierta_desplazada(self):
        """Bug de producción (staging, /visitanos): con la página abierta ya desplazada las interacciones de la cabecera
        daban «¡Vaya! Ocurrió un error» al visitante. Con la pastilla de Baby Caleb la cabecera ya no mide nada, pero
        tiene que seguir arrancando sin error así, y con la refracción puesta donde el navegador la sabe dibujar."""
        codigo = """
            (async () => {
            const fallar = (m) => console.error('Cabecera: ' + m);
            // El JavaScript del sitio llega en el paquete diferido de Odoo, después del «load».
            const modulo = '@website_dcasa/js/animaciones';
            for (let i = 0; i < 400 && !(odoo.loader?.modules?.has(modulo)
                    && document.body.getAttribute('is-ready') === 'true'); i++) {
                await new Promise((ok) => setTimeout(ok, 50));
            }
            if (!odoo.loader.modules.has(modulo)) {
                fallar('no cargó ' + modulo);
                return;
            }
            const servicio = odoo.__WOWL_DEBUG__.root.env.services['public.interactions'];
            const cabecera = document.querySelector('header#top');
            servicio.stopInteractions(cabecera);
            const raiz = document.documentElement;
            if (raiz.classList.contains('o_dcasa_refraccion')) fallar('al detenerse, la refracción no se quitó');
            cabecera.style.transform = 'translateY(-400px)';
            window.scrollTo(0, document.body.scrollHeight);
            try {
                await servicio.startInteractions(cabecera);
            } catch (e) {
                fallar('las interacciones de la cabecera no arrancan con la página desplazada: ' + e.message);
            }
            await new Promise((ok) => setTimeout(ok, 300));
            const puede = navigator.userAgentData?.brands?.some((b) => b.brand === 'Chromium')
                && CSS.supports('backdrop-filter', 'url(#a)');
            // Con movimiento reducido el vidrio se queda mate y quieto, sin refracción (tokens.css de su web).
            const quieto = matchMedia('(prefers-reduced-motion: reduce)').matches;
            if (puede && !quieto && !raiz.classList.contains('o_dcasa_refraccion')) fallar('sin la refracción del vidrio');
            if (quieto && raiz.classList.contains('o_dcasa_refraccion')) fallar('con movimiento reducido no hay refracción');
            if (puede && !quieto
                    && document.querySelector('#dcasa-liquido feTurbulence animate')?.getAttribute('dur') !== '18s') {
                fallar('el vidrio no fluye (sin el movimiento lento del ruido, 18 s)');
            }
            cabecera.style.transform = '';
            console.log('test successful');
            })();
        """
        self.browser_js('/visitanos', codigo, timeout=120)
