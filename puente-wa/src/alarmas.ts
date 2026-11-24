// Las alarmas que avisan ANTES de que alguien note que WhatsApp no contesta.
//
// Nacen de la caída del CRM de Baby Caleb (24-nov-2026): el puente pasó 14 horas en bucle y nadie
// lo supo hasta la mañana. Las tres señales que la habrían delatado temprano:
//
//   solo_prekeys  la sesión solo repone pre-keys (de 5 en 5) y no procesa NINGÚN mensaje: la firma
//                 exacta de esa caída. Se ve en lo que escribe la sesión, sin abrir el contenedor.
//   sin_mensajes  en horario de atención, pasan X minutos sin que entre un solo mensaje de clienta:
//                 la falla muda (dice «conectado» pero no recibe nada).
//   bucle         el contenedor arranca una y otra vez, o reconecta sin parar: algo lo tumba.
//
// Además, un aviso de una sola vez: al volver de una caída, cuántas conversaciones quedaron con
// mensajes atrasados que el asistente NO contesta solo (para que la dueña las conteste a mano).
//
// Funciones puras: dicen QUÉ avisar y cómo queda el estado; quien llama envía (por Telegram, el
// canal que ya usa el puente) y guarda. Los textos nunca llevan números de teléfono, QR ni claves.

import type { ResumenActividad } from "./almacen";

// ── Configuración ────────────────────────────────────────────────────────────

export interface Horario {
  /** «HH:MM», hora local del negocio. */
  inicio: string;
  fin: string;
  /** 0 = domingo … 6 = sábado (igual que el horario de Juan). */
  dias: number[];
  /** Zona IANA, p. ej. «America/Panama». */
  zona: string;
}

export interface ConfigAlarmas {
  /** La ventana de la alarma «solo pre-keys» (y su X de minutos). */
  soloPreKeysMinutos: number;
  /** Cuántas ráfagas de solo pre-keys dentro de la ventana hacen falta para avisar. */
  rafagasSoloPreKeys: number;
  /** Minutos sin un mensaje de clienta, en horario, para avisar. 0 = apagada. */
  sinMensajesMinutos: number;
  /** El horario de atención; null = la alarma «sin mensajes» no se evalúa. */
  horario: Horario | null;
  /** Arranques del contenedor en la última hora que ya son un bucle. */
  bucleArranquesHora: number;
  /** Reconexiones de WhatsApp en la última hora que ya son un bucle. */
  bucleReconexionesHora: number;
  /** Cada cuánto se repite un aviso mientras siga igual. */
  reavisoMinutos: number;
}

/**
 * Valores por defecto. Ninguno es una cifra de dinero: son umbrales de operación que se cambian
 * desde `wrangler.jsonc` (vars) sin tocar código.
 *
 *  · 15 min y 3 ráfagas: en el bucle del 24-nov el puente reponía pre-keys cada 1 a 5 minutos;
 *    un arranque sano repone UNA vez y enseguida escribe sesiones (tráfico).
 *  · 60 min sin mensajes en horario: el CRM de origen recibe entre 1.200 y 1.800 mensajes por
 *    semana; una hora entera en silencio en horario de atención no es normal.
 *  · 4 arranques o 6 reconexiones en una hora: con la paciencia nueva, un arranque sano no se
 *    repite más de una o dos veces por hora.
 */
export const ALARMAS_POR_DEFECTO: Omit<ConfigAlarmas, "horario" | "reavisoMinutos"> = {
  soloPreKeysMinutos: 15,
  rafagasSoloPreKeys: 3,
  sinMensajesMinutos: 60,
  bucleArranquesHora: 4,
  bucleReconexionesHora: 6,
};

const HORA = /^([01]\d|2[0-3]):([0-5]\d)$/;

/** «HH:MM» → minutos del día, o null si no tiene esa forma. */
function minutosDe(hhmm: string | undefined): number | null {
  const m = HORA.exec((hhmm ?? "").trim());
  return m ? Number(m[1]) * 60 + Number(m[2]) : null;
}

/**
 * Lee el horario de las variables. Cualquier parte que no sirva apaga la alarma «sin mensajes»
 * (mejor sin alarma que con una que avisa a las 3 de la mañana).
 */
export function leerHorario(env: { HORARIO_INICIO?: string; HORARIO_FIN?: string; HORARIO_DIAS?: string; HORARIO_ZONA?: string }): Horario | null {
  const inicio = minutosDe(env.HORARIO_INICIO);
  const fin = minutosDe(env.HORARIO_FIN);
  if (inicio === null || fin === null || fin <= inicio) return null;
  const dias = [...new Set((env.HORARIO_DIAS ?? "").split(",").map((d) => d.trim()).filter((d) => /^[0-6]$/.test(d)).map(Number))];
  if (!dias.length) return null;
  const zona = (env.HORARIO_ZONA ?? "").trim() || "America/Panama";
  return { inicio: env.HORARIO_INICIO!.trim(), fin: env.HORARIO_FIN!.trim(), dias: dias.sort(), zona };
}

export function leerConfigAlarmas(env: Record<string, unknown>): ConfigAlarmas {
  const n = (v: unknown, d: number, min: number, max: number) => {
    const x = Number(v);
    return v !== undefined && v !== "" && Number.isFinite(x) ? Math.min(max, Math.max(min, Math.round(x))) : d;
  };
  return {
    ...ALARMAS_POR_DEFECTO,
    sinMensajesMinutos: n(env.ALERTA_SIN_MENSAJES_MINUTOS, ALARMAS_POR_DEFECTO.sinMensajesMinutos, 0, 1440),
    horario: leerHorario(env as Record<string, string | undefined>),
    reavisoMinutos: n(env.ALERTA_REAVISO_MINUTOS, 120, 10, 10080),
  };
}

// ── La hora del negocio ──────────────────────────────────────────────────────

const DIAS_CORTOS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

/** Minuto del día y día de la semana (0 = domingo) en la zona del negocio. Igual que en Juan. */
export function relojDelNegocio(zona: string, ms: number): { minutosDelDia: number; dia: number } {
  let partes: Intl.DateTimeFormatPart[];
  try {
    partes = new Intl.DateTimeFormat("en-US", { timeZone: zona, hour: "numeric", minute: "numeric", hourCycle: "h23", weekday: "short" }).formatToParts(
      new Date(ms),
    );
  } catch {
    if (zona !== "America/Panama") return relojDelNegocio("America/Panama", ms);
    throw new Error("sin zona horaria");
  }
  const get = (t: string) => partes.find((p) => p.type === t)?.value ?? "0";
  return { minutosDelDia: Number(get("hour")) * 60 + Number(get("minute")), dia: Math.max(0, DIAS_CORTOS.indexOf(get("weekday"))) };
}

/**
 * Si ahora es horario de atención, el instante (ms) en que abrió HOY; si no, null. Sirve para no
 * contar la noche como «tiempo sin mensajes»: a las 9:05 no se avisa de un silencio que empezó ayer.
 */
export function aperturaDeHoy(h: Horario, ms: number): number | null {
  const { minutosDelDia, dia } = relojDelNegocio(h.zona, ms);
  const ini = minutosDe(h.inicio)!;
  const fin = minutosDe(h.fin)!;
  if (!h.dias.includes(dia) || minutosDelDia < ini || minutosDelDia >= fin) return null;
  const segundos = Math.floor(ms / 1000) % 60;
  return ms - (minutosDelDia - ini) * 60_000 - segundos * 1000 - (ms % 1000);
}

// ── El estado de cada alarma ─────────────────────────────────────────────────

export type TipoAlarma = "solo_prekeys" | "sin_mensajes" | "bucle";

export interface EstadoAlarma {
  /** Hay un aviso enviado y la situación sigue (o no se ha avisado que terminó). */
  activo: boolean;
  /** Desde cuándo se cumple la condición (ms), o null. */
  desde: number | null;
  /** Último aviso enviado (ms), o null. */
  ultimoAvisoEn: number | null;
}

export type EstadoAlarmas = Record<TipoAlarma, EstadoAlarma>;

export function alarmasNuevas(): EstadoAlarmas {
  const nueva = (): EstadoAlarma => ({ activo: false, desde: null, ultimoAvisoEn: null });
  return { solo_prekeys: nueva(), sin_mensajes: nueva(), bucle: nueva() };
}

/** Un estado guardado por una versión anterior (o a medias) no rompe nada. */
export function normalizarAlarmas(guardado: Partial<EstadoAlarmas> | null | undefined): EstadoAlarmas {
  const base = alarmasNuevas();
  if (!guardado) return base;
  for (const k of Object.keys(base) as TipoAlarma[]) base[k] = { ...base[k], ...(guardado[k] ?? {}) };
  return base;
}

// ── La evaluación ────────────────────────────────────────────────────────────

export interface Senales {
  /** ¿Estuvo conectado alguna vez? Una instalación nueva (sin QR escaneado) no avisa nada. */
  vinculado: boolean;
  /** ¿Está activo el aviso de «sin conexión»? Si lo está, no se suma el de «sin mensajes». */
  caidaAvisada: boolean;
  /** Lo que escribió la sesión dentro de la ventana de «solo pre-keys». */
  ventana: Pick<ResumenActividad, "lotesSoloPreKeys" | "preKeysNuevas" | "preKeysUsadas" | "trafico" | "entrantes">;
  /** Cuándo escribió la última clienta (ms), o null. */
  ultimoEntranteEn: number | null;
  /** Arranques del contenedor en la última hora. */
  arranquesUltimaHora: number;
  /** Reconexiones de WhatsApp en la última hora (lo dice el contenedor; null si no contestó). */
  reconexionesUltimaHora: number | null;
  /** Cómo terminó el contenedor la última vez («código 137 · …»), para el texto. */
  ultimaSalida: string | null;
  /** El pico de memoria que reportó el contenedor (MB), para el texto. */
  rssMaximoMB: number | null;
}

export interface Aviso {
  tipo: TipoAlarma | "atrasados";
  /** `recuperado` = el aviso que dice que la situación terminó. */
  recuperado: boolean;
  texto: string;
}

const CANAL = "WhatsApp por QR (el puente)";

function condiciones(s: Senales, ahora: number, cfg: ConfigAlarmas): Record<TipoAlarma, { se_cumple: boolean; minutos?: number }> {
  const v = s.ventana;
  const soloPreKeys =
    s.vinculado && v.lotesSoloPreKeys >= cfg.rafagasSoloPreKeys && v.trafico === 0 && v.preKeysUsadas === 0 && v.entrantes === 0;

  let sinMensajes = false;
  let minutosSinMensajes = 0;
  if (s.vinculado && !s.caidaAvisada && cfg.sinMensajesMinutos > 0 && cfg.horario) {
    const apertura = aperturaDeHoy(cfg.horario, ahora);
    if (apertura !== null) {
      const desde = Math.max(s.ultimoEntranteEn ?? 0, apertura);
      minutosSinMensajes = Math.floor((ahora - desde) / 60_000);
      sinMensajes = minutosSinMensajes >= cfg.sinMensajesMinutos;
    }
  }

  const bucle = s.vinculado && (s.arranquesUltimaHora >= cfg.bucleArranquesHora || (s.reconexionesUltimaHora ?? 0) >= cfg.bucleReconexionesHora);
  return {
    solo_prekeys: { se_cumple: soloPreKeys },
    sin_mensajes: { se_cumple: sinMensajes, minutos: minutosSinMensajes },
    bucle: { se_cumple: bucle },
  };
}

function textoDeAviso(tipo: TipoAlarma, s: Senales, cfg: ConfigAlarmas, extra: { minutos?: number }, sigue: boolean): string {
  const prefijo = sigue ? "Sigue igual. " : "";
  if (tipo === "solo_prekeys") {
    return (
      `${prefijo}${CANAL} lleva ${cfg.soloPreKeysMinutos} min solo reponiendo llaves de seguridad (pre-keys) sin procesar ` +
      "ningún mensaje. Es la señal de que está atascado en bucle, como en la caída del 24 de noviembre. El sistema no lo " +
      "reinicia a la carrera. Si sigue así, la salida es limpiar las pre-keys viejas (se hace sola a los 30 min si hay " +
      "demasiadas, y deja respaldo). Detalle: docs/JUAN_PUENTE.md («Si WhatsApp se atasca»)."
    );
  }
  if (tipo === "sin_mensajes") {
    return (
      `${prefijo}No entra ningún mensaje de clientas por ${CANAL} desde hace ${extra.minutos} min, en horario de atención. ` +
      "Puede ser un rato tranquilo o que el puente dejó de recibir sin darse cuenta. Para salir de la duda, escríbele al " +
      "número desde otro teléfono: el asistente tiene que contestar."
    );
  }
  const salida = s.ultimaSalida ? ` La última vez terminó con «${s.ultimaSalida}».` : "";
  const memoria = s.rssMaximoMB !== null ? ` Llegó a usar ${s.rssMaximoMB} MB de memoria.` : "";
  const pista =
    s.ultimaSalida?.includes("137") && s.rssMaximoMB !== null && s.rssMaximoMB > 200
      ? " Con un 137 y la memoria cerca de 256 MB, el contenedor `lite` se está quedando chico (ver docs/JUAN_PUENTE.md, «Decisiones de infraestructura»)."
      : "";
  return (
    `${prefijo}${CANAL} se reinició ${s.arranquesUltimaHora} veces o reconectó ${s.reconexionesUltimaHora ?? "?"} veces ` +
    `en la última hora: algo lo está tumbando una y otra vez.${salida}${memoria}${pista} Revisa /api/estado y docs/JUAN_PUENTE.md.`
  );
}

function textoDeRecuperado(tipo: TipoAlarma): string {
  if (tipo === "solo_prekeys") return `${CANAL} volvió a procesar mensajes: ya no está solo reponiendo pre-keys.`;
  if (tipo === "sin_mensajes") return `Volvieron a entrar mensajes de clientas por ${CANAL}.`;
  return `${CANAL} ya no se está reiniciando en bucle (lleva una hora estable).`;
}

/**
 * Evalúa las tres alarmas. Cada una avisa al cumplirse, repite cada `reavisoMinutos` mientras siga
 * y avisa UNA vez cuando termina (solo si había avisado). «Sin mensajes» termina en silencio si lo
 * que pasó fue que se acabó el horario (no entró nada: decir «volvieron los mensajes» sería mentir).
 */
export function evaluarAlarmas(s: Senales, previo: EstadoAlarmas, ahora: number, cfg: ConfigAlarmas): { avisos: Aviso[]; estado: EstadoAlarmas } {
  const estado = normalizarAlarmas(structuredClone(previo));
  const avisos: Aviso[] = [];
  const conds = condiciones(s, ahora, cfg);

  for (const tipo of Object.keys(conds) as TipoAlarma[]) {
    const c = conds[tipo];
    const a = estado[tipo];
    if (c.se_cumple) {
      if (a.desde === null) a.desde = ahora;
      const toca = !a.activo || a.ultimoAvisoEn === null || ahora - a.ultimoAvisoEn >= cfg.reavisoMinutos * 60_000;
      if (toca) {
        avisos.push({ tipo, recuperado: false, texto: textoDeAviso(tipo, s, cfg, c, a.activo) });
        a.activo = true;
        a.ultimoAvisoEn = ahora;
      }
      continue;
    }
    if (a.activo) {
      const entroAlgo = tipo !== "sin_mensajes" || (s.ultimoEntranteEn !== null && a.ultimoAvisoEn !== null && s.ultimoEntranteEn > a.ultimoAvisoEn);
      if (entroAlgo) avisos.push({ tipo, recuperado: true, texto: textoDeRecuperado(tipo) });
    }
    estado[tipo] = { activo: false, desde: null, ultimoAvisoEn: null };
  }
  return { avisos, estado };
}

/** Lo que el contenedor cuenta de la última reconexión (ver `ultimaReconexion` en nucleo.mjs). */
export interface ReconexionDelContenedor {
  id: string;
  terminada: boolean;
  atendidos: number;
  sinContestar: number;
  conversacionesSinContestar: number;
}

/**
 * El aviso de UNA vez por reconexión: cuántas conversaciones quedaron con mensajes atrasados viejos
 * que el asistente no contesta solo. Solo cuando WhatsApp terminó de entregar lo atrasado (si no, el
 * número todavía sube) y solo si hay alguna.
 */
export function avisoDeAtrasados(r: Partial<ReconexionDelContenedor> | null | undefined, yaAvisadoDe: string | null, vigenteMin: number): Aviso | null {
  if (!r || typeof r.id !== "string" || r.terminada !== true) return null;
  if (r.id === yaAvisadoDe) return null;
  const conversaciones = Number(r.conversacionesSinContestar ?? 0);
  if (!(conversaciones > 0)) return null;
  const mensajes = Number(r.sinContestar ?? conversaciones);
  const atendidos = Number(r.atendidos ?? 0);
  return {
    tipo: "atrasados",
    recuperado: false,
    texto:
      `Al volver la conexión de ${CANAL} llegaron ${mensajes} mensajes atrasados de ${conversaciones} ` +
      `${conversaciones === 1 ? "conversación" : "conversaciones"} que el asistente NO contesta solo (llevaban más de ` +
      `${vigenteMin} min esperando). Revísalos y contéstalos desde el teléfono.` +
      (atendidos > 0 ? ` Los ${atendidos} más recientes sí los atendió el asistente.` : ""),
  };
}
