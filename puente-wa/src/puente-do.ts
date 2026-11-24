// El Durable Object del puente: dueño del contenedor Y de la sesión.
//
// Tres trabajos:
//   1. Sostener el contenedor prendido y vigilarlo (con la lección más cara del CRM de
//      origen: el contenedor vive mientras vive su Durable Object).
//   2. Guardar la sesión de WhatsApp CIFRADA en su SQLite (el contenedor no tiene disco
//      persistente) — con UN SOLO ESCRITOR: la «época».
//   3. Aplicar el ritmo y los topes de envío, la copia diaria y el aviso por Telegram.
//
// ── Por qué esto extiende `Container` ──────────────────────────────────────
//
// El 17-sep-2026 se escuchó el Worker del CRM de origen tres minutos con el panel
// cerrado: CERO eventos. El canal no estaba degradado, estaba apagado. La causa está en
// `@cloudflare/containers`: su `alarm()` duerme dentro del manejador y al despertar se
// vuelve a armar, así que siempre hay una alarma en vuelo, y eso mantiene residente al
// Durable Object — y el contenedor vive mientras vive su DO. Un latido que hace su
// trabajo y RETORNA deja el DO sin alarma: se desaloja, y el contenedor con él.
//
// De ahí las reglas de este archivo:
//   · la vigilancia va por `schedule()`, NUNCA sobrescribiendo `alarm()`;
//   · `schedule()` AGREGA una tarea cada vez: programar tiene UN solo dueño
//     (`vigilar()`); el cron de plataforma solo revive la cadena si se cortó;
//   · sin retroceso exponencial: 30 s fijos;
//   · se renueva la actividad a mano (`renewActivityTimeout()`): al contenedor no le llega
//     ninguna petición, sostiene un socket y se queda callado.
//
// ── Un solo escritor de la sesión: la época ────────────────────────────────
//
// Dos contenedores escribiendo la misma sesión de Signal la corrompen. Hay tres
// candados: `max_instances = 1`, un único Durable Object (`idFromName("unico")`) y la
// ÉPOCA: un número que sube con cada arranque del contenedor y viaja en su entorno
// (`PUENTE_EPOCA`). Toda escritura del contenedor lleva su época; si no es la vigente
// (un contenedor «zombi» que sobrevivió a un `destroy()`), se rechaza con 409.

import type { DurableObject } from "cloudflare:workers";
import { Container } from "@cloudflare/containers";
import { avisoDeAtrasados, evaluarAlarmas, leerConfigAlarmas } from "./alarmas";
import { chatDeAvisos, enviarTelegram, evaluarAlerta, despuesDeAvisar, leerConfigAlerta } from "./alertas";
import { crearAlmacen, iniciarEsquema, type Almacen, PRE_KEYS_A_CONSERVAR } from "./almacen";
import { crearCifrador } from "./cifrado";
import { revisarConfiguracion } from "./configuracion";
import {
  GRACIA_TRAS_ARRANQUE_MS,
  PROGRESO_VIGENTE_MS,
  REINICIAR_SIN_PROGRESO_MS,
  TOPE_ESTADO_VIGILANCIA_MS,
  VIGILANCIA_S,
  derivarTokenContenedor,
  latidoVencido,
  reinicioPedido,
  veredictoDeSalud,
} from "./comun";
import { entregarAJuan } from "./juan";
import { decidirPoda, PODA_AUTOMATICA_DESDE } from "./poda";
import { armarArchivo, debeCopiar, leerArchivo, subirCopiaR2, type ArchivoDeCopia } from "./respaldo";
import type { Env, Fallo } from "./tipos";
import { aplicarVigilancia, esperaAntesDeReiniciar, normalizarDiario, resumirEstado, type Diario, type UltimasMetricas } from "./vigilancia";
import { validarEnviar } from "../contenedor/lib/contrato.mjs";
import { clasificarLlaves } from "../contenedor/lib/llaves.mjs";
import { enmascarar } from "../contenedor/lib/numeros.mjs";
import { ATRASADO_VIGENTE_MS } from "../contenedor/lib/propios.mjs";
import { evaluarCuotas, leerRitmo } from "../contenedor/lib/ritmo.mjs";
import { parsearListaHosts } from "../contenedor/lib/urls.mjs";

const PUERTO_CONTENEDOR = 8080;

/** Cuántos pendientes se intentan entregar por vigilancia. */
const PENDIENTES_POR_VIGILANCIA = 10;

const HORA_MS = 60 * 60_000;

/** Cada cuánto se limpia lo viejo (actividad de más de 48 h, respaldo de poda de más de 14 días). */
const MANTENIMIENTO_CADA_MS = HORA_MS;

/** Lo que importa de las métricas del contenedor, para guardarlo en el diario (sobrevive a su muerte). */
function resumirMetricas(m: any, ahora: number): UltimasMetricas {
  const num = (x: unknown) => (typeof x === "number" && Number.isFinite(x) ? x : null);
  return {
    en: new Date(ahora).toISOString(),
    rssMB: num(m?.memoria?.rssMB),
    rssMaximoMB: num(m?.memoria?.rssMaximoMB),
    heapUsadoMB: num(m?.memoria?.heapUsadoMB),
    cpuPorcentaje: num(m?.cpu?.porcentaje),
    retrasoBucleMs: num(m?.bucle?.retrasoP99Ms),
  };
}

function obsoleto(): Fallo {
  return {
    ok: false,
    status: 409,
    error: "Escritor obsoleto: este contenedor no es el vigente (otro arrancó después). No se escribe la sesión.",
  };
}

export class PuenteWa extends Container<Env> {
  /** El puerto donde escucha `servidor.mjs`. */
  defaultPort = PUERTO_CONTENEDOR;

  /**
   * Cuánto aguanta el contenedor sin actividad antes de que la librería lo apague.
   * Largo a propósito: su trabajo es justamente NO recibir peticiones (sostiene un socket y
   * se queda callado). Aun así no basta: `vigilar()` renueva la actividad explícitamente.
   */
  sleepAfter = "6h";

  /** Baileys tiene que salir a wss://web.whatsapp.com (y el contenedor a bajar los medios). */
  enableInternet = true;

  #almacen: Promise<Almacen> | null = null;
  #epoca = 0;
  /** ¿El contenedor ya estaba prendido cuando PEDIMOS arrancarlo? Ver `#arrancar()`. */
  #yaEstabaPrendido = false;
  #drenando = false;
  #drenajeProximo = 0;
  #drenajeFallos = 0;
  #ultimoMantenimiento = 0;

  constructor(ctx: DurableObject["ctx"], env: Env) {
    super(ctx, env);
    iniciarEsquema(ctx.storage.sql);
    this.envVars = this.#entornoDelContenedor(null);
    // La época y el token del contenedor se cargan ANTES de aceptar cualquier petición.
    ctx.blockConcurrencyWhile(async () => {
      this.#epoca = (await ctx.storage.get<number>("epoca")) ?? 0;
      await this.#refrescarEntorno();
    });
  }

  // ── Entorno del contenedor y época ───────────────────────────────────────

  #entornoDelContenedor(tokenContenedor: string | null): Record<string, string> {
    const e = this.env;
    const entorno: Record<string, string> = {
      PORT: String(PUERTO_CONTENEDOR),
      PUENTE_URL: e.PUENTE_BASE_URL ?? "",
      PUENTE_EPOCA: String(this.#epoca),
      MEDIOS_HOSTS_PERMITIDOS: e.MEDIOS_HOSTS_PERMITIDOS ?? "",
    };
    if (tokenContenedor) entorno.PUENTE_TOKEN = tokenContenedor;
    if (e.ENTRE_BURBUJAS_MS) entorno.ENTRE_BURBUJAS_MS = e.ENTRE_BURBUJAS_MS;
    return entorno;
  }

  /**
   * Deja en `this.envVars` el entorno VIGENTE. La librería lo lee en cada arranque, también
   * en los que dispara ella sola (`containerFetch` con el contenedor caído), así que siempre
   * tiene que estar al día.
   */
  async #refrescarEntorno(): Promise<void> {
    const token = this.env.WA_TOKEN ? await derivarTokenContenedor(this.env.WA_TOKEN) : null;
    this.envVars = this.#entornoDelContenedor(token);
  }

  /** Sube la época: el contenedor anterior (si sigue vivo) deja de poder escribir. */
  async #nuevaEpoca(): Promise<void> {
    this.#epoca += 1;
    await this.ctx.storage.put("epoca", this.#epoca);
    await this.#refrescarEntorno();
  }

  /** Huella (SHA-256) del token con el que arranca el contenedor; sirve para notar un cambio de WA_TOKEN. */
  async #huellaToken(): Promise<string> {
    const bytes = new TextEncoder().encode(this.envVars?.PUENTE_TOKEN ?? "");
    const h = await crypto.subtle.digest("SHA-256", bytes);
    return [...new Uint8Array(h)].map((b) => b.toString(16).padStart(2, "0")).join("");
  }

  #epocaVigente(epoca: string | null): boolean {
    return epoca !== null && Number(epoca) === this.#epoca;
  }

  /** ¿Están los secretos obligatorios (y sirven)? Sin ellos NO se enciende el contenedor. */
  #configurado(): boolean {
    return revisarConfiguracion(this.env).listo;
  }

  /**
   * ¿Debe estar encendido? Hace falta el interruptor `PUENTE_ACTIVO` Y los secretos. Sin
   * `WA_TOKEN` no hay token que darle al contenedor ni con qué atender a Juan; sin
   * `WA_SESION_CLAVE` no hay cómo guardar la sesión cifrada.
   */
  #activo(): boolean {
    return this.env.PUENTE_ACTIVO === "on" && this.#configurado();
  }

  async #alm(): Promise<Almacen> {
    if (!this.#almacen) {
      const secreto = this.env.WA_SESION_CLAVE;
      if (!secreto) throw new Error("Falta el secret WA_SESION_CLAVE.");
      const creado = crearCifrador(secreto, this.env.WA_SESION_CLAVE_ANTERIOR).then((cifrador) =>
        crearAlmacen({
          sql: this.ctx.storage.sql,
          transaccion: (fn) => this.ctx.storage.transactionSync(fn),
          cifrador,
          ahora: () => Date.now(),
        }),
      );
      // Si falla (clave corta), la siguiente llamada vuelve a intentarlo.
      creado.catch(() => {
        this.#almacen = null;
      });
      this.#almacen = creado;
    }
    return this.#almacen;
  }

  // ── Ciclo de vida ────────────────────────────────────────────────────────

  /**
   * `startAndWaitForPorts()`, pero contando arranques de verdad y subiendo la época.
   *
   * La librería llama `onStart()` al final de CADA `startAndWaitForPorts()`, sin mirar si
   * hizo falta arrancar algo: con la vigilancia cada 30 s serían 120 «arranques» por hora de
   * un contenedor que no se cayó ni una vez. Y la cuenta de arranques contra la de latidos
   * es LA señal con la que se encontró el fallo del 17-sep: una señal que sube sola no sirve.
   */
  async #arrancar(forzarEpocaNueva = false): Promise<void> {
    let corriendo = this.ctx.container?.running === true;

    // Si la dueña cambió WA_TOKEN en el panel, el contenedor vivo conserva el token viejo y todas
    // sus llamadas darían 401 (no podría ni leer su sesión). Se reconoce por la huella del token
    // con el que arrancó, y se reinicia: la sesión no se pierde, vive en el Durable Object.
    const huella = await this.#huellaToken();
    if (corriendo && !forzarEpocaNueva) {
      const guardada = await this.ctx.storage.get<string>("huellaToken");
      if (guardada && guardada !== huella) {
        console.log("WA_TOKEN cambió: se reinicia el contenedor para que tome el token nuevo");
        try {
          await this.destroy();
        } catch {
          /* ya estaba apagado */
        }
        corriendo = false;
      }
    }

    // Un arranque de verdad = época nueva ANTES de arrancar (el entorno se lee al arrancar).
    if (!corriendo || forzarEpocaNueva) {
      await this.#nuevaEpoca();
      await this.ctx.storage.put("huellaToken", huella);
    }
    this.#yaEstabaPrendido = corriendo && !forzarEpocaNueva;
    try {
      await this.startAndWaitForPorts({ ports: PUERTO_CONTENEDOR });
    } finally {
      this.#yaEstabaPrendido = false;
    }
  }

  override async onStart(): Promise<void> {
    if (this.#yaEstabaPrendido) return; // no fue un arranque, fue una comprobación
    const diario = await this.#diario();
    const ahora = Date.now();
    diario.arranquesContenedor += 1;
    diario.ultimoArranque = new Date(ahora).toISOString();
    // Los arranques de la última hora: muchos seguidos son un bucle (alarma «bucle», src/alarmas.ts).
    diario.arranquesRecientes = [...diario.arranquesRecientes.filter((t) => ahora - t < HORA_MS), ahora].slice(-50);
    await this.ctx.storage.put("diario", diario);
    console.log(`contenedor arriba (época ${this.#epoca})`);
  }

  /**
   * Por qué murió, en el diario y en el log. Durante dos horas el contenedor del CRM de
   * origen se apagó 89 veces y NADA decía por qué. Y el 24-nov-2026 murió con 137 sin que se
   * pudiera saber si fue por memoria: ahora el log lleva también la última memoria que reportó.
   */
  override async onStop({ exitCode, reason }: { exitCode: number; reason: string }): Promise<void> {
    const diario = await this.#diario();
    diario.ultimaMuerteVista = new Date().toISOString();
    diario.ultimaSalida = `código ${exitCode} · ${reason}`;
    await this.ctx.storage.put("diario", diario);
    const m = diario.ultimasMetricas;
    const memoria = m ? ` · última memoria ${m.rssMB ?? "?"} MB (pico ${m.rssMaximoMB ?? "?"} MB) a las ${m.en}` : "";
    console.log(`contenedor abajo: código ${exitCode} · ${reason}${memoria}`);
  }

  override onError(error: unknown): unknown {
    console.error("contenedor:", enmascarar(error instanceof Error ? error.message : String(error)));
    return error;
  }

  // ── La vigilancia ────────────────────────────────────────────────────────

  /**
   * El relevo del viejo `alarm()`. Lo llama `schedule()` cada 30 s y, si la cadena se
   * cortó, el cron de plataforma (`despertar()`).
   */
  async vigilar(): Promise<void> {
    // Apagado a propósito: ni contenedor ni cadena de alarmas. Se enciende con PUENTE_ACTIVO=on
    // (el cron de cada minuto lo nota).
    if (!this.#activo()) {
      await this.#apagarSiCorre();
      return;
    }

    // Primero lo que no puede faltar: la próxima vigilancia queda pedida antes de cualquier
    // cosa que pueda fallar (la lección de la noche muda, cuando `setAlarm` era la última línea).
    await this.#asegurarVigilancia();

    const ahora = Date.now();
    let falloDelLatido: string | null = null;
    try {
      // Que el contenedor esté vivo y con el puerto listo. Idempotente: si ya lo está no cuesta.
      // Si falla (p. ej. un contenedor tan ocupado que no contesta ni el ping del puerto, o Cloudflare
      // sin instancia libre), se anota y la vigilancia SIGUE: el progreso y las alarmas se miran igual.
      let falloDelArranque: string | null = null;
      try {
        await this.#arrancar();
      } catch (e) {
        falloDelArranque = enmascarar(e instanceof Error ? e.message : String(e));
        console.error("vigilancia: arranque:", falloDelArranque);
      }
      // La actividad se renueva aunque WhatsApp esté caído: se está diciendo «este contenedor
      // sigue haciendo falta», no «está sano».
      this.renewActivityTimeout();

      const alm = await this.#alm();
      // El /estado con un tope (que no deja colgada la vigilancia), pero un tope largo: no contestar
      // a tiempo NO es estar muerto. Lo que decide es si hay PROGRESO, y eso se ve en lo que la
      // sesión escribe aquí, en el Durable Object, conteste o no el contenedor.
      const delContenedor = falloDelArranque ? null : await this.#estadoDelContenedor(TOPE_ESTADO_VIGILANCIA_MS);
      const progresoEn = alm.ultimoProgresoEn(ahora - 2 * HORA_MS);
      const progresoReciente = progresoEn !== null && ahora - progresoEn < PROGRESO_VIGENTE_MS;
      const veredicto = veredictoDeSalud(delContenedor?.conexion, { progresoReciente });

      // Se lee el diario DESPUÉS de las esperas y se escribe enseguida: otras operaciones
      // (un reinicio pedido, el arranque) también lo tocan.
      const previo = await this.#diario();
      const { diario: nuevo, accion } = aplicarVigilancia(previo, veredicto, ahora, {
        progresoEn,
        conectando: delContenedor?.intentoEnCurso === true,
      });
      let diario: Diario = { ...nuevo, latidos: nuevo.latidos + 1, ultimoLatidoEn: ahora, ultimoFalloDelLatido: falloDelArranque };
      if (delContenedor?.metricas) diario.ultimasMetricas = resumirMetricas(delContenedor.metricas, ahora);

      // Aviso por Telegram. Se anota ANTES de enviar: si el envío falla no se repite cada 30 s.
      const alerta = evaluarAlerta(veredicto === "sano" ? previo : diario, veredicto, ahora, leerConfigAlerta(this.env));
      if (alerta) diario = { ...diario, ...despuesDeAvisar(diario, alerta, ahora) };

      // Las alarmas que avisan antes de que alguien note el silencio (src/alarmas.ts).
      const avisos: string[] = [];
      const cfgAlarmas = leerConfigAlarmas(this.env as unknown as Record<string, unknown>);
      const reconexiones = Number(delContenedor?.metricas?.reconexionesUltimaHora);
      const alarmas = evaluarAlarmas(
        {
          vinculado: Boolean(diario.ultimaConexionVista),
          caidaAvisada: diario.avisoActivo,
          ventana: alm.actividadDesde(ahora - cfgAlarmas.soloPreKeysMinutos * 60_000),
          ultimoEntranteEn: alm.ultimoEntranteEn(),
          arranquesUltimaHora: diario.arranquesRecientes.filter((t) => ahora - t < HORA_MS).length,
          reconexionesUltimaHora: Number.isFinite(reconexiones) ? reconexiones : null,
          ultimaSalida: diario.ultimaSalida,
          rssMaximoMB: diario.ultimasMetricas?.rssMaximoMB ?? null,
        },
        diario.alarmas,
        ahora,
        cfgAlarmas,
      );
      diario.alarmas = alarmas.estado;
      for (const a of alarmas.avisos) avisos.push(a.texto);
      const atrasados = avisoDeAtrasados(delContenedor?.ultimaReconexion, diario.atrasadosAvisadosDe, Math.round(ATRASADO_VIGENTE_MS / 60_000));
      if (atrasados) {
        avisos.push(atrasados.texto);
        diario.atrasadosAvisadosDe = String(delContenedor?.ultimaReconexion?.id);
      }

      // La autolimpieza de pre-keys (src/poda.ts): de rutina con el canal sano, o de emergencia si
      // lleva media hora en la firma del bucle. Siempre con respaldo y sin tocar `creds`.
      const mantenimiento = ahora - this.#ultimoMantenimiento >= MANTENIMIENTO_CADA_MS;
      const motivoPoda = decidirPoda({
        contarPreKeys: () => alm.contarPreKeys(),
        veredicto,
        ultimaPodaAutomaticaEn: diario.ultimaPodaAutomaticaEn,
        soloPreKeys: diario.alarmas.solo_prekeys,
        ahora,
        revisarRutina: mantenimiento,
      });
      if (motivoPoda) {
        const borradas = alm.podarPreKeys(PRE_KEYS_A_CONSERVAR);
        diario.ultimaPodaAutomaticaEn = ahora;
        diario.ultimaPoda = { en: new Date(ahora).toISOString(), borradas, motivo: motivoPoda };
        console.log(`poda automática de pre-keys (${motivoPoda}): ${borradas} al respaldo, quedan las ${PRE_KEYS_A_CONSERVAR} más nuevas`);
        if (motivoPoda === "emergencia") {
          avisos.push(
            `Para destrabar WhatsApp (el puente QR) se limpiaron ${borradas} pre-keys viejas: quedan las ${PRE_KEYS_A_CONSERVAR} ` +
              "más nuevas y lo borrado quedó respaldado 14 días (se puede deshacer). No hay que escanear el QR. Si en 15 minutos " +
              "no vuelven a entrar mensajes, revisa docs/JUAN_PUENTE.md («Si WhatsApp se atasca»).",
          );
        }
      }
      if (mantenimiento) {
        this.#ultimoMantenimiento = ahora;
        alm.podarActividad();
        const purgadas = alm.purgarRespaldoDePoda();
        if (purgadas) console.log(`respaldo de poda: ${purgadas} pre-keys de hace más de 14 días borradas del respaldo`);
      }

      if (accion === "reiniciar") diario.ultimaMuerteVista = new Date(ahora).toISOString();
      await this.ctx.storage.put("diario", diario);

      if (alerta) await this.#avisar(alerta.texto);
      for (const aviso of avisos) await this.#avisar(aviso);

      if (accion === "reiniciar") {
        // El martillo. Sale gratis en credenciales —viven en el Durable Object— y cuesta una resincronización.
        // Solo cae tras un buen rato sin conexión NI progreso (src/vigilancia.ts), y cada vez espera más.
        console.log(`el canal lleva demasiado sin conexión ni progreso: se reinicia el contenedor (reinicio seguido n.º ${diario.reiniciosSeguidos})`);
        try {
          await this.destroy();
        } catch {
          /* destruir algo que ya no existe no es un error que valga propagar */
        }
        await this.#arrancar(true);
      } else if (accion === "pedir_reconexion") {
        // Lo barato primero: pedirle que reconecte. Es idempotente.
        await this.#pedirReconexion();
      }

      if (veredicto === "sano") await this.#copiaDiaria(ahora);
      await this.#drenarPendientes();
    } catch (e) {
      falloDelLatido = enmascarar(e instanceof Error ? e.message : String(e));
      console.error("vigilancia:", falloDelLatido);
      // Aun con fallo, el latido ocurrió: el diario lo dice (y por qué falló).
      const d = await this.#diario();
      d.latidos += 1;
      d.ultimoLatidoEn = ahora;
      d.ultimoFalloDelLatido = falloDelLatido;
      await this.ctx.storage.put("diario", d).catch(() => {});
    }
  }

  /**
   * Encadena la próxima vigilancia. Nunca lanza: es la pieza que no puede faltar. ESTE es el
   * único sitio del archivo que programa: dos dueños serían dos cadenas, y las cadenas se
   * multiplican (a la hora habría sesenta vigilando en paralelo).
   */
  async #asegurarVigilancia(): Promise<void> {
    try {
      await this.schedule(VIGILANCIA_S, "vigilar");
    } catch (e) {
      console.error("no se pudo programar la vigilancia:", e);
    }
  }

  /** Lo llama el cron de cada minuto. NO vigila por su cuenta: solo revive la cadena si se cortó. */
  async despertar(): Promise<void> {
    if (!this.#activo()) {
      await this.#apagarSiCorre();
      return;
    }
    const diario = await this.#diario();
    const nuncaLatio = diario.ultimoLatidoEn === null;
    if (!nuncaLatio && !latidoVencido(diario.ultimoLatidoEn, Date.now())) return;
    console.log("el cron encontró la vigilancia detenida; la reanuda");
    await this.vigilar();
  }

  async #apagarSiCorre(): Promise<void> {
    if (this.ctx.container?.running === true) {
      console.log("el puente está apagado o sin configurar (PUENTE_ACTIVO / secretos): se apaga el contenedor");
      try {
        await this.destroy();
      } catch {
        /* ya estaba apagado */
      }
    }
  }

  async #avisar(texto: string): Promise<void> {
    const token = this.env.TELEGRAM_BOT_TOKEN_JUAN;
    const chat = chatDeAvisos(this.env);
    if (!token || !chat) {
      console.log("aviso sin enviar: faltan TELEGRAM_BOT_TOKEN_JUAN o ALERTA_TELEGRAM_CHAT");
      return;
    }
    const r = await enviarTelegram(fetch, token, chat, texto);
    if (!r.ok) console.error("aviso por Telegram:", r.motivo);
  }

  /** Copia diaria de la sesión (en el DO y, si está encendido, en R2). Un fallo se anota, no rompe nada. */
  async #copiaDiaria(ahora: number): Promise<void> {
    try {
      const alm = await this.#alm();
      const hayCreds = alm.hayCreds();
      if (!debeCopiar({ ultimaCopiaEn: alm.ultimaCopiaEn(), hayCreds, conectado: true, ahora })) return;
      // Recién vinculado, el dispositivo todavía puede estar subiendo sus llaves: una copia a medio
      // instalar no sirve. Se espera a la siguiente vigilancia (solo se descifra cuando toca copiar).
      if ((await alm.estadoSesion()).instalacionCompleta === false) return;
      const r = await this.copiarAhora();
      console.log(`copia de la sesión ${r.copia} (${r.filas} filas) · ${r.r2.motivo}`);
    } catch (e) {
      const d = await this.#diario();
      d.ultimoFalloDeCopia = enmascarar(e instanceof Error ? e.message : String(e));
      await this.ctx.storage.put("diario", d).catch(() => {});
      console.error("copia diaria:", d.ultimoFalloDeCopia);
    }
  }

  /**
   * Reintenta entregar a Juan los mensajes que no pudo recibir. En orden, y con espera
   * creciente si Juan sigue sin contestar (no se le martilla cada 30 s).
   */
  async #drenarPendientes(): Promise<void> {
    if (this.#drenando || Date.now() < this.#drenajeProximo) return;
    this.#drenando = true;
    try {
      const alm = await this.#alm();
      if (alm.contarPendientes() === 0) {
        this.#drenajeFallos = 0;
        return;
      }
      for (const p of await alm.pendientes(PENDIENTES_POR_VIGILANCIA)) {
        const r = await entregarAJuan(this.env, p.cuerpo);
        if (r.ok || (r.definitivo && [400, 413, 422].includes(r.status))) {
          alm.borrarPendiente(p.id);
          this.#drenajeFallos = 0;
          continue;
        }
        alm.fallarPendiente(p.id);
        this.#drenajeFallos += 1;
        this.#drenajeProximo = Date.now() + Math.min(30_000 * 2 ** this.#drenajeFallos, 10 * 60_000);
        break; // en orden: si el más viejo no entra, los demás tampoco
      }
    } catch (e) {
      console.error("pendientes:", enmascarar(e instanceof Error ? e.message : String(e)));
    } finally {
      this.#drenando = false;
    }
  }

  // ── Contenedor ───────────────────────────────────────────────────────────

  /**
   * Qué dice el contenedor de sí mismo. `null` si no contesta (o no contesta antes de `topeMs`).
   * No contestar se cuenta como «sin conexión», pero NO como muerto si hay progreso (ver vigilar()).
   */
  async #estadoDelContenedor(topeMs = TOPE_ESTADO_VIGILANCIA_MS): Promise<Record<string, any> | null> {
    let reloj: ReturnType<typeof setTimeout> | undefined;
    const tope = new Promise<null>((r) => {
      reloj = setTimeout(() => r(null), topeMs);
    });
    const pedido = (async () => {
      try {
        const r = await this.containerFetch("http://contenedor/estado");
        if (!r.ok) return null;
        return (await r.json()) as Record<string, any>;
      } catch {
        return null;
      }
    })();
    try {
      return await Promise.race([pedido, tope]);
    } finally {
      clearTimeout(reloj);
    }
  }

  async #pedirReconexion(): Promise<void> {
    let reloj: ReturnType<typeof setTimeout> | undefined;
    try {
      // Con tope, como el /estado: un contenedor ocupado no puede dejar colgada la vigilancia.
      await Promise.race([
        this.containerFetch("http://contenedor/reconectar", { method: "POST" }),
        new Promise((r) => {
          reloj = setTimeout(r, TOPE_ESTADO_VIGILANCIA_MS);
        }),
      ]);
    } catch (e) {
      console.error("no se pudo pedir la reconexión:", enmascarar(e instanceof Error ? e.message : String(e)));
    } finally {
      clearTimeout(reloj);
    }
  }

  async #diario(): Promise<Diario> {
    return normalizarDiario(await this.ctx.storage.get<Partial<Diario>>("diario"));
  }

  /** Para el panel y las pruebas. */
  async diario(): Promise<Diario> {
    return this.#diario();
  }

  /**
   * Lo destruye Y lo hace volver. Al volver debe reconectar con la sesión guardada, sin QR.
   * `reinicioPedido()` explica por qué se limpian esos campos.
   */
  async matar(): Promise<Diario> {
    const diario = { ...(await this.#diario()), ...reinicioPedido(new Date()) };
    await this.ctx.storage.put("diario", diario);
    try {
      await this.destroy();
    } catch {
      /* destruir algo que ya no existe no es un error que valga propagar */
    }
    if (this.#activo()) await this.#arrancar(true);
    return diario;
  }

  // ── La sesión (lo que llama el contenedor, con su época) ─────────────────

  async kvGet(clave: string): Promise<string | null> {
    return (await this.#alm()).get(clave);
  }

  async kvSet(clave: string, valor: string, epoca: string | null): Promise<{ ok: true } | Fallo> {
    if (!this.#epocaVigente(epoca)) return obsoleto();
    const alm = await this.#alm();
    await alm.set(clave, valor);
    this.#anotarLlaves(alm, [clave], []);
    return { ok: true };
  }

  async kvDel(clave: string, epoca: string | null): Promise<{ ok: true } | Fallo> {
    if (!this.#epocaVigente(epoca)) return obsoleto();
    const alm = await this.#alm();
    await alm.del(clave);
    this.#anotarLlaves(alm, [], [clave]);
    return { ok: true };
  }

  async kvLote(
    cuerpo: { leer?: string[]; escribir?: Record<string, string>; borrar?: string[] },
    epoca: string | null,
  ) {
    // Leer es inofensivo; escribir o borrar solo lo hace el escritor vigente.
    const escribe = Boolean(cuerpo.escribir && Object.keys(cuerpo.escribir).length) || Boolean(cuerpo.borrar?.length);
    if (escribe && !this.#epocaVigente(epoca)) return obsoleto();
    const alm = await this.#alm();
    const r = await alm.lote(cuerpo);
    if (escribe) this.#anotarLlaves(alm, Object.keys(cuerpo.escribir ?? {}), cuerpo.borrar ?? []);
    return r;
  }

  /**
   * Cuenta (por clase, nunca valores) lo que la sesión acaba de escribir: es la señal de progreso
   * de la vigilancia y la de la alarma «solo pre-keys». Contar nunca rompe una escritura.
   */
  #anotarLlaves(alm: Almacen, escritas: string[], borradas: string[]): void {
    try {
      const c = clasificarLlaves(escritas, borradas);
      alm.anotarActividad(
        { preKeysNuevas: c.preKeysNuevas, preKeysUsadas: c.preKeysUsadas, trafico: c.trafico, lotesSoloPreKeys: c.soloPreKeys ? 1 : 0, creds: c.creds },
        c.progreso,
      );
    } catch (e) {
      console.error("actividad:", enmascarar(e instanceof Error ? e.message : String(e)));
    }
  }

  async enviadosRecientes() {
    return (await this.#alm()).enviadosRecientes();
  }

  /** Escribió una clienta: ya no es «fría» para los topes, y es progreso (llegó un mensaje de verdad). */
  async marcarEntrante(celular: string): Promise<void> {
    const alm = await this.#alm();
    alm.marcarEntrante(celular);
    try {
      alm.anotarActividad({ entrantes: 1 }, true);
    } catch (e) {
      console.error("actividad:", enmascarar(e instanceof Error ? e.message : String(e)));
    }
  }

  async encolarPendiente(cuerpo: string): Promise<number> {
    return (await this.#alm()).encolarPendiente(cuerpo);
  }

  // ── Envío con ritmo y topes ──────────────────────────────────────────────

  async enviar(cuerpoTexto: string): Promise<{ status: number; cuerpo: unknown }> {
    if (!this.#activo()) {
      return { status: 503, cuerpo: { error: "El puente está apagado (PUENTE_ACTIVO).", estado: "apagado" } };
    }
    let crudo: unknown;
    try {
      crudo = JSON.parse(cuerpoTexto);
    } catch {
      return { status: 400, cuerpo: { error: "El cuerpo no es JSON." } };
    }
    const v = validarEnviar(crudo, { hostsPermitidos: parsearListaHosts(this.env.MEDIOS_HOSTS_PERMITIDOS) });
    if (!v.ok) return { status: v.status, cuerpo: { error: v.error } };
    const plan = v.plan;

    const alm = await this.#alm();
    const cfg = leerRitmo(this.env as unknown as Record<string, unknown>);
    const destino = plan.para.e164 ?? plan.para.jid;

    // Topes por minuto, por día, por destinatario y de «primer contacto». Si solo falta un
    // poco para que quepa en el minuto, se espera en vez de rechazar; lo demás es 429.
    const evaluar = () =>
      evaluarCuotas({
        ahora: Date.now(),
        para: destino,
        esFrio: alm.esFrio(destino),
        cantidad: plan.total,
        envios: alm.enviosRecientes(),
        cfg,
      });
    let cuota = evaluar();
    if (!cuota.ok && cuota.limite === "minuto" && cuota.reintentarEnS !== null && cuota.reintentarEnS <= cfg.esperaMaxPorMinutoS) {
      const espera = cuota.reintentarEnS;
      await new Promise((r) => setTimeout(r, espera * 1000 + 50));
      cuota = evaluar();
    }
    if (!cuota.ok) {
      return {
        status: 429,
        cuerpo: { error: `Tope de envío alcanzado: ${cuota.detalle}.`, limite: cuota.limite, reintentar_en_s: cuota.reintentarEnS },
      };
    }

    // Se reserva ANTES de enviar (dos peticiones a la vez no pasan las dos el mismo tope) y
    // se devuelve lo que no llegó a salir.
    const reservados = alm.reservarEnvios(destino, plan.total, alm.esFrio(destino));
    let respuesta: Response;
    try {
      await this.#arrancar();
      respuesta = await this.containerFetch("http://contenedor/enviar", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: cuerpoTexto,
      });
    } catch (e) {
      alm.liberarEnvios(reservados);
      return { status: 502, cuerpo: { error: `El contenedor no contestó: ${enmascarar(e instanceof Error ? e.message : String(e))}` } };
    }

    const texto = await respuesta.text();
    let cuerpo: any;
    try {
      cuerpo = JSON.parse(texto);
    } catch {
      cuerpo = { error: texto.replace(/\s+/g, " ").slice(0, 300) };
    }
    const ids: string[] = Array.isArray(cuerpo?.ids) ? cuerpo.ids : [];
    alm.liberarEnvios(reservados.slice(ids.length));
    if (ids.length) alm.anotarEnviados(ids);
    return { status: respuesta.status, cuerpo };
  }

  /** La foto de perfil de quien escribe (la pide el Worker de Juan). No cuenta para los topes: no escribe nada. */
  async fotoPerfil(cuerpoTexto: string): Promise<{ status: number; cuerpo: unknown }> {
    if (!this.#activo()) {
      return { status: 503, cuerpo: { error: "El puente está apagado (PUENTE_ACTIVO).", estado: "apagado" } };
    }
    if (cuerpoTexto.length > 2048) return { status: 400, cuerpo: { error: "Cuerpo demasiado grande." } };
    try {
      await this.#arrancar();
      const respuesta = await this.containerFetch("http://contenedor/foto-perfil", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: cuerpoTexto,
      });
      const texto = await respuesta.text();
      try {
        return { status: respuesta.status, cuerpo: JSON.parse(texto) };
      } catch {
        return { status: 502, cuerpo: { error: texto.replace(/\s+/g, " ").slice(0, 300) } };
      }
    } catch (e) {
      return { status: 502, cuerpo: { error: `El contenedor no contestó: ${enmascarar(e instanceof Error ? e.message : String(e))}` } };
    }
  }

  // ── Estado, QR y vinculación ─────────────────────────────────────────────

  async estadoPublico(): Promise<Record<string, unknown>> {
    const ahora = Date.now();
    const activo = this.#activo();
    const alm = await this.#alm();

    // El estado NO puede depender de que el contenedor conteste: con el contenedor frío el
    // proxy reintenta hasta 12,5 s y quien consulta se rendiría antes. Tope de 4 s. (Esto es solo
    // lo que se MUESTRA: que no conteste en 4 s no lo marca como muerto para nadie.)
    const delContenedor = activo ? await this.#estadoDelContenedor(4000) : null;
    const [sesion, diario] = await Promise.all([alm.estadoSesion(), this.#diario()]);
    const progresoEn = alm.ultimoProgresoEn(ahora - 2 * HORA_MS);
    const ultimoEntrante = alm.ultimoEntranteEn();
    const ventana = alm.actividadDesde(ahora - 15 * 60_000);
    const ocupado =
      activo && delContenedor?.conexion !== "conectada" && progresoEn !== null && ahora - progresoEn < PROGRESO_VIGENTE_MS;
    const arranque = diario.ultimoArranque ? Date.parse(diario.ultimoArranque) : NaN;
    const finDeGracia = Number.isFinite(arranque) ? arranque + GRACIA_TRAS_ARRANQUE_MS : null;

    const resumen = resumirEstado({
      activo,
      conexion: delContenedor?.conexion,
      vinculadoAlgunaVez: Boolean(diario.ultimaConexionVista) || sesion.vinculado,
      sinConexionDesde: diario.sinConexionDesde,
      ahora,
    });

    return {
      ok: true,
      estado: resumen.estado,
      conectado: resumen.conectado,
      desconectado_min: resumen.desconectadoMin,
      desconectado_desde: diario.sinConexionDesde ? new Date(diario.sinConexionDesde).toISOString() : null,
      ultima_conexion: diario.ultimaConexionVista,
      activo,
      // Sin conexión (o sin respuesta) PERO trabajando: procesa lo que se acumuló. No reiniciar.
      ocupado,
      vinculado_como: delContenedor?.vinculadoComo ?? null,
      contenedor: delContenedor
        ? {
            conexion: delContenedor.conexion,
            sincronizando: delContenedor.sincronizando,
            intentoEnCurso: delContenedor.intentoEnCurso,
            reconexiones: delContenedor.reconexiones,
            rescatesDelVigilante: delContenedor.rescatesDelVigilante,
            ultimaVigilancia: delContenedor.ultimaVigilancia,
            mensajesRecibidos: delContenedor.mensajesRecibidos,
            mensajesProcesados: delContenedor.mensajesProcesados,
            mensajesEnviados: delContenedor.mensajesEnviados,
            respuestasDelTelefono: delContenedor.respuestasDelTelefono,
            archivosRecibidos: delContenedor.archivosRecibidos,
            entregasFallidas: delContenedor.entregasFallidas,
            ignorados: delContenedor.ignorados,
            enviosEnCola: delContenedor.enviosEnCola,
            ultimaReconexion: delContenedor.ultimaReconexion,
            // memoria (rss/heap), procesador, atraso del bucle, llaves y mensajes de los últimos 15 min, colas
            metricas: delContenedor.metricas,
            ultimoError: delContenedor.ultimoError,
          }
        : { error: activo ? "el contenedor no respondió en 4 s (puede estar arrancando u ocupado procesando lo atrasado)" : "apagado" },
      // Lo último que el contenedor dijo de su memoria y procesador: sirve aunque ya no conteste.
      ultimas_metricas: diario.ultimasMetricas,
      sesion,
      // Lo que escribió la sesión (visto desde aquí, conteste o no el contenedor). Solo cuentas.
      actividad: {
        ultimos_15_min: ventana,
        ultimo_progreso: progresoEn ? new Date(progresoEn).toISOString() : null,
        ultimo_mensaje_de_clienta: ultimoEntrante ? new Date(ultimoEntrante).toISOString() : null,
        minutos_sin_mensajes_de_clientas: ultimoEntrante ? Math.floor((ahora - ultimoEntrante) / 60_000) : null,
        por_hora_24h: alm.actividadPorHora(ahora - 24 * HORA_MS),
      },
      latido: {
        ultimoEn: diario.ultimoLatidoEn ? new Date(diario.ultimoLatidoEn).toISOString() : null,
        vencido: latidoVencido(diario.ultimoLatidoEn, ahora),
        desconectadoSeguidos: diario.desconectadoSeguidos,
        reiniciosForzados: diario.reiniciosForzados,
        ultimoFallo: diario.ultimoFalloDelLatido,
        epoca: this.#epoca,
        arranquesContenedor: diario.arranquesContenedor,
        arranquesUltimaHora: diario.arranquesRecientes.filter((t) => ahora - t < HORA_MS).length,
        ultimaSalida: diario.ultimaSalida,
      },
      // Cómo decide el vigilante (src/vigilancia.ts): cuánta paciencia le queda antes del martillo.
      paciencia: {
        gracia_tras_arranque_hasta: finDeGracia && finDeGracia > ahora ? new Date(finDeGracia).toISOString() : null,
        reiniciar_sin_progreso_min: Math.round(REINICIAR_SIN_PROGRESO_MS / 60_000),
        reinicios_seguidos: diario.reiniciosSeguidos,
        proximo_martillo_tras_min: Math.round(esperaAntesDeReiniciar(diario.reiniciosSeguidos) / 60_000),
        ocupado_desde: diario.ocupadoDesde ? new Date(diario.ocupadoDesde).toISOString() : null,
      },
      alarmas: diario.alarmas,
      poda: {
        respaldo: alm.respaldoDePoda(),
        ultima: diario.ultimaPoda,
        automatica: { desde: PODA_AUTOMATICA_DESDE, conserva: PRE_KEYS_A_CONSERVAR },
      },
      copias: {
        ultima: alm.ultimaCopiaEn() ? new Date(alm.ultimaCopiaEn()!).toISOString() : null,
        guardadas: alm.listarCopias().length,
        r2: this.env.COPIA_R2 === "on" ? "encendida" : "apagada",
        ultimaR2: diario.ultimaCopiaR2,
        ultimoFallo: diario.ultimoFalloDeCopia,
      },
      pendientes: alm.contarPendientes(),
      cuotas: this.#cuotasEnUso(alm, ahora),
      aviso_telegram: {
        configurado: Boolean(this.env.TELEGRAM_BOT_TOKEN_JUAN && chatDeAvisos(this.env)),
        activo: diario.avisoActivo,
      },
    };
  }

  /** Cuánto del ritmo permitido se está usando (para que se vea antes de que Juan reciba un 429). */
  #cuotasEnUso(alm: Almacen, ahora: number) {
    const cfg = leerRitmo(this.env as unknown as Record<string, unknown>);
    const envios = alm.enviosRecientes();
    return {
      ultimo_minuto: envios.filter((e) => ahora - e.ts < 60_000).length,
      ultimas_24h: envios.length,
      personas_nuevas_24h: new Set(envios.filter((e) => e.frio).map((e) => e.para)).size,
      limites: {
        por_minuto: cfg.porMinuto,
        por_dia: cfg.porDia,
        por_destinatario_hora: cfg.porDestinatarioHora,
        personas_nuevas_por_dia: cfg.friosPorDia,
      },
    };
  }

  async qr(): Promise<{ status: number; cuerpo: unknown }> {
    if (!this.#activo()) return { status: 200, cuerpo: { qr: null, estado: "apagado" } };
    // Con tope por lo mismo que el estado: el QR es opcional —puede no haberlo— y no debe
    // dejar colgada la pantalla que lo muestra.
    try {
      const r = await Promise.race([
        this.containerFetch("http://contenedor/qr"),
        new Promise<null>((res) => setTimeout(() => res(null), 4000)),
      ]);
      if (!r) return { status: 202, cuerpo: { qr: null, estado: "arrancando" } };
      return { status: r.status, cuerpo: await r.json() };
    } catch {
      return { status: 202, cuerpo: { qr: null, estado: "arrancando" } };
    }
  }

  async desvincular(): Promise<{ status: number; cuerpo: unknown }> {
    if (!this.#activo()) return { status: 409, cuerpo: { error: "El puente está apagado." } };
    try {
      const r = await this.containerFetch("http://contenedor/logout", { method: "POST" });
      return { status: r.status, cuerpo: await r.json() };
    } catch (e) {
      return { status: 502, cuerpo: { error: enmascarar(e instanceof Error ? e.message : String(e)) } };
    }
  }

  // ── Copias de la sesión ──────────────────────────────────────────────────

  async copiarAhora() {
    const alm = await this.#alm();
    const { copia, filas } = alm.copiar();
    const archivo = armarArchivo(copia, new Date().toISOString(), alm.filasDeCopia(copia));
    const r2 = await subirCopiaR2(this.env, archivo);
    const diario = await this.#diario();
    diario.ultimaCopiaEn = Date.now();
    diario.ultimaCopiaR2 = r2.motivo;
    diario.ultimoFalloDeCopia = null;
    await this.ctx.storage.put("diario", diario);
    return { copia, filas, r2 };
  }

  async listarCopias() {
    return (await this.#alm()).listarCopias();
  }

  async exportarCopia(copia?: string): Promise<ArchivoDeCopia | null> {
    const alm = await this.#alm();
    const lista = alm.listarCopias();
    const elegida = copia ? lista.find((c) => c.copia === copia) : lista[0];
    if (!elegida) return null;
    return armarArchivo(elegida.copia, elegida.creada, alm.filasDeCopia(elegida.copia));
  }

  /**
   * Restaura la sesión. Orden: se carga la copia ANTES de tocar nada, se apaga el contenedor
   * (si no, volvería a escribir encima), se guarda lo que había como una copia más, se
   * reemplaza y se vuelve a levantar.
   */
  async restaurar(opciones: { copia?: string; archivo?: ArchivoDeCopia }): Promise<{ status: number; cuerpo: unknown }> {
    const alm = await this.#alm();
    let filas: ArchivoDeCopia["filas"];
    let origen: string;
    if (opciones.archivo) {
      filas = leerArchivo(JSON.stringify(opciones.archivo)).filas;
      origen = `archivo ${opciones.archivo.copia}`;
    } else {
      const lista = alm.listarCopias();
      const elegida = opciones.copia ? lista.find((c) => c.copia === opciones.copia) : lista[0];
      if (!elegida) return { status: 404, cuerpo: { error: "No existe esa copia.", copias: lista.map((c) => c.copia) } };
      filas = alm.filasDeCopia(elegida.copia);
      origen = `copia ${elegida.copia}`;
    }

    try {
      await this.destroy();
    } catch {
      /* ya estaba apagado */
    }
    // Lo que hubiera ahora queda guardado como una copia más (si había sesión).
    if (alm.hayCreds()) alm.copiar();
    try {
      const r = await alm.restaurar(filas);
      if (this.#activo()) await this.#arrancar(true);
      return {
        status: 200,
        cuerpo: { ok: true, restaurada: origen, filas: r.filas, mensaje: "Sesión restaurada. El contenedor vuelve a conectarse en menos de un minuto." },
      };
    } catch (e) {
      // No se tocó nada (la validación va antes de borrar). Se vuelve a levantar tal como estaba.
      if (this.#activo()) await this.#arrancar(true).catch(() => {});
      return { status: 422, cuerpo: { error: e instanceof Error ? e.message : String(e) } };
    }
  }

  /**
   * La poda a mano (`POST /api/podar`): conserva las 1.000 pre-keys más nuevas y respalda lo demás.
   * Nunca toca `creds`. Ver src/poda.ts.
   */
  async podar() {
    const alm = await this.#alm();
    const borradas = alm.podarPreKeys(PRE_KEYS_A_CONSERVAR);
    const diario = await this.#diario();
    diario.ultimaPoda = { en: new Date().toISOString(), borradas, motivo: "manual" };
    await this.ctx.storage.put("diario", diario);
    console.log(`poda manual de pre-keys: ${borradas} al respaldo`);
    return { borradas, conservadas: PRE_KEYS_A_CONSERVAR, respaldo: alm.respaldoDePoda() };
  }

  /** Devuelve a la sesión las pre-keys de la última poda (`POST /api/podar/deshacer`). */
  async deshacerPoda() {
    const r = (await this.#alm()).deshacerUltimaPoda();
    console.log(`poda deshecha: ${r.restauradas} pre-keys devueltas a la sesión`);
    return r;
  }

  async recifrar() {
    return (await this.#alm()).recifrar();
  }
}
