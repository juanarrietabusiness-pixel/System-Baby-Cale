import { describe, expect, it } from "vitest";
import { crearAlmacen, iniciarEsquema, PRE_KEYS_A_CONSERVAR, RESPALDO_PODA_DIAS } from "../src/almacen";
import { crearCifrador } from "../src/cifrado";
import { PODA_AUTOMATICA_DESDE, PODA_CADA_MS, PODA_EMERGENCIA_CADA_MS, PODA_EMERGENCIA_TRAS_MS, decidirPoda } from "../src/poda";
import { sqlDePrueba } from "./ayuda/sql";

// La autolimpieza de pre-keys. Lo que de verdad destrabó el CRM de Baby Caleb el 24-nov-2026: de 15.934 pre-keys
// se dejaron 1.005, con respaldo, y sin tocar la credencial del dispositivo (no hubo que escanear el QR).

const CLAVE = "clave-de-prueba-para-la-sesion-0123456789";
const DIA = 24 * 60 * 60_000;

async function montar() {
  const bd = sqlDePrueba();
  iniciarEsquema(bd.sql);
  const reloj = { t: Date.UTC(2026, 10, 24, 19, 0, 0) };
  const almacen = crearAlmacen({ sql: bd.sql, transaccion: bd.transaccion, cifrador: await crearCifrador(CLAVE), ahora: () => reloj.t });
  return { almacen, reloj, bd };
}

/** Como lo dejó el bucle: 812 del vínculo (todas a la misma hora) y luego miles de 5 en 5. */
async function sesionInflada(a: Awaited<ReturnType<typeof montar>>, total: number) {
  await a.almacen.set("creds", '{"nextPreKeyId":' + (total + 1) + ',"firstUnuploadedPreKeyId":' + (total + 1) + "}");
  await a.almacen.lote({ escribir: { "session-50760261919.0": "S", "lid-mapping-1": "L", "identity-key-x": "I" } });
  const vinculo: Record<string, string> = {};
  for (let i = 1; i <= 812; i++) vinculo[`pre-key-${i}`] = `pk${i}`;
  await a.almacen.lote({ escribir: vinculo });
  for (let i = 813; i <= total; i += 5) {
    a.reloj.t += 60_000;
    const rafaga: Record<string, string> = {};
    for (let j = i; j < Math.min(i + 5, total + 1); j++) rafaga[`pre-key-${j}`] = `pk${j}`;
    await a.almacen.lote({ escribir: rafaga });
  }
}

describe("podarPreKeys: conserva las 1.000 más nuevas, respalda lo demás y NUNCA toca creds", () => {
  it("de 15.934 deja 1.000 (las de número más alto), con respaldo, y la sesión sigue completa", async () => {
    const a = await montar();
    await sesionInflada(a, 15_934);
    expect(a.almacen.contarPreKeys()).toBe(15_934);
    const borradas = a.almacen.podarPreKeys();
    expect(borradas).toBe(15_934 - PRE_KEYS_A_CONSERVAR);
    expect(a.almacen.contarPreKeys()).toBe(PRE_KEYS_A_CONSERVAR);
    // quedaron las más nuevas, por NÚMERO (no por orden de texto: «pre-key-999» > «pre-key-15000» como texto)
    const leidas = (await a.almacen.lote({ leer: ["pre-key-14934", "pre-key-14935", "pre-key-15934", "pre-key-999", "pre-key-1"] })).valores;
    expect(leidas).toEqual({ "pre-key-14934": null, "pre-key-14935": "pk14935", "pre-key-15934": "pk15934", "pre-key-999": null, "pre-key-1": null });
    // la credencial y el resto de la sesión, intactos
    expect(await a.almacen.get("creds")).toContain("nextPreKeyId");
    expect((await a.almacen.lote({ leer: ["session-50760261919.0", "lid-mapping-1", "identity-key-x"] })).valores).toEqual({
      "session-50760261919.0": "S",
      "lid-mapping-1": "L",
      "identity-key-x": "I",
    });
    expect(a.almacen.respaldoDePoda().llaves).toBe(borradas);
  });

  it("el respaldo guarda las MISMAS filas cifradas (nada en claro)", async () => {
    const a = await montar();
    await sesionInflada(a, 1100);
    a.almacen.podarPreKeys();
    const volcado = a.bd.volcado("wa_prekeys_podadas");
    expect(volcado).not.toContain("pk1");
    expect(a.almacen.respaldoDePoda().llaves).toBe(100);
  });

  it("se puede deshacer: vuelven las de la última poda, sin pisar ninguna que exista", async () => {
    const a = await montar();
    await sesionInflada(a, 1500);
    a.almacen.podarPreKeys();
    await a.almacen.set("pre-key-3", "NUEVA"); // una que Baileys volvió a escribir después de la poda
    const r = a.almacen.deshacerUltimaPoda();
    expect(r.restauradas).toBe(499);
    expect(a.almacen.contarPreKeys()).toBe(1500);
    expect(await a.almacen.get("pre-key-3")).toBe("NUEVA");
    expect(await a.almacen.get("pre-key-4")).toBe("pk4");
    expect(a.almacen.respaldoDePoda().llaves).toBe(0);
    expect(a.almacen.deshacerUltimaPoda()).toEqual({ restauradas: 0, podadaEn: null });
  });

  it("con pocas no hace nada; dos podas seguidas no borran más de la cuenta", async () => {
    const a = await montar();
    await sesionInflada(a, 900);
    expect(a.almacen.podarPreKeys()).toBe(0);
    await sesionInflada(a, 1200);
    expect(a.almacen.podarPreKeys()).toBe(200);
    expect(a.almacen.podarPreKeys()).toBe(0);
  });

  it(`el respaldo se purga solo a los ${RESPALDO_PODA_DIAS} días`, async () => {
    const a = await montar();
    await sesionInflada(a, 1100);
    a.almacen.podarPreKeys();
    a.reloj.t += (RESPALDO_PODA_DIAS - 1) * DIA;
    expect(a.almacen.purgarRespaldoDePoda()).toBe(0);
    a.reloj.t += 2 * DIA;
    expect(a.almacen.purgarRespaldoDePoda()).toBe(100);
    expect(a.almacen.respaldoDePoda()).toEqual({ llaves: 0, ultimaPodaEn: null });
  });
});

describe("decidirPoda: cuándo se poda sola", () => {
  const T = Date.UTC(2026, 10, 24, 12, 0, 0);
  const tranquila = { activo: false, desde: null };
  const muchas = () => 15_934;

  it("con pocas pre-keys, nunca (y ni las cuenta si por tiempo no tocaba)", () => {
    let contadas = 0;
    const contar = () => {
      contadas += 1;
      return PODA_AUTOMATICA_DESDE;
    };
    expect(decidirPoda({ contarPreKeys: contar, veredicto: "sano", ultimaPodaAutomaticaEn: null, soloPreKeys: tranquila, ahora: T })).toBe(null);
    expect(contadas).toBe(1);
    expect(decidirPoda({ contarPreKeys: contar, veredicto: "caido", ultimaPodaAutomaticaEn: null, soloPreKeys: tranquila, ahora: T })).toBe(null);
    expect(contadas).toBe(1);
  });

  it("de rutina: con el canal sano y como mucho una vez por semana (y solo cuando se revisa la rutina)", () => {
    expect(decidirPoda({ contarPreKeys: muchas, veredicto: "sano", ultimaPodaAutomaticaEn: null, soloPreKeys: tranquila, ahora: T })).toBe("semanal");
    expect(decidirPoda({ contarPreKeys: muchas, veredicto: "sano", ultimaPodaAutomaticaEn: T - PODA_CADA_MS + 1, soloPreKeys: tranquila, ahora: T })).toBe(null);
    expect(decidirPoda({ contarPreKeys: muchas, veredicto: "caido", ultimaPodaAutomaticaEn: null, soloPreKeys: tranquila, ahora: T })).toBe(null);
    expect(decidirPoda({ contarPreKeys: muchas, veredicto: "sano", ultimaPodaAutomaticaEn: null, soloPreKeys: tranquila, ahora: T, revisarRutina: false })).toBe(null);
  });

  it("de emergencia: tras media hora seguida de «solo pre-keys», como mucho una vez al día", () => {
    const enBucle = (min: number) => ({ activo: true, desde: T - min * 60_000 });
    expect(decidirPoda({ contarPreKeys: muchas, veredicto: "caido", ultimaPodaAutomaticaEn: null, soloPreKeys: enBucle(29), ahora: T })).toBe(null);
    expect(PODA_EMERGENCIA_TRAS_MS).toBe(30 * 60_000);
    expect(decidirPoda({ contarPreKeys: muchas, veredicto: "caido", ultimaPodaAutomaticaEn: null, soloPreKeys: enBucle(30), ahora: T })).toBe("emergencia");
    expect(decidirPoda({ contarPreKeys: muchas, veredicto: "caido", ultimaPodaAutomaticaEn: T - PODA_EMERGENCIA_CADA_MS + 1, soloPreKeys: enBucle(90), ahora: T })).toBe(null);
  });
});
