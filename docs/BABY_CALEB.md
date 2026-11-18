# Esta copia es la de Baby Caleb

Este repositorio (`juanarrietabusiness-pixel/System-Baby-Cale`) nació el **2026-11-18** como espejo exacto de
`dcasapty/D_Casa_new_word` en el commit `d2ba8ca` (463 commits de historia, `main` idéntico). El original sigue como
remoto `upstream` para traer mejoras con `git merge` (`docs/REPLICAR.md` §8). Sobre ese espejo se hacen las adecuaciones
que pide el dueño, y este archivo es su registro: **lo que no está aquí no está decidido**.

La meta del dueño: que este sistema sea una **plantilla** que se pueda seguir copiando a otras empresas, cada una con sus
datos, su marca y los nombres de sus asistentes.

## Nombres en Cloudflare (cuenta de Juancito, subdominio `juanarrietabusiness.workers.dev`)

Prefijo elegido por el dueño: «sistemaBK», que Cloudflare solo acepta en minúsculas → **`sistemabk`**.

| Antes (D'CASA) | Ahora | Qué es |
|---|---|---|
| `dcasa` | `sistemabk` | Odoo + sitio (borde y contenedor). Producción en `https://sistemabk.juanarrietabusiness.workers.dev` |
| `dcasa-staging` | `sistemabk-staging` | Ídem, de prueba. `https://sistemabk-staging.juanarrietabusiness.workers.dev` |
| `dcasa-juan` / `-staging` | `sistemabk-chatbot` / `sistemabk-chatbot-staging` | El Worker del bot de clientes (hoy «Juan») |
| `dcasa-puente-wa` / `-staging` | `sistemabk-puente-wa` / `-staging` | Puente de WhatsApp por QR (opcional; D'CASA nunca lo desplegó) |
| `dcasa-respaldos` / `-staging` | `sistemabk-respaldos` / `sistemabk-respaldos-staging` | Buckets de R2 (hay que crearlos: wrangler no los crea) |
| `dcasa-odoo` | `sistemabk-odoo` | Repositorio de la imagen en el registro de Cloudflare |

Lo que dice «dcasa» y **se queda** (decisión del dueño, 2026-11-18, para poder traer mejoras de D'CASA): el prefijo
`dcasa_` de módulos y campos, las variables `DCASA_*`, el nombre interno de la base, los User-Agent y las sales de cifrado
del puente. Ya en uso en la cuenta y **no se tocan**: `babycaleb-web`, `babycaleb-sistema(-staging)`, `babycaleb-db`,
`babycaleb-privado`, `babycaleb-respaldos` (son del sistema actual de Baby Caleb).

## Decisiones del dueño

| Fecha | Tema | Decisión |
|---|---|---|
| 2026-11-18 | Forma de copiar | Espejo tal cual del repositorio y, sobre él, las adecuaciones que el dueño pida |
| 2026-11-18 | Repositorio | Público (los minutos de Actions de uno privado no alcanzan: cada CI + despliegue ronda 1 h 30 – 2 h) |
| 2026-11-18 | Entornos | Los mismos de D'CASA: pruebas, staging y producción. Staging solo para probar; producción con todos los secretos |
| 2026-11-18 | Dominio | `babycaleb.com` se mueve **un día aparte**, cuando producción esté revisada: `docs/DOMINIO.md` |
| 2026-11-18 | ITBMS | Se queda tal cual (7 %, como D'CASA). Baby Caleb hoy no cobra ITBMS: el dueño pone la tasa en cero desde Ajustes; el día que cobre, solo cambia la tasa |
| 2026-11-18 | Catálogo | Fuera todo lo de D'CASA. Entran los artículos del inventario del dueño del 2026-11-18 con su precio y su stock, más NAT-L a $45 con 0 en stock. Sin fotos: se suben a mano |
| 2026-11-18 | Conocimiento de los asistentes | En cero: nada de D'CASA, ni preguntas por responder. Cada negocio carga el suyo (a mano o por MCP). El mecanismo no se toca |
| 2026-11-18 | Marca del panel | Logo del panel, favicon y colores del panel se cambian desde Ajustes, por empresa. La web pública la programamos nosotros |
| 2026-11-18 | Web pública | Mismo diseño, sin nombre, logo, WhatsApp ni dirección de D'CASA |
| 2026-11-18 | Políticas (privacidad y términos) | **El mismo texto de D'CASA, palabra por palabra**, incluido el párrafo de Meta Muse Spark que entrena con las conversaciones, el apartado de Socios y la frase del respaldo de Anthropic. Solo cambia la empresa: donde dice D'CASA, su RUC, dirección y correo, van los de Baby Caleb (lo que falte, `PENDIENTE`) |
| 2026-11-18 | Inteligencia artificial | Los mismos proveedores y modelos que D'CASA: **toda la IA es Meta Muse Spark nivel `-contributor`** (sabiendo que entrena con las conversaciones). Brian: `BRIAN_PROVEEDOR=openai`, `BRIAN_BASE_URL=https://api.meta.ai/v1`, `BRIAN_MODELO=muse-spark-1.3-contributor`, la llave de Meta en `BRIAN_API_KEY` (el nombre se queda). Juan: `META_AI_API_KEY` en `sistemabk-chatbot` y en *Ajustes de Juan* proveedor `meta`, modelos `muse-spark-1.3-contributor` y precios al doble como D'CASA. Sin respaldo de Anthropic. El código está optimizado para esos costos: no se cambia |
| 2026-11-18 | Contacto de la web | Los de la web actual de Baby Caleb (`Baby-caleb/content.json`): WhatsApp +507 6757-5065, babycalebpanama@gmail.com, Instagram @babycalebpanama, Lunes a Sábado 9:00-18:00, «Venta 100% online con entrega a domicilio — Ciudad de Panamá», y el logo `logo-babycaleb.png` |
| 2026-11-18 | Datos de la empresa | Los pasa el dueño después. Mientras: «Baby Caleb», Panamá, y lo demás vacío |
| 2026-11-18 | Conocimiento por MCP | Se queda como está: solo desde la pantalla (hoy no hay herramienta de Brian/MCP para cargarlo) |
| 2026-11-18 | Plantillas de mensajes | Las de Sofía, la respuesta rápida /socios y el asunto fijo de Camila dicen el nombre de la empresa en lugar de D'CASA, y sin ofrecer Socios ni cumpleaños |
| 2026-11-18 | Presentación de los asistentes | Siguen diciendo «D'CASA» (p. ej. «Hola, soy Juan de D'CASA.») hasta el trabajo de nombres configurables |
| 2026-11-18 | Ejemplos de staging | Fuera las conversaciones de ejemplo de D'CASA; no se inventan ejemplos de Baby Caleb |
| 2026-11-18 | Socios y vendedores | Todas las cifras de `puntos.json` en PENDIENTE (ninguna de D'CASA) y el programa de vendedores apagado. No dan puntos ni comisiones hasta que el dueño ponga las de Baby Caleb; las ventas funcionan igual. Socios no tiene interruptor propio |
| 2026-11-18 | Costos | El dueño dirá qué herramientas del sistema de D'CASA se quedan y cuáles se quitan, para bajar el consumo |
| 2026-11-18 | Nombres de los asistentes | Cada empresa debe poder nombrarlos como quiera (trabajo aparte, por hacer) |

## Pendiente (preguntas abiertas y trabajo por hacer)

- Datos de la empresa: razón social, RUC y DV, dirección, teléfono, correo, web, lema de los documentos.
- Promoción de Dany Baby (DANY-AW600): «2 cajas (1,200 toallitas) por $35.00». Anotada, no programada.
- **RECORDARLE AL DUEÑO, PASO A PASO, EL DÍA DEL DOMINIO** (lo pidió el 2026-11-18): quitar `babycaleb.com` y
  `www.babycaleb.com/*` de `Baby-caleb/wrangler.jsonc`, porque esa web se despliega sola en cada push a su `main` y se
  volvería a llevar el dominio. Pasos en `docs/DOMINIO.md` (Fase B, paso 2); candado en
  `edge/test/dominio-babycaleb.test.ts`.
- Cobros en línea del sistema nuevo (hoy Tilopay y Yappy viven en la web actual, en `babycaleb.com`).
- Qué herramientas se quitan para bajar costos.
- Nombres configurables de los asistentes (Juan, Brian, Sofía, Camila, Andrés).
- `CLAUDE.md`, `docs/LEEME_PRIMERO.md` (bitácora), `docs/PRIORIDADES.md`, `docs/historico/` y `docs/gerencia/` siguen siendo
  los de D'CASA: se reescriben para Baby Caleb cuando el dueño lo pida (`docs/REPLICAR.md` §4.3).
- `.github/versiones_estables.json` y `volver-a-estable.yml` apuntan a imágenes de D'CASA que no existen en esta cuenta: **no
  usar ese botón** hasta tener la primera versión estable propia (`docs/REPLICAR.md` §4.3).
