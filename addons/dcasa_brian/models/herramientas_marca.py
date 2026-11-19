"""Brian y la marca del panel (Ajustes › Marca del panel, ``dcasa_interfaz/models/marca.py``) — 2026-11-18.

Las cuatro van por el mismo camino que Ajustes (``res.company._dcasa_panel_poner``): exige administrador ANTES de
escribir y valida igual (un color que no se lee se rechaza con uno que sí sirve). Solo administradores, como la
pantalla: la marca es de toda la empresa y la ve todo el equipo.

* ``ver_marca_del_panel`` (lectura): logo, ícono y colores de ahora, cómo se leen y el botón a la pantalla.
* ``cambiar_colores_del_panel`` (construcción): se deshace con otro cambio o con «volver a fábrica», no toca dinero,
  permisos ni datos de nadie, y lo que no se lee ni se guarda. Queda en el registro de acciones.
* ``poner_imagen_del_panel`` (construcción): el logo o el ícono, de una imagen que la persona le mandó a Brian en el
  chat o en Telegram. Como la imagen viene en el mensaje, la regla de los adjuntos hace que pida **Permitir** igual.
  **Por MCP no se manda la imagen**: el canal solo lleva texto (cada dato hasta 10 000 letras; un logo en base64 no
  cabe) y no tiene adjuntos. Desde MCP sirve con una imagen que ya se le mandó a Brian en el chat (por su nombre);
  si no, se sube en Ajustes › Marca del panel.
* ``volver_a_la_marca_de_fabrica`` (sensible): borra el logo y el ícono que se subieron, y eso no se recupera sin el
  archivo: lo aprueba una persona (Permitir), y desde MCP nunca se ejecuta solo.
"""
import base64

from odoo import api, models
from odoo.addons.dcasa_interfaz.marca import colores as C

from .registro import BrianError, herramienta

ADMIN = ('base.group_system',)
MENU = 'dcasa_interfaz.menu_dcasa_marca_panel'
IMAGENES = ('image/png', 'image/jpeg', 'image/webp')
USOS = {'logo': ('dcasa_panel_logo', 'logo'), 'icono': ('dcasa_panel_icono', 'ícono')}
QUE = {
    'colores': 'los colores de fábrica',
    'logo': 'el logo de fábrica (se quita el que subiste)',
    'icono': 'el ícono de fábrica (se quita el que subiste; si hay logo propio, el ícono sale de él)',
    'todo': 'el logo, el ícono y los colores de fábrica (se quitan los que subiste)',
}
PARAM_COLOR = {'type': 'string', 'description': 'Código del color, p. ej. «#1B3246». Opcional.'}


class BrianHerramientasMarca(models.AbstractModel):
    _inherit = 'brian.herramientas'

    @api.model
    def _b_marca(self, cambio=None):
        """Lo que contestan las cuatro: la marca de ahora y el botón a la pantalla."""
        empresa = self.env.company
        datos = empresa._dcasa_panel_resumen()
        datos['donde'] = 'Ajustes › Marca del panel'
        datos['la_web'] = 'La página web pública no cambia: esa la programa el equipo.'
        menu = self.env.ref(MENU, raise_if_not_found=False)
        if menu and self._b_menu_visible(menu):
            destino = self._b_destino_de_menu(menu, 'Marca del panel')
            if destino:
                datos['abrir'] = destino
        if cambio is not None:
            datos['mensaje'] = cambio
        return datos

    @api.model
    @herramienta(
        nombre='ver_marca_del_panel',
        descripcion='La marca del panel de la empresa: si el logo y el ícono son propios o de fábrica, los colores '
                    'principal y de acento, cómo se leen y dónde se cambian. No cambia la página web.',
        nivel='lectura', categoria='general', grupos=ADMIN,
        ejemplos=['¿qué colores tiene el panel?', '¿ya subimos nuestro logo al sistema?'],
    )
    def _h_ver_marca_del_panel(self):
        return self._b_marca()

    @api.model
    @herramienta(
        nombre='cambiar_colores_del_panel',
        descripcion='Cambia el color principal (la tinta: letra, títulos, enlaces, íconos; va sobre el crema del '
                    'panel) o el de acento (el relleno del botón principal y de lo elegido, con la letra del principal '
                    'encima) del panel. Si un color no se lee, dice cuál sí sirve.',
        parametros={'principal': PARAM_COLOR, 'acento': PARAM_COLOR},
        nivel='construccion', categoria='general', grupos=ADMIN,
        ejemplos=['pon el panel en verde oscuro #173A2B → principal=#173A2B',
                  'el acento en amarillo #F2C14E → acento=#F2C14E'],
    )
    def _h_cambiar_colores_del_panel(self, principal=None, acento=None):
        if not principal and not acento:
            raise BrianError('Dime el color principal, el de acento o los dos (por ejemplo, principal=#1B3246).')
        empresa = self.env.company
        try:
            nuevo_principal = C.normalizar(principal) or empresa.dcasa_panel_color_principal or C.FABRICA_PRINCIPAL
            nuevo_acento = C.normalizar(acento) or empresa.dcasa_panel_color_acento or C.FABRICA_ACENTO
        except ValueError as error:
            raise BrianError(str(error)) from None
        problema = C.problema_del_principal(nuevo_principal) or C.problema_del_acento(nuevo_acento, nuevo_principal)
        if problema:
            raise BrianError(problema + ' No cambié nada.')
        cambio = empresa._dcasa_panel_poner({'dcasa_panel_color_principal': nuevo_principal,
                                             'dcasa_panel_color_acento': nuevo_acento})
        return self._b_marca(
            'Listo: el panel ya tiene los colores nuevos; se ven al recargar la página (cada persona, en su próxima '
            'carga).' if cambio else 'Ya tenía esos colores: no cambié nada.')

    @api.model
    @herramienta(
        nombre='poner_imagen_del_panel',
        descripcion='Pone como logo o ícono del panel una imagen PNG, JPG o WebP que te mandaron en el chat o en '
                    'Telegram. Por MCP no llegan archivos: súbela en Ajustes › Marca del panel.',
        parametros={
            'adjunto': {'type': 'string', 'description': 'Nombre o número de la imagen que te mandaron, '
                                                         'p. ej. «logo.png».'},
            'uso': {'type': 'string', 'enum': list(USOS),
                    'description': 'logo (barra de la izquierda y menú del celular) o icono (pestaña y app del '
                                   'celular).'},
        },
        requeridos=['adjunto', 'uso'],
        nivel='construccion', categoria='general', grupos=ADMIN,
        ejemplos=['pon esta imagen como logo del sistema → adjunto=«logo.png», uso=logo'],
    )
    def _h_poner_imagen_del_panel(self, adjunto, uso):
        if uso not in USOS:
            raise BrianError('«uso» es logo o icono.')
        campo, nombre = USOS[uso]
        archivo = self._b_adjunto(adjunto)
        if (archivo.mimetype or '') not in IMAGENES:
            raise BrianError(f'«{archivo.name}» no es una imagen PNG, JPG o WebP. Si el {nombre} está en SVG, '
                             'pídele que lo exporte como PNG con fondo transparente.')
        self.env.company._dcasa_panel_poner({campo: base64.b64encode(archivo.raw)})
        return self._b_marca(f'Listo: «{archivo.name}» es el {nombre} del panel. Se ve al recargar la página.')

    @api.model
    @herramienta(
        nombre='volver_a_la_marca_de_fabrica',
        descripcion='Devuelve el panel a la marca de fábrica: los colores, el logo, el ícono o todo. Quita lo que se '
                    'subió (no se recupera sin el archivo). Pide confirmación.',
        parametros={'que': {'type': 'string', 'enum': list(QUE),
                            'description': 'colores, logo, icono o todo.'}},
        requeridos=['que'],
        nivel='sensible', categoria='general', grupos=ADMIN,
        ejemplos=['vuelve a los colores de antes → que=colores', 'quita nuestro logo del sistema → que=logo'],
    )
    def _h_volver_a_la_marca_de_fabrica(self, que):
        if que not in QUE:
            raise BrianError('«que» es colores, logo, icono o todo.')
        cambio = self.env.company._dcasa_panel_fabrica(que)
        return self._b_marca(f'Listo: el panel volvió a {QUE[que]}. Se ve al recargar la página.' if cambio
                             else 'Ya estaba así: no cambié nada.')


class BrianPoliticaMarca(models.AbstractModel):
    _inherit = 'brian.politica'

    @api.model
    def _resumir_volver_a_la_marca_de_fabrica(self, argumentos):
        que = argumentos.get('que')
        if que not in QUE:
            return None
        return (f'Devolver el panel de {self.env.company.name} a {QUE[que]}. Lo ve todo el equipo al recargar la '
                'página; la página web no cambia.')

    @api.model
    def _resumir_poner_imagen_del_panel(self, argumentos):
        uso = USOS.get(argumentos.get('uso'), (None, 'logo o ícono'))[1]
        return (f'Poner «{argumentos.get("adjunto")}» como {uso} del panel de {self.env.company.name}. Lo ve todo el '
                'equipo; no cambia las facturas ni la página web.')
