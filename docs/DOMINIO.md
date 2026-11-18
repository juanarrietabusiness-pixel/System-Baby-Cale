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
   `wrangler.jsonc`, **se lo quita al sistema nuevo**. Y ese repositorio despliega su web **sola, en cada push a su `main`**
   (`Baby-caleb/.github/workflows/web.yml`, todo lo que no sea `sistema/`, `docs/` ni `*.md`): cualquier arreglo pequeño a
   esa web bastaría. Por eso el paso 2 de la Fase B es obligatorio y `edge/test/dominio-babycaleb.test.ts` no deja pasar
   las pruebas de este sistema con `babycaleb.com` puesto hasta que su casilla esté marcada.
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

### Resultado de la Fase A (2026-11-18, Claude en Chrome, solo lectura; los redireccionamientos, comprobados con curl)

- **DNS (6 registros):** `babycaleb.com`, `panel.` y `ruta.` son registros «Worker» (los crean los dominios propios);
  `www` es un **CNAME proxiado a `babycaleb.com`**; un TXT de DMARC (`p=quarantine`, informes a
  `dmarc_rua@onsecureserver.net`, residuo de GoDaddy) y un CNAME `_domainconnect` de GoDaddy. **No hay MX, SPF ni DKIM:**
  el cambio de dominio no puede romper ningún correo (hoy no se recibe correo en `@babycaleb.com`).
- **Rutas de la zona:** una sola, `www.babycaleb.com/*` → `babycaleb-web`. Sin reglas de redirección, de página ni
  redireccionamientos masivos.
- **babycaleb-web:** dominio propio `babycaleb.com` + la ruta de `www`; su `workers.dev` está **apagado** (su
  `wrangler.jsonc` no declara `workers_dev` y tiene rutas). **babycaleb-sistema:** `panel.` y `ruta.`, sin rutas.
- **SSL/TLS:** modo Completo; **«Usar siempre HTTPS» apagado** y sin HSTS en la zona; TLS mínimo 1.0. Comprobado:
  `http://babycaleb.com/` responde **200 sin cifrar** (la web actual no redirige); `http://www.` y `https://www.` → 301 a
  `https://babycaleb.com/`; `http://panel.` → 301 a `https://panel.`.
- **No existen** `sistemabk` ni `sistemabk-staging` todavía.

Lo que eso decide para el día del cambio:

1. **`www` como ruta, igual que hoy**, y no como dominio propio: así el CNAME proxiado se queda y no se pisa ningún
   registro DNS. El borde de este sistema ya manda `www` → `https://babycaleb.com` (`edge/src/routing.ts`, función
   `route`, 301 en GET y 308 en lo demás). La llave del robot necesita *Zone · Workers Routes · Edit* para `babycaleb.com`.
2. **Encender «Usar siempre HTTPS»** en la zona (SSL/TLS › Certificados de perímetro). El borde manda HSTS, pero el
   navegador solo lo aprende después de una primera visita cifrada, y no redirige `http://` en la raíz. A `panel.` y `ruta.`
   no les cambia nada (ya redirigen) y a la web actual le arregla su `http://`: se puede encender **desde ya**, con el «sí»
   del dueño.
3. Para el correo a clientes de este sistema (Resend, `docs/CORREO.md`), más adelante: con DMARC en `quarantine` y sin
   SPF ni DKIM, un correo «de» `@babycaleb.com` iría a spam. Resend da los registros SPF y DKIM que hay que agregar.

## Fase B — el día del cambio (solo con el «sí» del dueño)

`www` va como **ruta**, no como dominio propio (ver «Resultado de la Fase A»).

Antes, todo esto tiene que ser verdad:

- [ ] **Repositorio Baby-caleb:** `wrangler.jsonc` ya no tiene `babycaleb.com` ni `www.babycaleb.com/*` en su `main`
      (commit: _poner aquí el enlace_). Se marca con `[x]` solo cuando ese commit ya está en `main` (paso 2).

- [ ] Producción sana en `https://sistemabk.juanarrietabusiness.workers.dev` (`/__edge/health`: 200, la versión
      desplegada, `base_al_dia: true`, `humo: ok`) y revisada por el dueño.
- [ ] Decidido qué pasa con los cobros en línea: la web vieja cobra con Tilopay y Yappy en `babycaleb.com`; el sistema
      nuevo todavía no tiene esos cobros conectados. **PENDIENTE**: decisión del dueño.
- [ ] Ningún pedido de la web vieja a medio pagar (Tilopay vuelve a `/pago/vuelta`).
- [x] Informe de la Fase A guardado (2026-11-18; ver «Resultado de la Fase A»: no hay registros de correo que cuidar).

Pasos, en este orden y en el mismo rato:

1. **En este repositorio**, un commit que ponga en `edge/wrangler.jsonc`
   `"routes": [{ "pattern": "babycaleb.com", "custom_domain": true }, { "pattern": "www.babycaleb.com/*", "zone_name": "babycaleb.com" }]`,
   con sus pruebas (`edge/test/fase1.test.ts`, `edge/test/anfitrion-canonico.test.ts`) y `CANONICAL_HOST` a
   `babycaleb.com`. CI a staging de ese commit (staging sigue con `"routes": []`).
2. **En el repositorio Baby-caleb** (`abrinay1997-stack/Baby-caleb`, con sus reglas: leer su `CLAUDE.md` y su
   `docs/TRAMPAS.md` antes, y con el «sí» del dueño), en una rama:
   1. Abrir `wrangler.jsonc` (el de la raíz, el de la web; **no** `sistema/wrangler.jsonc`, que es el de `panel.` y `ruta.`).
   2. Cambiar el bloque `"routes": [ { "pattern": "babycaleb.com", "custom_domain": true }, { "pattern":
      "www.babycaleb.com/*", "zone_name": "babycaleb.com" } ]` por `"routes": []` y agregar `"workers_dev": true` (hoy
      su `workers.dev` está apagado): la web vieja sigue viva en `https://babycaleb-web.juanarrietabusiness.workers.dev`
      por si hay que volver atrás. Revisar antes si esa web da algo por hecho con `workers.dev` apagado.
   3. Revisar en ese repositorio lo que dé por hecho que la web vive en `babycaleb.com` (su `SITE_URL`, las vueltas de
      Tilopay y Yappy, pruebas que fijen el dominio) y ajustarlo en el mismo commit, con sus pruebas en verde.
   4. Unir a su `main` **en el mismo rato del cambio**, justo antes o justo después del paso 4. Al unir, su CI
      despliega `babycaleb-web` sin dominio: si se une antes del paso 4, `babycaleb.com` queda unos minutos sin Worker.
   5. Marcar con `[x]` la casilla «Repositorio Baby-caleb» de arriba, con el enlace del commit, en el mismo commit del
      paso 1 de este repositorio (si no, `edge/test/dominio-babycaleb.test.ts` falla).
3. **Claude en Chrome**, en Workers & Pages › babycaleb-web › pestaña **Dominios**: si todavía aparece, borrar la ruta
   `www.babycaleb.com/*` (regla 3: si se queda, gana a la de este sistema; y dos Workers no comparten un mismo patrón).
   El dominio propio `babycaleb.com` se lo lleva el despliegue del paso 4 (regla 1). Si «Usar siempre HTTPS» sigue
   apagado, encenderlo. No tocar `panel.`, `ruta.`, el CNAME de `www` ni el TXT de DMARC.
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
