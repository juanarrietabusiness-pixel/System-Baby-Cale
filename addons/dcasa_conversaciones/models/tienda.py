"""Datos verificados de la tienda (dirección, horario, WhatsApp, cómo llegar), sacados de donde ya viven.

Una sola fuente para la herramienta ``horario_y_tienda`` y para las entradas automáticas de conocimiento con
fuente «tienda»: la dirección (calle, ciudad y provincia) y la ubicación en el mapa salen de la empresa
(*Ajustes › Empresas*: su dirección y la latitud y longitud de su contacto), el WhatsApp del sitio
(``website_dcasa``) y el horario de los ajustes de Juan. Si la dueña cambia cualquiera de ellos, el asistente lo dice
al día. Aquí no se escribe ningún dato de una empresa en particular (pedido del dueño, 2026-11-18: el conocimiento
del bot arranca en cero): lo que la empresa no haya llenado, el asistente no lo dice.
"""


def website_publico(env):
    return env['website'].sudo().search([], order='sequence, id', limit=1)


def url_base(env, website=None):
    website = website if website is not None else website_publico(env)
    base = website._dcasa_url_publica() if website else ''
    return (base or env['ir.config_parameter'].sudo().get_param('web.base.url') or '').rstrip('/')


def datos_tienda(env):
    """``{tienda, direccion, como_llegar, horario, whatsapp, correo, sitio}`` con lo que ya está en Odoo."""
    ajustes = env['dcasa.juan.ajustes'].obtener()
    horario = ajustes.horario()
    empresa = env.company.sudo()
    website = website_publico(env)
    base = url_base(env, website)
    direccion = ', '.join(p for p in (empresa.street, empresa.street2, empresa.city, empresa.state_id.name) if p)
    telefono = (website.dcasa_whatsapp_number if website and website.dcasa_whatsapp_number else empresa.phone) or ''
    return {
        'tienda': empresa.name,
        'direccion': direccion,
        'como_llegar': como_llegar(empresa, direccion, base),
        'horario': {
            'texto': f'{horario.texto()} (hora de Panamá)',
            **horario.como_json(),
        },
        'whatsapp': telefono,
        'correo': empresa.email or '',
        'sitio': base,
    }


def como_llegar(empresa, direccion, base):
    """La dirección, la ruta en Google Maps (solo si la empresa tiene su latitud y longitud) y la página «Visítanos»."""
    contacto = empresa.partner_id
    partes = [direccion] if direccion else []
    if contacto.partner_latitude or contacto.partner_longitude:
        partes.append('Ruta en Google Maps: https://www.google.com/maps/dir/?api=1&destination='
                      f'{contacto.partner_latitude}%2C{contacto.partner_longitude}')
    if base:
        partes.append(f'Más datos en {base}/visitanos')
    return '. '.join(partes) + '.' if partes else ''


def texto_tienda(datos):
    """Los mismos datos como párrafos para la base de conocimiento."""
    lineas = []
    if datos['direccion']:
        lineas.append(f"{datos['tienda']} está en {datos['direccion']}.")
    if datos['como_llegar']:
        lineas.append(f"Cómo llegar: {datos['como_llegar']}")
    lineas.append(f"El equipo atiende {datos['horario']['texto'][0].lower() + datos['horario']['texto'][1:]}. "
                  'Juan te contesta por mensaje a cualquier hora.')
    if datos['whatsapp']:
        lineas.append(f"WhatsApp: {datos['whatsapp']}.")
    if datos['correo']:
        lineas.append(f"Correo: {datos['correo']}.")
    return '\n'.join(lineas)
