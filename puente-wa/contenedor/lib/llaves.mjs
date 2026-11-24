// @ts-check
// Qué clase de llaves está escribiendo la sesión: la «firma» que separa un puente que
// trabaja de uno que da vueltas en el mismo lugar.
//
// Lección de la caída del CRM de Baby Caleb (24-nov-2026, docs/JUAN_PUENTE.md § F): durante
// 14 horas el puente solo escribía pre-keys DE 5 EN 5 y nada más. Eso es Baileys reponiendo
// llaves de un solo uso cada vez que conecta, y luego muriendo antes de procesar nada. Un
// puente que de verdad procesa mensajes escribe OTRAS llaves: sesiones de cada clienta,
// identidades, mapas de LID, y BORRA pre-keys (cada clienta nueva gasta una al escribir).
//
// Lo usan los dos lados: el contenedor (para su /estado) y el Durable Object (que ve TODAS
// las escrituras, sobreviva o no el contenedor, y con eso decide si hay progreso).

/** Prefijo con el que Baileys guarda cada pre-key («pre-key-123»). */
export const PREFIJO_PRE_KEY = "pre-key-";

/**
 * @typedef {{
 *   preKeysNuevas: number,
 *   preKeysUsadas: number,
 *   trafico: number,
 *   creds: number,
 *   soloPreKeys: boolean,
 *   progreso: boolean,
 * }} ClaseDeLote
 */

/**
 * Clasifica un lote de escrituras de la sesión.
 *
 *   preKeysNuevas  pre-keys escritas: Baileys reponiendo llaves (al conectar o cuando
 *                  WhatsApp avisa que quedan pocas). NO es progreso por sí solo.
 *   preKeysUsadas  pre-keys borradas: una clienta nueva escribió y su mensaje se descifró.
 *   trafico        sesiones, identidades, LID, sender-keys, app-state…: mensajes de verdad.
 *   creds          la credencial del dispositivo (cambia por muchas razones; no es progreso).
 *   soloPreKeys    el lote solo trae pre-keys nuevas: la firma de la caída del 24-nov.
 *   progreso       hubo trabajo real (tráfico o pre-keys usadas).
 *
 * @param {Iterable<string>} escritas  Claves escritas.
 * @param {Iterable<string>} [borradas]  Claves borradas.
 * @returns {ClaseDeLote}
 */
export function clasificarLlaves(escritas, borradas = []) {
  let preKeysNuevas = 0;
  let preKeysUsadas = 0;
  let trafico = 0;
  let creds = 0;
  for (const clave of escritas) {
    if (clave === "creds") creds += 1;
    else if (clave.startsWith(PREFIJO_PRE_KEY)) preKeysNuevas += 1;
    else trafico += 1;
  }
  for (const clave of borradas) {
    if (clave === "creds") creds += 1;
    else if (clave.startsWith(PREFIJO_PRE_KEY)) preKeysUsadas += 1;
    else trafico += 1;
  }
  const progreso = trafico > 0 || preKeysUsadas > 0;
  return { preKeysNuevas, preKeysUsadas, trafico, creds, soloPreKeys: preKeysNuevas > 0 && !progreso, progreso };
}
