# La marca del panel (Ajustes › Marca del panel)

Cada empresa pone **su logo, su ícono y sus colores** en el panel administrativo, sin programar. Pedido del dueño
(2026-11-18): «como esto es un template que se va a seguir copiando para otras empresas, en Ajustes cada empresa tiene
que poder cargar su logo y customizar su interfaz con los colores de la empresa». **La página web pública no cambia**:
esa la programa el equipo (`website_dcasa`), no el usuario.

Código: `addons/dcasa_interfaz` (`models/marca.py`, `marca/`, `controllers/marca.py`, `views/marca_views.xml`,
`static/src/js/marca.js`) y las herramientas de Brian en `addons/dcasa_brian/models/herramientas_marca.py`.

## Cómo se usa

**Ajustes › Marca del panel** (en la barra de la izquierda, dentro de Ajustes; también es una pestaña de la pantalla de
Ajustes). Solo la ven los **administradores**. Por empresa (si hay varias, cada una la suya):

| Qué | Dónde se ve | Si no se sube |
|---|---|---|
| **Logo del panel** (PNG, JPG o WebP; mejor con fondo transparente) | Arriba de la barra de la izquierda y del menú del celular | El de fábrica |
| **Ícono del panel** (mejor cuadrado) | La pestaña del navegador (favicon), el ícono del iPhone y los de la app instalable de Android (192 y 512, normales y «maskable») | Sale del logo del panel; si tampoco hay logo, el de fábrica |
| **Color principal** | Botones, enlaces, lo elegido, lo activo de la barra, la barra del navegador del celular y los íconos de las apps; toda la escala de azules del tema (fondos suaves, el marino de las cabeceras, los celestes del modo oscuro) sale de él | `#1340B1` |
| **Color de acento** | Insignias, números destacados y puntos sobre el oscuro de la marca (lo que hoy es amarillo) | `#FED00F` |

Debajo, **«Cómo se va a leer»** se calcula mientras se elige. Al guardar, el panel se recarga y ya se ve. **«Volver a
la marca de fábrica»** quita el logo y el ícono subidos y vuelve a los colores de fábrica.

Con Brian (administradores, también por MCP): «¿qué colores tiene el panel?», «pon el panel en #1B3246», «pon esta
imagen como logo del sistema» (con la imagen adjunta en el chat o en Telegram), «vuelve a los colores de antes». En la
Guía: *Administrar el sistema › Empresa › Poner el logo y los colores de tu empresa en el sistema*.

## Las reglas de los colores (y por qué)

El tema tiene dos pares fijos de letra y fondo, escritos en cientos de reglas de Odoo y de los módulos propios:
**letra blanca sobre el principal** (y el principal como letra sobre blanco, en los enlaces) y **el acento sobre el
oscuro de la marca, con letra oscura encima** («el amarillo nunca toca el blanco»). En lugar de calcular un color de
letra para cada regla, el servidor **no acepta un color que rompa esos pares** y propone uno que sí sirve:

- El principal pide **4.5 a 1** con el blanco (WCAG AA). Si no llega: «es muy claro… Prueba con #BA5C11, el mismo tono
  más oscuro».
- El acento pide **4.5 a 1** con el oscuro de la marca (el marino que sale del principal) y **3 a 1** con el principal.
  Si no llega: «tiene que ser un color claro y vivo… Prueba con…».
- Un color mal escrito («azul», `#12345`) se rechaza; `1340b1` o `#13b` se aceptan y se guardan como `#1340B1`.
- Lo mismo lo dicen Ajustes al guardar, la línea «Cómo se va a leer» y Brian (todo sale de `marca/colores.py`).

## Cómo funciona por dentro

- **Campos propios en la empresa** (`res.company`): `dcasa_panel_logo`, `dcasa_panel_icono` (imágenes en adjuntos, o
  sea en R2), `dcasa_panel_color_principal`, `dcasa_panel_color_acento` (de fábrica, el azul y el amarillo) y
  `dcasa_panel_version` (cambia solo cuando la marca cambia de verdad; va en las direcciones para que los navegadores
  pidan lo nuevo). **No se reutilizan** `res.company.logo` ni `primary_color`/`secondary_color`: esos son de las
  facturas, los correos y el sitio, se imprimen sobre papel blanco y no tienen las reglas de lectura del panel; así
  cambiar uno no cambia el otro.
- **De fábrica, la página es la de siempre.** Si no se subió nada y los colores son los de fábrica, `web.webclient_bootstrap`
  enlaza la misma hoja de Odoo, el mismo logo (`/dcasa_base/static/img/logo.png`), favicon, ícono del iPhone,
  manifiesto y `theme-color`. Por eso las referencias visuales y las pruebas de antes siguen pasando sin tocarlas.
- **Colores en caliente, sin recompilar.** El azul no vive en un solo lugar: además de `--dc-azul-*`, Bootstrap y Odoo lo
  calculan al compilar (unas 280 reglas: botones y su color al pasar el puntero, focos, pestañas, la barra de estado, el
  chat…), así que una variable CSS inyectada no llega. Con colores propios, la página enlaza
  `/dcasa_interfaz/marca/hoja/<empresa>/<versión>/<la hoja de Odoo>`: **la misma hoja compilada**, con cada color de la
  familia del azul llevado a la familia del principal (`marca/colores.py`, `Giro`: gira el tono, escala la saturación y
  la luz, y lo que se leía con blanco se sigue leyendo) y el amarillo exacto cambiado por el acento
  (`marca/tinte.py`). Mismas reglas en el mismo orden: la cascada no cambia. Se pinta una vez por hoja y colores
  (0,1 s, queda en memoria) y el navegador la guarda un año. El **modo oscuro** usa su propia hoja (`web.assets_web_dark`)
  pintada igual. Si pintar falla, la dirección **redirige a la hoja de Odoo**: el panel nunca se queda sin estilos.
- **No se pintan**, a propósito: las paletas que elige la persona (colores del calendario, etiquetas, tarjetas del
  kanban), los colores del contenido de la web (`o_cc*`, `o-color-*`) y los íconos de apps que ya tienen su color de
  categoría (Socios morado, Facturación verde…); en esos solo cambia el punto amarillo.
- **Íconos de las apps** (los SVG de la barra y del Inicio): `ir.ui.menu.load_web_menus` los pinta con la misma regla.
- **Logo**: `session_info` le pasa al navegador `dcasa_marca: {logo, nombre}`; la barra lateral y el menú del celular
  lo usan (`static/src/js/marca.js`). El logo se sirve por `/web/image/res.company/<id>/dcasa_panel_logo`.
- **Favicon e íconos del celular**: `/dcasa_interfaz/marca/icono/<empresa>/<versión>/<nombre>.png` los hace de la
  imagen subida (`marca/iconos.py`, con `ImageProcess` de Odoo: la misma geometría que `scripts/iconos_de_la_marca.py`).
  Son públicos, como los de fábrica (Android los pide a veces sin la sesión). Un SVG no se acepta: no se puede achicar.
- **El manifiesto** (`controllers/webmanifest.py`) lleva el color principal y esos íconos.

## Lo que no cambia

- **La página web** (`website_dcasa`): portada, tienda, `/web/login` (que usa el diseño del sitio) y `/master`. Una
  prueba compara las hojas, los íconos y el `theme-color` de la portada, la tienda y `/web/login` antes y después de
  poner una marca.
- Los documentos (factura, cotización, PDF) y los correos: siguen con el logo y los colores de la empresa de
  *Ajustes › Empresas*.
- El nombre de la app instalable («D'CASA Panamá», `web.web_app_name`) y las tipografías del panel.

## Límites conocidos

- Las hojas que Odoo carga aparte al abrir una gráfica o una tabla dinámica (`web.assets_backend_lazy`) y la de
  imprimir el panel no se pintan: ahí quedan detalles en el azul de fábrica.
- Con `?debug=assets` el panel usa la hoja de Odoo tal cual (colores de fábrica): ese modo arma los estilos de otra forma.
- El ícono de la pestaña «Marca del panel» dentro de Ajustes y el robot de Brian son imágenes fijas.
- La página «sin conexión» del panel (la que sale sin internet) muestra el ícono de fábrica.

## Pruebas

`addons/dcasa_interfaz/tests/test_marca_panel.py` (colores y contraste, el tinte de la hoja, la empresa, la página, los
íconos, la web que no cambia, la legibilidad de las hojas pintadas en claro y en oscuro con la red de
`test_modo_oscuro.py`, permisos y el navegador), `addons/dcasa_brian/tests/test_marca_brian.py` (las herramientas y
MCP) y `addons/dcasa_guia/tests/test_guia.py` (la tarea de la Guía).
