# La marca del panel (Ajustes › Marca del panel)

Cada empresa pone **su logo, su ícono y sus colores** en el panel administrativo, sin programar. Pedido del dueño
(2026-11-18): «como esto es un template que se va a seguir copiando para otras empresas, en Ajustes cada empresa tiene
que poder cargar su logo y customizar su interfaz con los colores de la empresa». **La página web pública no cambia**:
esa la programa el equipo (`website_dcasa`), no el usuario.

**De fábrica, el panel es Baby Caleb** (pedido del dueño del 2026-11-19, contrato en
[MARCA_BABY_CALEB.md](MARCA_BABY_CALEB.md)): crema `#F9F6ED` de fondo y superficie `#F2EFE5`, letra navy `#1B3246`,
el botón principal naranja `#EE924A` con letra navy, verde salvia `#91C9A2` para lo secundario, radio de 14 px y
Montserrat (titulares en 700, como frase). Antes de esa fecha la fábrica era la de D'CASA (azul `#1340B1`, amarillo
`#FED00F`, blancos fríos, Anton); ya no queda nada de eso en el panel.

Código: `addons/dcasa_interfaz` (`models/marca.py`, `marca/`, `controllers/marca.py`, `views/marca_views.xml`,
`static/src/js/marca.js`) y las herramientas de Brian en `addons/dcasa_brian/models/herramientas_marca.py`.

## Cómo se usa

**Ajustes › Marca del panel** (en la barra de la izquierda, dentro de Ajustes; también es una pestaña de la pantalla de
Ajustes). Solo la ven los **administradores**. Por empresa (si hay varias, cada una la suya):

| Qué | Dónde se ve | Si no se sube |
|---|---|---|
| **Logo del panel** (PNG, JPG o WebP; mejor con fondo transparente) | Arriba de la barra de la izquierda y del menú del celular | El de fábrica |
| **Ícono del panel** (mejor cuadrado) | La pestaña del navegador (favicon), el ícono del iPhone y los de la app instalable de Android (192 y 512, normales y «maskable») | Sale del logo del panel; si tampoco hay logo, el de fábrica |
| **Color principal** (la tinta) | La letra, los títulos, los enlaces, los íconos, lo activo, el aro de foco y el cuadro de los íconos de las apps; toda la escala del navy del tema (`--dc-azul-600…950`) sale de él | `#1B3246` (navy) |
| **Color de acento** (el relleno) | El botón principal, lo elegido (pestañas, pastillas, la etapa de la barra de estado), las barras de las gráficas, las insignias y los puntos, con sus tonos para letra y bordes | `#EE924A` (naranja) |

Debajo, **«Cómo se va a leer»** se calcula mientras se elige. Al guardar, el panel se recarga y ya se ve. **«Volver a
la marca de fábrica»** quita el logo y el ícono subidos y vuelve a los colores de fábrica.

Con Brian (administradores, también por MCP): «¿qué colores tiene el panel?», «pon el panel en #173A2B», «pon esta
imagen como logo del sistema» (con la imagen adjunta en el chat o en Telegram), «vuelve a los colores de antes». En la
Guía: *Administrar el sistema › Empresa › Poner el logo y los colores de tu empresa en el sistema*.

## Las reglas de los colores (y por qué)

El tema tiene dos pares fijos de letra y fondo, escritos en cientos de reglas de Odoo y de los módulos propios:
**el principal como letra sobre el crema** (y la letra crema encima del principal, donde es relleno) y **el acento de
relleno con la letra del principal encima** (en Baby Caleb, el naranja con la letra navy: «nunca letra blanca sobre el
naranja», que daría 2.37 a 1). En lugar de calcular un color de letra para cada regla, el servidor **no acepta un color
que rompa esos pares** y propone uno que sí sirve:

- El principal pide **4.5 a 1** con la superficie crema `#F2EFE5` (WCAG AA; el fondo más oscuro sobre el que va como
  letra). Si no llega: «es muy claro… Prueba con #AB5410, el mismo tono más oscuro».
- El acento pide **4.5 a 1** con el principal (es la letra que lleva encima). Si no llega: «tiene que ser un color claro
  y vivo… Prueba con…».
- Un color mal escrito («azul», `#12345`) se rechaza; `1b3246` o `#13b` se aceptan y se guardan como `#1B3246`.
- Lo mismo lo dicen Ajustes al guardar, la línea «Cómo se va a leer» y Brian (todo sale de `marca/colores.py`).

## Cómo funciona por dentro

- **Campos propios en la empresa** (`res.company`): `dcasa_panel_logo`, `dcasa_panel_icono` (imágenes en adjuntos, o
  sea en R2), `dcasa_panel_color_principal`, `dcasa_panel_color_acento` (de fábrica, el navy y el naranja) y
  `dcasa_panel_version` (cambia solo cuando la marca cambia de verdad; va en las direcciones para que los navegadores
  pidan lo nuevo). **No se reutilizan** `res.company.logo` ni `primary_color`/`secondary_color`: esos son de las
  facturas, los correos y el sitio, se imprimen sobre papel blanco y no tienen las reglas de lectura del panel; así
  cambiar uno no cambia el otro.
- **De fábrica, la hoja de Odoo tal cual.** La marca de Baby Caleb ya va compilada en la hoja (los valores de
  `dcasa_interfaz/static/src/scss/tokens.scss`, `dcasa_base/static/src/scss/primary_variables.scss` y su versión de
  noche en `static/src/oscuro/`). Si no se subió nada y los colores son los de fábrica, `web.webclient_bootstrap`
  enlaza la hoja de Odoo, el logo (`/dcasa_base/static/img/logo.png`), favicon, ícono del iPhone y manifiesto de
  fábrica.
- **Las bases que se instalaron con la fábrica de D'CASA** (staging) guardan en la empresa `#1340B1` y `#FED00F`: la
  migración `dcasa_interfaz` 19.0.1.4.0 los pasa a los de Baby Caleb al actualizar (`-u`), sin que nadie toque Ajustes;
  un color que la empresa sí eligió se queda (y si con el cambio el par dejara de leerse, vuelve entera a la fábrica).
  «Volver a la marca de fábrica» deja Baby Caleb, nunca el azul de D'CASA.
- **Colores en caliente, sin recompilar.** Los colores de la marca no viven en un solo lugar: además de `--dc-*`,
  Bootstrap y Odoo los calculan al compilar (cientos de reglas: botones y su color al pasar el puntero, focos, pestañas,
  la barra de estado, el chat…), así que una variable CSS inyectada no llega. Con colores propios, la página enlaza
  `/dcasa_interfaz/marca/hoja/<empresa>/<versión>/<la hoja de Odoo>`: **la misma hoja compilada**, con cada color de la
  familia del navy llevado a la familia del principal (`marca/colores.py`, `Giro`) y cada color de la familia del
  naranja llevado a la del acento (`GiroDelAcento`): giran el tono, escalan la saturación y la luz, y tres redes cuidan
  que lo que se leía como letra sobre el crema se siga leyendo (4.5:1), que los bordes e íconos se sigan viendo (3:1) y
  que los rellenos que llevaban la letra del principal la sigan llevando (4.5:1) (`marca/tinte.py`). Mismas reglas en el
  mismo orden: la cascada no cambia. Se pinta una vez por hoja y colores (0,1 s, queda en memoria) y el navegador la
  guarda un año. El **modo oscuro** usa su propia hoja (`web.assets_web_dark`) pintada igual. Si pintar falla, la
  dirección **redirige a la hoja de Odoo**: el panel nunca se queda sin estilos.
- **Lo que no gira, a propósito**: los neutros (las líneas `#DEDED9`, el borde de los campos `#7F8A91`, la letra de
  apoyo `#475967` y `#5E6D78`), la crema y la superficie, el salvia, y las superficies del modo oscuro (`#0F161C`,
  `#162129`…: navy profundo con poca saturación). Así, con el color de otra empresa, la letra de apoyo sigue gris y el
  oscuro sigue oscuro. La familia se mide por tono y saturación (`VENTANA`, `SATURACION` en `marca/colores.py`).
- **No se pintan**, a propósito: las paletas que elige la persona (colores del calendario, etiquetas, tarjetas del
  kanban), los colores del contenido de la web (`o_cc*`, `o-color-*`) y los íconos de apps con el cuadro salvia (en esos
  solo cambia el punto naranja).
- **Íconos de las apps** (los SVG de la barra y del Inicio): de fábrica, un cuadro navy (o salvia fuerte `#53735C`, o
  naranja fuerte `#985D2F`, según la familia) con el trazo crema y el punto naranja. `ir.ui.menu.load_web_menus` los
  pinta con la misma regla.
- **Logo**: `session_info` le pasa al navegador `dcasa_marca: {logo, nombre}`; la barra lateral y el menú del celular
  lo usan (`static/src/js/marca.js`). El logo se sirve por `/web/image/res.company/<id>/dcasa_panel_logo`.
- **Favicon e íconos del celular**: `/dcasa_interfaz/marca/icono/<empresa>/<versión>/<nombre>.png` los hace de la
  imagen subida (`marca/iconos.py`, con `ImageProcess` de Odoo: la misma geometría que `scripts/iconos_de_la_marca.py`).
  Son públicos, como los de fábrica (Android los pide a veces sin la sesión). Un SVG no se acepta: no se puede achicar.
- **El manifiesto** (`controllers/webmanifest.py`) lleva esos íconos. La barra del navegador (`theme-color`) y la
  pantalla de arranque van en el crema de la página, como el panel propio de Baby Caleb, con cualquier color de la
  empresa (de noche, el oscuro de la página).

## Lo que no cambia

- **La página web** (`website_dcasa`): portada, tienda, `/web/login` (que usa el diseño del sitio) y `/master`. Una
  prueba compara las hojas, los íconos y el `theme-color` de la portada, la tienda y `/web/login` antes y después de
  poner una marca.
- Los documentos (factura, cotización, PDF) y los correos: siguen con el logo y los colores de la empresa de
  *Ajustes › Empresas*.
- El nombre de la app instalable (`web.web_app_name`, «Baby Caleb») y la letra del panel (Montserrat).

## Límites conocidos

- Las hojas que Odoo carga aparte al abrir una gráfica o una tabla dinámica (`web.assets_backend_lazy`) y la de
  imprimir el panel no se pintan: ahí quedan detalles en el navy y el naranja de fábrica.
- Con `?debug=assets` el panel usa la hoja de Odoo tal cual (colores de fábrica): ese modo arma los estilos de otra forma.
- El ícono de la pestaña «Marca del panel» dentro de Ajustes y el robot de Brian son imágenes fijas.
- La página «sin conexión» del panel (la que sale sin internet) muestra el ícono de fábrica.

## Pruebas

`addons/dcasa_interfaz/tests/test_marca_panel.py` (colores y contraste, el tinte de la hoja, la empresa, la página, los
íconos, la web que no cambia, la legibilidad de las hojas pintadas en claro y en oscuro con la red de
`test_modo_oscuro.py`, permisos y el navegador), `addons/dcasa_brian/tests/test_marca_brian.py` (las herramientas y
MCP) y `addons/dcasa_guia/tests/test_guia.py` (la tarea de la Guía).
