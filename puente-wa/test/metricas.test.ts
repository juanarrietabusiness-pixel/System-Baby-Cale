import { describe, expect, it } from "vitest";
import { TIPO_HISTORIAL, crearFiltroDeHistorial } from "../contenedor/lib/historial.mjs";
import { clasificarLlaves } from "../contenedor/lib/llaves.mjs";
import { crearMedidor, crearSerie } from "../contenedor/lib/metricas.mjs";

// Las piezas que nacieron de la caída del CRM de Baby Caleb (24-nov-2026): la firma «solo pre-keys», la
// reconexión liviana y las métricas que faltaron para saber si el contenedor murió por memoria.

describe("clasificarLlaves: ¿trabaja o da vueltas?", () => {
  it("un lote de solo pre-keys nuevas es la firma del bucle (no es progreso)", () => {
    const c = clasificarLlaves(["pre-key-101", "pre-key-102", "pre-key-103", "pre-key-104", "pre-key-105"]);
    expect(c).toEqual({ preKeysNuevas: 5, preKeysUsadas: 0, trafico: 0, creds: 0, soloPreKeys: true, progreso: false });
    // con la credencial al lado sigue siendo la misma firma (Baileys guarda creds al reponer)
    expect(clasificarLlaves(["creds", "pre-key-1"]).soloPreKeys).toBe(true);
  });

  it("sesiones, identidades, LID, sender-keys… son tráfico de verdad", () => {
    const c = clasificarLlaves(["session-50760261919.0", "identity-key-x", "lid-mapping-1", "sender-key-g", "app-state-sync-version-a"]);
    expect(c).toMatchObject({ trafico: 5, soloPreKeys: false, progreso: true });
  });

  it("una pre-key BORRADA es una clienta nueva cuyo mensaje se descifró: progreso", () => {
    expect(clasificarLlaves([], ["pre-key-7"])).toMatchObject({ preKeysUsadas: 1, progreso: true, soloPreKeys: false });
    expect(clasificarLlaves(["pre-key-9"], ["pre-key-7"]).soloPreKeys).toBe(false);
  });

  it("solo la credencial: ni progreso ni bucle", () => {
    expect(clasificarLlaves(["creds"])).toMatchObject({ creds: 1, progreso: false, soloPreKeys: false });
  });
});

describe("filtro de historial (reconexión liviana)", () => {
  it("baja solo lo chico y necesario; nunca las conversaciones viejas", () => {
    const filtro = crearFiltroDeHistorial(undefined);
    const si = Object.entries(TIPO_HISTORIAL).filter(([, n]) => filtro({ syncType: n })).map(([k]) => k);
    expect(si.sort()).toEqual(["INITIAL_BOOTSTRAP", "NON_BLOCKING_DATA", "PUSH_NAME"]);
    expect(filtro({ syncType: null })).toBe(false);
  });

  it("usa los números del proto de Baileys cuando viene", () => {
    const proto = { HistorySync: { HistorySyncType: { INITIAL_BOOTSTRAP: 10, PUSH_NAME: 14, NON_BLOCKING_DATA: 15, RECENT: 13 } } };
    const filtro = crearFiltroDeHistorial(proto);
    expect(filtro({ syncType: 10 })).toBe(true);
    expect(filtro({ syncType: 13 })).toBe(false);
  });
});

describe("crearSerie: cuántas cosas en los últimos 15 minutos", () => {
  it("suma dentro de la ventana y olvida lo que salió de ella; su memoria no crece con el tráfico", () => {
    const reloj = { t: 0 };
    const s = crearSerie({ ahora: () => reloj.t });
    for (let i = 0; i < 10_000; i++) {
      s.sumar(1);
      reloj.t += 6_000; // 10.000 sumas a lo largo de casi 17 horas
    }
    // en la ventana caben ~15 min = 150 sumas (± una cubeta)
    expect(s.total()).toBeGreaterThanOrEqual(140);
    expect(s.total()).toBeLessThanOrEqual(160);
    reloj.t += 20 * 60_000;
    expect(s.total()).toBe(0);
  });
});

describe("crearMedidor: memoria, procesador y atraso del bucle", () => {
  const MB = 1024 * 1024;

  function proceso(rss: number, cpu: { user: number; system: number }) {
    return {
      memoryUsage: () => ({ rss, heapUsed: 40 * MB, heapTotal: 60 * MB, external: 2 * MB, arrayBuffers: MB }),
      cpuUsage: () => ({ ...cpu }),
    };
  }

  it("calcula el % de un núcleo entre muestras, lee cgroup si está y guarda el pico de memoria", () => {
    const reloj = { t: 0 };
    const cpu = { user: 0, system: 0 };
    let rss = 100 * MB;
    const p = { memoryUsage: () => proceso(rss, cpu).memoryUsage(), cpuUsage: () => ({ ...cpu }) };
    const archivos: Record<string, string> = {
      "/sys/fs/cgroup/memory.current": String(180 * MB),
      "/sys/fs/cgroup/memory.max": String(256 * MB),
      "/sys/fs/cgroup/cpu.max": "6250 100000",
      "/sys/fs/cgroup/cpu.stat": "usage_usec 0\nnr_throttled 0\nthrottled_usec 0",
    };
    const retraso = { percentile: () => 2_500_000_000, max: 4_000_000_000, reset: () => {} };
    const m = crearMedidor({ proceso: p, leerArchivo: (r) => archivos[r], retraso, ahora: () => reloj.t, so: { loadavg: () => [1.234, 0, 0], totalmem: () => 512 * MB, freemem: () => 128 * MB } });
    reloj.t += 30_000;
    cpu.user += 1_500_000; // 1,5 s de CPU en 30 s = 5 % de un núcleo (cerca del techo de un `lite`)
    archivos["/sys/fs/cgroup/cpu.stat"] = "usage_usec 1500000\nnr_throttled 10\nthrottled_usec 3000000";
    rss = 230 * MB;
    m.muestrear();
    rss = 120 * MB;
    const l = m.leer();
    expect(l.cpu).toMatchObject({ porcentaje: 5, limitadoPorcentaje: 10, limiteVcpu: 0.0625, ventanaS: 30 });
    expect(l.memoria).toMatchObject({ rssMB: 120, rssMaximoMB: 230, heapUsadoMB: 40, contenedorMB: 180, limiteMB: 256 });
    expect(l.bucle).toEqual({ retrasoP99Ms: 2500, retrasoMaxMs: 4000 });
    expect(l.sistema).toMatchObject({ carga1m: 1.23, memoriaTotalMB: 512, memoriaLibreMB: 128 });
  });

  it("si algo no se puede medir, queda en null y NUNCA rompe", () => {
    const roto = {
      memoryUsage: () => {
        throw new Error("no");
      },
      cpuUsage: () => {
        throw new Error("no");
      },
    };
    const m = crearMedidor({
      proceso: roto,
      leerArchivo: () => {
        throw new Error("sin cgroup");
      },
    });
    expect(() => m.muestrear()).not.toThrow();
    const l = m.leer();
    expect(l.memoria).toBe(null);
    expect(l.cpu.porcentaje).toBe(null);
    expect(l.sistema).toBe(null);
  });

  it("sin dependencias usa el proceso real de Node", () => {
    const m = crearMedidor();
    m.muestrear();
    expect(m.leer().memoria!.rssMB).toBeGreaterThan(0);
  });
});
