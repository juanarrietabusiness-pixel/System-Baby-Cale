import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { crearNucleo, GRACIA_INTENTO_MS } from "../contenedor/nucleo.mjs";
import { RITMO_POR_DEFECTO } from "../contenedor/lib/ritmo.mjs";
import { crearBaileysFalso, crearPuenteFalso, msgImagen, msgTexto } from "./ayuda/baileys";
import { crearCtx, jsonResp, type CtxFalso } from "./ayuda/contenedor-falso";

// PRUEBA DE CARGA: volver después de una desconexión larga.
//
// Es la caída del CRM de Baby Caleb (24-nov-2026) puesta en una prueba. Al volver, WhatsApp entrega de golpe lo
// que se acumuló; el puente tarda en procesarlo; un vigilante impaciente lo mataba a la mitad y la vuelta siguiente
// encontraba todavía más. Aquí se comprueba, con WhatsApp de mentira y el reloj simulado, que:
//   · el contenedor no recicla su propia conexión mientras inicia sesión despacio ni mientras procesa lo atrasado;
//   · el Durable Object NO destruye el contenedor mientras hay progreso, aunque el /estado no conteste;
//   · la memoria no se dispara con miles de mensajes atrasados;
//   · el bucle de «solo pre-keys» se avisa y, si sigue, se limpia solo (con respaldo, sin tocar la credencial).

vi.mock("@cloudflare/containers", async () => {
  const m = await import("./ayuda/contenedor-falso");
  return { Container: m.ContenedorBase };
});

import { PuenteWa } from "../src/puente-do";

const MIN = 60_000;
const HORA = 60 * MIN;

// ── El contenedor ────────────────────────────────────────────────────────────

describe("carga en el contenedor: 12 horas de mensajes atrasados", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("inicia sesión despacio y procesa 6.000 atrasados sin reciclarse, en tandas, con las descargas en fila y la memoria a raya", async () => {
    vi.useFakeTimers();
    const heapAntes = process.memoryUsage().heapUsed;
    const baileys = crearBaileysFalso();
    const base = crearPuenteFalso();
    // El Worker tarda 1,5 s en recibir cada mensaje (Juan acusando recibo): la fila de entrantes se llena.
    const puente = Object.assign(async (ruta: string, init?: any) => {
      if (ruta === "/puente/entrante") await new Promise((r) => setTimeout(r, 1500));
      return base(ruta, init);
    }, base);
    let descargando = 0;
    let maxDescargas = 0;
    baileys.downloadMediaMessage.mockImplementation(async () => {
      descargando += 1;
      maxDescargas = Math.max(maxDescargas, descargando);
      await new Promise((r) => setTimeout(r, 500));
      descargando -= 1;
      return Buffer.from("FOTO-DE-PRUEBA");
    });
    let tandasCedidas = 0;
    const nucleo = crearNucleo({
      baileys,
      puente: puente as any,
      qr: { toDataURL: async () => "data:image/png;base64,QQ" },
      logger: {},
      descargar: vi.fn(),
      dormir: (ms: number) => new Promise((r) => setTimeout(r, ms)),
      ceder: () => {
        tandasCedidas += 1;
        return new Promise((r) => setImmediate(r));
      },
      azar: () => 0.5,
      log: { log: vi.fn(), error: vi.fn() },
      config: { ritmo: RITMO_POR_DEFECTO, hostsPermitidos: [] },
    });
    try {
      await nucleo.arrancar();
      const sock = baileys.ultimo;
      const keys = sock.config.auth.keys;
      const post = (ruta: string) => nucleo.manejar({ metodo: "POST", ruta, cuerpo: "" });

      // 1) Inicio de sesión LENTO (1/16 de CPU): repone pre-keys y tarda 100 s en abrir. El Durable Object le
      //    pide reconectar cada 30 s (como hacía el vigilante del CRM). Nada de eso puede cortar el intento.
      await vi.advanceTimersByTimeAsync(5_000);
      await keys.set({ "pre-key": Object.fromEntries(Array.from({ length: 5 }, (_, i) => [String(900 + i), { k: "x" }])) });
      for (let t = 0; t < 90_000; t += 30_000) {
        const r = await post("/reconectar");
        expect(r.cuerpo.programada).not.toBe(true);
        await vi.advanceTimersByTimeAsync(30_000);
      }
      await vi.advanceTimersByTimeAsync(5_000); // 100 s sin abrir: con la regla vieja (30 s) ya lo habría reciclado 3 veces
      expect(GRACIA_INTENTO_MS).toBeGreaterThan(100_000);
      expect(baileys.makeWASocket).toHaveBeenCalledOnce();
      sock.conexion({ connection: "open" });
      expect(nucleo.estado.sincronizando).toBe(true);

      // 2) Lo atrasado: 6.000 mensajes de 1.500 clientas de las últimas 12 h, en paquetes de 300 cada 2 s (como
      //    los entrega Baileys). Solo los de los últimos 15 min se contestan; el resto se cuenta. Cada paquete
      //    escribe sesiones (progreso de verdad). En medio, 30 mensajes en vivo con foto.
      const ahoraS = () => Math.floor(Date.now() / 1000);
      let recientes = 0;
      for (let p = 0; p < 20; p++) {
        const paquete = Array.from({ length: 300 }, (_, i) => {
          const n = p * 300 + i;
          const reciente = n % 100 === 0; // 60 de 6.000
          if (reciente) recientes += 1;
          const hace = reciente ? 5 * 60 : 12 * 3600 - n * 6;
          return msgTexto(`mensaje ${n}`, { id: `OFF${n}`, ts: ahoraS() - hace, de: `5076${String(n % 1500).padStart(7, "0")}@s.whatsapp.net` });
        });
        sock.upsert(paquete, "append");
        await keys.set({ session: { [`5076${p}.0`]: "S" } });
        if (p % 2 === 0) {
          sock.upsert(Array.from({ length: 3 }, (_, i) => msgImagen({ id: `VIVO${p}-${i}`, de: `5079${String(p * 3 + i).padStart(7, "0")}@s.whatsapp.net` })));
        }
        const estado = await nucleo.manejar({ metodo: "GET", ruta: "/estado" });
        expect(estado.status).toBe(200); // contesta EN MEDIO de la avalancha
        expect((await post("/reconectar")).cuerpo.ignorada).toBe("ya está conectada");
        await vi.advanceTimersByTimeAsync(2_000);
      }
      sock.conexion({ receivedPendingNotifications: true });

      // 3) Se deja trabajar 10 minutos (la fila de entrega a 1,5 s por mensaje).
      for (let s = 0; s < 20; s++) await vi.advanceTimersByTimeAsync(30_000);

      // Ni un reciclaje: un solo socket, ningún rescate.
      expect(baileys.makeWASocket).toHaveBeenCalledOnce();
      expect(nucleo.estado.rescatesDelVigilante).toBe(0);
      expect(nucleo.estado.conexion).toBe("conectada");
      // Lo reciente y lo en vivo, entregado una sola vez; lo viejo, contado por conversación.
      const ids = base.entrantes.map((e: any) => e.id_mensaje);
      expect(new Set(ids).size).toBe(ids.length);
      expect(ids.filter((i: string) => i.startsWith("OFF"))).toHaveLength(recientes);
      expect(ids.filter((i: string) => i.startsWith("VIVO"))).toHaveLength(30);
      expect(nucleo.estado.ultimaReconexion).toMatchObject({ terminada: true, atendidos: recientes, sinContestar: 6000 - recientes });
      expect(nucleo.estado.ultimaReconexion!.conversacionesSinContestar).toBeLessThanOrEqual(1500);
      // En tandas (cediendo el turno) y las descargas de a una.
      expect(tandasCedidas).toBeGreaterThanOrEqual(20 * (300 / 25 - 1));
      expect(maxDescargas).toBe(1);
      // La fila de entrantes se vació y las métricas lo dicen.
      const e = (await nucleo.manejar({ metodo: "GET", ruta: "/estado" })).cuerpo;
      expect(e.metricas.colas.entrantes).toBe(0);
      expect(e.metricas.llaves.trafico).toBeGreaterThan(0);
      expect(e.metricas.mensajes.procesados).toBe(recientes + 30);
      // La memoria no se dispara: el núcleo no se queda con los miles de mensajes (solo cuenta).
      const crecio = (process.memoryUsage().heapUsed - heapAntes) / (1024 * 1024);
      expect(crecio).toBeLessThan(120);
    } finally {
      nucleo.detener();
    }
  }, 60_000);
});

// ── El Durable Object ────────────────────────────────────────────────────────

const TOKEN = "token-de-prueba-0123456789-abcdefghij";
const CLAVE = "clave-de-prueba-para-la-sesion-0123456789";
const T0 = Date.UTC(2026, 10, 24, 5, 0, 0); // 24-nov-2026, 00:00 en Panamá: la hora en que empezó el bucle

type Do = PuenteWa & Record<string, any>;

async function montarDo(envExtra: Record<string, unknown> = {}, ctx: CtxFalso = crearCtx()) {
  const env: any = {
    PUENTE_ACTIVO: "on",
    PUENTE_BASE_URL: "https://dcasa-puente-wa-staging.dcasapty.workers.dev",
    WA_TOKEN: TOKEN,
    WA_SESION_CLAVE: CLAVE,
    TELEGRAM_BOT_TOKEN_JUAN: "123456:token-falso-de-prueba",
    ALERTA_TELEGRAM_CHAT: "-100777",
    JUAN: { fetch: vi.fn(async () => new Response("{}", { status: 200 })) },
    ...envExtra,
  };
  const d = new PuenteWa(ctx as any, env) as Do;
  await Promise.all(ctx.listo);
  return { d, ctx, env };
}

/** El contenedor contesta su /estado así; `null` = no contesta (falla); «colgado» = nunca termina de contestar. */
function contenedor(d: Do, estado: Record<string, unknown> | null | "colgado") {
  d.manejador = (u: URL) => {
    if (u.pathname === "/estado") {
      if (estado === "colgado") return new Promise<Response>(() => {});
      if (estado === null) throw new Error("no contesta");
      return jsonResp(estado);
    }
    if (u.pathname === "/reconectar") return jsonResp({ ok: true });
    return jsonResp({ error: "no existe" }, 404);
  };
}

let telegram: ReturnType<typeof vi.fn>;
const textosTelegram = () =>
  telegram.mock.calls.filter((c: any[]) => String(c[0]).startsWith("https://api.telegram.org/")).map((c: any[]) => JSON.parse(String(c[1].body)).text as string);

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date", "setTimeout", "clearTimeout"] });
  vi.setSystemTime(T0);
  telegram = vi.fn(async () => new Response("{}", { status: 200 }));
  vi.stubGlobal("fetch", telegram);
  vi.spyOn(console, "log").mockImplementation(() => {});
  vi.spyOn(console, "error").mockImplementation(() => {});
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

const asentar = async () => {
  for (let i = 0; i < 300; i++) await Promise.resolve();
};

/** Una vigilancia completa: deja correr el tope del /estado si el contenedor no contesta. */
async function vigilar(d: Do) {
  let terminada = false;
  const p = d.vigilar().finally(() => {
    terminada = true;
  });
  for (let vuelta = 0; !terminada && vuelta < 400; vuelta++) {
    await asentar();
    await new Promise((r) => setImmediate(r));
    const antes = Date.now();
    await vi.advanceTimersByTimeAsync(1_000);
    vi.setSystemTime(antes); // la espera del tope no mueve el reloj del escenario
  }
  await p;
}

const conectado = { conexion: "conectada", metricas: { memoria: { rssMB: 140, rssMaximoMB: 160, heapUsadoMB: 70 }, cpu: { porcentaje: 3 }, bucle: { retrasoP99Ms: 40 }, reconexionesUltimaHora: 0 } };

describe("carga en el Durable Object: el vigilante no mata mientras hay progreso", () => {
  it("45 min sin conexión y sin que el /estado conteste, pero escribiendo sesiones: CERO reinicios; al dejar de avanzar, uno", async () => {
    const { d } = await montarDo();
    contenedor(d, conectado);
    await vigilar(d); // arranca y conecta
    vi.setSystemTime(T0 + 30 * MIN); // ya fuera de la gracia del arranque
    await vigilar(d);
    const epoca = String(d.envVars!.PUENTE_EPOCA);

    // Vuelve de un corte con una avalancha: el /estado no contesta (el bucle de eventos está ocupado descifrando)
    // pero la sesión escribe sesiones e identidades (progreso real) y llegan mensajes a Juan.
    contenedor(d, null);
    const inicio = Date.now();
    for (let t = 0; t < 45 * MIN; t += 30_000) {
      vi.setSystemTime(inicio + t);
      await d.kvLote({ escribir: { [`session-5076${t}.0`]: "S", [`identity-key-${t}`]: "I" }, borrar: [] }, epoca);
      if (t % (2 * MIN) === 0) await d.marcarEntrante(`5076000${t % 1000}`);
      await vigilar(d);
    }
    expect(d.paradas).toHaveLength(0); // con la regla vieja (5 vigilancias ≈ 2,5 min) habrían sido ~18
    expect(d.llamadas.filter((l: any) => l.url.endsWith("/reconectar"))).toHaveLength(0);
    const dia = await d.diario();
    expect(dia.reiniciosForzados).toBe(0);
    expect(dia.ocupadoDesde).toBe(inicio);
    const estado = (await d.estadoPublico()) as any;
    expect(estado.ocupado).toBe(true);
    expect(estado.actividad.ultimos_15_min.trafico).toBeGreaterThan(0);
    expect(estado.ultimas_metricas).toMatchObject({ rssMB: 140, rssMaximoMB: 160 });
    // El aviso de «sin conexión» dice que está trabajando y que NO se reinicie.
    expect(textosTelegram().some((t) => t.includes("está trabajando") && t.includes("NO lo reinicies"))).toBe(true);
    // Y no saltó la alarma del bucle: hubo tráfico de verdad.
    expect(textosTelegram().some((t) => t.includes("solo reponiendo"))).toBe(false);

    // Deja de avanzar (de verdad trabado): a los 10 min sin progreso, el martillo. Una vez.
    const quieto = Date.now();
    for (let t = 30_000; t <= 12 * MIN; t += 30_000) {
      vi.setSystemTime(quieto + t);
      await vigilar(d);
    }
    expect(d.paradas).toHaveLength(1);
  }, 60_000);

  it("el bucle del 24-nov: solo pre-keys de 5 en 5 y el contenedor muriendo → aviso en cuanto se ve la firma, limpieza sola tras 30 min (con respaldo, sin tocar creds)", async () => {
    const { d, ctx } = await montarDo();
    contenedor(d, conectado);
    await vigilar(d);
    // La sesión inflada: la credencial, algo de tráfico viejo y 15.934 pre-keys.
    const epoca = () => String(d.envVars!.PUENTE_EPOCA);
    await d.kvSet("creds", '{"nextPreKeyId":15935,"firstUnuploadedPreKeyId":15935}', epoca());
    await d.kvLote({ escribir: Object.fromEntries(Array.from({ length: 15_934 }, (_, i) => [`pre-key-${i + 1}`, "pk"])) }, epoca());
    vi.setSystemTime(T0 + 30 * MIN);
    await vigilar(d);

    // El bucle: cada 3 min el contenedor arranca, repone 5 pre-keys y muere (exit 137). Nada de tráfico.
    contenedor(d, { conexion: "cerrada", metricas: { memoria: { rssMB: 250, rssMaximoMB: 252 }, reconexionesUltimaHora: 1 } });
    const inicio = Date.now();
    let siguiente = 15_935;
    for (let t = 0; t <= 50 * MIN; t += 30_000) {
      vi.setSystemTime(inicio + t);
      if (t % (3 * MIN) === 0) {
        const rafaga = Object.fromEntries(Array.from({ length: 5 }, () => [`pre-key-${siguiente++}`, "pk"]));
        await d.kvLote({ escribir: rafaga }, epoca());
        await d.kvSet("creds", `{"nextPreKeyId":${siguiente}}`, epoca());
        await d.destroy(); // muere solo (137); la vigilancia lo vuelve a levantar
      }
      await vigilar(d);
    }
    const textos = textosTelegram();
    const iSolo = textos.findIndex((x) => x.includes("solo reponiendo"));
    expect(iSolo).toBeGreaterThanOrEqual(0);
    expect(textos.some((x) => x.includes("se reinició") && x.includes("137"))).toBe(true); // alarma «bucle»
    expect(textos.some((x) => x.includes("se limpiaron") && x.includes("No hay que escanear el QR"))).toBe(true);

    // Lo que quedó: 1.000 pre-keys (las más nuevas), el respaldo con el resto, y la credencial INTACTA.
    const estado = (await d.estadoPublico()) as any;
    expect(estado.sesion.preKeys).toBeLessThanOrEqual(1000 + 5 * 5); // las 1.000 + las ráfagas que siguieron
    expect(estado.sesion.vinculado).toBe(true);
    expect(await d.kvGet("creds")).toContain("nextPreKeyId");
    expect(estado.poda.ultima).toMatchObject({ motivo: "emergencia" });
    expect(estado.poda.respaldo.llaves).toBeGreaterThan(14_900);
    expect(await d.kvGet(`pre-key-${siguiente - 1}`)).toBe("pk"); // la más nueva sigue ahí
    expect(await d.kvGet("pre-key-1")).toBe(null);

    // Vuelve el tráfico: la alarma avisa que se recuperó.
    contenedor(d, conectado);
    vi.setSystemTime(Date.now() + 16 * MIN);
    await d.kvLote({ escribir: { "session-50760261919.0": "S" } }, epoca());
    await vigilar(d);
    expect(textosTelegram().some((x) => x.includes("volvió a procesar mensajes"))).toBe(true);
    // La actividad guardada no crece sin límite (una fila por minuto, 48 h como mucho).
    expect(ctx.storage.sql.exec("SELECT COUNT(*) AS n FROM wa_actividad").toArray()[0].n).toBeLessThanOrEqual(48 * 60);
  }, 60_000);

  it("un /estado que se queda colgado no cuelga la vigilancia (tope de 20 s) y, con progreso, no cuenta como caída", async () => {
    const { d } = await montarDo();
    contenedor(d, conectado);
    await vigilar(d);
    vi.setSystemTime(T0 + 30 * MIN);
    contenedor(d, "colgado");
    await d.kvLote({ escribir: { "session-50760261919.0": "S" } }, String(d.envVars!.PUENTE_EPOCA));
    await vigilar(d); // termina gracias al tope
    const dia = await d.diario();
    expect(dia.latidos).toBe(2);
    expect(dia.ultimoFalloDelLatido).toBe(null);
    expect(dia.ocupadoDesde).toBe(T0 + 30 * MIN);
    expect(d.llamadas.filter((l: any) => l.url.endsWith("/reconectar"))).toHaveLength(0);
  });

  it("al volver, avisa UNA vez cuántas conversaciones quedaron con mensajes atrasados sin contestar", async () => {
    const { d } = await montarDo();
    const reconexion = { id: "2026-11-24T19:08:00.000Z", terminada: true, atendidos: 3, sinContestar: 40, conversacionesSinContestar: 17 };
    contenedor(d, { ...conectado, ultimaReconexion: reconexion });
    await vigilar(d);
    vi.setSystemTime(Date.now() + 30_000);
    await vigilar(d);
    const avisos = textosTelegram().filter((t) => t.includes("atrasados"));
    expect(avisos).toHaveLength(1);
    expect(avisos[0]).toContain("40 mensajes atrasados de 17 conversaciones");
  });

  it("en horario de atención, sin un solo mensaje de clientas en 60 min: avisa (con el chat de Juan si falta el del puente)", async () => {
    const { d } = await montarDo({
      ALERTA_TELEGRAM_CHAT: undefined,
      ALERTA_TELEGRAM_CHAT_ID: "-100888",
      HORARIO_INICIO: "09:00",
      HORARIO_FIN: "18:00",
      HORARIO_DIAS: "1,2,3,4,5,6",
      HORARIO_ZONA: "America/Panama",
      ALERTA_SIN_MENSAJES_MINUTOS: "60",
    });
    vi.setSystemTime(Date.parse("2026-11-24T09:30:00-05:00"));
    contenedor(d, conectado);
    await vigilar(d);
    await d.marcarEntrante("50760261919"); // una clienta a las 9:30
    vi.setSystemTime(Date.parse("2026-11-24T10:25:00-05:00"));
    await vigilar(d);
    expect(textosTelegram()).toHaveLength(0);
    vi.setSystemTime(Date.parse("2026-11-24T10:31:00-05:00"));
    await vigilar(d);
    const llamadas = telegram.mock.calls.filter((c: any[]) => String(c[0]).startsWith("https://api.telegram.org/"));
    expect(llamadas).toHaveLength(1);
    expect(JSON.parse(String(llamadas[0][1].body))).toMatchObject({ chat_id: "-100888" });
    expect(textosTelegram()[0]).toContain("No entra ningún mensaje de clientas");
  });
});
