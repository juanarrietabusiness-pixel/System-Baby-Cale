# El puente de WhatsApp de D'CASA (para Juan)

Esta guía es para la dueña. Está escrita sin tecnicismos; lo que es solo para quien opera el sistema va
al final, en el apéndice.

> **Estado (2026-11-06):** el puente está construido y probado con un WhatsApp de mentira (un doble), pero **nunca
> se conectó a un WhatsApp real ni se desplegó**. Desde el 2026-11-02 Juan atiende el WhatsApp de la tienda por la
> **API oficial de Meta** ([JUAN_CANALES.md](JUAN_CANALES.md)). Esta guía queda para otra instalación o como plan de
> emergencia; se mantiene aparte porque el código del puente y su flujo de despliegue la citan.
>
> **Actualización (2026-11-24): la caída del CRM de Baby Caleb.** El puente QR de ese CRM (del que salió este) pasó
> **14 horas en bucle**: al volver de un rato desconectado, WhatsApp le entregó de golpe lo acumulado, el puente tardaba en
> procesarlo, y un vigilante impaciente lo mataba antes de terminar, una y otra vez. Se destrabó limpiando las llaves
> acumuladas (pre-keys). Este puente ya trae los arreglos: un **vigilante paciente**, una **reconexión liviana**, la
> **autolimpieza de pre-keys** con respaldo, **avisos** antes de que alguien note el silencio y **métricas** de memoria y
> procesador (sección F y apartado G). Aun así, la conclusión de ese informe es la de esta guía: **el canal principal debe
> ser la API oficial de WhatsApp (Meta); el QR, como mucho, de respaldo** (sección 8).

---

## En una frase

El puente es el «teléfono» que sostiene WhatsApp las 24 horas para que el asistente («el equipo de D'CASA»)
pueda leer lo que escriben los clientes y contestarles, incluso con fotos y documentos. Funciona vinculando
un número **como si fuera WhatsApp Web** (por código QR).

## Lo importante antes de todo

1. **Es un camino no oficial.** WhatsApp (Meta) no lo aprueba y puede **bloquear el número** sin aviso y sin
   apelación. Tú lo decidiste sabiéndolo. Esta guía te dice cómo bajar ese riesgo (sección 6) y qué hacer si
   pasa (sección 7), pero **nadie puede garantizar que no te bloqueen**.
2. **Tu teléfono sigue funcionando igual.** Sigues leyendo y contestando desde el teléfono. Lo que tú
   escribes desde ahí el asistente lo nota y **se calla** en esa conversación (la toma una persona).
3. **Nunca pegues una contraseña o clave en un chat ni en GitHub.** Van solo en el panel de Cloudflare.

---

## 1. Qué necesitas tener listo

- La cuenta de Cloudflare de D'CASA (ya la usa la tienda).
- El **teléfono del negocio** con WhatsApp, con internet, en tus manos el día de vincular.
- Un gestor de contraseñas (para crear y guardar los dos secretos de abajo).
- Telegram, si quieres que el sistema te **avise** cuando WhatsApp se desconecte (recomendado).
- El Worker del asistente (`juan`) ya desplegado: el puente se conecta a él.

## 2. Poner los secretos (una sola vez)

Los secretos **no pasan por GitHub**: los pegas tú en Cloudflare, en el Worker del puente
(**dcasa-puente-wa**; el de pruebas se llama **dcasa-puente-wa-staging**):

> Cloudflare → Workers y Pages → **dcasa-puente-wa** → Configuración → **Variables y secretos** →
> Agregar → tipo **Secreto**.

| Nombre | Para qué sirve | Cómo es |
|---|---|---|
| `WA_TOKEN` | La contraseña que comparten el puente y el asistente (`juan`). | Generada por ti con tu gestor: **mínimo 24 caracteres, solo letras, números y guiones** (sin ñ, tildes ni símbolos raros). **El mismo valor** que en el Worker `juan`. |
| `WA_SESION_CLAVE` | Cierra con llave la sesión de WhatsApp guardada (nadie que vea la base de datos puede usarla). | Otra contraseña **distinta**, de **mínimo 32 caracteres**. **No se cambia nunca** una vez puesta (si se pierde o se cambia mal, hay que volver a escanear el QR). Guárdala en tu gestor. |
| `TELEGRAM_BOT_TOKEN_JUAN` | *(Opcional)* El bot de Telegram que te avisa. | El que te da BotFather. |
| `ALERTA_TELEGRAM_CHAT` | *(Opcional)* Tu chat de Telegram, a donde llegan los avisos. | El número de tu chat. También sirve con el nombre que usa el Worker `juan`, `ALERTA_TELEGRAM_CHAT_ID`: con uno de los dos basta. |

Mientras falten los dos primeros, **el puente no hace nada peligroso**: no enciende el contenedor, no intenta
conectar WhatsApp y, si le preguntas cómo está, contesta «sin configurar» y **solo los nombres** de lo que
falta. Cuando los pones, empieza solo (en un minuto).

> Al desplegar nuevas versiones **nunca se borran** los secretos que pusiste en el panel.

## 3. Enlazar el número con el código QR

Hazlo **solo cuando hayas decidido el número** y con el asistente ya probado.

1. En el teléfono del negocio: **WhatsApp → Ajustes → Dispositivos vinculados → Vincular un dispositivo**.
2. Pide el código QR (en Odoo, cuando esa pantalla esté lista; mientras tanto lo pide quien opera, apéndice A).
3. Apunta la cámara del teléfono al código. **El código vence a los 45 segundos**: si el teléfono dice
   «Revisa tu conexión y vuelve a intentarlo», casi seguro el código ya estaba vencido; pide uno nuevo
   y escanea enseguida.
4. En unos segundos el estado pasa a **conectado**. Entonces en la lista de dispositivos del teléfono verás
   uno llamado **DCASA Panama**.
5. **La prueba que de verdad cuenta:** desde **otro** teléfono, escríbele al número. El asistente tiene que
   contestar. Pídele también una foto del catálogo: tiene que llegar la imagen. (Si solo miras que diga
   «conectado», puede pasar que el aparato haya quedado a medio instalar. Quien opera comprueba además que
   `instalacionCompleta` sea `true`, apéndice A.)

Una vez vinculado **no vuelve a pedir el código**, aunque se reinicie todo: la sesión queda guardada,
cifrada, dentro del propio sistema.

## 4. Cómo saber cómo está

El estado tiene cinco posibilidades:

| Estado | Qué significa | Qué haces |
|---|---|---|
| **conectado** | Todo bien. | Nada. |
| **necesita QR** | Nunca se vinculó, o se desvinculó desde el teléfono. | Escanear un código nuevo (sección 3). |
| **desconectado desde hace N min** | Estaba vinculado y se cayó la conexión. Se reintenta solo. | Esperar unos minutos; si pasa de 10, te llega el aviso de Telegram. |
| **desconectado**, con `ocupado: true` | Volvió de un corte y está **procesando lo que se acumuló** (no contesta todavía, pero avanza). | **Nada, y no lo reinicies**: lo cortarías a la mitad. Se le deja terminar. |
| **apagado** | El interruptor `PUENTE_ACTIVO` no está en «on». | Solo si lo apagaste tú a propósito. |
| **sin configurar** | Faltan secretos (se listan por nombre). | Sección 2. |

## 5. Lo que el puente hace por ti

- **Responde con ritmo humano:** muestra «escribiendo…», marca el mensaje como leído, deja **al menos 1
  segundo entre burbujas** y un poco más al azar. No contesta nunca a grupos ni a estados.
- **Lo atrasado reciente sí se contesta; lo viejo no:** lo que un cliente escribió mientras el puente estaba
  desconectado se contesta si tiene **15 minutos o menos** (un corte corto ya no deja a nadie sin respuesta). Lo más
  viejo no se contesta solo —sería responder tarde y quizá encima de lo que tú ya contestaste desde el teléfono—: se
  cuenta, y **te llega un aviso** con cuántas conversaciones quedaron para contestar a mano. El historial viejo de
  WhatsApp ni se descarga.
- **Si Juan (el asistente) está caído un rato,** los mensajes de los clientes **no se pierden**: se guardan
  (cifrados, hasta 48 horas) y se entregan en cuanto vuelva.
- **Cuando escribes tú desde el teléfono,** el asistente se entera y deja de contestar esa conversación.
- **Copia de seguridad diaria** de la sesión (cifrada), 7 días.
- **Se limpia solo:** las llaves de un solo uso (pre-keys) que se acumulan se podan solas cuando pasan de 2.000 (una
  vez por semana), dejando las 1.000 más nuevas, con respaldo de 14 días y **sin tocar la vinculación** (no hay que
  volver a escanear el QR).
- **Te avisa por Telegram** si WhatsApp lleva 10 minutos desconectado (y cuando vuelve), y además:
  - si lleva 15 minutos **solo reponiendo llaves sin procesar ningún mensaje** (la señal exacta de la caída del 24-nov);
  - si en **horario de atención** (lunes a sábado, 9:00–18:00) pasa **una hora sin que entre ningún mensaje**;
  - si se **reinicia o reconecta en bucle** (muchas veces en una hora);
  - al volver de una caída, **cuántas conversaciones quedaron con mensajes atrasados sin contestar**.

## 6. Cómo bajar el riesgo de bloqueo

Lo que más delata a un bot no es lo que dice, sino **cómo** escribe. Ya está puesto:

- **Topes de envío** (se pueden bajar, no conviene subirlos): 10 mensajes por minuto, 400 por día, 30 por
  hora a una misma persona, y **15 personas nuevas por día** (gente que nunca te escribió).
- **El asistente solo contesta** a quien escribe. Los seguimientos son los dos que tú decidiste (a las 5 horas
  y a los 5 días), nunca campañas masivas.

Lo que **te toca a ti**:

- Usa un número **con historia** (de uso real desde hace tiempo), no una línea recién comprada.
- **Pide a la gente que guarde el número** en sus contactos. Los números que muchos guardan y con los que
  se conversa van menos al bloqueo.
- **No envíes mensajes masivos** ni listas de difusión desde ese número, ni por el teléfono.
- Activa la **verificación en dos pasos** de WhatsApp en ese número.
- Mantén el teléfono con batería e internet y **ábrelo al menos una vez cada pocos días**.
- No vincules y desvincules muchas veces seguidas.
- Si alguien reporta o bloquea al número, o WhatsApp muestra un aviso de «actividad inusual», **para** (ver
  sección 7) antes de que se agrave.
- Ten el **plan B** (sección 8) preparado de antemano, no el día del bloqueo.

## 7. Si WhatsApp lo desconecta

| Qué ves | Qué hacer |
|---|---|
| «Desconectado hace 2 o 3 min» | Nada: se reconecta solo. Si no lo logra y **no avanza nada**, lo reinicia solo a los 10 minutos (y si eso no lo arregla, espera cada vez más entre un reinicio y otro: 20, 40, 60 min). |
| Aviso de Telegram: «lleva 10 min sin conexión» | Mira el estado. Pide a quien opera que lo **reinicie** (apéndice A, no pide QR). Revisa que el teléfono del negocio tenga internet. |
| Aviso: «sin contestar a clientas, pero está trabajando» | **No lo reinicies.** Está procesando lo que se acumuló; el sistema lo deja terminar. Si pasa una hora así, mira «Si WhatsApp se atasca» (abajo). |
| Aviso: «solo reponiendo llaves de seguridad (pre-keys)» | Es la firma de la caída del 24-nov. Mira «Si WhatsApp se atasca» (abajo). |
| Aviso: «no entra ningún mensaje desde hace N min» | Escríbele al número **desde otro teléfono**: si el asistente contesta, era un rato tranquilo. Si no contesta, pide a quien opera que mire `/api/estado`. |
| Aviso: «se reinició N veces en la última hora» | Algo lo tumba en bucle. Pide a quien opera que mire `/api/estado` (memoria y procesador). Si dice código 137 y la memoria cerca de 256 MB, el contenedor se está quedando chico (apartado G). |
| Aviso: «llegaron N mensajes atrasados de M conversaciones» | Contéstalas **a mano** desde el teléfono: el asistente no contesta lo que llevaba más de 15 min esperando. |
| **«Necesita QR»** o en el teléfono ya no aparece el dispositivo «DCASA Panama» | La vinculación se perdió (la quitaron desde el teléfono, o WhatsApp la cerró). Escanea un código nuevo (sección 3). Hasta entonces el asistente no contesta por WhatsApp. |
| Se desvincula **seguido** | No sigas reintentando: puede ser una señal de WhatsApp. Para y mira la sección 8. |
| WhatsApp **avisa o restringe** el número | **Para de inmediato:** borra el secreto `WA_TOKEN` en el panel de Cloudflare (el puente apaga el contenedor en un minuto; nada se borra y se puede reanudar). Sigue atendiendo desde el teléfono con normalidad y pasa al plan B. |
| Se perdió o se dañó la sesión guardada | Se restaura desde la copia diaria (apéndice B). Si no se puede, escanear un QR nuevo. |

El aviso de Telegram nunca lleva el código QR, contraseñas ni números de clientes; solo te dice qué pasa y dónde mirar.

### Si WhatsApp se atasca

Lo que pasó en el CRM de Baby Caleb el 24-nov-2026, y lo que hace este puente para que no se repita:

1. **Lo normal al volver de un corte es que tarde.** WhatsApp entrega de golpe todo lo acumulado y el puente lo procesa
   de a poco. Mientras haya **progreso** (se escriben llaves de sesión o entran mensajes), el sistema **no lo toca**: ni
   le pide reconectar ni lo reinicia, aunque no conteste. Por eso **no lo reinicies a mano** en ese momento.
2. **Si lleva 15 minutos solo «reponiendo pre-keys»** (te llega ese aviso), está dando vueltas sin procesar nada. El
   sistema espera media hora más; si sigue igual y hay más de 2.000 pre-keys guardadas, **las limpia solo**: deja las
   1.000 más nuevas, guarda lo borrado 14 días y **no toca la vinculación** (no hay que escanear el QR). Te avisa cuando
   lo hace. Fue lo que destrabó el CRM de origen.
3. **Si aun así no vuelve**, quien opera puede limpiar a mano (`POST /api/podar`, mismo respaldo) y, si algo sale mal,
   devolver lo podado (`POST /api/podar/deshacer`). Ver apéndice A.
4. **Si se cae en bucle con el código 137** y la memoria estaba cerca de 256 MB, el contenedor `lite` se quedó chico:
   es una decisión de dinero (apartado G).
5. Al volver, revisa el aviso de **mensajes atrasados**: esas conversaciones hay que contestarlas a mano.

## 8. «Coexistencia» y el plan B (la API oficial de Meta)

**La alternativa oficial** se llama *WhatsApp Cloud API*: Meta te da un acceso aprobado y el número está a
salvo. Cuesta poco: responder a un cliente dentro de las 24 horas de su último mensaje es gratis; escribir
primero o después de las 24 horas exige **plantillas aprobadas** que Meta cobra por mensaje (unos centavos).
Hay trámites con Meta (verificar el negocio con el RUC), y Meta ve que la atención es automatizada (lo
correcto: el asistente ya se presenta como automático y ofrece una persona).

**«Coexistencia»** es la forma de usar la API oficial **sin dejar de usar el teléfono**: el mismo número
queda a la vez en la app **WhatsApp Business** del teléfono y en la API. Tú y tus vendedoras siguen
contestando desde el teléfono y el asistente atiende por la API. Condiciones, según lo que leímos (no pudimos
abrir las páginas oficiales de Meta desde aquí: **confírmalas el día que decidas**):

- El número tiene que estar en la app **WhatsApp Business** (no en el WhatsApp normal).
- Hay que abrir la app en el teléfono **al menos cada 14 días** o se pausa el enlace.
- No sincroniza grupos ni mensajes temporales.

**Cuándo conviene pasar a la API oficial:**

- WhatsApp avisó, restringió o bloqueó el número, o se desvincula seguido sin explicación.
- El número de ventas se volvió demasiado importante para arriesgarlo (perderlo es perder el teléfono de la tienda).
- Quieres escribirle primero a muchos clientes (campañas, recordatorios): por QR eso es lo que más riesgo da.
- WhatsApp cambia su protocolo y el puente se rompe más de lo razonable.

El asistente **ya tenía el adaptador de la API oficial preparado** como plan B, y así se hizo: desde el 2026-11-02
WhatsApp va por la API oficial ([JUAN_CANALES.md](JUAN_CANALES.md)) y el puente nunca se encendió.

> Recomendación honesta de la auditoría (docs/auditoria/ronda7/crm-whatsapp.md): para **el número de
> ventas**, lo más seguro es la API oficial con coexistencia; el QR queda mejor sobre **un segundo número**
> o como respaldo. La decisión de usarlo igual es tuya y ya la tomaste sabiéndolo.

**Lo que confirmó la caída del 24-nov-2026 (CRM de Baby Caleb).** Ese CRM tiene **dos** canales de WhatsApp: el QR se
cayó 14 horas; otro CRM del mismo dueño, conectado por la **API oficial**, atendió a casi 6.000 clientes y **nunca** se
ha caído. No es suerte, es otra forma de conectarse:

| | WhatsApp por QR (este puente) | API oficial de Meta |
|---|---|---|
| ¿Quién sostiene la conexión 24/7? | Nosotros (un contenedor) | Meta; nosotros solo recibimos avisos |
| ¿Quién guarda las llaves de cifrado? | Nosotros: miles, y crecen | Meta |
| Si el sistema se cae un rato | Al volver le llega todo de golpe | Meta reintenta cada mensaje por separado |
| ¿Algo crece sin control? | Sí (llaves por contacto, pre-keys) | No |
| Riesgo de bloqueo del número | Sí, sube con el volumen | No, si se respetan las reglas de Meta |

**Recomendación:** la **API oficial como canal principal** (es lo que ya usa D'CASA desde el 2026-11-02); el QR, **solo
de respaldo** o sobre un segundo número. Con mucho volumen, el QR no: todo lo que causó esa caída crece con el volumen,
y el riesgo de bloqueo también. Con la API oficial lo que se vigila es otra cosa (el costo de la IA, las plantillas que
Meta cobra, la calidad del número y no procesar dos veces el mismo aviso de Meta); está en [JUAN_CANALES.md](JUAN_CANALES.md).

## 9. Qué guarda el puente y qué no

- **Guarda**, cifrada, la sesión de WhatsApp (lo que evita escanear el QR cada vez) y sus copias de 7 días.
- **No guarda** los mensajes ni los archivos de los clientes: pasan directo al asistente. La única excepción
  son los mensajes que el asistente no pudo recibir, que esperan cifrados hasta 48 horas.
- **En los registros del sistema nunca** aparece el QR, una contraseña, un texto de cliente ni un número de
  teléfono completo (solo los últimos 4 dígitos).
- Los archivos que **recibimos** de clientes tienen tope de tamaño (fotos y audios hasta 10 MB, documentos y
  videos hasta 12 MB); si uno pasa, el asistente igual recibe el mensaje y sabe que había un archivo.
- Una foto de comprobante de pago o de identidad **no la ve la IA**: se anota para una vendedora (regla del
  asistente, docs/JUAN.md).

## 10. Cuánto cuesta

El contenedor del puente encendido todo el mes se midió en el CRM de origen en **≈ $1.50 a $2.00 al mes**,
dentro del plan de Cloudflare que ya pagas. (La alarma que lo vigila cada 30 segundos no se ha medido aún;
se mirará a las 24 horas del primer despliegue.) La copia en R2 está apagada: si la enciendes, es otro recurso
(centavos). Un contenedor más grande (`basic`) costaría **≈ $7 al mes**; ver el apartado G antes de decidirlo.

Los arreglos del 24-nov (vigilante paciente, avisos, autolimpieza, métricas) **no cuestan nada**: corren dentro de lo
mismo que ya existe (unas filas más en la base del propio puente).

## 11. Decisiones que te tocan

1. **El número** que se vincula (tú lo decides al final). Recomendación: no el de ventas +507 6026-1919 si
   puedes evitarlo (sección 8).
2. ¿Quieres el **aviso por Telegram**? Necesita `TELEGRAM_BOT_TOKEN_JUAN` y `ALERTA_TELEGRAM_CHAT`.
3. ¿Quieres una **segunda copia de la sesión en R2**, fuera del sistema (protege si se borra el Worker por
   error)? Está apagada. Encenderla es un cambio pequeño de configuración y un bucket nuevo.
4. ¿Cuándo pasar al **plan B**? (sección 8).
5. **Las decisiones de infraestructura** que dejó la caída del 24-nov (contenedor más grande, forma nueva de pedir
   contenedores, una cola entre el puente y Juan): apartado G, con su costo.
6. **El horario de atención y la hora sin mensajes** del aviso «no entra ningún mensaje» (hoy: lunes a sábado,
   9:00–18:00, el que publica la web de Baby Caleb; 60 minutos). Se cambian en `puente-wa/wrangler.jsonc`.

---

# Apéndice para quien opera (técnico)

Todo con `WA_TOKEN` (**del gestor de contraseñas, no del chat**) en la variable `WA_TOKEN` de tu terminal:
`export WA_TOKEN='…'` y `PUENTE=https://dcasa-puente-wa.dcasapty.workers.dev` (o el de staging). El token va
siempre en la cabecera `Authorization: Bearer`; **nunca en la URL** (no se acepta).

## A. Rutas (todas con token salvo `/health`)

| Ruta | Para qué |
|---|---|
| `GET /health` | «ok». Sin token. |
| `GET /api/estado` | `estado` (`conectado` · `necesita_qr` · `desconectado` · `iniciando` · `apagado` · `sin_configurar`), `conectado`, `ocupado` (sin conexión pero avanzando: no reiniciar), `desconectado_min`/`desconectado_desde`, la sesión (`vinculado`, `instalacionCompleta`, `siguiente`, `sinSubir`, `preKeys`…), contadores, cuota, copias, `pendientes`, `secretos_faltantes`. Además (2026-11-24): `contenedor.metricas` (memoria rss/heap y pico, % de CPU de un núcleo —en `lite` el techo es ~6 %—, atraso del bucle de eventos, llaves escritas por clase y mensajes en los últimos 15 min, colas, reconexiones de la última hora, minutos desde el último mensaje), `contenedor.sincronizando`/`intentoEnCurso`/`ultimaReconexion` (atrasados atendidos y sin contestar), `ultimas_metricas` (la última lectura, aunque el contenedor ya no conteste), `actividad` (lo que escribió la sesión: últimos 15 min y hora por hora de las últimas 24 h; si una hora solo tiene `preKeysNuevas`, estaba en bucle), `paciencia` (gracia, reinicios seguidos, cuánto falta para el próximo martillo), `alarmas` y `poda` (respaldo y última poda). Sin `WA_TOKEN` configurado responde igual, sin token, pero solo con los **nombres** que faltan. |
| `GET /api/qr` | El QR como imagen (`data:image/png;base64,…`) mientras sirve (<45 s); `null` si ya está conectado. Sin caché. Nunca se imprime en registros. |
| `POST /api/foto-perfil` | `{para}` (celular, jid de persona o `@lid`) → 200 `{ok, mime, base64}` con la foto pequeña de WhatsApp (`profilePictureUrl(jid,'preview')`, bajada solo de `pps.whatsapp.net` / `mmg.whatsapp.net`, hasta 300 KB); 404 si no tiene foto o no la deja ver (lo normal); 400 destino inválido (grupos y estados nunca); 409 sin conexión; 502 la descarga falló. No escribe nada ni cuenta para los topes de envío. |
| `POST /api/enviar` | `{para, chunks:[…], medios?:[{tipo:"imagen\|documento", url, nombre?, mime?, pie?}]}`. Respuestas: 200 `{ok, id_mensaje, ids, enviados}`; 400 cuerpo inválido; 409 sin conexión; 422 medio rechazado; 429 tope (`Retry-After`); 502 falla (con `parcial` e `ids` de lo que sí salió); 503 apagado o cola llena. |
| `POST /api/reiniciar` | Destruye y levanta el contenedor (**no pide QR**). Tras desplegar una imagen nueva, úsalo para que la tome. |
| `POST /api/desvincular` | Cierra la sesión en WhatsApp y la borra: pedirá QR. |
| `GET/POST /api/copias` · `GET /api/copias/exportar?id=` | Listar · sacar una copia ahora · bajar una copia (cifrada) como archivo. |
| `POST /api/restaurar` | Ver B. |
| `POST /api/podar` · `POST /api/podar/deshacer` | Podar pre-keys a mano: deja las **1.000 de número más alto**, guarda lo borrado (cifrado) 14 días y **nunca toca `creds`** · devolver a la sesión las de la última poda. La poda también corre sola (`puente-wa/src/poda.ts`): una vez por semana si hay más de 2.000 y el canal está sano, o de emergencia (una vez al día) tras 30 min de la alarma «solo pre-keys». |
| `POST /api/recifrar` | Recifrar con la clave nueva (C). |
| `/puente/*` | Solo del contenedor, con **su** token (derivado del `WA_TOKEN` por HMAC). Con `WA_TOKEN` no se abren, y con el del contenedor no se abre `/api/*`. |

Variables (en `puente-wa/wrangler.jsonc`): `PUENTE_ACTIVO`, `PUENTE_BASE_URL`, `MEDIOS_HOSTS_PERMITIDOS`
(dominios de los que se descargan medios: por defecto `dcasapty.com` y `dcasapty.workers.dev`),
`LIMITE_POR_MINUTO`, `LIMITE_POR_DIA`, `LIMITE_POR_DESTINATARIO_HORA`, `LIMITE_FRIOS_DIA`, `ALERTA_MINUTOS`,
`ALERTA_REAVISO_MINUTOS`, `ALERTA_SIN_MENSAJES_MINUTOS` (0 = sin ese aviso), `HORARIO_INICIO`/`HORARIO_FIN` («HH:MM»),
`HORARIO_DIAS` (0 = domingo … 6 = sábado), `HORARIO_ZONA` (IANA; si el horario no tiene la forma correcta, el aviso
«sin mensajes» se apaga solo), `COPIA_R2`. El mínimo entre burbujas (1 s) no baja de eso aunque se configure menos.
El chat de Telegram de los avisos puede llamarse `ALERTA_TELEGRAM_CHAT` (el del puente) o `ALERTA_TELEGRAM_CHAT_ID` (el
nombre que usa el Worker `juan`): con el mismo valor en los dos Workers basta. **Ningún secreto nuevo.**

Los umbrales del vigilante paciente están en `puente-wa/src/comun.ts` (con el porqué de cada uno): 10 min de gracia tras
cada arranque, 5 min de vigencia de un progreso, martillo a los 10 min sin conexión ni progreso (20, 40, 60 si se
repite), «ocupado» creíble hasta 60 min, y 20 s de tope para el `/estado` de la vigilancia (no contestar no es morir). En
el contenedor (`contenedor/nucleo.mjs`): 2 min para cada intento de conexión vivo (`GRACIA_INTENTO_MS`), tandas de 25
mensajes (`LOTE_ENTRANTES`). Lo atrasado que se contesta: 15 min (`ATRASADO_VIGENTE_MS`, `lib/propios.mjs`).

Cómo Juan debe usarlo (contrato, docs/JUAN.md): el celular va en E.164 sin «+» (`50760261919`); también se
aceptan `6026-1919`, `+507 6026 1919`, `00507…` y un jid. **Grupos, estados y canales se rechazan siempre.**
Se manda primero el texto y después los medios (cada imagen con su pie). Las imágenes y documentos los
**descarga el puente** (solo `https`, solo de los dominios permitidos, direcciones públicas, redirecciones
vigiladas, tipo y tamaño comprobados con el contenido real) y se envían ya descargados.

## B. Copias y restauración de la sesión

La sesión (`creds` y llaves de Signal) vive en el SQLite del Durable Object, **cifrada con `WA_SESION_CLAVE`**
(AES-GCM). Copias:

1. **Dentro del Durable Object**, siempre: una al vincular y luego **diaria**, 7 conservadas.
2. **R2, opcional y apagada** (`COPIA_R2` = «on» + bucket `COPIAS` enlazado en `wrangler.jsonc`). El código
   **no borra** objetos de R2: la retención se pone con una regla de ciclo de vida del bucket.
3. **A mano:** `curl -H "Authorization: Bearer $WA_TOKEN" "$PUENTE/api/copias/exportar" > sesion.json`
   (cifrada). **Guarda la copia y `WA_SESION_CLAVE` en lugares distintos**: la una sin la otra no sirve.

Restaurar (cuando la sesión se dañó pero WhatsApp no la desvinculó):

```
curl -s -H "Authorization: Bearer $WA_TOKEN" "$PUENTE/api/copias"                       # ver las copias
curl -s -X POST -H "Authorization: Bearer $WA_TOKEN" "$PUENTE/api/restaurar" \
     -d '{"copia":"2026-10-09T03-17-00Z"}'                                               # sin «copia»: la más reciente
# o desde un archivo exportado:  -d '{"archivo": <contenido de sesion.json>}'
# o desde R2:                    -d '{"origen":"r2","copia":"2026-10-09T03-17-00Z"}'
```

El puente apaga el contenedor, guarda lo que había como una copia más, comprueba que la copia se descifra con
la clave actual (si no, **no toca nada** y responde 422), la restaura de forma atómica y levanta el
contenedor con una **época nueva**. Si WhatsApp ya desvinculó el dispositivo desde el teléfono, ninguna copia
sirve: hay que escanear un QR nuevo. Si se pierde `WA_SESION_CLAVE`, las copias son inservibles.

## C. Rotar secretos

- **`WA_TOKEN`:** cámbialo en **los dos** Workers (puente y `juan`). El puente nota el cambio y reinicia solo
  el contenedor para que tome el token derivado nuevo (la sesión no se pierde). Habrá unos segundos de 401
  entre un cambio y el otro.
- **`WA_SESION_CLAVE`** (casi nunca): (1) pon la clave vieja en `WA_SESION_CLAVE_ANTERIOR` y la nueva en
  `WA_SESION_CLAVE`; (2) `POST /api/recifrar`; (3) `POST /api/copias` (las copias anteriores siguen cifradas
  con la clave vieja); (4) cuando ya no necesites las copias viejas, borra `WA_SESION_CLAVE_ANTERIOR`.

## D. Un solo escritor

Dos programas escribiendo la misma sesión de Signal la corrompen. Hay cuatro candados: `max_instances = 1`;
un único Durable Object (`idFromName("unico")`); una **cola** en el contenedor que manda de una petición a la
vez (así tampoco se entrelazan las burbujas de dos clientes); y una **época** que sube con cada arranque del
contenedor y que viaja en cada escritura: un contenedor «zombi» de una época anterior recibe 409 y no escribe.

## E. Despliegue (workflow manual)

`.github/workflows/desplegar-puente.yml` (Actions → *Desplegar puente de WhatsApp*), **solo a mano**:
`entorno` (staging / production) y `accion` (**dry-run** por defecto / desplegar). El ensayo corre tipos,
pruebas, la configuración de Wrangler de los dos entornos y construye la imagen, sin tocar Cloudflare. Para
desplegar usa **solo** `CLOUDFLARE_API_TOKEN` y `CLOUDFLARE_ACCOUNT_ID` (con permiso *Cloudflare Images: Edit*
para subir la imagen); no lee ni sube secretos del puente, y el primer despliegue sale bien sin ellos.
Comprueba antes que exista el Worker `dcasa-juan` (producción) o `dcasa-juan-staging` (staging), porque el
puente lo enlaza por service binding y Cloudflare no despliega un enlace a un Worker que no existe.
**Orden:** `juan` primero, puente después, secretos en el panel al final. Wrangler va **fijado** por el
`package-lock.json` (una versión nueva rompió el despliegue del CRM de origen sin que nadie tocara nada).
**Staging** (`dcasa-puente-wa-staging`) tiene su propia sesión y su propio contenedor: vincúlale siempre un
número de **pruebas**, nunca el del negocio, y nunca el mismo número en los dos entornos (se expulsarían).

## F. Tropiezos que ya pagó el CRM de Baby Caleb, y dónde quedaron cubiertos

| Tropiezo | Cómo queda cubierto aquí |
|---|---|
| El contenedor vive mientras vive su Durable Object (una noche muda) | El DO extiende `Container`, vigila por `schedule()` cada 30 s sin retroceso y renueva la actividad; **un cron cada minuto** revive la cadena si se cortó. Un solo dueño programa. |
| Un fallo al reconectar cortaba la cadena para siempre | `programarReconexion` encadena siempre el siguiente intento; el vigilante interno rescata sockets «zombi». |
| Dos sockets sobre el mismo número se expulsan | `cerrarAnterior()` + generaciones, `max_instances = 1`, época. |
| Vinculaba y se caía a los segundos (812 llaves en <30 s) | Almacén **por lotes**: una petición lleva todo el lote; probado con 812 llaves. `instalacionCompleta` (`sinSubir == siguiente`) es la señal que de verdad dice «terminó de instalarse». |
| 401 «mudo» por un token con caracteres fuera de ASCII | `WA_TOKEN` se exige ASCII (se reporta en `/api/estado`); el token del contenedor es hexadecimal. |
| Error 1042 al llamar Worker a Worker por URL pública | Todo por **service binding** (`JUAN`). |
| El bot contestaba encima de la dueña | Cada envío anota su id **antes** de enviar; un mensaje propio no anotado = persona → `propio:true`. Los ids se recuerdan 2 h en el DO (sobreviven a reinicios). |
| Conversaciones fantasma por estados/grupos | `esChatDeUnaPersona` al entrar y al salir. |
| Notas de voz y fotos llegaban vacías | Se descargan en el momento y viajan en base64; si no se puede, se dice (`medio_omitido`). |
| `unhandledRejection` mataba Node 22 | Capturado en `servidor.mjs`. |
| QR vencido → «revisa tu conexión» | El QR se sirve solo si tiene menos de 45 s y nunca con la sesión conectada. |
| `npx wrangler@4` rompió el despliegue | Wrangler fijado en el lock; el workflow usa `npm ci`. |
| Una prueba que pasa no dice que el sistema funcione | Prueba de punta a punta (`test/integracion.test.ts`) y el estado muestra `instalacionCompleta`. |
| **24-nov-2026: 14 h en bucle al volver de un corte** (vigilante impaciente + avalancha de lo atrasado + 15.934 pre-keys en un `lite`) | Vigilante paciente, reconexión liviana, autolimpieza de pre-keys, avisos y métricas: detalle en la tabla de abajo. Prueba de carga: `test/carga.test.ts`. |
| Lo que llegaba mientras el puente estaba desconectado se tiraba entero | Baileys 7 lo entrega como `append`; antes todo `append` era «historial». Ahora lo de ≤ 15 min se contesta y lo más viejo se cuenta y se avisa (`lib/propios.mjs`). |

### Auditoría contra el informe de la caída del 24-nov-2026

Cada recomendación del informe del CRM de Baby Caleb, contra este puente (rutas dentro de `puente-wa/`):

| Recomendación del informe | Antes | Ahora | Dónde |
|---|---|---|---|
| Gracia tras cada arranque | **Faltaba** (reconectar desde la 1.ª vigilancia) | 10 min sin pedir reconectar ni destruir | `src/comun.ts` (`GRACIA_TRAS_ARRANQUE_MS`), `src/vigilancia.ts` (`aplicarVigilancia`) |
| No pedir reconectar mientras conecta | **Faltaba**: `/reconectar` cortaba el intento en curso; el vigilante interno lo reciclaba a los 30 s | `/reconectar` respeta un intento vivo; el intento vivo tiene 2 min; el DO no lo pide si el contenedor dice `intentoEnCurso` | `contenedor/nucleo.mjs` (`GRACIA_INTENTO_MS`, `intentoEnCurso`, ruta `/reconectar`), `src/vigilancia.ts` |
| No matarlo solo porque tarda en contestar | **Faltaba**: se destruía a la 5.ª vigilancia sin conexión (≈2,5 min), avanzara o no | Solo tras 10 min sin conexión **ni progreso** (llaves de tráfico o mensajes, vistos en el DO), y cada reinicio seguido espera el doble (20, 40, 60). Sin respuesta pero con progreso = «ocupado». El `/estado` de la vigilancia espera 20 s (no 4) y no contestar no es morir | `src/comun.ts`, `src/vigilancia.ts`, `src/puente-do.ts` (`vigilar`, `#estadoDelContenedor`), `src/almacen.ts` (`wa_actividad`) |
| No procesar historial viejo | **A medias**: `syncFullHistory: false`, pero Baileys igual bajaba el historial «RECENT» | Solo se baja lo chico y necesario (arranque inicial con los mapas de LID, nombres) | `contenedor/lib/historial.mjs`, `contenedor/nucleo.mjs` (`shouldSyncHistoryMessage`) |
| Atender los mensajes de a pocos | **A medias**: entrega a Juan de uno en uno (fila), pero un paquete grande se recorría de un tirón | Tandas de 25 cediendo el turno; caché de llaves de Baileys (menos viajes al Worker por mensaje) | `contenedor/nucleo.mjs` (`LOTE_ENTRANTES`, `alLlegarMensajes`, `makeCacheableSignalKeyStore`) |
| Descargar fotos y audios en fila | **Ya cubierto** (fila de entrantes, una a la vez) | Igual, ahora con prueba que lo exige | `contenedor/nucleo.mjs` (`colaEntrantes`), `test/nucleo.test.ts`, `test/carga.test.ts` |
| Limpieza automática de pre-keys (~1.000, con respaldo) | **A medias**: solo a mano (`/api/podar`), sin respaldo, y elegía «las más nuevas» por fecha | Automática (semanal con el canal sano si hay > 2.000; de emergencia tras 30 min de «solo pre-keys»), por **número**, con respaldo de 14 días y `POST /api/podar/deshacer`; nunca toca `creds` | `src/poda.ts`, `src/almacen.ts` (`podarPreKeys`, `wa_prekeys_podadas`), `src/router.ts` |
| Alarma «solo se escriben pre-keys» | **Faltaba** | 3 ráfagas en 15 min sin tráfico ni mensajes → aviso; avisa también cuando se recupera | `contenedor/lib/llaves.mjs`, `src/alarmas.ts`, `src/puente-do.ts` (`#anotarLlaves`) |
| Alarma «no entra ningún mensaje» en horario | **Faltaba** | 60 min sin mensajes de clientas, lunes a sábado 9:00–18:00 (Panamá), contados desde la apertura | `src/alarmas.ts`, `wrangler.jsonc` (`HORARIO_*`, `ALERTA_SIN_MENSAJES_MINUTOS`) |
| (Extra) Reconexiones en bucle | **Faltaba** | 4 arranques o 6 reconexiones en una hora → aviso con el código de salida y el pico de memoria | `src/alarmas.ts`, `src/puente-do.ts` (`onStart`, `onStop`) |
| Memoria y procesador en `/estado` | **Faltaba** (por eso no se supo si el 137 era memoria) | rss/heap y pico, % de CPU, freno por cgroup, atraso del bucle; la última lectura queda en el diario y sale en el log al morir | `contenedor/lib/metricas.mjs`, `contenedor/servidor.mjs`, `src/puente-do.ts` (`ultimas_metricas`, `onStop`) |
| Avisar por Telegram | **Ya cubierto** (el mismo bot de Juan, `TELEGRAM_BOT_TOKEN_JUAN`) | Se reutiliza; el chat vale también con el nombre de Juan (`ALERTA_TELEGRAM_CHAT_ID`). Ningún servicio ni secreto nuevo | `src/alertas.ts` (`chatDeAvisos`) |
| Responder a mano a quien escribió durante la caída | **Faltaba** (no había forma de saberlo) | Lo de ≤ 15 min se contesta solo; del resto llega un aviso con cuántas conversaciones | `contenedor/lib/propios.mjs` (`ATRASADO_VIGENTE_MS`), `src/alarmas.ts` (`avisoDeAtrasados`) |
| Prueba de carga antes de salir en vivo | **Faltaba** | Simulada: 6.000 atrasados + inicio de sesión lento + `/estado` colgado 45 min + bucle de pre-keys. **Pendiente** la de verdad, con WhatsApp real, en staging | `test/carga.test.ts` |
| Contenedor más grande (`basic`) | `lite` | **Sin cambiar: decide el dueño** (cuesta dinero) | apartado G |
| `scheduling_policy: "durable_object"` | `default` | **Sin cambiar**: la librería todavía no lo soporta | apartado G, comentario en `wrangler.jsonc` |
| Cola (Cloudflare Queues) entre el puente y Juan | — | **No hace falta hoy** (ya hay fila y respaldo durable); propuesta | apartado G |

Pendiente de medir en producción real: el costo de 24 horas del Durable Object con su alarma, y todo lo que
solo se ve con WhatsApp de verdad (la primera vinculación, el primer día de uso y una vuelta real de un corte largo:
cuánta memoria y CPU marca `/api/estado` en ese momento).

## G. Decisiones de infraestructura (propuestas; nada de esto está aplicado)

Cifras de la documentación de Cloudflare (noviembre de 2026; revisarlas el día que se decida). Los mínimos incluidos en
el plan de $5 (25 GiB-hora de memoria, 375 vCPU-minuto, 200 GB-hora de disco al mes) **se comparten con el contenedor de
Odoo**, así que para el puente se cuenta el precio completo.

1. **Contenedor `basic` en vez de `lite`** (¼ de procesador y 1 GiB en vez de 1/16 y 256 MiB).
   - Costo aproximado encendido 24/7: `lite` ≈ $1.64 de memoria + $0.37 de disco ≈ **$2/mes**; `basic` ≈ $6.57 +
     $0.74 ≈ **$7.30/mes** (+ CPU solo por uso real: centavos con el tráfico de hoy). Diferencia: **≈ $5.30/mes**.
   - Recomendación: **quedarse en `lite` mientras los números lo permitan** (es lo que decidió el CRM de origen tras la
     caída: el PR #41 se cerró sin publicar) y decidir con datos: si `/api/estado` muestra `rssMaximoMB` por encima de
     ~200 MB, `cpu.porcentaje` pegado al ~6 % o `bucle.retrasoP99Ms` de varios segundos al volver de un corte, o llega el
     aviso de «bucle» con código 137, pasar a `basic`. Es una línea en `wrangler.jsonc` (los dos entornos) y un despliegue.
2. **`scheduling_policy: "durable_object"`** (la forma nueva de pedir contenedores; `default` quedó obsoleta).
   - Costo: **$0**. Y como el puente **nunca se ha desplegado**, cambiarla antes del primer despliegue real no exige
     migrar nada (en una app ya creada la política es inmutable y habría que crear otra y mudar la sesión).
   - Por qué no se hizo ya: la política está **en beta**, exige declarar la imagen en `images` y pasarla (con el tamaño)
     a `ctx.container.start()`, y `@cloudflare/containers` 0.3.7 —la última publicada— no lo hace. Recomendación: hacer el
     cambio **antes del primer despliegue real**, cuando la librería lo soporte (o con un `start()` propio, probado en
     staging). Ayudaría además con el error «There is no container instance that can be provided to this Durable Object»
     que el CRM de origen vio entre reinicios con `max_instances = 1`.
3. **Una cola (Cloudflare Queues) entre el puente y Juan.**
   - Costo: con el volumen del CRM de origen (1.200–1.800 mensajes por semana, ~8.000 al mes × 3 operaciones) queda
     dentro del millón de operaciones incluido: **$0**.
   - Por qué no hace falta hoy: este puente ya tiene lo que la cola daría. Los mensajes van a Juan **de uno en uno**
     (fila en el contenedor) y, si Juan no está, quedan **guardados y cifrados hasta 48 h** y se reintentan en orden
     (`wa_pendientes`). Además, un mensaje de Queues admite 128 KB y aquí viajan fotos y documentos de hasta 12 MB: habría
     que subir los archivos a R2 y mandar solo la referencia, y cambiar el Worker `juan` para que consuma la cola. Es un
     cambio de infraestructura en dos Workers: si algún día el volumen lo pide, se propone aparte.
4. **La API oficial como canal principal** (sección 8): es la que de verdad quita este tipo de caída.
