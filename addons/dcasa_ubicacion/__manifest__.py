{
    'name': 'Ubicación exacta de entrega (web, chat y QR del motorizado)',
    'summary': 'La clienta marca su punto en el mapa (web o enlace del chat) o lo comparte por WhatsApp; el envío se '
               'cotiza solo y el comprobante lleva un QR con Waze y Google Maps para el motorizado',
    'description': """
Pedido del dueño de Baby Caleb (2026-11-25), con la idea de Nébula y sus fallas corregidas. Ver docs/UBICACION.md.

* **Checkout**: «¿Dónde le entregamos?» con «Marcar en el mapa» (Google Maps, pin fijo, «Usar mi ubicación», buscador
  de barriadas y lugares de la tabla de envíos, «¿Es aquí?») o «Escribirla». La zona (barriada, corregimiento,
  distrito, provincia) sale de la tabla de la calculadora y el precio del envío, de ahí mismo.
* **Chat**: el enlace de un solo uso ``/u/<secreto>`` amarrado a la conversación (Juan lo manda; al confirmar, Juan le
  escribe con la zona y el precio) y ``POST /dcasa/juan/v1/ubicacion`` para la ubicación de WhatsApp o un enlace de
  mapa. ``cotizar_envio`` sin lugar usa el punto guardado.
* **Motorizado**: el QR del comprobante y de la nota de entrega abre ``/entrega/<secreto>`` (Waze, Google Maps,
  dirección, referencia, llamar). Vence a los 30 días y no cambia nada.
* **Brian / MCP**: ``ubicacion_de_entrega``, ``enlace_de_ubicacion_para_cliente`` y ``poner_ubicacion_de_entrega``.
* Claves (opcionales, en Cloudflare): ``GOOGLE_MAPS_CLAVE_NAVEGADOR`` (el mapa) y ``GOOGLE_MAPS_CLAVE_SERVIDOR`` (la
  calle). Sin ellas: GPS, búsqueda en la tabla y dirección escrita siguen funcionando.
""",
    'version': '19.0.1.0.0',
    'category': 'Sales/Sales',
    'author': "D'CASA Panamá",
    'website': 'https://dcasapty.com',
    'license': 'LGPL-3',
    'depends': ['dcasa_envios', 'dcasa_conversaciones', 'website_dcasa', 'dcasa_invoice', 'dcasa_brian',
                'dcasa_brian_tienda', 'website_sale', 'delivery', 'sale_stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/iconos_templates.xml',
        'views/paginas_templates.xml',
        'views/checkout_templates.xml',
        'views/reporte_templates.xml',
        'views/pedido_templates.xml',
        'views/backend_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'dcasa_ubicacion/static/src/lib/mapa_entrega.js',
            'dcasa_ubicacion/static/src/interactions/checkout_ubicacion.js',
            'dcasa_ubicacion/static/src/scss/ubicacion.scss',
        ],
    },
    'installable': True,
}
