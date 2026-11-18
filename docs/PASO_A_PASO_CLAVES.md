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

## Paso 5 — La IA de Brian (`BRIAN_API_KEY`)

El despliegue no arranca sin ella, aunque en staging no uses a Brian.

1. Entra a console.anthropic.com › **API Keys** › **Create Key**.
2. Nombre: `sistemabk staging` (y otra `sistemabk producción` cuando toque). Si la consola te deja ponerle un tope de
   gasto al espacio de trabajo, ponle uno bajo a la de staging.
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
3. Más abajo, **Environment variables** › **Add environment variable**: nombre `URL_SITIO`, valor
   `https://sistemabk-staging.juanarrietabusiness.workers.dev` (sin `/` al final). **No** crees `CANONICAL_HOST`.
4. Para producción (cuando toque): **New environment** › `production` › en **Deployment branches and tags** elige
   **Selected branches and tags** › **Add deployment branch or tag rule** › `main`. Las mismas diez claves con sus valores
   de producción, y `URL_SITIO` = `https://sistemabk.juanarrietabusiness.workers.dev` hasta el día del dominio.
5. Avísale a Claude «ya están». Claude revisa que estén los nombres (sin ver los valores) y lanza el despliegue a staging.

## Lo que viene después (no hace falta ahora)

- Claves del bot de clientes (`sistemabk-chatbot`): su IA, WhatsApp, Telegram. Van en el panel de Cloudflare, no en GitHub.
- Opcionales: Telegram de Brian, correo (Resend), la puerta del equipo (Cloudflare Access), Turnstile.
