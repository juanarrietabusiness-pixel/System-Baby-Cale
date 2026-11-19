"""Lo que tiene que cumplir la marca Baby Caleb en los documentos y los correos (docs/MARCA_BABY_CALEB.md).

Lo usan las pruebas de este módulo y las de los módulos que imprimen con su papel (abonos, nómina, contabilidad,
consolidación) o que mandan correos (dcasa_correo, dcasa_camila): así la regla vive en un solo lugar.
"""
import re

from lxml import html as lxml_html

# Lo de D'CASA que no puede quedar: el azul, el amarillo, los navys y la tinta de su ADN, y sus letras.
COLORES_DE_DCASA = ('1340b1', 'fed00f', '0e2a6b', '0b2a6f', '0b1f5c', '1b2233', '4a5163', 'f4f1ea')
LETRAS_DE_DCASA = ('anton', 'oswald', 'inter')

# Los del contrato (brand.json de Baby Caleb).
NAVY = '1b3246'
NARANJA = 'ee924a'
SALVIA = '91c9a2'
NARANJA_TEXTO = '985d2f'
CREMA = 'f9f6ed'


def sin_rastro_de_dcasa(case, texto, donde):
    """Ni un color ni una letra de D'CASA en ``texto`` (CSS, HTML o SCSS)."""
    minusculas = texto.lower()
    for color in COLORES_DE_DCASA:
        case.assertNotIn(color, minusculas, f"{donde}: queda el color #{color.upper()} de D'CASA")
    for letra in LETRAS_DE_DCASA:
        case.assertIsNone(re.search(rf'\b{letra}\b', minusculas), f"{donde}: queda la letra {letra} de D'CASA")


def parte_de(case, css, archivo):
    """Lo que aporta ``archivo`` (p. ej. ``/dcasa_invoice/static/src/scss/report_dcasa.scss``) al CSS compilado de un
    paquete: Odoo marca el principio de cada archivo con su ruta en un comentario."""
    marca = f'/* {archivo} */'
    case.assertIn(marca, css, f'{archivo} no está en el paquete de estilos de los informes')
    parte = css.split(marca, 1)[1]
    siguiente = re.search(r'/\* /[\w./-]+ \*/', parte)
    return parte[:siguiente.start()] if siguiente else parte


def css_de_los_informes(case, archivo, paquete='web.report_assets_common'):
    """El CSS compilado de ``archivo`` dentro de un paquete de estilos (de fábrica, el de los informes, el que lee
    wkhtmltopdf; ``web.assets_backend`` para el panel, ``web.assets_frontend`` para la web). Sin servidor."""
    adjuntos = case.env['ir.qweb']._get_asset_bundle(paquete, js=False).css()
    return parte_de(case, ''.join(adjunto.raw.decode() for adjunto in adjuntos), archivo)


def css_de_la_hoja(case, informe, registros, archivo):
    """Como ``css_de_los_informes``, pero tal como lo pide wkhtmltopdf: del paquete de estilos que enlaza el HTML del
    informe, por HTTP al propio Odoo. ``case`` es un ``HttpCase``. Devuelve el CSS entero y la parte del archivo."""
    html = case.env['ir.actions.report']._render_qweb_html(informe, registros.ids)[0].decode()
    enlaces = [href for href in lxml_html.fromstring(html).xpath('//link[@rel="stylesheet"]/@href')
               if 'report_assets_common' in href]
    case.assertTrue(enlaces, 'el informe no enlaza su hoja de estilos')
    respuesta = case.url_open(enlaces[0])
    case.assertEqual(respuesta.status_code, 200)
    return respuesta.text, parte_de(case, respuesta.text, archivo)


def letra_de_relleno(css):
    """Los colores de relleno (naranja y verde) usados como color de letra en un CSS: deben ser ninguno."""
    plano = css.lower().replace(' ', '')
    return [color for color in (NARANJA, SALVIA) if re.search(rf'(?<![-\w])color:#{color}', plano)]


def estilo(elemento):
    """El estilo en línea de un elemento (y su bgcolor), sin espacios y en minúsculas."""
    return re.sub(r'\s+', '', (elemento.get('style') or '') + ';bgcolor:' + (elemento.get('bgcolor') or '')).lower()


def correo_con_la_marca(case, cuerpo, donde):
    """Lo que pide el contrato a un correo: estilos en línea (sin <style>, sin @font-face ni woff2), Montserrat con
    respaldo Arial/Helvetica en todo lo que fija letra, nada de D'CASA y ningún texto en el naranja de relleno."""
    minusculas = cuerpo.lower()
    for prohibido in ('<style', '@font-face', 'woff', '<link', 'gradient', 'box-shadow', 'text-shadow', '<script',
                      'javascript:'):
        case.assertNotIn(prohibido, minusculas, f'{donde}: {prohibido}')
    sin_rastro_de_dcasa(case, cuerpo, donde)
    arbol = lxml_html.fromstring(cuerpo)
    for elemento in arbol.iter():
        if not isinstance(elemento.tag, str):
            continue
        propio = estilo(elemento)
        letra = re.search(r'font-family:([^;]+)', propio)
        if letra:
            case.assertTrue(letra.group(1).startswith('montserrat'), f'{donde}: letra {letra.group(1)}')
            case.assertIn('arial', letra.group(1), f'{donde}: sin respaldo Arial')
            case.assertIn('helvetica', letra.group(1), f'{donde}: sin respaldo Helvetica')
        color = re.search(r'(?:^|;)color:#([0-9a-f]{6})', propio)
        if color:
            case.assertNotEqual(color.group(1), NARANJA, f'{donde}: el naranja de relleno no se lee como letra (2.37)')
            case.assertNotEqual(color.group(1), SALVIA, f'{donde}: el verde de relleno no se lee como letra (1.90)')
            case.assertNotEqual(color.group(1), 'ffffff', f'{donde}: la letra blanca no es de la marca')
    return arbol


def botones_naranja(arbol):
    """Las celdas que hacen de botón principal: relleno naranja (bgcolor y background-color)."""
    return [td for td in arbol.iter('td')
            if f'bgcolor:#{NARANJA}' in estilo(td) and f'background-color:#{NARANJA}' in estilo(td)]


def es_pastilla_navy_sobre_naranja(case, celda):
    """El botón principal: pastilla (radio 999px) y, en el enlace, la letra navy en negrita."""
    case.assertIn('border-radius:999px', estilo(celda), 'el botón es una pastilla')
    (enlace,) = celda.iter('a')
    propio = estilo(enlace)
    case.assertIn(f'color:#{NAVY}', propio, 'la letra del botón es navy (5.56 sobre el naranja)')
    case.assertIn('font-weight:bold', propio)
    case.assertTrue(enlace.text_content().strip(), 'el botón es texto: se lee aunque no carguen las imágenes')
    return enlace
