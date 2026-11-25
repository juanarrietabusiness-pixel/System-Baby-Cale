# Plan: llevar la ubicación exacta y los envíos a D'CASA

Pedido del dueño (2026-11-25): «deja un plan de todo lo que tú hiciste para el tema del cálculo y los envíos de esta
última tarea, porque vamos a implementar esto en de casa». Se hizo primero en Baby Caleb, con dos auditorías
independientes de por medio. El diseño completo, el contrato con el Worker de Juan y las reglas de privacidad están en
[UBICACION.md](UBICACION.md); aquí va **qué hace, qué decide la gente de D'CASA, qué se copia tal cual, qué se adapta y
en qué orden**.

## 1. Qué hace (para contárselo a la dueña y a Gerencia)

- **El dolor que ataca**: los pedidos devueltos porque el chofer no encuentra la casa o no hay nadie.
- **En la web** (checkout, «¡Gracias!» y la página del pedido / link de pago): el cliente marca su casa en un mapa
  («Mi ubicación» con el GPS o moviendo el mapa bajo un pin fijo, con un buscador de barriadas de la tabla de envíos) o
  la escribe. Con el punto, la zona sale sola y **el precio del envío sale solo de la misma tabla de la calculadora**
  (con la promoción de envío). El **número de casa e indicaciones son obligatorios**; quién recibe, otro teléfono y la
  foto de la casa, opcionales. «Confirmar» cuenta como el «Sí, aquí es».
- **En el chat** (Juan): ubicación de WhatsApp/Telegram con el clip, enlaces de Google Maps/Waze/Apple pegados en el
  chat, y un **enlace de un solo uso** con tres pasos (en WhatsApp de la API oficial, además el botón nativo «Enviar
  ubicación»). Al marcarla, el cliente recibe «✅ ¡Listo!…» con la zona y el envío, y el equipo un aviso interno. Para
  un regalo, «para otra casa» crea una dirección aparte. En el chat de la web (Andrés), «Usar mi ubicación» + número de
  casa quedan en el carrito y el checkout los trae.
- **El chofer**: el comprobante y la nota de entrega llevan un **QR** a una página con «Abrir en Waze», «Abrir en Google
  Maps», la dirección, cómo reconocer el sitio, quién recibe, la foto de la casa, «Llamar» y «💬 Avisar que llegué».
  Sirve mientras el pedido no se entregue y se cierra 3 días después.
- **Avisos**: al confirmar una venta a domicilio sin la casa en el mapa, el asistente le pide el punto (o la vendedora
  recibe un pendiente con «📲 Pedir ubicación por WhatsApp»); el día de la entrega, «🚚 Sale hoy: avisarle» pregunta si
  habrá alguien en casa.
- **Panel y Brian (MCP)**: «Ruta del motorizado» en la venta, «Abrir en Waze/Google Maps» y el enlace en la ficha;
  Brian tiene `ubicacion_de_entrega`, `enlace_de_ubicacion_para_cliente`, `poner_ubicacion_de_entrega`,
  `poner_quien_recibe`, `quitar_foto_de_fachada`, `pedir_ubicacion_al_cliente` y `avisar_que_sale_hoy`.

## 2. Qué tiene que decidir D'CASA antes de copiar

1. **Privacidad (cambia una regla de D'CASA).** D'CASA hoy **nunca guarda la dirección exacta** (issue #25: Juan solo
   pide el barrio). Esto guarda el punto, porque sin él no hay QR. Necesita el «sí» de la dueña y **la línea en la
   política de privacidad** (copiar la de Baby Caleb de `website_dcasa/views/legal_templates.xml`, pasada a la marca:
   qué se guarda del punto, para qué, que el punto no pasa por la IA —lo que el cliente escribe sí— y que lo ve Google).
2. **Diseño.** LEEME_PRIMERO §2 de D'CASA: los cambios de diseño se muestran a Gerencia en **capturas antes/después
   (computadora y celular)** y **no van a producción sin su «sí» a lo que vio**. Son pantallas nuevas: el bloque del
   checkout, `/u/`, `/entrega/`, la tarjeta de «¡Gracias!» y del pedido, la ficha del cliente y los botones de la venta.
3. **Google Maps.** Un proyecto de Google Cloud de D'CASA con facturación, dos claves (§6), y una cuota diaria con
   alerta de presupuesto. Sin claves todo funciona (GPS, búsqueda en la tabla, dirección escrita), pero sin mapa para
   afinar el pin.
4. **Tarifa aprobada.** El precio por el punto usa las mismas reglas que Juan: tarifa aprobada por Gerencia, lugar
   revisado, no «se cotiza aparte». Sin eso, «por cotizar», como hoy.
5. **Los avisos** (pedir el punto al confirmar, «Sale hoy»): si D'CASA los quiere encendidos desde el primer día.

## 3. Qué se copia tal cual

Comparado el 2026-11-25 contra `main` de D'CASA (`9e6b76df`): estos archivos eran **idénticos** en las dos ramas antes
del trabajo (base `34c81a0^` de Baby Caleb) o son **nuevos**; se copian como quedaron en Baby Caleb y solo se cambia la
voz o la marca donde se indica en §4.

| Pieza | Archivos |
|---|---|
| El módulo entero (nuevo) | `addons/dcasa_ubicacion/` — motor, modelos, rutas, páginas, checkout, QR, avisos, la casa, herramientas, pruebas, datos, íconos |
| El enlace de WhatsApp sin «�» (nuevo) | `addons/dcasa_base/whatsapp.py` (`api.whatsapp.com/send`; `wa.me` cambia los emojis en WhatsApp Web y en Instagram) |
| La auditoría tapada de Brian | `addons/dcasa_brian/models/registro.py` (`privado`, `tapar`) y `accion.py` (`privado`, `_tapado`) |
| El mensaje como asistente | `addons/dcasa_conversaciones/models/cliente_worker.py` (`autor='bot'`) |
| El borde (pruebas) | `edge/test/routing.test.ts`, `edge/test/reenvio.test.ts`, `edge/CONTRATO_CONTENEDOR.md` |
| Juan (archivos nuevos) | `juan/src/canales/ubicacion.ts`, `juan/src/motor/enlacesMapa.ts`, `juan/src/motor/ubicacion.ts` y sus pruebas (`juan/test/motor/enlacesMapa.test.ts`, `juan/test/dcasa/{ubicacion,indicaciones,enviar-como-bot,boton-ubicacion}.test.ts`) |

## 4. Qué se adapta (archivos que en D'CASA son distintos o que llevan la marca)

**Distintos en D'CASA** (D'CASA tiene cambios propios en ellos): se lleva **solo el cambio de la ubicación** con
`git diff 34c81a0^ <commit final> -- <archivo>` y se aplica a mano, no se copia el archivo:

- Odoo: `dcasa_base/tests/test_superficie_rpc.py` (las entradas de `dcasa_ubicacion`, más `set_delivery_line` y los
  botones de la ficha), `dcasa_brian_tienda/static/src/js/brian_tienda.js` (precisión, bloque «indicaciones», textos —
  en D'CASA de tú—, el «impreciso»), `dcasa_conversaciones/models/mensaje.py` (`_enviar` pasa el autor),
  `dcasa_conversaciones/tests/{test_api,test_herramientas}.py` (`DE_OTROS_MODULOS`), `dcasa_guia/data/guia.json` (las
  entradas `envio-*` nuevas, de tú), `website_dcasa/views/legal_templates.xml` (§2.1), `docker/entrypoint.sh`
  (`dcasa_ubicacion` al final de `ODOO_MODULES`).
- Los enlaces de WhatsApp (auditoría 2): `website_dcasa/models/website.py` (`_dcasa_whatsapp_numero` y
  `_dcasa_whatsapp_url` con `whatsapp.enlace`), `dcasa_brian_tienda/models/website.py` (el número sin `RE_WA`),
  `dcasa_meta_eventos/static/src/js/meta_pixel.js` (el selector de `Contact` reconoce `api.whatsapp.com/send`), y los
  que la ubicación no toca pero tenían el mismo «�»: `dcasa_abonos/models/abono_vencimiento.py`,
  `dcasa_catalogo/models/sale_order.py`, `dcasa_mi_cuenta/models/mi_cuenta.py`, `dcasa_socios/controllers/{main,vendedores}.py`.
  Las pruebas que buscaban `wa.me` en esos módulos (y en `website_dcasa`, `dcasa_pago_yappy`, `dcasa_correo`,
  `dcasa_camila`, `dcasa_buscar_foto`) se cambian al enlace nuevo, nunca se saltan.
- El checkout (auditoría 2): en `dcasa_ubicacion/controllers/checkout.py`, `shop_address` (la invitada que vuelve
  atrás va a «Editar» su dirección) y `/tienda/ubicacion/olvidar-chat` (la tarjeta «¿Le entregamos ahí?» para
  quien ya tiene cuenta); hereda de `DcasaCheckout` de `website_dcasa`: comprobar que en D'CASA se llame igual.
- Borde: `edge/src/{handler,index,routing}.ts` (las dos claves en `VARIABLES_DEL_CONTENEDOR`, `/u/` y `/entrega/` sin
  caché y con el secreto fuera del registro) y `edge/test/fase1.test.ts`.
- Juan: `juan/src/canales/whatsappCloud.ts` (botón nativo), `juan/src/dcasa/{prompt,salvaguardas}.ts` (las preguntas de
  la ubicación por canal, el número de casa, «como la vez pasada», «para otra casa», la respuesta a «Sale hoy»; la
  guardia conserva los íconos de las frases de Odoo), `juan/src/motor/{conversacion,herramientas}.ts`,
  `juan/src/tienda/{bloques,motor,peticion,prompt}.ts` y sus pruebas. **Cuidado**: el prompt de D'CASA es de tú y tiene
  pruebas que fijan la parte fija; las frases con ícono van en la parte que cambia por turno.
- Puente QR: `puente-wa/contenedor/lib/{propios,entrante}.mjs`, `puente-wa/src/router.ts` y sus pruebas (la ubicación
  del mensaje entrante; la prueba de la poda con el marcador «pk:»).

**Solo de Baby Caleb (no se llevan)**: `addons/dcasa_correo/*` (el remitente `ventas@babycaleb.com`), `docker/negocio.env`,
`docs/BABY_CALEB.md` y lo de la marca de Baby Caleb.

**La marca y la voz de D'CASA**:

- Colores: azul `#1340B1` y amarillo `#FED00F` (**el amarillo nunca sobre blanco**: los CTA amarillos solo sobre azul),
  navy para el texto; Anton (títulos, caja alta), Oswald (subtítulos), Inter (cuerpo); plano. En
  `static/src/scss/ubicacion.scss` (variables al principio) y en el `<style>` de `views/paginas_templates.xml` (las
  páginas `/u/` y `/entrega/` no cargan el tema del sitio). El pin del mapa (SVG) también.
- **Tuteo** («el pana que sabe de casas»; nada de «remate» ni «¡¡CORRE!!»): las páginas, `_texto_para_la_clienta`
  (`models/enlace.py`), la frase de `enlace_de_ubicacion` (`models/herramientas.py`), los mensajes de `models/avisos.py`,
  `motor/casa.py` («Avisar que llegué»), los avisos de `static/src/lib/mapa_entrega.js` y
  `static/src/interactions/checkout_ubicacion.js`, y la Guía. Las pruebas que fijan textos se ajustan (nunca se saltan).
- **Tienda física**: D'CASA sí tiene «Retiro en tienda». El bloque solo cuenta si la venta va a domicilio
  (`sale.order._dcasa_va_a_domicilio`); probar que con retiro no se pide el mapa ni sale el QR. **Ojo (visto en la
  auditoría 2 con la tienda encendida)**: «Retiro en tienda — Gratis» quedaba marcado por defecto aun después de
  marcar la casa en el mapa (el total salía sin envío). Decidir con Gerencia si, al marcar la casa, se elige sola la
  entrega a domicilio.
- **ITBMS**: D'CASA lo cobra; el envío lleva el ITBMS del producto del transportista (lo decide `dcasa_envios`). Probar
  el total del checkout con el punto.
- **El nombre en «Avisar que llegué»** sale del sitio («Hola Ana, soy el chofer de D'CASA…»: en D'CASA «chofer»).

## 5. En qué orden

1. Las decisiones de §2, con capturas de Baby Caleb para explicar.
2. Rama de trabajo desde `main` de D'CASA. Copiar §3; aplicar §4 archivo por archivo con el diff de Baby Caleb.
3. Adaptar marca y voz; capturas **antes/después** a Gerencia (computadora y celular, datos de prueba).
4. En local: `scripts/test.sh` con **todos los módulos instalados** y `TEST_TAGS` de `dcasa_ubicacion`, `dcasa_brian`,
   `dcasa_conversaciones`, `dcasa_base`, `dcasa_guia`, `dcasa_invoice`, `dcasa_envios`, `dcasa_brian_tienda` y
   `website_dcasa` (en Baby Caleb, probar solo el módulo escondió un choque de nombres que rompía el PDF de las
   cotizaciones); `ruff check addons`; `npm test && npm run typecheck` en `edge/`, `juan/` y `puente-wa/`. Además, una
   compra de verdad en el navegador a 390 px: marcar el punto, ver el precio, «Confirmar», descargar el comprobante y
   escanear el QR.
5. CI → staging. **Probarlo comprando en staging** (el incidente del 2026-11-25 de Baby Caleb: CI y salud en verde no
   garantizan lo que se ve). Con las claves de Google puestas, comprobar que el mapa carga (con la clave restringida al
   dominio: la página manda `Referrer-Policy: strict-origin` para eso).
6. Producción según la receta de D'CASA (`docs/DESPLIEGUE.md`), con el «sí» de Gerencia a las capturas.

## 6. Las claves de Google (las pone la dueña, nunca por el chat)

1. **console.cloud.google.com** › proyecto «D'CASA» con facturación; **cuota diaria y alerta de presupuesto**.
2. Activar **Maps JavaScript API** y **Geocoding API** (Places no hace falta: se busca en la tabla de la tienda).
3. Dos claves: **navegador** (sitios `dcasapty.com/*`, `www.dcasapty.com/*`, `staging.dcasapty.com/*`; API Maps
   JavaScript) y **servidor** (solo Geocoding).
4. Cloudflare › Workers `dcasa` y `dcasa-staging` › Settings › Variables and Secrets: `GOOGLE_MAPS_CLAVE_NAVEGADOR` y
   `GOOGLE_MAPS_CLAVE_SERVIDOR`. Desplegar o reiniciar para que el contenedor las lea (Cloudflare puede arrancar una
   imagen nueva con las variables del arranque anterior: si el mapa no aparece, reiniciar).

## 7. Lo que enseñaron las dos auditorías (para no repetirlo en D'CASA)

- **Probar con todos los módulos**: un `_dcasa_nota` nuevo en `sale.order` tapó el del PDF de `dcasa_invoice`; la
  unión de dos ramas dejó `_confirmar` sin parámetros nuevos (500 en «Sí, aquí es»). Las herencias pasan `**opciones`.
- **El dinero**: el link de pago no recalcula con un pago en curso (la transferencia dejaba de confirmar la venta) ni
  si el envío lo puso una persona; el «por cotizar» en $0 sí se reemplaza. «Agregar envío» del panel debe dejar la
  línea como la del sistema (`set_delivery_line`). El «¡Listo!» no dice un precio que contradiga la promoción.
- **«Para otra casa»** no puede pisar la ficha del cliente: dirección hija.
- **El QR**: abierto mientras no se entregue (un apartado de 40 días), cerrado después, sin revivir.
- **Privacidad**: la auditoría inmutable de Brian guardaba coordenadas, secretos y la casa (ahora `privado`); el
  modelo veía las coordenadas de un cuarto enlace o escritas a mano (ahora se tapan todas).
- **Seguridad**: una imagen de 190 KB tumbaba Odoo (tope de píxeles, dos a la vez); SSRF con
  `http://127.0.0.1:9999\@maps.app.goo.gl/x` (validar con urllib3); un QR vencido revivía con la casa nueva.
- **La clienta**: una clave de Google mala dejaba la página colgada (`gm_authFailure`); «Confirmar» sin «Sí» no hacía
  nada visible; la dirección de facturación pedía el mapa; un GPS de ±800 m se guardaba como bueno.
- **Odoo 19**: `super()` de una ruta `http` devuelve un `Response` (`get_data(as_text=True)`); `/report` es de solo
  lectura (el QR no crea registros al imprimir); `/odoo/enviar` del Worker calla a Juan salvo `autor: "bot"`.
- **Segunda auditoría** (sobre los arreglos de la primera): la «otra casa» de tipo «entrega» se volvía la dirección
  por defecto de todas las ventas de la clienta (ahora tipo «otra»); el clip podía mover un regalo ya marcado; dos
  regalos pendientes compartían la misma ficha; un pago de Tilopay en borrador no frenaba el recálculo; «Escribir»
  otra calle dejaba el punto viejo como bueno; el QR podía no cerrarse nunca si no se validan las salidas (tope de 90
  días); en el navegador, «Confirmar» se saltaba el aviso de «su punto está en otro distrito», un dedo al bajar la
  página movía el pin, una caída de señal trababa el checkout y los emojis de wa.me salían como «�» en WhatsApp Web
  (usar `api.whatsapp.com/send`). **Moraleja**: cada arreglo grande merece su propia revisión.

## 8. Lo que falta del lado de Baby Caleb (no bloquea copiarlo)

Las claves de Google de Baby Caleb y la plantilla aprobada de Meta para escribir fuera de las 24 horas (hoy, fuera de
la ventana, la vendedora lo manda por WhatsApp con un toque).
