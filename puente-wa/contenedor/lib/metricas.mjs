// @ts-check
// Lo que el contenedor dice de sí mismo en /estado: memoria, procesador, si el proceso está
// trabado, y contadores por ventana de tiempo.
//
// Existe por la caída del CRM de Baby Caleb (24-nov-2026): el contenedor moría con el código
// 137 y NO se pudo saber si era por falta de memoria o porque lo mataba el vigilante, porque
// Cloudflare no muestra la memoria ni el procesador por dentro. Ahora el propio proceso lo
// cuenta, y el Durable Object guarda la última lectura (sobrevive a la muerte del contenedor).
//
// Todo llega inyectado (el proceso, el sistema operativo, la lectura de archivos, el medidor
// del bucle de eventos) para probarlo sin depender de la máquina. Cualquier lectura que falle
// queda en null: una métrica que no se pudo medir no puede tumbar el /estado.

/** Ancho de cada cubeta de las series (un minuto). */
export const CUBETA_MS = 60_000;
/** La ventana de las series: los últimos 15 minutos (la misma del aviso «solo pre-keys»). */
export const VENTANA_MS = 15 * 60_000;

const MB = 1024 * 1024;
const enMB = (/** @type {number} */ bytes) => Math.round((bytes / MB) * 10) / 10;

/**
 * Un contador por ventana deslizante: cuántas cosas pasaron en los últimos `ventanaMs`.
 * Guarda una cubeta por minuto, así que su memoria no crece con el tráfico.
 *
 * @param {{ ventanaMs?: number, cubetaMs?: number, ahora?: () => number }} [o]
 */
export function crearSerie({ ventanaMs = VENTANA_MS, cubetaMs = CUBETA_MS, ahora = () => Date.now() } = {}) {
  /** @type {Map<number, number>} */
  const cubetas = new Map();
  /** @param {number} t */
  function podar(t) {
    const primera = Math.floor((t - ventanaMs) / cubetaMs);
    for (const k of cubetas.keys()) if (k <= primera) cubetas.delete(k);
  }
  return {
    /** @param {number} [n] */
    sumar(n = 1) {
      if (!n) return;
      const t = ahora();
      const k = Math.floor(t / cubetaMs);
      cubetas.set(k, (cubetas.get(k) ?? 0) + n);
      podar(t);
    },
    total() {
      podar(ahora());
      let s = 0;
      for (const v of cubetas.values()) s += v;
      return s;
    },
  };
}

/** @param {() => any} f */
function intentar(f) {
  try {
    return f();
  } catch {
    return null;
  }
}

/**
 * Lee un número de un archivo de cgroup v2 (`memory.current`, `memory.max`…). `max` = sin límite.
 * @param {((ruta: string) => string) | null | undefined} leer
 * @param {string} ruta
 * @returns {number | null}
 */
function numeroDeArchivo(leer, ruta) {
  if (!leer) return null;
  const crudo = intentar(() => String(leer(ruta)).trim());
  if (!crudo || crudo === "max") return null;
  const n = Number(crudo);
  return Number.isFinite(n) ? n : null;
}

/**
 * `cpu.stat` de cgroup v2 → { usage_usec, throttled_usec, nr_throttled… }.
 * @param {((ruta: string) => string) | null | undefined} leer
 * @returns {Record<string, number> | null}
 */
function estadisticaDeCpu(leer) {
  if (!leer) return null;
  const crudo = intentar(() => String(leer("/sys/fs/cgroup/cpu.stat")));
  if (!crudo) return null;
  /** @type {Record<string, number>} */
  const salida = {};
  for (const linea of crudo.split("\n")) {
    const [k, v] = linea.trim().split(/\s+/);
    if (k && v !== undefined && Number.isFinite(Number(v))) salida[k] = Number(v);
  }
  return salida;
}

/**
 * El tope de procesador del contenedor (`cpu.max` = «6250 100000» → 0.0625 vCPU, el `lite`).
 * @param {((ruta: string) => string) | null | undefined} leer
 */
function limiteDeCpu(leer) {
  if (!leer) return null;
  const crudo = intentar(() => String(leer("/sys/fs/cgroup/cpu.max")).trim());
  if (!crudo) return null;
  const [cuota, periodo] = crudo.split(/\s+/);
  if (cuota === "max") return null;
  const c = Number(cuota);
  const p = Number(periodo);
  return Number.isFinite(c) && Number.isFinite(p) && p > 0 ? Math.round((c / p) * 10_000) / 10_000 : null;
}

/**
 * @typedef {{
 *   proceso?: { memoryUsage(): any, cpuUsage(previo?: any): { user: number, system: number } },
 *   so?: { loadavg(): number[], totalmem(): number, freemem(): number } | null,
 *   leerArchivo?: ((ruta: string) => string) | null,
 *   retraso?: { percentile(p: number): number, max: number, reset(): void } | null,
 *   ahora?: () => number,
 * }} DepsMedidor
 */

/**
 * El medidor: `muestrear()` cada vigilancia (30 s) calcula el procesador usado desde la
 * muestra anterior; `leer()` devuelve la última foto (con la memoria al momento).
 *
 * @param {DepsMedidor} [deps]
 */
export function crearMedidor(deps = {}) {
  const proceso = deps.proceso ?? globalThis.process;
  const { so = null, leerArchivo = null, retraso = null } = deps;
  const ahora = deps.ahora ?? (() => Date.now());

  let anteriorCpu = intentar(() => proceso.cpuUsage());
  let anteriorEn = ahora();
  let anteriorCgroup = estadisticaDeCpu(leerArchivo);
  /** El pico de memoria desde que arrancó el proceso: lo que se quiere saber después de un 137. */
  let rssMaximoMB = 0;

  /** @type {{ porcentaje: number | null, limitadoPorcentaje: number | null, limiteVcpu: number | null, ventanaS: number | null }} */
  let cpu = { porcentaje: null, limitadoPorcentaje: null, limiteVcpu: limiteDeCpu(leerArchivo), ventanaS: null };
  /** @type {{ retrasoP99Ms: number | null, retrasoMaxMs: number | null }} */
  let bucle = { retrasoP99Ms: null, retrasoMaxMs: null };

  function memoria() {
    const m = intentar(() => proceso.memoryUsage());
    if (!m) return null;
    const rssMB = enMB(m.rss);
    if (rssMB > rssMaximoMB) rssMaximoMB = rssMB;
    const cgroupMB = numeroDeArchivo(leerArchivo, "/sys/fs/cgroup/memory.current");
    const limiteCgroup = numeroDeArchivo(leerArchivo, "/sys/fs/cgroup/memory.max");
    return {
      rssMB,
      rssMaximoMB,
      heapUsadoMB: enMB(m.heapUsed),
      heapTotalMB: enMB(m.heapTotal),
      externoMB: enMB(m.external ?? 0),
      arrayBuffersMB: enMB(m.arrayBuffers ?? 0),
      // Lo que cuenta el contenedor entero (no solo Node) y su tope, si se pueden leer.
      contenedorMB: cgroupMB === null ? null : enMB(cgroupMB),
      limiteMB: limiteCgroup === null ? null : enMB(limiteCgroup),
    };
  }

  function muestrear() {
    const t = ahora();
    const ms = t - anteriorEn;
    const actualCpu = intentar(() => proceso.cpuUsage());
    if (actualCpu && anteriorCpu && ms > 0) {
      const usadoMs = (actualCpu.user - anteriorCpu.user + (actualCpu.system - anteriorCpu.system)) / 1000;
      const cgroup = estadisticaDeCpu(leerArchivo);
      const limitadoMs =
        cgroup && anteriorCgroup && typeof cgroup.throttled_usec === "number" && typeof anteriorCgroup.throttled_usec === "number"
          ? (cgroup.throttled_usec - anteriorCgroup.throttled_usec) / 1000
          : null;
      cpu = {
        // Porcentaje de UN núcleo. En `lite` el techo es ~6 % (1/16 de procesador): cerca de ese
        // número es que está trabajando al máximo.
        porcentaje: Math.round((usadoMs / ms) * 1000) / 10,
        // Cuánto del tiempo estuvo frenado por el tope de procesador (si cgroup lo dice).
        limitadoPorcentaje: limitadoMs === null ? null : Math.round((limitadoMs / ms) * 1000) / 10,
        limiteVcpu: cpu.limiteVcpu,
        ventanaS: Math.round(ms / 1000),
      };
      anteriorCgroup = cgroup;
    }
    anteriorCpu = actualCpu ?? anteriorCpu;
    anteriorEn = t;
    if (retraso) {
      const p99 = intentar(() => retraso.percentile(99));
      const max = intentar(() => retraso.max);
      // El medidor de Node cuenta en nanosegundos.
      bucle = {
        retrasoP99Ms: typeof p99 === "number" && Number.isFinite(p99) ? Math.round(p99 / 1e6) : null,
        retrasoMaxMs: typeof max === "number" && Number.isFinite(max) ? Math.round(max / 1e6) : null,
      };
      intentar(() => retraso.reset());
    }
    memoria(); // también para que el pico de memoria se registre aunque nadie consulte
  }

  function leer() {
    return {
      memoria: memoria(),
      cpu,
      // Cuánto se atrasó el bucle de eventos: si pasa de unos segundos, el proceso está ocupado
      // descifrando y no alcanza a contestar el /estado a tiempo (no es que esté muerto).
      bucle,
      sistema: so
        ? {
            carga1m: intentar(() => Math.round(so.loadavg()[0] * 100) / 100),
            memoriaTotalMB: intentar(() => enMB(so.totalmem())),
            memoriaLibreMB: intentar(() => enMB(so.freemem())),
          }
        : null,
    };
  }

  return { muestrear, leer };
}
