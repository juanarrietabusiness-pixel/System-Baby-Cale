"""Las rutas públicas de la ubicación (docs/UBICACION.md). Van estrictas, como el enlace de los choferes:

* ``GET /u/<secreto>``: la página donde la clienta marca su punto (el enlace de un solo uso que le manda Juan).
  ``POST …/zona`` ({lat, lon}) dice qué zona y qué precio salen del punto, sin guardar nada; ``POST …/guardar``
  ({lat, lon, origen, precision, referencia}) lo guarda. El secreto autentica: sin sesión ni cookie
  (``save_session=False``), sin CSRF. Vencido, usado o inventado: la misma página de «este enlace ya no sirve».
* ``GET /entrega/<secreto>``: la página del motorizado (el QR del comprobante). Solo lee; vence a los 30 días.
* ``POST /tienda/ubicacion/zona`` (JSON-RPC del sitio): la vista previa del checkout (zona, precio y el aviso si lo
  escrito nombra otro distrito). No guarda nada.

Todas: ``Cache-Control: no-store``, ``X-Robots-Tag: noindex``, ``Referrer-Policy: no-referrer``, CSP con nonce en las
páginas, cuerpo de a lo sumo 2 KB y 60 peticiones por minuto por IP (la red /64 en IPv6). Las coordenadas no se
escriben en el registro del servidor.
"""
import json
import secrets

from odoo import http
from odoo.addons.dcasa_base.red import llave_ip
from odoo.addons.dcasa_envios.controllers.choferes import excede
from odoo.http import request

from ..models.zona import UbicacionInvalida
from ..motor import geo

MAX_CUERPO = 2048
MAX_BUSQUEDA = 60
MAX_POR_MINUTO = 60
ESPERA_S = 60
CABECERAS = {
    'Cache-Control': 'no-store',
    'X-Robots-Tag': 'noindex, nofollow',
    'Referrer-Policy': 'no-referrer',
    'X-Content-Type-Options': 'nosniff',
}
# Google Maps en el navegador (su guía de CSP estricta): el cargador trae más scripts (``strict-dynamic``), imágenes y
# teselas de sus dominios, y pone estilos en línea.
CSP_CON_MAPA = ("default-src 'none'; script-src 'nonce-{nonce}' 'strict-dynamic' https: 'unsafe-eval' blob:; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: blob: https://*.googleapis.com https://*.gstatic.com https://*.google.com "
                "https://*.googleusercontent.com; connect-src 'self' https://*.googleapis.com https://*.google.com "
                "https://*.gstatic.com data: blob:; frame-src https://*.google.com; worker-src blob:; "
                "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
CSP_SIN_MAPA = ("default-src 'none'; script-src 'nonce-{nonce}'; style-src 'nonce-{nonce}'; font-src 'self'; "
                "img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'none'; "
                "frame-ancestors 'none'")


def _cabeceras(**extra):
    return list(dict(CABECERAS, **extra).items())


def _json(datos, status=200):
    return request.make_json_response(datos, headers=_cabeceras(), status=status)


def _demasiado(en_json=True):
    texto = 'Muchos intentos seguidos: espere un minuto y vuelva a intentar.'
    respuesta = _json({'error': texto}, 429) if en_json else request.make_response(
        texto, headers=_cabeceras(**{'Content-Type': 'text/plain; charset=utf-8'}), status=429)
    respuesta.headers['Retry-After'] = str(ESPERA_S)
    return respuesta


def _cuerpo():
    """El JSON pequeño que manda la página, o ``None``."""
    if (request.httprequest.content_length or 0) > MAX_CUERPO:
        return None
    crudo = request.httprequest.get_data()
    if len(crudo) > MAX_CUERPO:
        return None
    try:
        cuerpo = json.loads(crudo.decode('utf-8') or 'null')
    except (ValueError, UnicodeDecodeError, RecursionError):
        return None
    return cuerpo if isinstance(cuerpo, dict) else None


def _limite():
    return excede('ubicacion:' + llave_ip(request.httprequest.remote_addr), maximo=MAX_POR_MINUTO)


def _pagina(plantilla, valores, con_mapa=False, status=200):
    nonce = secrets.token_urlsafe(16)
    html = request.env['ir.qweb']._render(plantilla, dict(valores, nonce=nonce))
    csp = (CSP_CON_MAPA if con_mapa else CSP_SIN_MAPA).format(nonce=nonce)
    return request.make_response(html, status=status, headers=_cabeceras(**{
        'Content-Type': 'text/html; charset=utf-8', 'Content-Security-Policy': csp,
        'Permissions-Policy': 'geolocation=(self), camera=(), microphone=()'}))


def vista_previa(env, lat, lon, texto=''):
    """Lo que la página muestra antes de confirmar: la zona, el precio (o «se lo confirmamos») y, si lo escrito nombra
    otro distrito, el aviso. ``UbicacionInvalida`` si el punto no sirve. No guarda nada."""
    Ubicacion = env['dcasa.ubicacion']
    _lat, _lon, zona = Ubicacion._validar(lat, lon)
    precio = Ubicacion._precio(zona['lugar'])
    return {
        'zona': zona['texto'],
        'barriada': zona['barriada'], 'corregimiento': zona['corregimiento'], 'distrito': zona['distrito'],
        'provincia': zona['provincia'],
        'precio': precio['total_txt'] if precio['con_precio'] else None,
        'aviso': geo.aviso_de_cruce(texto, zona, Ubicacion._distritos()) if texto else '',
    }


def buscar_lugares(env, texto):
    """Hasta 6 lugares de la tabla (barriadas, PH, lugares conocidos) con su zona y su punto, para centrar el mapa.
    Sin precios, km ni ids: es lo mismo que se ve en cualquier mapa."""
    texto = geo.texto_corto(texto, MAX_BUSQUEDA)
    if len(texto) < 2 or len(texto.split()) > 8:
        return []
    Lugar = env['dcasa.envio.lugar'].sudo()
    datos = Lugar.buscar_para_cotizar(texto, limite=10)
    salida = []
    for resultado in datos['resultados']:
        lugar = Lugar.browse(resultado['id'])
        punto = geo.punto(lugar.lat, lugar.lon)
        if punto:
            salida.append({'nombre': resultado['nombre'], 'zona': resultado.get('zona') or '',
                           'lat': punto[0], 'lon': punto[1]})
        if len(salida) >= 6:
            break
    return salida


class UbicacionPublica(http.Controller):

    # --- El enlace de un solo uso (chat) ---------------------------------------------------------------------------

    def _enlace(self, token):
        enlace = request.env['dcasa.ubicacion.enlace']._del_secreto(token)
        if not enlace or enlace.estado == 'vencido':
            return None
        return enlace

    @http.route('/u/<string:token>', type='http', auth='public', methods=['GET'], csrf=False, save_session=False)
    def enlace_pagina(self, token, **_parametros):
        if _limite():
            return _demasiado(en_json=False)
        enlace = self._enlace(token)
        empresa = request.env.company.sudo()
        valores = {'empresa': empresa.name, 'token': token, 'estado': 'no_sirve', 'zona': ''}
        if enlace and enlace.estado == 'usado':
            valores.update(estado='usado', zona=enlace.zona or '')
        elif enlace:
            clave = request.env['dcasa.ubicacion']._clave_navegador()
            valores.update(estado='vigente', clave_google=clave, nombre=(enlace.partner_id.name or '').split()[0]
                           if enlace.partner_id.name else '')
            return _pagina('dcasa_ubicacion.enlace_pagina', valores, con_mapa=bool(clave))
        return _pagina('dcasa_ubicacion.enlace_pagina', valores, status=200 if enlace else 404)

    @http.route('/u/<string:token>/zona', type='http', auth='public', methods=['POST'], csrf=False,
                save_session=False, max_content_length=MAX_CUERPO)
    def enlace_zona(self, token, **_parametros):
        if _limite():
            return _demasiado()
        enlace = self._enlace(token)
        if not enlace or enlace.estado != 'vigente':
            return _json({'error': 'Este enlace ya no sirve.'}, 404)
        cuerpo = _cuerpo() or {}
        try:
            return _json(vista_previa(request.env, cuerpo.get('lat'), cuerpo.get('lon')))
        except UbicacionInvalida as error:
            return _json({'error': str(error.args[0]), 'motivo': error.motivo}, 422)

    @http.route('/u/<string:token>/buscar', type='http', auth='public', methods=['POST'], csrf=False,
                save_session=False, max_content_length=MAX_CUERPO)
    def enlace_buscar(self, token, **_parametros):
        if _limite():
            return _demasiado()
        enlace = self._enlace(token)
        if not enlace or enlace.estado != 'vigente':
            return _json({'error': 'Este enlace ya no sirve.'}, 404)
        return _json({'lugares': buscar_lugares(request.env, (_cuerpo() or {}).get('texto'))})

    @http.route('/u/<string:token>/guardar', type='http', auth='public', methods=['POST'], csrf=False,
                save_session=False, max_content_length=MAX_CUERPO)
    def enlace_guardar(self, token, **_parametros):
        if _limite():
            return _demasiado()
        enlace = self._enlace(token)
        if not enlace or enlace.estado != 'vigente':
            return _json({'error': 'Este enlace ya no sirve.'}, 404)
        cuerpo = _cuerpo() or {}
        origen = cuerpo.get('origen')
        if origen not in ('gps', 'pin', 'busqueda'):
            return _json({'error': 'No sabemos cómo marcó el punto: vuelva a intentarlo.'}, 400)
        referencia = geo.texto_corto(cuerpo.get('referencia'), geo.MAX_REFERENCIA)
        if not referencia:
            return _json({'error': 'Cuéntenos cómo reconocer el sitio (color de la casa, portón, un punto de '
                                   'referencia).', 'campo': 'referencia'}, 400)
        try:
            zona = enlace._confirmar(cuerpo.get('lat'), cuerpo.get('lon'), origen,
                                     precision=cuerpo.get('precision'), referencia=referencia)
        except UbicacionInvalida as error:
            return _json({'error': str(error.args[0]), 'motivo': error.motivo}, 422)
        return _json({'ok': True, 'zona': zona['texto']})

    # --- La página del motorizado (QR) -----------------------------------------------------------------------------

    @http.route('/entrega/<string:token>', type='http', auth='public', methods=['GET'], csrf=False,
                save_session=False)
    def entrega_pagina(self, token, **_parametros):
        if _limite():
            return _demasiado(en_json=False)
        entrega = request.env['dcasa.ubicacion.entrega']._del_secreto(token)
        empresa = request.env.company.sudo()
        if not entrega:
            return _pagina('dcasa_ubicacion.entrega_pagina', {'empresa': empresa.name, 'datos': None}, status=404)
        return _pagina('dcasa_ubicacion.entrega_pagina', {'empresa': empresa.name,
                                                           'datos': entrega._para_el_motorizado()})

    # --- La vista previa del checkout ------------------------------------------------------------------------------

    @http.route('/tienda/ubicacion/zona', type='jsonrpc', auth='public', website=True, methods=['POST'])
    def tienda_zona(self, lat=None, lon=None, texto=None, **_parametros):
        if _limite():
            return {'error': 'Muchos intentos seguidos: espere un minuto.'}
        try:
            return vista_previa(request.env, lat, lon, geo.texto_corto(texto, 300))
        except UbicacionInvalida as error:
            return {'error': str(error.args[0]), 'motivo': error.motivo}

    @http.route('/tienda/ubicacion/buscar', type='jsonrpc', auth='public', website=True, methods=['POST'])
    def tienda_buscar(self, texto=None, **_parametros):
        if _limite():
            return {'error': 'Muchos intentos seguidos: espere un minuto.'}
        return {'lugares': buscar_lugares(request.env, texto)}
