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
| 2026-11-18 | ITBMS | Se queda tal cual (7 %, como D'CASA). Baby Caleb hoy no cobra ITBMS: el dueño pone la tasa en cero desde Ajustes; el día que cobre, solo cambia la tasa. **Hecho así desde el 2026-11-24:** el interruptor `DCASA_COBRA_ITBMS=0` (`docker/negocio.env`, dentro de la imagen) deja sin impuesto de venta el catálogo, la web, Juan y las cotizaciones; comprobado en staging el 2026-11-25 |
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
| 2026-11-24 | «Comprobante de pago» | El papel de Odoo no es la factura fiscal de la DGI, así que **no dice «Factura»**: pagado, «Comprobante de pago»; sin ningún pago, «Comprobante de compra»; con saldo, «Abono». También el nombre del PDF, el asunto y el cuerpo del correo, Mi cuenta, la nota de entrega y el aviso del correo en el pago (`_dcasa_titulo_documento`). Issue para D'CASA: dcasapty/D_Casa_new_word#137 |
| 2026-11-24 | Razón social | **Baby Caleb Panamá** (`res_company_data.xml`; las bases ya instaladas, por `dcasa_base` 19.0.1.12.0 si nadie lo cambió a mano). El RUC lo escribe el dueño en *Ajustes › Empresas*: el repositorio es público |
| 2026-11-24 | Sin tienda física | Venta 100 % en línea: el pago no ofrece «Pago en la tienda» y la entrega «Retiro en tienda» queda archivada (apagados, no borrados). Interruptor `DCASA_TIENDA_FISICA=0` en staging y producción (`docker/negocio.env`, dentro de la imagen → arranque → `website._dcasa_aplicar_sin_tienda_fisica`) |
| 2026-11-24 | Textos del comprobante | Garantía, cambios y términos armados **solo con lo que respondió el dueño** (cambios, defectos, pagos, delivery, factura fiscal), sin cifras nuevas; reemplazan los de D'CASA (muebles, colchones, flete). **Aprobados por el dueño el mismo día** («esto me gusta, digo que sí»); se cambian en *Ajustes › Empresas › Documentos* |
| 2026-11-24 | Pagos en línea | Tilopay, Yappy directo y la comisión del sitio, traídos de D'CASA (#130 y #131). **Nacen apagados y sin credenciales**; staging fijado en modo de prueba. Cómo se encienden: `docs/TILOPAY.md` y `docs/YAPPY.md` |
| 2026-11-24 | Promoción de Dany Baby | **2 cajas por $35.00 (4 por $70.00), sin fecha de fin; una caja suelta va a precio completo** («la promoción solamente son 2 cajas… si no, la tercera caja se cobra completa»): 3 = $55.00, 5 = $90.00. Programada como **Precio por par** del producto (solo Gerencia; DANY-AW600 a $35.00 por `catalogo.json` y, en staging, por la migración de `dcasa_catalogo` 19.0.2.4.0). Igual en la web y su pago, el chat de la tienda, la cotización y el PDF de Juan y las ventas del panel. No se suma a la campaña del sitio (gana la más barata) y el tope de la vendedora se mide sobre el precio de la promoción. Detalle: `docs/CATALOGO.md` › «La promoción por pares» |
| 2026-11-24 | Caja de producción | **Personalizada: 1 vCPU, 3 GiB y 8 GB de disco** (≈ $21 al mes, 24/7), en `edge/wrangler.jsonc`. `basic` (la de staging) le pareció demasiado lenta al dueño; D'CASA usa `standard-1` (½ vCPU, 4 GiB, ≈ $28-31). Si su jefe la ve lenta, se vuelve a `standard-1` con una línea y un despliegue. Recomendado además: la tienda rápida (`TIENDA_FEED_TOKEN` en los secretos de producción) |

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
- **Staging al día el 2026-11-25** (CI/CD 45538969686, commit `814ce5e`, con el bot Juan; 7.559 pruebas de Odoo y todas
  las demás en verde). Entró todo lo de la rama: comprobante de pago, razón social, textos del comprobante, pagos en
  línea apagados, la caja de producción, el WhatsApp QR blindado (sin desplegar su puente) y la promoción de Dany Baby.
  **Comprobado comprando en la web de staging desde un navegador de celular:** el pañal de $50 sale a $50.00 sin
  «+ ITBMS» en la ficha, el carrito ni el pago; la entrega es solo «Entrega a domicilio: te cotizamos por WhatsApp»;
  el pago, solo Yappy y transferencia (sin «Pago en la tienda»); Dany Baby: 1 caja $20.00, 2 cajas $35.00 y 3 cajas
  $55.00, con el aviso «Promoción 2 cajas por $35» en la ficha. El 2026-11-24 nada de eso se veía en staging aunque las
  pruebas pasaban: Cloudflare arrancó la imagen nueva con las variables del arranque anterior. Desde `bc086bc` la
  identidad del negocio va dentro de la imagen (`docker/negocio.env`) y el CI la comprueba en la base
  (`docs/CONTEXTO_AGENTICO.md`, «Incidente 2026-11-25»).
- **Staging con la ubicación exacta (2026-11-26)**: CI/CD #31 (`ada3fe9`): todas las pruebas en verde (Odoo, Juan,
  borde, puente, integración, simulacro de restauración e imagen) y staging sano con esa versión. **Comprado desde un
  navegador de teléfono (390 px)**: el bloque «¿Dónde le entregamos?» con «Mi ubicación» (GPS), la casa guardada en la
  dirección («Casa 12, portón verde»), la entrega «por cotizar», el pago por transferencia y «¡Gracias por tu compra!»
  (S00059), sin errores en la consola. La compra encontró dos fallos que las pruebas no veían (con un punto «Fuera de
  nuestra lista» «Confirmar» se quedaba quieto, y tras escribir la calle había que tocarlo dos veces): arreglados en
  `4524798`/`ebfa000` con sus pruebas (ubicación: 135, 0 fallos) y vueltos a subir a staging (CI/CD #32, sano con
  `ebfa000`): dos compras más desde el teléfono con **un solo «Confirmar»**, y sin barriada «Confirmar» lleva a
  «Barriada o calle» con el foco. Detalle menor visto: «Código postal» lleva un «*» aunque Panamá no lo pide (la
  compra pasa sin él). **Staging no tiene la
  tabla de lugares ni las claves de Google**: todo punto sale «Fuera de nuestra lista» y el envío «se lo confirmamos».
- **Producción instalada el 2026-11-26** (Desplegar #1, 04:38 UTC, desde `main`, con la imagen ya probada en staging:
  `ebfa000`, `sha256:f0b57c20…`; sin respaldo previo porque el Worker no existía): **sana a las 04:46 UTC** en
  `https://sistemabk.juanarrietabusiness.workers.dev` (versión `ebfa0005e724`, base al día, humo ok). La portada y la
  tienda responden con la marca Baby Caleb (5 productos, sin errores, vistos desde un teléfono). Base **nueva y
  vacía** (sin nada de staging). `babycaleb.com` sigue en la web actual hasta el día del dominio (`docs/DOMINIO.md`).
  El dueño puso las 10 claves y 4 variables del entorno `production` de GitHub y las dos claves de Google en el
  Worker `sistemabk` (después de que el contenedor arrancara: Odoo las lee con el próximo despliegue de imagen nueva;
  igual en staging). CI/CD #33 desde `main` ya había pasado todas las pruebas con ese código.
- **El mapa de Google, en staging y producción (2026-11-26)**: el dueño creó el proyecto «Baby Caleb» en Google Cloud
  (Maps JavaScript y Geocoding, dos claves con sus límites, presupuesto de $5 al mes con avisos al 50/90/100 %) y pegó
  `GOOGLE_MAPS_CLAVE_NAVEGADOR` y `GOOGLE_MAPS_CLAVE_SERVIDOR` en `sistemabk-staging` y `sistemabk`. Imagen nueva
  `8b80a9a` (CI/CD #35, todas las pruebas en verde) a staging y luego a producción (Desplegar #2 desde `main`, con
  respaldo previo): **el mapa carga en los dos** (comprobado desde un teléfono, sin errores; en producción sin crear
  pedidos: solo un carrito anónimo de prueba). Las cuotas diarias de Google quedaron «ilimitadas»: el freno es nuestro
  tope de 800 consultas de Geocoding por día; el dueño puede ponerles un número en Google Cloud.
- **La tabla de envíos de Baby Caleb (2026-11-26)**: el dueño no quiso precio por zona («No, definitivamente no»):
  quiere **el mismo sistema de D'CASA** (precio por km), medido desde el pin de salida de Baby Caleb, con **mínimo de
  $3** (cifra suya). El pin lo confirmó su agente de Chrome en Google Maps; no está en el repositorio (es público): va
  en el archivo y en *Envíos › Tarifa › Punto de salida*. Medido con el método de `docs/ENVIOS.md` («Medir el archivo
  para otro punto de salida»): 403 corregimientos con Google (clave temporal de Routes API como secreto de red del
  entorno de la sesión), los otros 10 817 lugares con OSRM ajustado. Salen **dos versiones** del archivo
  (`envios-babycaleb.html`, fuera del repositorio, entregado al dueño): **en moto** (ruta sin corredores; es la que se
  parece más a sus precios por zona de hoy) y **en carro** (por los corredores, como D'CASA). **El dueño eligió la de
  moto: sus motorizados van sin corredor** (2026-11-26). La tarifa del archivo es
  una **propuesta en revisión**: el mínimo es del dueño; los dos puntos de la recta, el redondeo y la distancia máxima
  los propuse para parecerse a sus tarifas por zona del sistema (`ver_zonas`), y Gerencia los cambia o aprueba en
  Odoo. **Se cotiza hasta 300 km, como D'CASA** (lo pidió el dueño el 2026-11-26: los mismos 11 299 lugares y el mismo
  límite; 11 161 quedan con precio). Panamá Oeste y el interior (por Ferguson) hoy se cotizan a mano: con la recta de
  la ciudad, lejos sale caro (Penonomé ≈ $29, Chitré ≈ $45); se ajusta en Odoo antes de aprobar.
  **En producción desde el 2026-11-26** (Desplegar con la imagen `ca3c8a8` probada en staging): el dueño cargó
  `envios-babycaleb.html` y aprobó la tarifa (su agente de Chrome, con el pin comprobado). Comprobado desde un teléfono,
  sin crear pedidos: el buscador del checkout encuentra Bella Vista, Tocumen, Arraiján y Penonomé, y el GPS en Albrook
  Mall (4,8 km) da «Envío $4». El código para el punto de salida: `4f8a3e3`, `65db073`, `ca3c8a8`.

- **babycaleb.com en el sistema nuevo (2026-11-27, 04:20 UTC; con el «sí» del dueño: «es la exigencia de mi jefe»;
  el equipo atiende los pedidos de la web en Odoo desde esa noche).** Desplegar #4 a producción con la imagen `3440faa`
  (CI/CD #37: todas las pruebas en verde; el simulacro de restauración se repitió una vez por un 403 de
  `packages.microsoft.com` en el runner). Comprobado: `babycaleb.com` responde el sistema nuevo, `/shop` abre, `www` →
  301 a la raíz, `panel.` y `ruta.` siguen en `babycaleb-sistema`. La web vieja soltó el dominio (Baby-caleb `56ded25`
  en su `main`, despliegue en verde) y sigue en `babycaleb-web.juanarrietabusiness.workers.dev`. Detalle y cómo volver
  atrás: `docs/DOMINIO.md`. **Falta:** encender Tilopay y Yappy (el dueño pega sus claves en `sistemabk` y hace falta
  un despliegue con imagen nueva para que Odoo las lea), el correo (Resend con `babycaleb.com`), `URL_SITIO` de Juan y
  Search Console.

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
  - **Textos de garantía, cambios y términos del comprobante:** desde el 2026-11-24 son los de Baby Caleb, armados con
    sus respuestas y aprobados por él. Se cambian en *Ajustes › Empresas › Documentos*.
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
- **Water wipes Nateen:** el dueño confirmó (2026-11-24) que se sigue vendiendo, aunque la web vieja lo marque «descatalogado»: queda publicado.
- Datos de la empresa: RUC y DV (los escribe el dueño en *Ajustes › Empresas*), web y lema de los documentos. La razón
  social ya es «Baby Caleb Panamá» y no hay dirección (vende en línea).
- **Promoción de Dany Baby (programada el 2026-11-24, en staging desde el 2026-11-25):** lo que queda para el dueño: (1) una venta ya **confirmada** a la que le cambian la cantidad no se acomoda sola (3 cajas quedan a $20.00 cada una): se revisa a mano o se cambia antes de confirmar; (2) si quiere que la promoción **sí** se sume a una campaña del sitio, hoy no se suma (gana la más barata); (3) el texto de la ficha dice «Promoción: 2 cajas por $35.00. Va por pares: una caja suelta va a su precio normal.»: si quiere otras palabras, se cambian en el código (no hay cifras en él).
- **Cifras de Socios y del programa de vendedores de Baby Caleb**: `addons/dcasa_socios/data/puntos.json` (versión 6)
  está todo en `null` y el catálogo de premios vacío (hecho el 2026-11-18). Qué cifra enciende qué parte:
  `docs/SOCIOS.md` › «Cambiar las reglas». Mientras tanto no se acredita ni se canjea nada y las ventas van igual.
- Textos con la marca «Socios D'CASA» / «D'CASA» que siguen en la web del programa (títulos de `/socios`, la banda de
  Socios de la portada —sin cifras, pero con «Suma puntos y gana invitando»—, el producto «Premio del programa Socios
  D'CASA», los tipos de vendedor, la bienvenida por correo que dice «tus puntos»): se cambian con el trabajo de la web
  pública o de nombres configurables.
- **Ubicación exacta de la entrega (hecha el 2026-11-25, `dcasa_ubicacion`, detalle en `docs/UBICACION.md`; el plan
  para llevarla a D'CASA, `docs/UBICACION_PARA_DCASA.md`).** Con las ideas A–E del dueño (pedir el punto al comprar,
  «🚚 Sale hoy», «Avisar que llegué», quién recibe y otro teléfono, foto de la fachada) y dos auditorías independientes
  (seguridad y privacidad, dinero y datos, la clienta en el navegador) con sus arreglos. La línea de la política de
  privacidad ya está (el dueño dio su «sí»). Lo que queda del dueño:
  - **Las dos claves de Google** (lo más urgente: sin ellas no hay mapa para afinar el pin; el GPS del teléfono, la
    búsqueda de barriadas y la dirección escrita sí funcionan): Maps JavaScript, restringida a los dominios del sitio,
    como `GOOGLE_MAPS_CLAVE_NAVEGADOR`, y Geocoding, solo para el servidor, como `GOOGLE_MAPS_CLAVE_SERVIDOR`. Se pegan
    en Cloudflare › `sistemabk` (y `sistemabk-staging`) › Settings › Variables and Secrets, nunca en el chat. En Google
    Cloud, una cuota diaria y una alerta de presupuesto.
  - **La tabla de lugares y la tarifa de envíos** (Envíos › Tarifa › «Cargar lugares y tarifa desde el archivo», y
    «Aprobar la tarifa»; `docs/ENVIOS.md`): sin ella, el mapa no sabe la barriada ni el precio y todo envío sale «se lo
    confirmamos». No está en el repositorio (es público): la sube Gerencia.
  - **Una plantilla aprobada de Meta** (opcional) para que el asistente pueda escribir por WhatsApp oficial pasadas las
    24 horas; hoy, fuera de la ventana, la vendedora lo manda por WhatsApp con un toque.
  - **Lo que dice la web de los pañales «100 % fibras de bambú»** y los textos de las certificaciones («según el
    fabricante») para el conocimiento de Juan: se cargan cuando el dueño los confirme.
- **RECORDARLE AL DUEÑO, EL DÍA DEL DOMINIO, TODO LO DEL CORREO** (lo pidió el 2026-11-25): Resend con `babycaleb.com`
  verificado (registros DNS en Cloudflare; ya hay un `_dmarc`: no agregar otro), la clave de solo envío como secreto
  `RESEND_API_KEY` del Worker `sistemabk`, Email Routing de `clientes@babycaleb.com` a su Gmail, Gmail «Enviar como»
  `clientes@` (servidor `smtp.resend.com`, puerto 465, usuario `resend`, otra clave de Resend) y, en Odoo › Ajustes ›
  Correo a clientes, «Enviar correo de prueba» y encender «Enviar correos a clientes». El correo es el mismo de D'CASA
  (sale de `ventas@babycaleb.com`, las respuestas llegan a `clientes@babycaleb.com`); pasos en `docs/CORREO.md` §2-§6.
  Pendiente su respuesta: ¿el comprobante se emite solo al pagar en línea (Yappy/tarjeta)?
- **RECORDARLE AL DUEÑO, PASO A PASO, EL DÍA DEL DOMINIO** (lo pidió el 2026-11-18): quitar `babycaleb.com` y
  `www.babycaleb.com/*` de `Baby-caleb/wrangler.jsonc`, porque esa web se despliega sola en cada push a su `main` y se
  volvería a llevar el dominio. Pasos en `docs/DOMINIO.md` (Fase B, paso 2); candado en
  `edge/test/dominio-babycaleb.test.ts`.
- **Cobros en línea del sistema nuevo:** el código ya está (apagado). **El dueño decidió (2026-11-24) usar las mismas
  cuentas de Tilopay y Yappy que cobran hoy en `babycaleb.com`.** Con eso:
  - **Se encienden el día del dominio**, cuando `babycaleb.com` ya apunte a `sistemabk`; hasta entonces cobra la web
    vieja. El botón de Yappy está registrado para `babycaleb.com` (`YAPPY_DOMINIO` letra por letra): desde la dirección
    `workers.dev` Yappy no lo aceptaría.
  - **Nunca poner la cuenta de Tilopay en «Modo Prueba»** mientras la web vieja venda: el interruptor es de toda la
    cuenta (TILOPAY.md, b'). Por eso staging (fijado en `prueba`) no se prueba con esta cuenta: la prueba es un cobro
    real chico en producción, el día del dominio.
  - **La clave secreta de Yappy se muestra una sola vez.** Si el dueño no la tiene guardada, generar otra rompe el
    cobro de la web vieja hasta cambiarla allá también: mejor hacerlo el día del dominio.
  - **El aviso (webhook) de Tilopay no existe para estos pagos** (Soporte de Tilopay, 2026-11-24: para `processPayment`
    «todavía no está disponible»; solo para cobros recurrentes). No se registra nada: el pago se confirma cuando la
    clienta vuelve de Tilopay y, si cierra la ventana, la tarea programada lo pregunta sola (lo reciente, cada 8
    minutos). La pantalla «Gestión de URLs» del panel de Tilopay no es para esto (TILOPAY.md, d3').
  - Las claves se pegan en Cloudflare › `sistemabk` › Settings › Variables and Secrets (nombres en TILOPAY.md y
    YAPPY.md), nunca en el chat ni en GitHub.
- **WhatsApp por QR (`puente-wa`), blindado el 2026-11-24 tras la caída del CRM** (detalle en `docs/JUAN_PUENTE.md`,
  §F y §G): vigilante paciente, limpieza automática de pre-keys con respaldo, avisos por Telegram y memoria y CPU en
  `/api/estado`. Sigue **sin desplegar**. **El dueño confirmó las tres (2026-11-24, «sí a las tres, déjalo así»):**
  (1) contestar solo los mensajes atrasados de 15 minutos o menos y avisar del resto; (2) el aviso «no entran
  mensajes» tras 60 minutos, de lunes a sábado de 9:00 a 18:00; (3) seguir en la caja `lite` (≈ $2 al mes) y pasar a
  `basic` (≈ $7,30) solo si el estado lo pide. La recomendación: la API oficial de Meta como canal principal y el QR de
  respaldo.
- **Duración de cada foto del carrusel de la portada:** 3 s de fábrica (vino de un pedido de la dueña de D'CASA); se
  cambia desde el panel.
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
