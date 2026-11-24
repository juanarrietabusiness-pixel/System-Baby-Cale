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
| `dcasa-respaldos` / `-staging` | `sistemabk-production` / `sistemabk-staging` | Buckets de R2 (hay que crearlos: wrangler no los crea) |
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
| 2026-11-19 | Marca de todo el sistema | **El branding de la web de Baby Caleb, tal cual**, en la web pública, el panel, los documentos y los correos: crema, navy, naranja y verde salvia, Montserrat y botones en pastilla. Fuera el azul, el amarillo, Anton y Oswald, y toda foto o sección de muebles. El contrato es `docs/MARCA_BABY_CALEB.md` y reemplaza las reglas de marca de D'CASA de `CLAUDE.md`. Esto cambia la decisión del 2026-11-18 «Web pública: mismo diseño» |
| 2026-11-24 | Web pública | **Igual a babycaleb.com:** la cabecera (solo el nombre y los enlaces Productos, Beneficios, Historia, Tips, Cómo comprar y FAQ), la portada, el pie y las páginas `/beneficios`, `/historia`, `/tips`, `/como-comprar` y `/faq`. Se conservan y se irán mejorando la ficha del producto, el carrito y la cuenta. Socios y Contacto salen del menú y quedan en el pie. La banda de Socios sale de la portada hasta que el programa tenga cifras. Las tallas pasan a pastillas. Auditoría de accesibilidad: 0 problemas |
| 2026-11-24 | Fotos y publicación | «Sube las fotos de Baby Caleb y publica los productos»: las de su web (`content.json`, `public/img/`) entran con el catálogo (`dcasa_catalogo/data/fotos/`, la principal y la de cada talla con su segunda foto) y se publica lo que tiene foto: Nateen de cierre, Nateen Pants y Water wipes Nateen. Una foto puesta a mano no se pisa. Velvee, Dany Baby y Fular Moon (en su web, el logo o «Foto próximamente») siguen sin publicar hasta tener la suya |
| 2026-11-24 | Asistentes de Baby Caleb | Juan (mensajería) y Andrés (chat de la web) ya no son de mueblería: hablan de pañales, toallitas y fulares, de tallas (RN a XXL) y de lo que trae cada caja, siempre con las herramientas; el nombre de la empresa sale de *Ajustes de Juan* (`nombre_publico`), nunca escrito a mano; voz neutra («alguien de la tienda que conoce bien los productos»), lo demás igual. El lector de fotos y «Busca con una foto» reconocen pañales, toallitas y fulares con su talla. **Ajustes de Juan todavía dice «el equipo de D'CASA» y «Hola, soy Juan de D'CASA.»** (la decisión del 2026-11-18): se cambia ahí cuando el dueño diga. `docs/JUAN.md` describe la voz y la presentación de D'CASA: manda esto |

## Estado

- **Staging instalado el 2026-11-19** (CI/CD #8, commit `9be5e55`): `https://sistemabk-staging.juanarrietabusiness.workers.dev`,
  sano (`/__edge/health`: borde, Odoo y contenedor ok, base al día, humo ok). El chatbot
  `sistemabk-chatbot-staging` también está arriba, todavía sin sus claves (`JUAN_ODOO_TOKEN`, `JUAN_WORKER_TOKEN`, la IA:
  ver `docs/PASO_A_PASO_CLAVES.md`). Entrar: `/web/login`, usuario `admin`, la `ODOO_ADMIN_PASSWORD` de staging; pide
  enrolar el doble factor.
- **Staging al día el 2026-11-24** (CI/CD 45421430520, commit `09aca67`, con el bot Juan): la web igual a
  babycaleb.com, las fotos de su web en el catálogo y los productos con foto publicados. Auditoría en vivo con axe-core a
  390, 768 y 1440 px: 0 problemas. Quedan para la siguiente subida los arreglos de la ficha en el celular (`cc867fe`) y
  la guía sin muebles (`f42bfef`). Staging sigue 24/7: el dueño no quiere que duerma (2026-11-24).
- **Producción**: no desplegada. `main` sigue siendo el espejo exacto de D'CASA; todas las adecuaciones viven en la rama
  `claude/nifty-keller-k8rcmz`.

## Pendiente (preguntas abiertas y trabajo por hacer)

- **Factura electrónica de la DGI (averiguado el 2026-11-24, con fuentes):**
  - El **Facturador Gratuito no se puede conectar**: la DGI dice que «no permite integración con otros sistemas»
    (https://dgi.mef.gob.pa/_7FacturaElectronica/f-Gratuito). Para emitir desde Odoo hace falta un **PAC**.
  - Desde el 2026-01-01 el Gratuito solo vale hasta **B/.36,000 al año y 100 documentos al mes** (Resolución 201-6299).
    Si Baby Caleb pasa de eso, el PAC es obligatorio: lo confirma la contadora.
  - PAC con API y que mandan el correo a la clienta: **Hypernova Labs** (módulo para Odoo 19, Community, $95),
    **efacturapty / Ideati** (API pública; $40, $60 o $119 al año por 50, 100 o 200 facturas al mes) y **Factura
    Fácil** (API pública con pruebas). Lista oficial de los 18 PAC: https://dgi.mef.gob.pa/_7FacturaElectronica/Proveedorespac
  - `addons/dcasa_fe_pa` (de D'CASA, no instalado) ya arma el XML y el CUFE y tiene la cola, la contingencia y la
    anulación, pero **no tiene conector con ningún PAC real**, no firma, `xsd/` está vacía, arrastra combos de D'CASA y
    no retiene el correo hasta la autorización (la clienta recibiría la factura sin CUFE ni QR). Elegido el PAC: o su
    conector, o un conector para `dcasa_fe_pa`.
  - Lo del dueño: la firma electrónica del Registro Público (B/.50), el contrato y las credenciales del PAC (como
    secretos), la Declaración Jurada rectificativa en e-Tax 2.0 y la confirmación de la afiliación. Mientras tanto,
    sigue con el Gratuito (en el cambio se usan los dos hasta 90 días, Resolución 201-9775).

- **Marca Baby Caleb (2026-11-19), lo que decide el dueño:**
  - **Textos de garantía, cambios y términos de la factura:** siguen siendo los de D'CASA y hablan de muebles («Tus muebles
    tienen garantía…», colchones, flete). Se cambian en *Ajustes › Empresas › Documentos*. Ninguno se inventa: los da el
    dueño.
  - **El checkout ofrece «Retiro en tienda» y «Pago en la tienda»**, y Baby Caleb no tiene tienda física. Solo se
    cambiaron los textos. Quitarlos cambia la lógica, porque toca los apartados.
  - **La banda de Socios de la portada** dice «Suma puntos y gana invitando». Desde el 2026-11-24 **no sale** mientras
    las cifras de `puntos.json` estén en PENDIENTE (`website._dcasa_socios_con_cifras`); vuelve sola cuando las haya.
  - **Lo técnico que todavía dice «D'CASA»:** los nombres de los módulos en *Aplicaciones* y los de las plantillas. No
    se ven en la tienda ni en las pantallas de trabajo.
- **Decisiones de diseño tomadas el 2026-11-19 al llevar la marca** (las revisa el dueño en staging):
  - Con productos elegidos para el carrusel de la portada, las fotos van dentro del marco redondeado del hero, sin velo.
  - Socios va en una tarjeta crema con la foto de las cajas Nateen, para no juntar tres bandas verdes.
  - Los antetítulos van sin número («03 /»), porque el orden de las secciones es otro.
  - Los testimonios van de dos en dos.
  - En la ficha del producto, WhatsApp sigue siendo el botón principal y «Agregar al carrito» va de contorno.
  - En los PDF el papel queda blanco, porque se imprimen.
- **Fotos del dueño (2026-11-24):** Velvee (P, M y G), Dany Baby y Fular Moon ya tienen las suyas en el catálogo. Las
  subió a «up media» de la rama `main` (la de D'CASA): el robot de D'CASA movió las de Velvee P y G a `descartado/` y las
  de Velvee M quedaron en la raíz. No se perdió ninguna; se tomaron de ahí. **Para la próxima:** subirlas igual; se
  recogen de `main`.
- **Lo que dicen las fotos y conviene confirmar:** cada paquete de Velvee trae 50 (P), 44 (M) y 42 (G) pañales, y la
  lista del dueño dice 150, 132 y 126: ¿se vende el bulto de 3 paquetes? Si es así, la ficha debería decirlo. La caja
  de Dany Baby dice «6 PCS» de 100: confirma la lista (6 paquetes de 100) y no la web (12 de 50).
- **Water wipes Nateen** quedó publicado, pero la web de Baby Caleb lo marca «descatalogado» (`content.json`). Si ya no
  se vende, se despublica en su ficha.
- Datos de la empresa: razón social, RUC y DV, dirección, teléfono, correo, web, lema de los documentos.
- Promoción de Dany Baby (DANY-AW600): «2 cajas (1,200 toallitas) por $35.00». Anotada, no programada.
- **Cifras de Socios y del programa de vendedores de Baby Caleb**: `addons/dcasa_socios/data/puntos.json` (versión 6)
  está todo en `null` y el catálogo de premios vacío (hecho el 2026-11-18). Qué cifra enciende qué parte:
  `docs/SOCIOS.md` › «Cambiar las reglas». Mientras tanto no se acredita ni se canjea nada y las ventas van igual.
- Textos con la marca «Socios D'CASA» / «D'CASA» que siguen en la web del programa (títulos de `/socios`, la banda de
  Socios de la portada —sin cifras, pero con «Suma puntos y gana invitando»—, el producto «Premio del programa Socios
  D'CASA», los tipos de vendedor, la bienvenida por correo que dice «tus puntos»): se cambian con el trabajo de la web
  pública o de nombres configurables.
- **RECORDARLE AL DUEÑO, PASO A PASO, EL DÍA DEL DOMINIO** (lo pidió el 2026-11-18): quitar `babycaleb.com` y
  `www.babycaleb.com/*` de `Baby-caleb/wrangler.jsonc`, porque esa web se despliega sola en cada push a su `main` y se
  volvería a llevar el dominio. Pasos en `docs/DOMINIO.md` (Fase B, paso 2); candado en
  `edge/test/dominio-babycaleb.test.ts`.
- Cobros en línea del sistema nuevo (hoy Tilopay y Yappy viven en la web actual, en `babycaleb.com`).
- Qué herramientas se quitan para bajar costos (el dueño no quiere el sistema dormido, 2026-11-19). La lista para
  marcar está en [HERRAMIENTAS_BABY_CALEB.md](HERRAMIENTAS_BABY_CALEB.md). El dueño ya dijo que quitará las llamadas y
  videollamadas y las notificaciones de fábrica: son parte de `mail`, así que se esconden, no se desinstalan. Lo que más pesa es la
  memoria **reservada** de la caja: se paga se use o no. La CPU se paga solo por uso. Quitar herramientas baja la cuenta
  sobre todo si permite una caja más chica. Cajas posibles para producción, 24/7, con los precios de Cloudflare del
  2026-11-19 (cálculo nuestro, sin contar la CPU):
  - `basic` (¼ vCPU, 1 GiB) ≈ $7,3. D'CASA la encontró justa y lenta. Staging ya corre ahí con todo, así que se puede medir.
  - Personalizada (1 vCPU, 3 GiB) ≈ $21,2. Es la mínima que permite la política `default`: ≥ 1 vCPU y ≥ 3 GiB por vCPU.
    Es más rápida que `standard-1`.
  - `standard-1` (½ vCPU, 4 GiB) ≈ $27,8. Es la de D'CASA.

  El mejor momento para quitar herramientas es antes de instalar producción: en una base nueva simplemente no se
  instalan (`ODOO_MODULES` en `docker/entrypoint.sh`, cuidando las dependencias y las pruebas).
- Nombres configurables de los asistentes (Juan, Brian, Sofía, Camila, Andrés).
- `CLAUDE.md`, `docs/LEEME_PRIMERO.md` (bitácora), `docs/PRIORIDADES.md`, `docs/historico/` y `docs/gerencia/` siguen siendo
  los de D'CASA: se reescriben para Baby Caleb cuando el dueño lo pida (`docs/REPLICAR.md` §4.3).
- `.github/versiones_estables.json` y `volver-a-estable.yml` apuntan a imágenes de D'CASA que no existen en esta cuenta: **no
  usar ese botón** hasta tener la primera versión estable propia (`docs/REPLICAR.md` §4.3).
