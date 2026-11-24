// @ts-check
// Qué historial de WhatsApp vale la pena bajar al conectar.
//
// Al vincular, WhatsApp le ofrece al dispositivo nuevo paquetes de historial (comprimidos y
// a veces de varios MB). Baileys, por defecto, los baja y descomprime TODOS menos el «FULL».
// El puente no los usa para nada —no contesta historial— y en un contenedor `lite` (1/16 de
// procesador, 256 MiB) bajar y descomprimir historial es justo el trabajo que no se puede
// permitir mientras hay mensajes de clientas esperando. Lección de la caída del CRM de Baby
// Caleb (24-nov-2026): la reconexión tiene que ser LIVIANA.
//
// No se apaga todo: Baileys 7 advierte (y con razón) que sin ningún historial se queda sin
// los mapas iniciales de LID, y eso trae errores de sesión. Se conserva lo chico y necesario.

/** Los tipos de historial de WhatsApp (proto.HistorySync.HistorySyncType), por si el proto no viene. */
export const TIPO_HISTORIAL = Object.freeze({
  INITIAL_BOOTSTRAP: 0,
  INITIAL_STATUS_V3: 1,
  FULL: 2,
  RECENT: 3,
  PUSH_NAME: 4,
  NON_BLOCKING_DATA: 5,
  ON_DEMAND: 6,
});

/**
 * El filtro para la opción `shouldSyncHistoryMessage` de Baileys.
 *
 *   INITIAL_BOOTSTRAP   SÍ: trae los mapas iniciales de LID ↔ número (sin ellos, errores de sesión).
 *   PUSH_NAME           SÍ: solo nombres de contacto; es chico.
 *   NON_BLOCKING_DATA   SÍ: datos chicos del protocolo.
 *   RECENT, FULL        NO: conversaciones viejas enteras (lo pesado). Además, sin RECENT Baileys
 *                       no espera 20 s «sincronizando» y pasa directo a recibir mensajes.
 *   ON_DEMAND           NO: historial que se pide a mano; el puente nunca lo pide.
 *   INITIAL_STATUS_V3   NO: estados de los contactos; el puente no atiende estados.
 *
 * @param {any} [proto]  El `proto` de Baileys (para leer los números reales del enum).
 * @returns {(h: { syncType?: number | null }) => boolean}
 */
export function crearFiltroDeHistorial(proto) {
  const tipos = proto?.HistorySync?.HistorySyncType ?? TIPO_HISTORIAL;
  const permitidos = new Set([tipos.INITIAL_BOOTSTRAP, tipos.PUSH_NAME, tipos.NON_BLOCKING_DATA]);
  return (h) => h?.syncType !== null && h?.syncType !== undefined && permitidos.has(Number(h.syncType));
}
