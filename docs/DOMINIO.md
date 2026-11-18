# El dominio babycaleb.com: cómo está hoy y cómo se pasa al sistema nuevo

Escrito el 2026-11-18 para la copia de Baby Caleb (Workers `sistemabk` y `sistemabk-staging` en la cuenta de Cloudflare de
Juancito, subdominio `juanarrietabusiness.workers.dev`). Decisión del dueño: **el dominio se mueve un día aparte**, cuando
producción ya esté revisada en su dirección `workers.dev`. Hasta entonces `edge/wrangler.jsonc` tiene `"routes": []`.

## En palabras sencillas

Hoy `babycaleb.com` es la puerta de la web actual de Baby Caleb, y por esa puerta también vuelven los pagos (Tilopay y
Yappy). El sistema nuevo vive mientras tanto en `https://sistemabk.juanarrietabusiness.workers.dev`. El día del cambio se
quita el letrero de la web vieja y se le pone al sistema nuevo, en el mismo rato. `panel.babycaleb.com` y
`ruta.babycaleb.com` siguen con el sistema actual: no se tocan.

## Cómo está hoy (leído del repositorio Baby-caleb el 2026-11-18)

| Nombre | Tipo | Va al Worker | Lo declara |
|---|---|---|---|
| `babycaleb.com` | Dominio propio (custom domain) | `babycaleb-web` | `Baby-caleb/wrangler.jsonc:109-111` |
| `www.babycaleb.com/*` | **Ruta** de la zona | `babycaleb-web` | ídem |
| `panel.babycaleb.com` | Dominio propio | `babycaleb-sistema` | `Baby-caleb/sistema/wrangler.jsonc:157-159` |
| `ruta.babycaleb.com` | Dominio propio | `babycaleb-sistema` (ahí vive su MCP, `/mcp`) | ídem |

Lo que cuelga hoy de `babycaleb.com` (direcciones que aparecen en el código de Baby-caleb): la web y sus fichas,
`/pago/vuelta` (la vuelta de Tilopay), `/api/pago/yappy` y `/api/pago/yappy/iniciar` (Yappy; el dominio está registrado en
Yappy), `/api/chat`, `/api/catalogo`, `/api/zonas`, `/faq`. **El día que el dominio pase al sistema nuevo, todo eso deja de
responder** salvo que el sistema nuevo lo atienda.

## Tres reglas de Cloudflare que mandan aquí (comprobadas)

1. **Sin terminal, wrangler se lleva el dominio sin preguntar.** En el CI (sin TTY), wrangler 4.158 pone
   `override_existing_origin` y `override_existing_dns_record` en `true` (`edge/node_modules/wrangler/wrangler-dist/cli.js`,
   función de los dominios propios). Por eso el dominio **no** se pone en `edge/wrangler.jsonc` antes de tiempo.
2. **Lo mismo vale al revés:** si el repositorio Baby-caleb vuelve a desplegar `babycaleb-web` con `babycaleb.com` en su
   `wrangler.jsonc`, **se lo quita al sistema nuevo**. El día del cambio hay que sacar esas dos rutas de
   `Baby-caleb/wrangler.jsonc` (cambio en ese repositorio, con sus reglas y con el «sí» del dueño).
3. **Una ruta gana a un dominio propio** en el mismo nombre («Routes … take precedence if configured on the same
   hostname», developers.cloudflare.com/workers/configuration/routing/routes). Si `babycaleb-web` conserva la ruta
   `www.babycaleb.com/*`, `www` sigue yendo a la web vieja aunque el sistema nuevo tenga ese dominio. Esa ruta se borra a mano.

## Fase A — ahora: revisión solo de lectura con Claude en Chrome

Pega esto en Claude en Chrome, con la sesión de Cloudflare abierta en la cuenta de Juancito:

```text
Necesito un informe del dominio babycaleb.com en mi cuenta de Cloudflare. SOLO MIRA: no cambies, borres, agregues ni
guardes nada, y si alguna pantalla te pide confirmar algo, cancela.

1. Websites › babycaleb.com › DNS › Records: copia la tabla completa (tipo, nombre, contenido, proxy, TTL). Marca
   aparte los de correo (MX, TXT de SPF, DKIM y DMARC) y los que digan "Worker".
2. Websites › babycaleb.com › Workers Routes: lista cada ruta con su patrón y su Worker.
3. Workers & Pages › babycaleb-web › Settings › Domains & Routes: lista dominios propios y rutas.
4. Workers & Pages › babycaleb-sistema › Settings › Domains & Routes: lo mismo.
5. Websites › babycaleb.com › SSL/TLS: el modo de cifrado. Y en Rules: cualquier redirección o regla de página.
6. Si existen Workers llamados sistemabk o sistemabk-staging, dime sus dominios y rutas (deberían ser ninguno).

Devuélveme todo en tablas, sin resumir, y al final una lista de lo que te pareció raro o riesgoso.
```

Lo que devuelva se pega en la sesión de Claude Code que esté trabajando el sistema. Con eso se arma la Fase B exacta
(sobre todo, qué registros de correo no se pueden tocar).

## Fase B — el día del cambio (solo con el «sí» del dueño)

Antes, todo esto tiene que ser verdad:

- [ ] Producción sana en `https://sistemabk.juanarrietabusiness.workers.dev` (`/__edge/health`: 200, la versión
      desplegada, `base_al_dia: true`, `humo: ok`) y revisada por el dueño.
- [ ] Decidido qué pasa con los cobros en línea: la web vieja cobra con Tilopay y Yappy en `babycaleb.com`; el sistema
      nuevo todavía no tiene esos cobros conectados. **PENDIENTE**: decisión del dueño.
- [ ] Ningún pedido de la web vieja a medio pagar (Tilopay vuelve a `/pago/vuelta`).
- [ ] Informe de la Fase A guardado (registros de correo anotados).

Pasos, en este orden y en el mismo rato:

1. **En este repositorio**, un commit que ponga en `edge/wrangler.jsonc`
   `"routes": [{ "pattern": "babycaleb.com", "custom_domain": true }, { "pattern": "www.babycaleb.com", "custom_domain": true }]`,
   con sus pruebas (`edge/test/fase1.test.ts`, `edge/test/anfitrion-canonico.test.ts`) y `CANONICAL_HOST` a
   `babycaleb.com`. CI a staging de ese commit (staging sigue con `"routes": []`).
2. **En el repositorio Baby-caleb**, un commit que quite `babycaleb.com` y `www.babycaleb.com/*` de su `wrangler.jsonc`
   (regla 2). Sin desplegarlo todavía si su CI despliega solo al unir; coordinarlo para que no corra antes del paso 4.
3. **Claude en Chrome**, en Workers & Pages › babycaleb-web › Settings › Domains & Routes: borrar la ruta
   `www.babycaleb.com/*` (regla 3). El dominio propio `babycaleb.com` se lo lleva el despliegue del paso 4 (regla 1).
   No tocar los registros de correo ni `panel.` ni `ruta.`.
4. **GitHub › Settings › Environments › production**: `URL_SITIO` = `https://babycaleb.com`. Luego *Actions › Desplegar*,
   `entorno = production`, con el `imagen_digest` y el `app_version` del CI del paso 1. Ese día el respaldo previo llama a
   `URL_SITIO`, que todavía apunta a la web vieja: con el «sí» del dueño se desmarca `respaldo_previo`, o se respalda antes
   con la dirección vieja (`docs/REPLICAR.md` §6.8, Desplegar 29 y 30 de D'CASA en `docs/CONTEXTO_AGENTICO.md`).
5. Comprobar: `https://babycaleb.com/__edge/health` y `https://www.babycaleb.com` (el borde manda `www` al dominio), abrir
   el Inicio del panel, y que `panel.babycaleb.com` y `ruta.babycaleb.com` siguen respondiendo.
6. Después: registrar otra vez el webhook de Telegram de Brian, `URL_SITIO` de Juan al dominio y *Desplegar Juan*,
   Access/Turnstile/Resend con el dominio nuevo (`docs/REPLICAR.md` §6.8 paso 7).

**Volver atrás:** en Workers & Pages › babycaleb-web › Settings › Domains & Routes, agregar de nuevo el dominio propio
`babycaleb.com` (acepta llevárselo) y la ruta `www.babycaleb.com/*`; en GitHub, `URL_SITIO` de producción a la dirección
`workers.dev`.
