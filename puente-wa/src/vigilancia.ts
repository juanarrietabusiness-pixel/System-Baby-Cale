// La decisión de cada vigilancia, sin entrada/salida.
//
// El Durable Object vigila a su contenedor cada 30 s (y el cron de plataforma cada
// minuto lo respalda). Aquí está el JUICIO: dado lo que dijo el contenedor, qué anota
// el diario y qué hay que hacer (nada, esperar, pedir que reconecte, o el martillo de
// destruir el contenedor). Aparte y puro para poder probarlo a fondo.
//
// PACIENTE desde la caída del CRM de Baby Caleb (24-nov-2026, ver src/comun.ts): el martillo
// solo cae si lleva un buen rato sin conexión Y sin progreso, nunca en los minutos de gracia
// tras un arranque, y cada reinicio seguido espera el doble que el anterior.

import {
  GRACIA_TRAS_ARRANQUE_MS,
  OCUPADO_MAXIMO_MS,
  REINICIAR_SIN_PROGRESO_MS,
  REINICIO_ESPERA_MAX_MS,
  type Veredicto,
} from "./comun";
import { alarmasNuevas, normalizarAlarmas, type EstadoAlarmas } from "./alarmas";

/** Lo último que el contenedor dijo de su memoria y su procesador (sobrevive a su muerte). */
export interface UltimasMetricas {
  en: string;
  rssMB: number | null;
  rssMaximoMB: number | null;
  heapUsadoMB: number | null;
  cpuPorcentaje: number | null;
  retrasoBucleMs: number | null;
}

export interface Diario {
  arrancadoEn: string;
  latidos: number;
  arranquesContenedor: number;
  ultimoArranque: string | null;
  ultimaMuerteVista: string | null;
  /**
   * Cuándo se vigiló por última vez. Es la señal que faltó el 16-sep-2026: el canal
   * llevaba horas mudo y el panel lo mostraba como si nada.
   */
  ultimoLatidoEn: number | null;
  /** Vigilancias seguidas con el contenedor prendido pero WhatsApp caído (solo para mostrar). */
  desconectadoSeguidos: number;
  /** La última vez que se vio el socket de WhatsApp realmente abierto (ISO). */
  ultimaConexionVista: string | null;
  /**
   * Desde cuándo NO hay una conexión sana (ms desde epoch), o null si la hay. Es lo que
   * lee `/api/estado` («desconectado desde hace N min») y lo que dispara el aviso.
   */
  sinConexionDesde: number | null;
  /** Cuántas veces hubo que destruir el contenedor para recuperarlo. */
  reiniciosForzados: number;
  /** Reinicios forzados SEGUIDOS, sin un rato sano en medio: cada uno duplica la espera del siguiente. */
  reiniciosSeguidos: number;
  /** Cuándo fue el último reinicio forzado (ms). */
  ultimoReinicioForzadoEn: number | null;
  /** Desde cuándo está «ocupado» (sin conexión pero con progreso), o null. */
  ocupadoDesde: number | null;
  /** Cuándo arrancó el contenedor las últimas veces (ms): muchos en una hora es un bucle. */
  arranquesRecientes: number[];
  /** Lo último que impidió vigilar, si algo lo impidió. */
  ultimoFalloDelLatido: string | null;
  /** Por qué murió el contenedor la última vez, según el propio runtime. */
  ultimaSalida: string | null;
  /** Lo último que el contenedor dijo de su memoria y procesador (para saber de qué murió). */
  ultimasMetricas: UltimasMetricas | null;
  /** Aviso por Telegram: hay uno enviado y todavía no se avisó la recuperación. */
  avisoActivo: boolean;
  ultimoAvisoEn: number | null;
  /** Las alarmas nuevas (solo pre-keys, sin mensajes, bucle): ver src/alarmas.ts. */
  alarmas: EstadoAlarmas;
  /** La reconexión cuyos mensajes atrasados ya se avisaron (id que da el contenedor). */
  atrasadosAvisadosDe: string | null;
  /** Última poda AUTOMÁTICA de pre-keys (ms) y lo que hizo (también las manuales). */
  ultimaPodaAutomaticaEn: number | null;
  ultimaPoda: { en: string; borradas: number; motivo: string } | null;
  /** Última copia diaria de la sesión (ms desde epoch) y su resultado. */
  ultimaCopiaEn: number | null;
  ultimaCopiaR2: string | null;
  ultimoFalloDeCopia: string | null;
}

export function diarioNuevo(ahora = new Date()): Diario {
  return {
    arrancadoEn: ahora.toISOString(),
    latidos: 0,
    arranquesContenedor: 0,
    ultimoArranque: null,
    ultimaMuerteVista: null,
    ultimoLatidoEn: null,
    desconectadoSeguidos: 0,
    ultimaConexionVista: null,
    sinConexionDesde: null,
    reiniciosForzados: 0,
    reiniciosSeguidos: 0,
    ultimoReinicioForzadoEn: null,
    ocupadoDesde: null,
    arranquesRecientes: [],
    ultimoFalloDelLatido: null,
    ultimaSalida: null,
    ultimasMetricas: null,
    avisoActivo: false,
    ultimoAvisoEn: null,
    alarmas: alarmasNuevas(),
    atrasadosAvisadosDe: null,
    ultimaPodaAutomaticaEn: null,
    ultimaPoda: null,
    ultimaCopiaEn: null,
    ultimaCopiaR2: null,
    ultimoFalloDeCopia: null,
  };
}

/**
 * Un diario escrito por una versión anterior no trae los campos nuevos. Sin estos
 * respaldos, el primer `+= 1` daría NaN y ese NaN viajaría al estado.
 */
export function normalizarDiario(guardado: Partial<Diario> | undefined | null, ahora = new Date()): Diario {
  const base = diarioNuevo(ahora);
  if (!guardado) return base;
  const d = { ...base, ...guardado };
  d.alarmas = normalizarAlarmas(guardado.alarmas);
  if (!Array.isArray(d.arranquesRecientes)) d.arranquesRecientes = [];
  return d;
}

export type Accion = "nada" | "esperar" | "pedir_reconexion" | "reiniciar";

export interface ContextoVigilancia {
  /** El último progreso real visto (ms): tráfico de llaves o un mensaje entregado. */
  progresoEn?: number | null;
  /** El contenedor dice que tiene un intento de conexión en curso: no se le pide otro. */
  conectando?: boolean;
}

/** Cuánto hay que esperar antes del próximo martillo, según los reinicios seguidos. */
export function esperaAntesDeReiniciar(reiniciosSeguidos: number): number {
  return Math.min(REINICIAR_SIN_PROGRESO_MS * 2 ** Math.max(0, reiniciosSeguidos), REINICIO_ESPERA_MAX_MS);
}

/**
 * Aplica lo que dijo el contenedor al diario y decide qué hacer.
 *
 *   sano                    → todo al día; nada que hacer (y se olvida la racha de reinicios).
 *   esperando-a-una-persona → sin vincular o esperando el QR. NO es un fallo y NO se
 *                             reinicia: reiniciar genera un código nuevo y le tumba al
 *                             dueño el que está mirando. Sí cuenta como «sin conexión»
 *                             para el estado y el aviso.
 *   ocupado                 → sin conexión (o sin respuesta) pero con progreso: está
 *                             procesando lo atrasado. Esperar. Si dura más de
 *                             `OCUPADO_MAXIMO_MS` sin conectar, se trata como caído.
 *   caido                   → en los minutos de gracia tras un arranque, esperar. Después,
 *                             pedirle que reconecte (barato; si el contenedor tiene un intento
 *                             en curso, ni eso). El martillo solo cuando lleva
 *                             `esperaAntesDeReiniciar()` sin conexión NI progreso.
 */
export function aplicarVigilancia(
  diario: Diario,
  veredicto: Veredicto,
  ahora: number,
  ctx: ContextoVigilancia = {},
): { diario: Diario; accion: Accion } {
  const d: Diario = { ...diario, arranquesRecientes: [...(diario.arranquesRecientes ?? [])] };

  if (veredicto === "sano") {
    d.desconectadoSeguidos = 0;
    d.sinConexionDesde = null;
    d.ultimaConexionVista = new Date(ahora).toISOString();
    d.reiniciosSeguidos = 0;
    d.ocupadoDesde = null;
    return { diario: d, accion: "nada" };
  }

  if (d.sinConexionDesde === null) d.sinConexionDesde = ahora;

  if (veredicto === "esperando-a-una-persona") {
    d.desconectadoSeguidos = 0;
    d.ocupadoDesde = null;
    return { diario: d, accion: "nada" };
  }

  d.desconectadoSeguidos += 1;

  let creerleAlProgreso = true;
  if (veredicto === "ocupado") {
    if (d.ocupadoDesde === null) d.ocupadoDesde = ahora;
    if (ahora - d.ocupadoDesde < OCUPADO_MAXIMO_MS) return { diario: d, accion: "esperar" };
    // Lleva demasiado «ocupado» sin llegar a conectar: ya no se le cree al progreso (sigue como caído).
    creerleAlProgreso = false;
  } else {
    d.ocupadoDesde = null;
  }

  const arranque = d.ultimoArranque ? Date.parse(d.ultimoArranque) : NaN;
  if (Number.isFinite(arranque) && ahora - arranque < GRACIA_TRAS_ARRANQUE_MS) return { diario: d, accion: "esperar" };

  // Desde cuándo está quieto: lo último entre la caída, el último progreso y el último martillo.
  const quietoDesde = Math.max(d.sinConexionDesde, creerleAlProgreso ? (ctx.progresoEn ?? 0) : 0, d.ultimoReinicioForzadoEn ?? 0);
  if (ahora - quietoDesde >= esperaAntesDeReiniciar(d.reiniciosSeguidos)) {
    d.reiniciosForzados += 1;
    d.reiniciosSeguidos += 1;
    d.ultimoReinicioForzadoEn = ahora;
    d.desconectadoSeguidos = 0;
    d.ocupadoDesde = null;
    return { diario: d, accion: "reiniciar" };
  }
  return { diario: d, accion: ctx.conectando ? "esperar" : "pedir_reconexion" };
}

export type EstadoCanal = "apagado" | "iniciando" | "necesita_qr" | "conectado" | "desconectado";

/**
 * El estado que se le muestra al mundo en `/api/estado`:
 *
 *   apagado       PUENTE_ACTIVO no está en «on»: no se enciende el contenedor.
 *   conectado     WhatsApp conectado.
 *   necesita_qr   hay que escanear un código (nunca vinculado, o desvinculado desde el teléfono).
 *   desconectado  estuvo vinculado y ahora no hay conexión (se está reintentando).
 *   iniciando     recién encendido, todavía sin respuesta del contenedor.
 */
export function resumirEstado(i: {
  activo: boolean;
  conexion: string | null | undefined;
  vinculadoAlgunaVez: boolean;
  sinConexionDesde: number | null;
  ahora: number;
}): { estado: EstadoCanal; conectado: boolean; desconectadoMin: number | null } {
  if (!i.activo) return { estado: "apagado", conectado: false, desconectadoMin: null };
  const min = i.sinConexionDesde === null ? null : Math.max(0, Math.floor((i.ahora - i.sinConexionDesde) / 60_000));
  if (i.conexion === "conectada") return { estado: "conectado", conectado: true, desconectadoMin: null };
  if (i.conexion === "esperando-qr" || i.conexion === "desvinculada") {
    return { estado: "necesita_qr", conectado: false, desconectadoMin: min };
  }
  if (i.vinculadoAlgunaVez && min !== null) return { estado: "desconectado", conectado: false, desconectadoMin: min };
  return { estado: "iniciando", conectado: false, desconectadoMin: min };
}
