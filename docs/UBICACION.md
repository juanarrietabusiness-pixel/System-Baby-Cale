# Ubicación exacta de entrega (`dcasa_ubicacion`)

Pedido del dueño (2026-11-25): «el usuario debería poder poner su ubicación en tiempo real desde el chatbot, desde la
página web, o responderla en texto, pero en texto se presta a errores humanos […] cuando se emite el comprobante de
pago, hay un QR para los motorizados que les abre dos botones, uno de Waze y uno de Google Maps […] y tenemos que tener
algo que confirme que esa dirección está bien puesta y no se preste a confusiones». Mapa: **Google Maps** (decisión del
dueño, 2026-11-25). La idea viene de Nébula (`nebula-storefront` / `nebula-admin`); aquí se rehace sobre Odoo y se
corrigen sus fallas (ver «Qué mejora frente a Nébula»).

## En palabras sencillas

- **En la web**, al poner la dirección de entrega la clienta elige **«Marcar en el mapa»** (con «Usar mi ubicación» o
  moviendo el mapa debajo de un pin fijo, con un buscador de barriadas, PH y lugares conocidos) o **«Escribirla»**. Con el punto, la barriada, el
  corregimiento, el distrito y la provincia se llenan solos con la tabla de la calculadora de envíos y el **precio del
  envío sale solo**. Antes de seguir ve **«¿Es aquí?»** con el mapa de cerca.
- **En el chat**:
  - **WhatsApp y Telegram**: la clienta comparte su ubicación con el clip (📎 › Ubicación). Juan la guarda como su punto
    de entrega y le dice el precio del envío.
  - **Un enlace de Google Maps o de Waze** pegado en cualquier chat también sirve: Juan saca el punto del enlace.
  - **Instagram y Messenger** (no comparten ubicación): Juan manda un **enlace de un solo uso**
    (`https://babycaleb.com/u/…`) amarrado a esa conversación. La clienta marca su punto en el mapa y Juan le escribe
    solo con el precio: **no copia ni pega nada**.
- **El comprobante** lleva un **QR para el motorizado**: abre una página con **«Abrir en Waze»**, **«Abrir en Google
  Maps»**, la dirección, la referencia y «Llamar». La página vence y no deja cambiar nada.
- **El panel y Brian (MCP)**: la venta muestra el punto con sus dos botones; Brian da la ubicación de una venta, crea
  el enlace para mandarlo a mano y guarda un enlace de Google Maps que la clienta mandó por otro lado.

## Cerrar la brecha del envío (2026-11-25, segunda vuelta)

El dueño: «el dolor número uno son los pedidos devueltos». Lo que se agregó:

- **El número de casa y las indicaciones van siempre**, como en PedidosYa: en el checkout (con el mapa o escrita), en la
  página del enlace y en el chat (Juan las pregunta y las guarda con `guardar_indicaciones`; Andrés muestra un campo
  «🏠 Número de casa e indicaciones»).
- **Andrés (chat de la web)**: «Usar mi ubicación actual» ahora es precisa (antes, a propósito, unos 100 m: solo para el
  precio). Si la clienta escribe el número de casa, el punto y las indicaciones se guardan en SU carrito
  (`POST /dcasa/brian/v1/carrito/ubicacion`) y el checkout los trae: solo toca «Sí, aquí es».
- **El link de pago** (la página del pedido): si va a domicilio y falta la casa, una tarjeta «📍 Marcar mi casa en el
  mapa» (`/u/pedido/<id>?access_token=…`, con el permiso del pedido). Al confirmar, el envío del pedido se recalcula y
  vuelve al pedido.
- **El enlace del chat**: el mensaje trae tres pasos (1️⃣ abra, 2️⃣ «Mi ubicación» y permita, 3️⃣ casa y «Sí, aquí es»),
  la vista previa muestra un pin en un mapa y, en WhatsApp de la API oficial, además sale el **botón nativo «Enviar
  ubicación»** (`location_request_message`). Si algo falla, la página ofrece **«Copiar mi ubicación»** y **«Mandarla por
  WhatsApp»** (un enlace de Google Maps que Juan sabe leer).
- **El equipo lo ve en el chat de Odoo**: cuando llega la ubicación, un aviso interno con la zona, la calle, la casa, el
  envío y de dónde salió el punto (sin coordenadas: la ruta está en la ficha y en la venta).
- **Sin mapa no se acepta un GPS impreciso** (más de 100 m: en una computadora el «GPS» sale de la conexión a internet y
  puede errar por kilómetros): se le pide usar el celular o buscar la barriada.

| Canal | Ubicación fija | En tiempo real | Botón «Enviar ubicación» | Enlace de Maps o Waze | Enlace de un solo uso |
|---|---|---|---|---|---|
| WhatsApp (API oficial) | Sí | No (Meta no la entrega) | Sí (nativo) | Sí | Sí |
| WhatsApp (QR) | Sí | Sí (el primer punto) | No (sin botones) | Sí | Sí |
| Telegram | Sí | Sí | No | Sí | Sí |
| Instagram / Messenger | No | No | No | Sí | Sí |
| Chat de la web (Andrés) | — | — | «Usar mi ubicación actual» | — | — |

## Lo que vive la clienta en el navegador (2026-11-25, auditoría 2)

- **El aviso de cruce ya no se salta**: si escribió otro distrito (el regalo para la mamá en San Miguelito) y el punto
  cae en otro (tocó «Mi ubicación» en La Chorrera), «Confirmar» baja a la tarjeta con **«📍 Es aquí» / «🏠 Es otra
  casa»** en lugar de «Sí, aquí es». El servidor también lo exige (`dcasa_ubic_cruce_ok`). Bajo «Mi ubicación», «¿Es
  para otra casa? Búsquela 👇». Sin mapa, el aviso dice «busque la barriada», no «mueva el mapa».
- **Un arrastre sin querer no cambia la casa**: en el teléfono el mapa se mueve con dos dedos (`cooperative`; con uno
  baja la página), es más bajo (300 px como mucho) y tras el GPS o una búsqueda la página deja el pin y la tarjeta
  encima de la barra fija de «Confirmar». Si el pin se movió más de 30 m después de un «Sí» o de un GPS bueno,
  «Confirmar» pregunta «👆 Movió el pin. ¿Es aquí?». Cambiar a Satélite no quita el «sí».
- **Sin señal no se traba**: «📶 Sin señal. Toque para reintentar»; «Confirmar» y volver la conexión piden la zona otra
  vez. En `/u`, «Ese punto no sirve» solo cuando de verdad no sirve. Pasado el tope de visitas, las páginas salen con
  su plantilla, «Reintentar» y WhatsApp.
- **Con cuenta, el punto del chat de la tienda llega**: Odoo no pasa por el formulario si ya tiene dirección, así que
  `/shop/checkout` pregunta arriba «¿Le entregamos ahí?» («Sí» abre su dirección con ese punto; «No» lo olvida).
  «Agregar dirección» no lo trae. Andrés ya no promete «al pagar ya estará marcada», y con un GPS impreciso guarda al
  menos la casa que escribió.
- **WhatsApp sin «�»**: todos los enlaces son `api.whatsapp.com/send` (`dcasa_base/whatsapp.py`); `wa.me` cambiaba los
  emojis en WhatsApp Web y en Instagram.
- **Sin callejones**: sin permiso de ubicación, lo que falta es buscar la barriada (y una línea de cómo permitirla); si
  la barriada no está en la tabla, «💬 Mándenos su dirección por WhatsApp» con lo que buscó y su casa.
- **La invitada que vuelve atrás** desde «Método de entrega» vuelve a SU dirección (con el punto, la casa y quién
  recibe), no a una vacía.
- **El link de pago**: «Marcar mi casa» va antes de «Aceptar y firmar» / «Pagar»; «Cambiar» es un botón de 48 px.
- **«Escribir»**: la calle se llama «Barriada o calle» (el número va aparte), el número de casa se pide después de la
  ciudad y «Departamento, suite» vacío no sale.
- **El motorizado**: con un punto aproximado, «Llamar» arriba como sin punto; de usted y sin «tienda».

## De dónde sale cada punto (y qué tan fiable es)

| Origen | Cómo se ve | Fiable |
|---|---|---|
| `gps` | «Ubicación del teléfono (±N m)» | Sí, si la precisión es de 100 m o menos |
| `pin` | «Marcada en el mapa» | Sí |
| `whatsapp` | «Compartida por WhatsApp» (o Telegram) | Sí |
| `enlace` | «De un enlace de Google Maps o Waze» | Sí |
| `busqueda` | «Buscada en el mapa» (una dirección de Google sin mover el pin) | Regular: se le pide confirmar |
| `escrita` | «Escrita a mano» | No: el motorizado llama antes |

## Cómo se confirma que está bien puesta

1. **«¿Es aquí?»**: el mapa a nivel de calle con el pin, la zona deducida y el precio. Hasta que la clienta toca «Sí,
   aquí es», el punto no cuenta como confirmado.
2. **Precisión del GPS**: si el teléfono da más de 100 m de error, se le pide mover el mapa hasta su puerta.
3. **Lo escrito contra el punto**: si escribió una barriada o un distrito y el pin cae en otro distrito, se le avisa
   («Su punto está en San Miguelito y escribió Arraiján: ¿cuál es?»).
4. **Dentro de Panamá y de la cobertura**: fuera de Panamá no se acepta; más lejos de lo que se envía («Cotizar aparte
   desde»), se acepta pero el envío se confirma por WhatsApp.
5. **La referencia** («casa verde de portón negro, frente al chino») es obligatoria con el mapa.

## Los avisos de la entrega (2026-11-25, tercera vuelta: `models/avisos.py`)

El dueño: «la gente no lee: íconos y pocas palabras»; «lo que priorizamos es lo más fácil para el cliente».

- **Al comprar, si su casa no está en el mapa** (escrita a mano, buscada sin mover el pin, GPS de más de 100 m o sin
  punto) y la venta va a domicilio, al confirmarla se le pide **una vez**: el asistente le escribe «🛍️ ¡Gracias por su
  compra! 📍 Para que el motorizado llegue directo a su casa, márquela aquí: …» con el enlace de un solo uso ligado a la
  venta. Si no puede escribirle, la vendedora (o el responsable por defecto de Ajustes de Juan) recibe el pendiente
  «📍 Pedirle la ubicación de entrega» y en la venta tiene **«📲 Pedir ubicación por WhatsApp»** (WhatsApp con el
  mismo texto). El pendiente se cierra solo cuando la clienta marca un punto confiable. Nunca hace fallar la venta ni el pago.
- **Con la venta ya confirmada**, el «listo» no habla de precio: «✅ ¡Listo! Ya tenemos su casa: Villa Lucre, San
  Miguelito. 🏠 Casa 24. 🛵 Su pedido S00042 va para allá.» Lo cobrado no se cambia: si la tabla da otro envío para esa
  zona, queda una nota en la venta para que el equipo decida.
- **El día de la entrega**, una persona toca **«🚚 Sale hoy: avisarle»** (en la venta, en la entrega, para varias desde
  Acciones de la lista, o Brian): «🚚 ¡Hoy le llega su pedido S00042 a Villa Lucre! ¿Habrá alguien en casa para
  recibirlo? ✅ Sí / 📍 Cambiar» (sin punto, con el enlace del mapa). Una vez por venta y por día. Juan entiende la
  respuesta: si dice que sí, agradece; si no habrá nadie o quiere otro día u hora, la pasa a una vendedora (la fecha la
  confirma siempre una vendedora); si quiere cambiar el lugar, le manda el enlace, que queda ligado a esa venta, y el
  equipo recibe un pendiente para que el motorizado abra otra vez la ruta.
- **¿Cuándo le escribe sola?** WhatsApp por QR y Telegram, siempre; WhatsApp de la API oficial, Instagram y Messenger,
  solo dentro de las 24 horas desde su último mensaje (fuera de eso Meta pide una plantilla aprobada, que no hay; se
  deja una hora de margen). Además: el canal y el asistente encendidos, el Worker configurado y la clienta sin «No
  contactar». Si no, la persona lo manda por WhatsApp. El mensaje va a nombre del asistente (`autor: "bot"`) y queda «por
  enviar»: sale con el cron que manda lo pendiente (que se adelanta), nunca dentro de la confirmación de la venta.
- **Brian / MCP**: `pedir_ubicacion_al_cliente` y `avisar_que_sale_hoy` (dicen qué pasó: por el chat o el enlace de
  WhatsApp para abrir), sin coordenadas.

## Privacidad (cambia una regla de D'CASA)

D'CASA, a propósito, **nunca guardaba la dirección exacta** (issue #25: Juan solo pide el barrio). Ahora el punto de
entrega **sí se guarda**, porque sin él no hay QR para el motorizado. Reglas:

- Se guarda solo en la **dirección de entrega** de la clienta (`res.partner`) y en la entrega de esa venta
  (`dcasa.ubicacion.entrega`). Nunca en el texto de la conversación, en la auditoría de Brian (`brian.accion`), en el
  registro del servidor ni en lo que ve el modelo de IA: el modelo solo recibe la zona («Brisas del Golf, San
  Miguelito») y el precio.
- El enlace de un solo uso vence a las 24 horas; la página del motorizado, a los 30 días. Los secretos se guardan como
  huella (SHA-256), no como texto.
- **Pendiente del dueño**: la política de privacidad dice lo mismo que la de D'CASA; conviene agregar una línea sobre la
  ubicación de entrega (para qué se usa y cuánto se guarda). No se cambia sin su «sí».

## Las claves de Google

| Nombre (Cloudflare, Worker `sistemabk` y `sistemabk-staging`) | Para qué | Límites que se le ponen en Google Cloud |
|---|---|---|
| `GOOGLE_MAPS_CLAVE_NAVEGADOR` | El mapa en el navegador (se ve en la página: es normal) | Sitios: `babycaleb.com/*`, `www.babycaleb.com/*`, `sistemabk-staging.juanarrietabusiness.workers.dev/*` · APIs: Maps JavaScript |
| `GOOGLE_MAPS_CLAVE_SERVIDOR` | La dirección de calle a partir del punto (Geocoding), desde Odoo | APIs: solo Geocoding |

El buscador del mapa **no usa Google**: busca en la tabla de lugares de la calculadora (barriadas, PH, lugares
conocidos, como los dice la gente). Google ya no da su buscador viejo a proyectos nuevos y el nuevo (Places API New)
no hace falta; si un día se quiere, se activa aparte.

**Sin claves, todo sigue funcionando**: «Usar mi ubicación» (GPS) y la dirección escrita no las necesitan; la zona y
el precio salen de la tabla de la calculadora, nunca de Google. Sin la clave del navegador no se ve el mapa; sin la del
servidor no se llena la calle.

## Contrato entre Odoo y el Worker de Juan

Lo que el Worker de Juan (`juan/`, `puente-wa/`) le manda a Odoo y lo que recibe. Las coordenadas viajan del canal a
Odoo **sin pasar por el modelo**.

### 1. `POST /dcasa/juan/v1/ubicacion` (nuevo)

Misma autenticación que `/herramienta` (`Authorization: Bearer <JUAN_ODOO_TOKEN>`). Lo llama el Worker cuando entra un
mensaje con ubicación (WhatsApp, Telegram, Messenger) o con un enlace de mapa que ya resolvió a coordenadas.

```json
{"conversacion_id": 123, "lat": 9.0012345, "lon": -79.5123456, "origen": "whatsapp",
 "nombre_lugar": "Super 99 Brisas", "direccion": "Vía Domingo Díaz"}
```

- `origen`: `whatsapp` (también Telegram y Messenger: ubicación compartida en el chat) o `enlace` (un enlace de Google
  Maps, Waze o Apple Maps). `nombre_lugar` y `direccion` (opcionales, hasta 120 y 200 letras) son los que trae WhatsApp
  cuando la clienta elige un lugar en vez de su ubicación actual.
- Respuesta `200`: `{"ok": true, "resultado": {"guardada": true, "zona": "Brisas del Golf · Rufina Alfaro · San
  Miguelito", "envio": {…}}}`. `envio` tiene **la misma forma que el resultado de `cotizar_envio`** (con
  `por_ubicacion: true`): el Worker lo pone como consulta previa de `cotizar_envio` para que el modelo conteste con el
  precio, igual que «Usar mi ubicación» del chat de la tienda.
- `422` `{"ok": false, "error": "…", "motivo": "fuera_de_panama" | "coordenadas"}`: el punto no sirve; el Worker le
  dice al modelo «(la ubicación que mandó no es de Panamá)» y el modelo le pide otra.
- `404`: no existe la conversación. Envíos apagados: `200` con `envio` = la respuesta de apagado.
- Odoo nunca escribe las coordenadas en el registro ni en la auditoría.

### 2. La herramienta `enlace_de_ubicacion` (nueva, la usa el modelo)

Sin parámetros; necesita conversación. Devuelve `{"enlace": "https://…/u/<token>", "vence": "…", "frase_para_el_cliente":
"…", "instruccion": "…"}`. Cuando la clienta confirma su punto en esa página, **Odoo** le escribe por el mismo canal
(`POST /odoo/enviar` del Worker con `"autor": "bot"`) con la zona y el precio del envío, y deja el punto guardado.
Con `autor: "bot"` el Worker lo manda **como el asistente**: no da la conversación por tomada (sin eso, Juan se callaría
como cuando escribe una vendedora) y lo guarda en la historia como mensaje del asistente, para que el modelo lo vea en el
siguiente turno. Cualquier otro valor (o ninguno) es una vendedora, como siempre.

### 3. `cotizar_envio` sin lugar

Si la clienta ya tiene un punto de entrega guardado y confirmado, `cotizar_envio()` sin `lugar` ni `lugar_id` cotiza
con ese punto (`por_ubicacion: true`). Así, cuando contesta «sí, súmelo» al mensaje del enlace, el modelo vuelve a
cotizar sin pedirle nada y llama a `agregar_envio` con el `lugar_id` que sale.

### 4. Enlaces de mapa en el texto (lo resuelve el Worker)

Se reconocen: `maps.app.goo.gl/…`, `goo.gl/maps/…`, `google.com/maps/…` (`@lat,lon`, `?q=lat,lon`, `ll=`,
`!3dLAT!4dLON`), `waze.com/ul?ll=lat,lon` y `maps.apple.com/?ll=` o `?q=`. Los cortos se siguen **solo** a hosts de
Google (`maps.app.goo.gl`, `goo.gl`, `maps.google.com`, `www.google.com`, `google.com`), como mucho 3 saltos, 5 s y sin
leer el cuerpo. Un enlace sin coordenadas (una búsqueda por nombre) no se adivina.

## Qué mejora frente a Nébula

| Nébula | Aquí |
|---|---|
| Teselas de CARTO sin clave (su propio admin dice que no aguantan una tienda pública) | Google Maps con clave limitada a los sitios |
| Dirección de Nominatim (calle y ciudad); sin distrito, corregimiento ni barriada | Zona de la tabla de la calculadora (la misma que pone el precio) y la calle de Google |
| Sin paso de confirmar; la precisión del GPS no se usa | «¿Es aquí?» obligatorio, precisión ≤ 100 m o mover el pin, aviso si lo escrito no cuadra |
| Un punto fuera de Panamá es solo un aviso | No se acepta |
| Nada para el chat | Ubicación de WhatsApp y Telegram, enlaces de mapa y enlace de un solo uso amarrado a la conversación |
| El QR abre una página **permanente** que deja marcar «entregado» sin iniciar sesión | La página vence a los 30 días y no cambia nada |
| El precio de la zona no entra en la cotización | El precio del envío del checkout sale del punto |

## Dónde está cada cosa

| Pieza | Archivo |
|---|---|
| Motor (punto, zona, avisos, botones, enlaces de mapa) | `addons/dcasa_ubicacion/motor/geo.py`, `motor/enlaces_mapa.py` |
| Zona, precio y calle de Google | `models/zona.py` (`dcasa.ubicacion`) |
| El punto en la ficha | `models/res_partner.py` |
| Enlace de un solo uso | `models/enlace.py` (`dcasa.ubicacion.enlace`), página `/u/<secreto>` en `controllers/publico.py` y `views/paginas_templates.xml` |
| Entrega y QR del motorizado | `models/entrega.py` (`dcasa.ubicacion.entrega`), `views/reporte_templates.xml`, página `/entrega/<secreto>` |
| Precio en el checkout | `models/delivery.py`, `controllers/checkout.py`, `views/checkout_templates.xml`, `static/src/interactions/checkout_ubicacion.js` |
| El mapa (navegador) | `static/src/lib/mapa_entrega.js` |
| Juan y Brian | `models/herramientas.py`, `controllers/juan.py` |
| Los avisos de la entrega (pedir el punto al comprar, «🚚 Sale hoy») | `models/avisos.py`, `models/herramientas_avisos.py`, `views/avisos_views.xml`, `data/avisos_data.xml`; la respuesta en `juan/src/dcasa/prompt.ts` |
| Borde | `edge/src/routing.ts` (sin caché, secreto fuera del registro), `edge/src/handler.ts` (las dos claves) |
| Para copiarlo a D'CASA | [UBICACION_PARA_DCASA.md](UBICACION_PARA_DCASA.md) |
