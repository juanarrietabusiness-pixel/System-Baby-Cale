# Paso a paso: las cuentas y las claves para desplegar

Para el dueño, sin tecnicismos. Escrito el 2026-11-18 para la copia de Baby Caleb (Workers `sistemabk`, cuenta de
Cloudflare de Juancito). Lo técnico de cada clave está en `docs/replicar/CUENTAS_Y_SECRETOS.md`.

## Antes de empezar: tres reglas

1. **Ninguna clave se escribe en el chat**, ni en un correo, ni en un documento. Se copia de donde sale y se pega directo
   donde va. Claude nunca necesita verla: puede comprobar que quedó puesta sin leerla.
2. **Todas se guardan primero en tu gestor de contraseñas** (Bitwarden, 1Password, el de Google…), con su nombre exacto y
   el entorno (`staging` o `production`). Dos de ellas **no se pueden cambiar nunca** (`PGBACKREST_CIPHER_PASS` y
   `DCASA_PIN_PEPPER`): si se pierden, se pierden los respaldos o los PIN de los socios. Cloudflare y GitHub no dejan volver
   a leerlas.
3. **Staging y producción llevan claves distintas.** La única excepción son las dos de Cloudflare del paso 3 y del paso 1
   (la llave del robot y el número de cuenta), que pueden ser las mismas en los dos.

**Por qué GitHub y no tu cuenta de Claude:** el que arma el sistema y lo sube a Cloudflare es un robot que vive en
GitHub. El robot solo ve las llaves que estén guardadas en GitHub. Lo que guardes en tu cuenta de Claude solo lo puede usar
Claude dentro de la conversación. Por eso las de despliegue van en GitHub, y las del bot de clientes (su IA, WhatsApp) van
después directo en Cloudflare.

## Paso 1 — El número de tu cuenta de Cloudflare (`CLOUDFLARE_ACCOUNT_ID`)

1. Entra a dash.cloudflare.com con la cuenta de Juancito.
2. Menú de la izquierda › **Workers & Pages**.
3. A la derecha aparece **Account ID** (32 letras y números). Botón de copiar → pégalo en el gestor de contraseñas como
   `CLOUDFLARE_ACCOUNT_ID`.

## Paso 2 — Las dos cajas de respaldos (buckets de R2)

1. Menú de la izquierda › **R2 Object Storage** › **Create bucket**.
2. Nombre: `sistemabk-respaldos-staging`. En **Location** elige **Provide a location hint** › **Eastern North America
   (ENAM)**. Storage class: Standard. **Create bucket**.
3. Repite con el nombre `sistemabk-respaldos` (el de producción), también ENAM.
4. No actives acceso público ni reglas de borrado automático en ninguna de las dos.

(No uses `babycaleb-respaldos`: es del sistema actual de Baby Caleb.)

## Paso 3 — La llave de cada caja (un token de R2 por caja)

Hazlo **dos veces**, una por caja:

1. **R2 Object Storage** › **Manage API tokens** (puede salir como «API» › «Manage API tokens») › **Create Account API
   token**.
2. Nombre: `sistemabk staging` (o `sistemabk producción`). Permisos: **Object Read & Write**. En **Specify bucket(s)**:
   **Apply to specific buckets only** y elige solo `sistemabk-respaldos-staging` (o solo `sistemabk-respaldos`). TTL:
   Forever. **Create API Token**.
3. La pantalla muestra **Access Key ID** y **Secret Access Key** **una sola vez**. Cópialas ya al gestor de contraseñas
   como `R2_ACCESS_KEY_ID` y `R2_SECRET_ACCESS_KEY` del entorno que corresponda.

## Paso 4 — La llave del robot (`CLOUDFLARE_API_TOKEN`)

1. Arriba a la derecha, tu perfil › **My Profile** › **API Tokens** › **Create Token** › **Create Custom Token**.
2. Nombre: `sistemabk GitHub`. Permisos (cada fila: Account · el permiso · el nivel):
   - Account · **Workers Scripts** · Edit
   - Account · **Containers** · Edit
   - Account · **Account Settings** · Read
   - Account · **Workers KV Storage** · Edit
3. **Account Resources**: Include · la cuenta de Juancito (solo esa). Sin fecha de vencimiento.
4. **Continue to summary** › **Create Token** → cópiala ya (se ve una sola vez) como `CLOUDFLARE_API_TOKEN`.

Si el primer despliegue dice que falta un permiso, el mensaje dice cuál: se agrega a esta misma llave (*Edit*) y se
relanza. El día del dominio se le suma *Zone · Workers Routes · Edit* para `babycaleb.com` (`docs/DOMINIO.md`).

## Paso 5 — La IA de Brian (`BRIAN_API_KEY`): Meta Muse Spark, igual que D'CASA

Toda la IA de Baby Caleb corre con **Meta Muse Spark nivel `-contributor`**, el mismo de D'CASA (decisión del dueño,
2026-11-18). El nombre del secreto sigue siendo `BRIAN_API_KEY` aunque la llave sea de Meta: así lo lee el sistema.
El despliegue no arranca sin ella, aunque en staging no uses a Brian.

1. Entra a la misma cuenta de desarrollador de Meta donde sacaste la llave de D'CASA (la de la API de modelos de Meta,
   `dev.meta.ai`).
2. Crea una llave **nueva** con nombre `sistemabk staging` (y otra `sistemabk producción` cuando toque). Nueva y no la
   de D'CASA, para poder apagar una sin tocar la otra.
3. Cópiala ya al gestor de contraseñas como `BRIAN_API_KEY`.

## Paso 6 — Las cinco claves que inventas tú

En tu gestor de contraseñas, usa **Generar contraseña** con estas condiciones: **64 caracteres, solo letras y números**
(sin símbolos). Una distinta para cada una, y otras cinco distintas para producción:

| Nombre | Para qué | Ojo |
|---|---|---|
| `PGBACKREST_CIPHER_PASS` | El candado de los respaldos | **Nunca se cambia** |
| `DCASA_PIN_PEPPER` | Protege los PIN de los socios | **Nunca se cambia** |
| `RESPALDO_TOKEN` | Permiso para pedir un respaldo a mano | — |
| `ODOO_ADMIN_PASSWORD` | La clave del usuario `admin` del panel | Con esta entras la primera vez |
| `ODOO_MASTER_PASSWORD` | La clave maestra de Odoo | Distinta de la de `admin` |

## Paso 7 — Pegar todo en GitHub

1. github.com › el repositorio **System-Baby-Cale** › **Settings** › **Environments** › **New environment** › nombre
   `staging` › **Configure environment**.
2. Abajo, **Environment secrets** › **Add environment secret**, una por una, con el nombre exacto (mayúsculas y guiones
   bajos tal cual):
   `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `PGBACKREST_CIPHER_PASS`,
   `RESPALDO_TOKEN`, `ODOO_ADMIN_PASSWORD`, `ODOO_MASTER_PASSWORD`, `DCASA_PIN_PEPPER`, `BRIAN_API_KEY`.
3. Más abajo, **Environment variables** › **Add environment variable**, estas cuatro (nombre → valor, exactos):
   - `URL_SITIO` → `https://sistemabk-staging.juanarrietabusiness.workers.dev` (sin `/` al final)
   - `BRIAN_PROVEEDOR` → `openai` (es la vía «compatible con OpenAI» por la que entra Meta; no es ChatGPT)
   - `BRIAN_BASE_URL` → `https://api.meta.ai/v1`
   - `BRIAN_MODELO` → `muse-spark-1.3-contributor`

   **No** crees `CANONICAL_HOST`.
4. Para producción (cuando toque): **New environment** › `production` › en **Deployment branches and tags** elige
   **Selected branches and tags** › **Add deployment branch or tag rule** › `main`. Las mismas diez claves con sus valores
   de producción, `URL_SITIO` = `https://sistemabk.juanarrietabusiness.workers.dev` hasta el día del dominio, y las mismas
   tres variables de Brian (`openai`, `https://api.meta.ai/v1`, `muse-spark-1.3-contributor`).
5. Avísale a Claude «ya están». Claude revisa que estén los nombres (sin ver los valores) y lanza el despliegue a staging.

## Lo que viene después (no hace falta ahora)

- **La IA del bot de clientes (Juan), igual que D'CASA.** En el panel de Cloudflare › Workers & Pages ›
  `sistemabk-chatbot` (y `-staging`) › Settings › Variables and Secrets: secreto `META_AI_API_KEY` con una llave de Meta
  nueva (como en el paso 5). Y en el panel de Odoo, *Conversaciones › Configuración › Ajustes de Juan*: proveedor
  **`meta`**; modelo rápido y modelo inteligente **`muse-spark-1.3-contributor`**; y en precios
  `{"muse-spark-1.3-contributor": {"entrada": 0.20, "entrada_cache": 0.004, "salida": 0.40}}` (el doble del precio real a
  propósito, como D'CASA: `docs/JUAN.md`). Sin respaldo de Anthropic: toda la IA es Meta. Esto vive en la base de datos,
  no en el código, por eso no viene copiado.
- Las demás claves del bot de clientes (WhatsApp, Telegram) también van en el panel de Cloudflare, no en GitHub.
- Opcionales: Telegram de Brian, correo (Resend), la puerta del equipo (Cloudflare Access), Turnstile.

## Plantilla para tu bloc de notas (sin valores)

La estructura que el dueño usaba para D'CASA, puesta al día para esta copia (2026-11-18). Las **etiquetas** (los nombres
de las llaves que tú creas en Cloudflare) cambiaron a `sistemabk-`, como todo lo de esta copia en Cloudflare. Los
**nombres de los secretos no cambian** aunque digan `DCASA_`: el sistema los busca por ese nombre exacto. Aquí nunca se
escriben los valores: van en el gestor de contraseñas.

```text
═══ CLOUDFLARE ═══
R2 Token: sistemabk-staging          (caja sistemabk-respaldos-staging)
  Access Key ID:                     → GitHub › staging › R2_ACCESS_KEY_ID
  Secret Access Key:                 → GitHub › staging › R2_SECRET_ACCESS_KEY

R2 Token: sistemabk-produccion       (caja sistemabk-respaldos)
  Access Key ID:                     → GitHub › production › R2_ACCESS_KEY_ID
  Secret Access Key:                 → GitHub › production › R2_SECRET_ACCESS_KEY

sistemabk-github-deploy (la llave del robot)
  Token:                             → GitHub › staging y production › CLOUDFLARE_API_TOKEN
  Account ID:                        → GitHub › staging y production › CLOUDFLARE_ACCOUNT_ID
  Subdomain: juanarrietabusiness     (no es secreto; ya está en el código)

═══ STAGING (GitHub › Environments › staging › secrets) ═══
PGBACKREST_CIPHER_PASS:              (NUNCA se cambia)
DCASA_PIN_PEPPER:                    (NUNCA se cambia)
ODOO_ADMIN_PASSWORD:
ODOO_MASTER_PASSWORD:                (distinta de la de admin)
RESPALDO_TOKEN:
BRIAN_API_KEY:                       (llave NUEVA de Meta)
TIENDA_FEED_TOKEN:                   (opcional: caché de páginas)
Variables (no secretas):
  URL_SITIO = https://sistemabk-staging.juanarrietabusiness.workers.dev
  BRIAN_PROVEEDOR = openai
  BRIAN_BASE_URL = https://api.meta.ai/v1
  BRIAN_MODELO = muse-spark-1.3-contributor

═══ PRODUCCIÓN (GitHub › Environments › production › secrets) ═══
PGBACKREST_CIPHER_PASS:              (NUNCA se cambia)
DCASA_PIN_PEPPER:                    (NUNCA se cambia)
ODOO_ADMIN_PASSWORD:
ODOO_MASTER_PASSWORD:
RESPALDO_TOKEN:
BRIAN_API_KEY:                       (otra llave NUEVA de Meta)
TIENDA_FEED_TOKEN:                   (opcional)
Variables (no secretas):
  URL_SITIO = https://sistemabk.juanarrietabusiness.workers.dev   (hasta el día del dominio)
  BRIAN_PROVEEDOR = openai
  BRIAN_BASE_URL = https://api.meta.ai/v1
  BRIAN_MODELO = muse-spark-1.3-contributor

═══ JUAN, el chatbot (panel de Cloudflare, NO GitHub) ═══
STAGING  → mismo valor en sistemabk-staging y en sistemabk-chatbot-staging
  JUAN_ODOO_TOKEN:
  JUAN_WORKER_TOKEN:
PRODUCCIÓN → mismo valor en sistemabk y en sistemabk-chatbot
  JUAN_ODOO_TOKEN:
  JUAN_WORKER_TOKEN:
META_AI_API_KEY:                     (llave NUEVA de Meta) → sistemabk-chatbot (y -staging)
TELEGRAM_BOT_TOKEN_JUAN:             (bot NUEVO) → sistemabk-chatbot
TELEGRAM_WEBHOOK_SECRET_JUAN:        → sistemabk-chatbot

═══ PUERTA DEL EQUIPO (opcional, después; GitHub › cada entorno) ═══
DCASA_PUERTA_RUTA:
DCASA_ACCESS_EQUIPO:
DCASA_ACCESS_AUD:                    (= el Application Audience (AUD) Tag de Cloudflare)
DCASA_PUERTA_SECRETO:                (distinto por entorno)

═══ TELEGRAM BRIAN (opcional, después; bot NUEVO) ═══
TELEGRAM_BOT_TOKEN:                  → GitHub › cada entorno
BRIAN_TELEGRAM_SECRETO:              → GitHub › cada entorno
ID OWNER TELEGRAM:                   → panel de sistemabk: BRIAN_TELEGRAM_CHATS y DCASA_ALERTA_TELEGRAM_CHAT
```

Para el **primer despliegue a staging** solo hacen falta el bloque de Cloudflare y el de STAGING. Lo demás va después.
Los dos bots de Telegram, las llaves de Meta y todo lo que se inventa son **nuevos**: nada se reusa de D'CASA (un bot de
Telegram apunta a un solo sistema, y los de D'CASA apuntan a D'CASA).
