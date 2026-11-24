// La autolimpieza de pre-keys: cuándo se poda sola.
//
// Las pre-keys son llaves de un solo uso que WhatsApp reparte a las clientas nuevas. Baileys sube
// 812 al vincular y repone de 5 en 5; borra la que se usa, pero las que nunca se usan (y las que
// repone en cada reconexión fallida) se quedan para siempre. En el CRM de Baby Caleb llegaron a
// 15.934 (lo sano son unas 800). El 24-nov-2026 se dejaron 1.005 —con respaldo— y a los 8 minutos
// el puente, que llevaba 14 horas en bucle, volvió a funcionar. El mecanismo exacto no está
// demostrado (las caídas cortas de antes se curaron sin limpiar), pero limpiar con respaldo y sin
// tocar la credencial del dispositivo no le hizo daño a nada y es lo que lo destrabó.
//
// ¿Es seguro hacerlo solo, con Baileys 7.0.0-rc14? Sí, con estas condiciones:
//   · se conservan las 1.000 de NÚMERO más alto: las que pueden seguir en los servidores de
//     WhatsApp o en un mensaje atrasado son siempre de las más nuevas (los números solo suben);
//   · NUNCA se toca `creds` (tocarla obliga a escanear el QR) ni ninguna otra llave;
//   · lo borrado queda respaldado (cifrado) 14 días y se puede devolver (`POST /api/podar/deshacer`);
//   · si aun así una clienta llegara con una pre-key podada, Baileys pide el reenvío y WhatsApp
//     arma una sesión nueva (no se pierde el mensaje: llega un poco más tarde).
// Por eso la poda automática NO es la válvula de todos los días: solo corre cuando hay de verdad
// demasiadas, una vez por semana con el canal sano, o una vez al día como salida de emergencia
// cuando el puente lleva media hora en la firma del bucle («solo pre-keys»).

import { PRE_KEYS_A_CONSERVAR } from "./almacen";
import type { EstadoAlarma } from "./alarmas";
import type { Veredicto } from "./comun";

/** Con menos que esto no se poda solo (lo sano ronda 800; 812 recién vinculado). */
export const PODA_AUTOMATICA_DESDE = 2000;
/** La poda de rutina: como mucho una vez por semana (lo que sugirió el informe del CRM de origen). */
export const PODA_CADA_MS = 7 * 24 * 60 * 60_000;
/** La de emergencia: tras media hora seguida de la alarma «solo pre-keys»… */
export const PODA_EMERGENCIA_TRAS_MS = 30 * 60_000;
/** …y como mucho una vez al día (si una poda no lo destrabó, otra enseguida tampoco). */
export const PODA_EMERGENCIA_CADA_MS = 24 * 60 * 60_000;

export type MotivoPoda = "semanal" | "emergencia";

/**
 * ¿Toca podar sola ahora? `contarPreKeys` se llama solo si por tiempo ya tocaría (contarlas recorre
 * la sesión entera, y la vigilancia corre cada 30 s).
 */
export function decidirPoda(i: {
  contarPreKeys: () => number;
  veredicto: Veredicto;
  ultimaPodaAutomaticaEn: number | null;
  soloPreKeys: Pick<EstadoAlarma, "activo" | "desde">;
  ahora: number;
  /** La de rutina solo se revisa de vez en cuando (en el mantenimiento de cada hora), no cada 30 s. */
  revisarRutina?: boolean;
}): MotivoPoda | null {
  const desdeLaUltima = i.ultimaPodaAutomaticaEn === null ? Infinity : i.ahora - i.ultimaPodaAutomaticaEn;
  const emergencia =
    i.soloPreKeys.activo && i.soloPreKeys.desde !== null && i.ahora - i.soloPreKeys.desde >= PODA_EMERGENCIA_TRAS_MS && desdeLaUltima >= PODA_EMERGENCIA_CADA_MS;
  const semanal = (i.revisarRutina ?? true) && i.veredicto === "sano" && desdeLaUltima >= PODA_CADA_MS;
  if (!emergencia && !semanal) return null;
  if (i.contarPreKeys() <= Math.max(PODA_AUTOMATICA_DESDE, PRE_KEYS_A_CONSERVAR)) return null;
  return emergencia ? "emergencia" : "semanal";
}
