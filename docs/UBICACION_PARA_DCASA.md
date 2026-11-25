# Llevar la ubicación exacta de entrega a D'CASA

Este documento es para copiar a D'CASA (`dcasapty/D_Casa_new_word`) el sistema de ubicación que se hizo primero en
Baby Caleb el 2026-11-25. El diseño completo y el contrato entre Odoo y el Worker de Juan están en
[UBICACION.md](UBICACION.md). Aquí va **qué se copia, qué se adapta a D'CASA y en qué orden**.

## Qué hace (para contárselo a la dueña)

- **En la web**, al poner la dirección de entrega, el cliente elige **«Marcar en el mapa»** (Google Maps con «Usar mi
  ubicación» y un buscador de barriadas) o **«Escribirla»**. Con el punto, la barriada, el corregimiento, el distrito y
  la provincia se llenan solos y el **precio del envío sale solo**, de la misma tabla de la calculadora. Antes de seguir
  ve **«¿Es aquí?»**, y si lo que escribió nombra otro distrito que el del punto, se le avisa.
- **En el chat**:
  - **WhatsApp y Telegram**: el cliente comparte su ubicación con el clip (📎 › Ubicación) y Juan le da el precio.
  - **Un enlace de Google Maps o de Waze** pegado en el chat también sirve.
  - **Instagram y Messenger**: Juan le manda un **enlace de un solo uso** amarrado a su conversación. El cliente marca
    el punto y Juan le escribe solo con el precio: **no copia ni pega nada**.
- **El comprobante y la nota de entrega** llevan un **QR para el chofer**: abre una página con **«Abrir en Waze»**,
  **«Abrir en Google Maps»**, la dirección, cómo reconocer el sitio y «Llamar». La página vence a los 30 días y no
  cambia nada.
- **El panel y Brian (MCP)**:
  - la venta tiene el botón «Ruta del motorizado»;
  - la ficha del cliente tiene la pestaña «Ubicación de entrega» con «Crear enlace para que marque su ubicación»;
  - Brian tiene `ubicacion_de_entrega`, `enlace_de_ubicacion_para_cliente` y `poner_ubicacion_de_entrega`.

## Qué decisiones necesita de la dueña de D'CASA (antes de copiar)

1. **Privacidad.** D'CASA hoy, a propósito, **nunca guarda la dirección exacta** (issue #25: Juan solo pide el barrio).
   Esto la guarda, porque sin ella no hay QR para el chofer. Se guarda solo en la dirección de entrega y en la entrega
   de la venta; nunca en el chat, en la auditoría ni en el registro.
   - Necesita su «sí» para el cambio.
   - Necesita una línea nueva en la política de privacidad.
2. **Google Maps.** Necesita un proyecto de Google Cloud con facturación y dos claves (abajo). Google regala un cupo al
   mes por servicio.
3. **Capturas antes/después** del checkout, de la página del enlace y de la del chofer (LEEME_PRIMERO §2: todo cambio
   de diseño espera su «sí»).
4. **El precio a domicilio.** En D'CASA el envío a domicilio solo da precio con la **tarifa aprobada**. Mientras no lo
   esté, todo funciona igual, pero el envío dice «por cotizar».

## Qué se copia tal cual

| Pieza | De Baby Caleb (`juanarrietabusiness-pixel/System-Baby-Cale`) |
|---|---|
| El módulo entero | `addons/dcasa_ubicacion/` (motor, modelos, rutas, páginas, checkout, QR, herramientas, pruebas) |
| El borde | En `edge/src/routing.ts`: `/u/` y `/entrega/` sin caché y con el secreto fuera del registro. En `edge/src/handler.ts` y `edge/src/index.ts`: las dos claves de Google. También sus pruebas en `edge/test/routing.test.ts`, `reenvio.test.ts` y `fase1.test.ts`, y `edge/CONTRATO_CONTENEDOR.md` |
| El mensaje como asistente | `addons/dcasa_conversaciones/models/cliente_worker.py` (`autor='bot'`) y `mensaje.py` (`_enviar` lo pasa) |
| La lista de módulos | `docker/entrypoint.sh`: `dcasa_ubicacion` al final de `ODOO_MODULES` |
| Las pruebas que cambian | `dcasa_conversaciones/tests/test_api.py` (`enlace_de_ubicacion` en `DE_OTROS_MODULOS`) y `dcasa_base/tests/test_superficie_rpc.py` (las cuatro entradas de `dcasa_ubicacion`) |
| La Guía | `dcasa_guia/data/guia.json`: «Mandarle a una clienta el enlace…» y «Abrir la ruta del motorizado…» (pasar a tuteo) |
| El Worker de Juan | Lo de `juan/` y `puente-wa/` de la rama de Baby Caleb: la ubicación de WhatsApp, Telegram y Messenger, los enlaces de mapa, `guardarUbicacion`, `autor: "bot"` en `/odoo/enviar` y el prompt |
| Los documentos | `docs/UBICACION.md` (cambiar Baby Caleb por D'CASA donde toque) y este archivo |

## Qué se adapta a D'CASA

- **La marca.** Las páginas sueltas (`views/paginas_templates.xml`) y el bloque del checkout (`static/src/scss/
  ubicacion.scss`) usan la marca de Baby Caleb (crema, navy, naranja, Montserrat). En D'CASA van:
  - azul `#1340B1` y amarillo `#FED00F`, **el amarillo nunca sobre blanco**;
  - Anton, Oswald e Inter;
  - todo plano.
  El pin del mapa (SVG) también cambia de color.
- **La voz.** Baby Caleb habla **de usted**; D'CASA **tutea** («el pana que sabe de casas»). Hay que pasar a tú:
  - las páginas;
  - el mensaje «Recibimos su ubicación…» (`models/enlace.py`, `_texto_para_la_clienta`);
  - la frase de `enlace_de_ubicacion`;
  - los avisos de `mapa_entrega.js` y de `checkout_ubicacion.js`;
  - las entradas de la Guía.
- **Retiro en tienda.** D'CASA sí tiene tienda física. El bloque «¿Dónde le entregamos?» sale en el formulario de
  dirección; si el cliente elige «Retiro en tienda», el punto no estorba (el QR solo sale si la venta va a domicilio:
  `sale.order._dcasa_va_a_domicilio`).
- **Las claves de Google** son de D'CASA: otro proyecto, limitado a `dcasapty.com/*` y `staging.dcasapty.com/*`.
- **La caja de producción.** El mapa no pesa en el servidor (lo dibuja Google en el teléfono del cliente). Lo único que
  corre en Odoo es buscar el lugar más cercano entre los ~11 000 de la tabla: milisegundos.

## Las claves de Google (las pone la dueña, nunca por el chat)

1. **console.cloud.google.com** › proyecto «D'CASA» con facturación.
2. Activar **Maps JavaScript API** y **Geocoding API**. **Places API (New)** solo si un día se quiere el buscador de
   Google: hoy se busca en la tabla de lugares de la tienda.
3. Dos claves:

   | Clave | Límites de sitios | Límites de APIs |
   |---|---|---|
   | **Navegador** | `dcasapty.com/*`, `www.dcasapty.com/*`, `staging.dcasapty.com/*` | Maps JavaScript |
   | **Servidor** | ninguno | solo Geocoding |

4. Cloudflare › Workers `dcasa` y `dcasa-staging` › Settings › Variables and Secrets:
   - **`GOOGLE_MAPS_CLAVE_NAVEGADOR`** (puede ir como variable: se ve en la página);
   - **`GOOGLE_MAPS_CLAVE_SERVIDOR`** (secreto).
5. Desplegar o reiniciar para que el contenedor las lea. **Ojo con lo aprendido el 2026-11-25**
   (CONTEXTO_AGENTICO.md): Cloudflare puede arrancar una imagen nueva con las variables del arranque anterior. Si el
   mapa no aparece después del despliegue, reiniciar el contenedor.

**Sin claves todo funciona igual**:
- «Usar mi ubicación» usa el GPS del teléfono y no necesita Google;
- la búsqueda usa la tabla de la tienda;
- la zona y el precio salen de la tabla.
Sin la clave del navegador no se ve el mapa; sin la del servidor no se llena la calle.

## En qué orden

1. Las decisiones de la dueña (arriba), con capturas.
2. Copiar el módulo y lo demás de la tabla «Qué se copia tal cual», y adaptar marca y voz.
3. `scripts/test.sh dcasa_ubicacion,dcasa_base,dcasa_conversaciones` (con `TEST_TAGS` del módulo y de
   `TestSuperficieRpc`), `cd edge && npm test`, `cd juan && npm test` y `cd puente-wa && npm test`.
4. CI → staging. **Probarlo de verdad en staging comprando**: marcar el punto en el checkout, ver el precio del envío,
   descargar el comprobante y escanear el QR con el teléfono.
5. Producción con el «sí» de la dueña.

## Lo que se aprendió haciéndolo

- **El PDF de Odoo 19 se arma en una transacción de solo lectura** (`/report/...` tiene `readonly=True`). El QR no
  puede crear la entrega al imprimir: se crea al confirmar la venta, al publicar el comprobante o cuando el cliente pone
  su punto, y el PDF solo la lee.
- **Cuando Odoo escribe por el chat (`/odoo/enviar`), Juan entiende que una persona tomó la conversación y se calla.**
  Para el mensaje «recibimos su ubicación» se agregó `autor: "bot"`: sale como el asistente y Juan sigue atendiendo.
- **`agregar_envio` solo suma un lugar que `cotizar_envio` cotizó en esa conversación** (lo dice la auditoría). Por eso
  el precio que sale de la ubicación de WhatsApp se pide por el mismo ejecutor de herramientas, auditado sin
  coordenadas.
- **Google ya no da el buscador viejo (Places Autocomplete «legacy») a proyectos nuevos.** Por eso el buscador usa la
  tabla de lugares de la tienda, que además conoce las barriadas como las dice la gente.
