import { describe, expect, it } from "vitest";
import {
  ALARMAS_POR_DEFECTO,
  alarmasNuevas,
  aperturaDeHoy,
  avisoDeAtrasados,
  evaluarAlarmas,
  leerConfigAlarmas,
  leerHorario,
  normalizarAlarmas,
  type ConfigAlarmas,
  type Senales,
} from "../src/alarmas";

// Panamá es UTC-5 todo el año. Martes 24-nov-2026.
const PANAMA = (hhmm: string, dia = "2026-11-24") => Date.parse(`${dia}T${hhmm}:00-05:00`);
const MIN = 60_000;

const HORARIO = { inicio: "09:00", fin: "18:00", dias: [1, 2, 3, 4, 5, 6], zona: "America/Panama" };
const CFG: ConfigAlarmas = { ...ALARMAS_POR_DEFECTO, horario: HORARIO, reavisoMinutos: 120 };

function senales(extra: Partial<Senales> = {}): Senales {
  return {
    vinculado: true,
    caidaAvisada: false,
    ventana: { lotesSoloPreKeys: 0, preKeysNuevas: 0, preKeysUsadas: 0, trafico: 10, entrantes: 3 },
    ultimoEntranteEn: PANAMA("10:00"),
    arranquesUltimaHora: 1,
    reconexionesUltimaHora: 0,
    ultimaSalida: null,
    rssMaximoMB: null,
    ...extra,
  };
}

describe("configuración de las alarmas", () => {
  it("horario: «HH:MM», días 0-6 y zona; cualquier cosa rara la apaga (mejor sin alarma que una que avisa de madrugada)", () => {
    expect(leerHorario({ HORARIO_INICIO: "09:00", HORARIO_FIN: "18:00", HORARIO_DIAS: "1,2,3,4,5,6", HORARIO_ZONA: "America/Panama" })).toEqual(HORARIO);
    expect(leerHorario({ HORARIO_INICIO: "9", HORARIO_FIN: "18:00", HORARIO_DIAS: "1" })).toBe(null);
    expect(leerHorario({ HORARIO_INICIO: "18:00", HORARIO_FIN: "09:00", HORARIO_DIAS: "1" })).toBe(null);
    expect(leerHorario({ HORARIO_INICIO: "09:00", HORARIO_FIN: "18:00", HORARIO_DIAS: "" })).toBe(null);
    expect(leerHorario({})).toBe(null);
  });

  it("los umbrales se leen de las variables, con topes; sin nada, los de por defecto", () => {
    expect(leerConfigAlarmas({})).toMatchObject({ sinMensajesMinutos: 60, soloPreKeysMinutos: 15, rafagasSoloPreKeys: 3, horario: null, reavisoMinutos: 120 });
    expect(leerConfigAlarmas({ ALERTA_SIN_MENSAJES_MINUTOS: "0" }).sinMensajesMinutos).toBe(0);
    expect(leerConfigAlarmas({ ALERTA_SIN_MENSAJES_MINUTOS: "90" }).sinMensajesMinutos).toBe(90);
    expect(leerConfigAlarmas({ ALERTA_SIN_MENSAJES_MINUTOS: "abc" }).sinMensajesMinutos).toBe(60);
  });

  it("aperturaDeHoy: en horario da cuándo abrió hoy; fuera de horario o en domingo, null", () => {
    expect(aperturaDeHoy(HORARIO, PANAMA("10:37"))).toBe(PANAMA("09:00"));
    expect(aperturaDeHoy(HORARIO, PANAMA("08:59"))).toBe(null);
    expect(aperturaDeHoy(HORARIO, PANAMA("18:00"))).toBe(null);
    expect(aperturaDeHoy(HORARIO, PANAMA("11:00", "2026-11-22"))).toBe(null); // domingo
  });

  it("un estado guardado a medias no rompe nada", () => {
    expect(normalizarAlarmas({ bucle: { activo: true } as any })).toMatchObject({ bucle: { activo: true, desde: null }, solo_prekeys: { activo: false } });
    expect(normalizarAlarmas(undefined)).toEqual(alarmasNuevas());
  });
});

describe("alarma «solo pre-keys» (la firma exacta de la caída del 24-nov)", () => {
  const bucle = { lotesSoloPreKeys: 5, preKeysNuevas: 25, preKeysUsadas: 0, trafico: 0, entrantes: 0 };

  it("avisa cuando en 15 min solo hubo ráfagas de pre-keys y ni un mensaje; repite a las 2 h; avisa al recuperarse", () => {
    const t = PANAMA("03:00");
    let r = evaluarAlarmas(senales({ ventana: bucle }), alarmasNuevas(), t, CFG);
    expect(r.avisos).toHaveLength(1);
    expect(r.avisos[0]).toMatchObject({ tipo: "solo_prekeys", recuperado: false });
    expect(r.avisos[0].texto).toContain("pre-keys");
    expect(r.estado.solo_prekeys).toMatchObject({ activo: true, desde: t });

    r = evaluarAlarmas(senales({ ventana: bucle }), r.estado, t + 30 * MIN, CFG);
    expect(r.avisos).toHaveLength(0); // no insiste
    r = evaluarAlarmas(senales({ ventana: bucle }), r.estado, t + 120 * MIN, CFG);
    expect(r.avisos[0].texto).toMatch(/^Sigue igual/);
    expect(r.estado.solo_prekeys.desde).toBe(t); // el «desde» no se pisa

    r = evaluarAlarmas(senales(), r.estado, t + 125 * MIN, CFG);
    expect(r.avisos).toEqual([expect.objectContaining({ tipo: "solo_prekeys", recuperado: true })]);
    expect(r.estado.solo_prekeys).toEqual({ activo: false, desde: null, ultimoAvisoEn: null });
  });

  it("un arranque sano (repone UNA vez y enseguida escribe sesiones) no avisa", () => {
    const sano = { lotesSoloPreKeys: 1, preKeysNuevas: 5, preKeysUsadas: 0, trafico: 40, entrantes: 2 };
    expect(evaluarAlarmas(senales({ ventana: sano }), alarmasNuevas(), PANAMA("10:00"), CFG).avisos).toEqual([]);
    // dos ráfagas todavía no es bucle
    expect(evaluarAlarmas(senales({ ventana: { ...bucle, lotesSoloPreKeys: 2 } }), alarmasNuevas(), PANAMA("10:00"), CFG).avisos).toEqual([]);
    // una pre-key usada = una clienta nueva cuyo mensaje se descifró: no es bucle
    expect(evaluarAlarmas(senales({ ventana: { ...bucle, preKeysUsadas: 1 } }), alarmasNuevas(), PANAMA("10:00"), CFG).avisos).toEqual([]);
  });

  it("una instalación nueva (nunca conectó) no avisa nada", () => {
    expect(evaluarAlarmas(senales({ vinculado: false, ventana: bucle, arranquesUltimaHora: 9 }), alarmasNuevas(), PANAMA("10:00"), CFG).avisos).toEqual([]);
  });
});

describe("alarma «sin mensajes» en horario de atención", () => {
  it("avisa a los 60 min sin mensajes de clientas, contados desde la apertura (no desde anoche)", () => {
    const anoche = PANAMA("17:50", "2026-11-23");
    expect(evaluarAlarmas(senales({ ultimoEntranteEn: anoche }), alarmasNuevas(), PANAMA("09:30"), CFG).avisos).toEqual([]);
    const r = evaluarAlarmas(senales({ ultimoEntranteEn: anoche }), alarmasNuevas(), PANAMA("10:00"), CFG);
    expect(r.avisos).toHaveLength(1);
    expect(r.avisos[0]).toMatchObject({ tipo: "sin_mensajes" });
    expect(r.avisos[0].texto).toContain("60 min");
  });

  it("fuera de horario, en domingo o con la alarma en 0: nunca", () => {
    const viejo = PANAMA("08:00", "2026-11-20");
    expect(evaluarAlarmas(senales({ ultimoEntranteEn: viejo }), alarmasNuevas(), PANAMA("20:00"), CFG).avisos).toEqual([]);
    expect(evaluarAlarmas(senales({ ultimoEntranteEn: viejo }), alarmasNuevas(), PANAMA("12:00", "2026-11-22"), CFG).avisos).toEqual([]);
    expect(evaluarAlarmas(senales({ ultimoEntranteEn: viejo }), alarmasNuevas(), PANAMA("12:00"), { ...CFG, sinMensajesMinutos: 0 }).avisos).toEqual([]);
    expect(evaluarAlarmas(senales({ ultimoEntranteEn: viejo }), alarmasNuevas(), PANAMA("12:00"), { ...CFG, horario: null }).avisos).toEqual([]);
  });

  it("si ya se avisó que está desconectado, no suma este aviso (sería el mismo problema dos veces)", () => {
    expect(evaluarAlarmas(senales({ ultimoEntranteEn: PANAMA("08:00"), caidaAvisada: true }), alarmasNuevas(), PANAMA("12:00"), CFG).avisos).toEqual([]);
  });

  it("al entrar un mensaje avisa que volvieron; si lo que pasó es que se acabó el horario, termina en silencio", () => {
    let r = evaluarAlarmas(senales({ ultimoEntranteEn: PANAMA("08:00") }), alarmasNuevas(), PANAMA("12:00"), CFG);
    const tras = evaluarAlarmas(senales({ ultimoEntranteEn: PANAMA("12:10") }), r.estado, PANAMA("12:10"), CFG);
    expect(tras.avisos).toEqual([expect.objectContaining({ tipo: "sin_mensajes", recuperado: true })]);

    r = evaluarAlarmas(senales({ ultimoEntranteEn: PANAMA("08:00") }), alarmasNuevas(), PANAMA("17:30"), CFG);
    const cierre = evaluarAlarmas(senales({ ultimoEntranteEn: PANAMA("08:00") }), r.estado, PANAMA("18:05"), CFG);
    expect(cierre.avisos).toEqual([]);
    expect(cierre.estado.sin_mensajes.activo).toBe(false);
  });
});

describe("alarma «bucle»", () => {
  it("4 arranques o 6 reconexiones en una hora; el texto da la pista del 137 y la memoria", () => {
    const r = evaluarAlarmas(senales({ arranquesUltimaHora: 4, ultimaSalida: "código 137 · runtime_signal", rssMaximoMB: 248 }), alarmasNuevas(), PANAMA("10:00"), CFG);
    expect(r.avisos[0].tipo).toBe("bucle");
    expect(r.avisos[0].texto).toContain("137");
    expect(r.avisos[0].texto).toContain("248 MB");
    expect(r.avisos[0].texto).toContain("se está quedando chico");
    expect(evaluarAlarmas(senales({ reconexionesUltimaHora: 6 }), alarmasNuevas(), PANAMA("10:00"), CFG).avisos[0].tipo).toBe("bucle");
    expect(evaluarAlarmas(senales({ arranquesUltimaHora: 3, reconexionesUltimaHora: 5 }), alarmasNuevas(), PANAMA("10:00"), CFG).avisos).toEqual([]);
  });

  it("los textos nunca llevan números de teléfono ni claves", () => {
    const todo = evaluarAlarmas(
      senales({ ventana: { lotesSoloPreKeys: 9, preKeysNuevas: 45, preKeysUsadas: 0, trafico: 0, entrantes: 0 }, arranquesUltimaHora: 9, ultimoEntranteEn: PANAMA("07:00") }),
      alarmasNuevas(),
      PANAMA("12:00"),
      CFG,
    );
    expect(todo.avisos).toHaveLength(3);
    expect(JSON.stringify(todo.avisos)).not.toMatch(/\d{8,}|token|clave/i);
  });
});

describe("aviso de mensajes atrasados sin contestar", () => {
  const r = { id: "2026-11-24T19:08:00.000Z", terminada: true, atendidos: 4, sinContestar: 31, conversacionesSinContestar: 12 };

  it("una vez por reconexión, cuando WhatsApp terminó de entregar, y solo si quedó alguna conversación", () => {
    const a = avisoDeAtrasados(r, null, 15)!;
    expect(a.texto).toContain("31 mensajes atrasados de 12 conversaciones");
    expect(a.texto).toContain("15 min");
    expect(a.texto).toContain("Los 4 más recientes");
    expect(avisoDeAtrasados(r, r.id, 15)).toBe(null); // ya avisado
    expect(avisoDeAtrasados({ ...r, terminada: false }, null, 15)).toBe(null); // todavía está llegando
    expect(avisoDeAtrasados({ ...r, conversacionesSinContestar: 0, sinContestar: 0 }, null, 15)).toBe(null);
    expect(avisoDeAtrasados(null, null, 15)).toBe(null);
    expect(avisoDeAtrasados({ ...r, conversacionesSinContestar: 1, sinContestar: 1, atendidos: 0 }, null, 15)!.texto).toContain("1 conversación ");
  });
});
