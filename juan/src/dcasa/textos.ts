// Los pocos textos que el SISTEMA (no el modelo) le dice al cliente. Voz de la marca (Baby Caleb, 2026-11-24): de usted,
// siempre, breve y sin emojis (son avisos fijos). Si Odoo manda su propio texto (p. ej. el de `pasar_a_vendedora`), ese gana.

import type { Horario } from "../config";

export const TEXTO_TOPE_DIARIO =
  "Gracias por escribirnos tanto. Por hoy ya le acompañé un buen rato; mañana seguimos con gusto. " +
  "Si prefiere, escríbame *persona* y le atiende una vendedora.";

export const TEXTO_FALLO_TECNICO = "Ahorita no puedo responderle yo, pero ya avisé: una vendedora le atiende por aquí en cuanto pueda.";

export const TEXTO_ARCHIVO_RECIBIDO = "Recibí su archivo. Una vendedora lo revisa y le confirma por aquí.";

/** «08:00» → «8:00 a. m.»; «17:00» → «5:00 p. m.» */
export function horaLegible(hhmm: string): string {
  const [h, m] = hhmm.split(":").map(Number);
  const sufijo = h >= 12 ? "p. m." : "a. m.";
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}:${String(m).padStart(2, "0")} ${sufijo}`;
}

/** Solo si `pasar_a_vendedora` no trajo texto (o Odoo no contestó). */
export function textoPasoAVendedora(dentroDeHorario: boolean, horario: Horario): string {
  return dentroDeHorario
    ? "Listo, ya le pasé su consulta a una vendedora. Le escribe por aquí en un momento."
    : `Listo, dejé su consulta para una vendedora. Le escribe por aquí cuando abramos, a partir de las ${horaLegible(horario.inicio).replace(/\.$/, "")}.`;
}
