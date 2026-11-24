import { describe, expect, it } from "vitest";
import { GRACIA_TRAS_ARRANQUE_MS, OCUPADO_MAXIMO_MS, PROGRESO_VIGENTE_MS, REINICIAR_SIN_PROGRESO_MS } from "../src/comun";
import { aplicarVigilancia, diarioNuevo, esperaAntesDeReiniciar, normalizarDiario, resumirEstado, type Diario } from "../src/vigilancia";

const T0 = 1_800_000_000_000;
const MIN = 60_000;

/** Un diario cuyo contenedor arrancó hace `hace` minutos (fuera de la gracia si es > 10). */
function arrancadoHace(hace: number, extra: Partial<Diario> = {}): Diario {
  return { ...diarioNuevo(), ultimoArranque: new Date(T0 - hace * MIN).toISOString(), ...extra };
}

/** Corre vigilancias cada 30 s desde `desde` hasta `hasta` (ms) con el mismo veredicto; devuelve las acciones. */
function correr(d: Diario, veredicto: Parameters<typeof aplicarVigilancia>[1], desde: number, hasta: number, ctx = {}) {
  const acciones: { t: number; accion: string }[] = [];
  for (let t = desde; t <= hasta; t += 30_000) {
    const r = aplicarVigilancia(d, veredicto, t, ctx);
    d = r.diario;
    acciones.push({ t, accion: r.accion });
  }
  return { diario: d, acciones };
}

// CAMBIO de sentido (2026-11-24, caída del CRM de Baby Caleb): antes el martillo (destruir el contenedor) caía a la
// quinta vigilancia seguida sin conexión, ≈2,5 min, aunque el puente estuviera procesando lo atrasado. Así una caída
// de un rato se volvió un bucle de 14 horas. Ahora: gracia tras cada arranque, el martillo solo tras 10 min sin
// conexión NI progreso, y cada reinicio seguido espera el doble.
describe("aplicarVigilancia: el vigilante paciente", () => {
  it("sano: todo al día, nada que hacer", () => {
    const { diario, accion } = aplicarVigilancia(diarioNuevo(), "sano", T0);
    expect(accion).toBe("nada");
    expect(diario).toMatchObject({ desconectadoSeguidos: 0, sinConexionDesde: null });
    expect(diario.ultimaConexionVista).toBe(new Date(T0).toISOString());
  });

  it("caído (fuera de la gracia): primero se pide reconectar (lo barato) y se anota desde cuándo no hay conexión", () => {
    const r = aplicarVigilancia(arrancadoHace(60), "caido", T0);
    expect(r.accion).toBe("pedir_reconexion");
    expect(r.diario).toMatchObject({ desconectadoSeguidos: 1, sinConexionDesde: T0 });
    // «desde cuándo» no se pisa en los latidos siguientes
    const r2 = aplicarVigilancia(r.diario, "caido", T0 + 30_000);
    expect(r2.diario.sinConexionDesde).toBe(T0);
    expect(r2.diario.desconectadoSeguidos).toBe(2);
  });

  it("en los minutos de gracia tras un arranque solo espera: ni le pide reconectar ni lo destruye", () => {
    expect(GRACIA_TRAS_ARRANQUE_MS).toBe(10 * MIN);
    const { acciones } = correr(arrancadoHace(0), "caido", T0, T0 + GRACIA_TRAS_ARRANQUE_MS - 30_000);
    expect(acciones.every((a) => a.accion === "esperar")).toBe(true);
  });

  it("el martillo cae solo tras 10 min sin conexión NI progreso (antes: 2,5 min)", () => {
    const { acciones, diario } = correr(arrancadoHace(60), "caido", T0, T0 + REINICIAR_SIN_PROGRESO_MS);
    const primero = acciones.find((a) => a.accion === "reiniciar")!;
    expect(primero.t - T0).toBe(REINICIAR_SIN_PROGRESO_MS);
    expect(acciones.filter((a) => a.accion === "reiniciar")).toHaveLength(1);
    expect(acciones.filter((a) => a.t - T0 < REINICIAR_SIN_PROGRESO_MS).every((a) => a.accion === "pedir_reconexion")).toBe(true);
    expect(diario).toMatchObject({ reiniciosForzados: 1, reiniciosSeguidos: 1, desconectadoSeguidos: 0, ultimoReinicioForzadoEn: primero.t });
  });

  it("un progreso reciente corre el reloj del martillo (se cuenta desde lo último que avanzó)", () => {
    const progresoEn = T0 + 8 * MIN; // escribió sesiones hace poco
    const r = aplicarVigilancia(arrancadoHace(60, { sinConexionDesde: T0 }), "caido", T0 + 12 * MIN, { progresoEn });
    expect(r.accion).toBe("pedir_reconexion"); // 4 min desde el progreso, no 12 desde la caída
    const r2 = aplicarVigilancia(r.diario, "caido", progresoEn + REINICIAR_SIN_PROGRESO_MS, { progresoEn });
    expect(r2.accion).toBe("reiniciar");
  });

  it("cada reinicio seguido espera el doble: 10 → 20 → 40 → 60 → 60 min", () => {
    expect([0, 1, 2, 3, 4, 9].map((n) => esperaAntesDeReiniciar(n) / MIN)).toEqual([10, 20, 40, 60, 60, 60]);
    // Simulado: 4 horas caído y sin progreso. Tras cada martillo hay un arranque (y su gracia).
    let d = arrancadoHace(60);
    const martillos: number[] = [];
    for (let t = T0; t <= T0 + 4 * 60 * MIN; t += 30_000) {
      const r = aplicarVigilancia(d, "caido", t);
      d = r.diario;
      if (r.accion === "reiniciar") {
        martillos.push(t);
        d = { ...d, ultimoArranque: new Date(t).toISOString() };
      }
    }
    const separaciones = martillos.slice(1).map((t, i) => (t - martillos[i]) / MIN);
    expect((martillos[0] - T0) / MIN).toBe(10);
    expect(separaciones.slice(0, 4)).toEqual([20, 40, 60, 60]);
    // En 4 horas, 6 martillos y no 96 como con la regla vieja (uno cada 2,5 min).
    expect(martillos.length).toBeLessThanOrEqual(6);
  });

  it("un latido sano en medio corta la racha y la espera vuelve a 10 min", () => {
    let d = arrancadoHace(60, { reiniciosSeguidos: 3, ultimoReinicioForzadoEn: T0 - 90 * MIN });
    d = aplicarVigilancia(d, "sano", T0).diario;
    expect(d.reiniciosSeguidos).toBe(0);
    expect(d.desconectadoSeguidos).toBe(0);
    const { acciones } = correr(d, "caido", T0 + 30_000, T0 + 30_000 + REINICIAR_SIN_PROGRESO_MS);
    expect(acciones.at(-1)!.accion).toBe("reiniciar");
  });

  it("ocupado (sin conexión pero con progreso): espera, aunque pasen horas de la regla vieja", () => {
    const { acciones, diario } = correr(arrancadoHace(60), "ocupado", T0, T0 + 50 * MIN, { progresoEn: T0 });
    expect(acciones.every((a) => a.accion === "esperar")).toBe(true);
    expect(diario.ocupadoDesde).toBe(T0);
    expect(diario.reiniciosForzados).toBe(0);
  });

  it("ocupado más de una hora sin llegar a conectar: ya no se le cree al progreso", () => {
    const d = arrancadoHace(120, { sinConexionDesde: T0, ocupadoDesde: T0 });
    const ahora = T0 + OCUPADO_MAXIMO_MS;
    const r = aplicarVigilancia(d, "ocupado", ahora, { progresoEn: ahora - PROGRESO_VIGENTE_MS / 2 });
    expect(r.accion).toBe("reiniciar");
  });

  it("si el contenedor tiene un intento de conexión en curso, NO se le pide otro (cortarlo es empezar de cero)", () => {
    const r = aplicarVigilancia(arrancadoHace(60), "caido", T0, { conectando: true });
    expect(r.accion).toBe("esperar");
    // pero el martillo sigue valiendo si se pasa del tiempo sin conectar ni avanzar
    const r2 = aplicarVigilancia(r.diario, "caido", T0 + REINICIAR_SIN_PROGRESO_MS, { conectando: true });
    expect(r2.accion).toBe("reiniciar");
  });

  it("esperando a una persona (QR / desvinculado): NUNCA se reinicia (tumbaría el QR que está mirando)", () => {
    let d = arrancadoHace(60);
    for (let i = 0; i < 200; i++) {
      const r = aplicarVigilancia(d, "esperando-a-una-persona", T0 + i * 30_000);
      expect(r.accion).toBe("nada");
      d = r.diario;
    }
    expect(d.reiniciosForzados).toBe(0);
    expect(d.sinConexionDesde).toBe(T0); // pero sí cuenta como «sin conexión» para el estado y el aviso
  });

  it("no muta el diario que recibe", () => {
    const original = arrancadoHace(60, { arranquesRecientes: [T0 - MIN] });
    const copia = structuredClone(original);
    aplicarVigilancia(original, "caido", T0 + REINICIAR_SIN_PROGRESO_MS);
    expect(original).toEqual(copia);
  });
});

describe("normalizarDiario", () => {
  it("un diario viejo sin los campos nuevos no produce NaN", () => {
    const d = normalizarDiario({ latidos: 5 } as any);
    expect(d.latidos).toBe(5);
    expect(d.desconectadoSeguidos).toBe(0);
    expect(d.reiniciosForzados).toBe(0);
    expect(d.sinConexionDesde).toBe(null);
    expect(d.avisoActivo).toBe(false);
    const r = aplicarVigilancia(d, "caido", T0);
    expect(Number.isNaN(r.diario.desconectadoSeguidos)).toBe(false);
  });

  it("sin nada guardado, un diario nuevo", () => {
    expect(normalizarDiario(undefined)).toMatchObject({ latidos: 0, ultimoLatidoEn: null });
    expect(normalizarDiario(null)).toMatchObject({ latidos: 0 });
  });
});

describe("resumirEstado (lo que ve Juan en /api/estado)", () => {
  const base = { activo: true, vinculadoAlgunaVez: true, sinConexionDesde: null, ahora: T0 };

  it("conectado", () => {
    expect(resumirEstado({ ...base, conexion: "conectada" })).toEqual({ estado: "conectado", conectado: true, desconectadoMin: null });
  });

  it("necesita QR (sin vincular, esperando el código, o desvinculado desde el teléfono)", () => {
    expect(resumirEstado({ ...base, conexion: "esperando-qr", vinculadoAlgunaVez: false })).toMatchObject({ estado: "necesita_qr", conectado: false });
    expect(resumirEstado({ ...base, conexion: "desvinculada", sinConexionDesde: T0 - 7 * MIN })).toEqual({
      estado: "necesita_qr",
      conectado: false,
      desconectadoMin: 7,
    });
  });

  it("desconectado desde hace N min", () => {
    expect(resumirEstado({ ...base, conexion: "cerrada", sinConexionDesde: T0 - 12 * MIN - 5000 })).toEqual({
      estado: "desconectado",
      conectado: false,
      desconectadoMin: 12,
    });
    // El contenedor ni contesta: también es «desconectado» si antes estuvo vinculado.
    expect(resumirEstado({ ...base, conexion: null, sinConexionDesde: T0 - 3 * MIN })).toMatchObject({ estado: "desconectado", desconectadoMin: 3 });
  });

  it("iniciando: recién encendido, nunca estuvo vinculado", () => {
    expect(resumirEstado({ ...base, conexion: "arrancando", vinculadoAlgunaVez: false })).toMatchObject({ estado: "iniciando" });
    expect(resumirEstado({ ...base, conexion: null, vinculadoAlgunaVez: false, sinConexionDesde: T0 })).toMatchObject({ estado: "iniciando" });
  });

  it("apagado", () => {
    expect(resumirEstado({ ...base, activo: false, conexion: "conectada" })).toEqual({ estado: "apagado", conectado: false, desconectadoMin: null });
  });
});
