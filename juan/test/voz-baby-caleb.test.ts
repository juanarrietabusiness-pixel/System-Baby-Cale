/**
 * La voz de Baby Caleb en TODOS los asistentes del Worker (el dueño, 2026-11-24, con la voz de su CRM): de usted, siempre;
 * uno o dos emojis cálidos como mucho; y los precios tal cual los da la herramienta (Baby Caleb no cobra ITBMS).
 *
 * Una sola prueba que recorre los prompts de Juan (mensajería y seguimiento), de Andrés (el chat de la web), de las
 * sugerencias del panel y las notas de reintento del guardián: que ninguno vuelva a pedir el tuteo, los cero emojis o el
 * «+ ITBMS» siempre de D'CASA. El resumen del panel es para el equipo y se queda sin emojis (test/odoo-panel-resumir.test.ts).
 */
import { describe, expect, it } from "vitest";
import { CONFIG_POR_DEFECTO, normalizarConfig } from "../src/config";
import { promptEstable, promptSeguimiento } from "../src/dcasa/prompt";
import { notaDeCorreccion } from "../src/dcasa/salvaguardas";
import { promptDelBorrador, validarPeticion, type PeticionSugerir } from "../src/odoo-panel-sugerir";
import { promptTienda } from "../src/tienda/prompt";
import { AHORA_INICIAL } from "./helpers/mundo";

const cfg = normalizarConfig({ nombre_publico: "el equipo de Baby Caleb", brian_tienda: { activo: true } });
const peticion = validarPeticion({
  conversacion_id: 7,
  canal: "whatsapp_cloud",
  mensajes: [{ autor: "cliente", texto: "hola, ¿tienes pañales talla M?" }],
  nombre: "Karen",
  interes: "pañales talla M",
  etiquetas: [],
}) as PeticionSugerir;

const PROMPTS: Record<string, string> = {
  "Juan (mensajería)": promptEstable(cfg),
  "Juan (seguimiento 1)": promptSeguimiento(cfg, { numero: 1, interes: "pañales talla M", ahora: AHORA_INICIAL }),
  "Juan (seguimiento 2)": promptSeguimiento(cfg, { numero: 2, interes: "", ahora: AHORA_INICIAL }),
  "Andrés (chat de la web)": promptTienda(cfg),
  "Sugerencias del panel": promptDelBorrador(cfg, peticion),
  "Guardián (nota de reintento)": notaDeCorreccion([{ tipo: "precio_inventado", detalle: "$5.00" }]),
};

describe("la voz de Baby Caleb en todos los prompts", () => {
  it.each(Object.entries(PROMPTS))("%s: no dice «Tuteo» ni «Cero emojis»", (_nombre, p) => {
    expect(p).not.toMatch(/\btuteo\b/i);
    expect(p).not.toMatch(/cero emojis|sin emojis/i);
  });

  it.each(Object.entries(PROMPTS))("%s: pide «usted» y prohíbe tutear", (_nombre, p) => {
    expect(p).toMatch(/de usted, siempre/i);
    expect(p).toMatch(/nunca tutees/i);
  });

  it.each(Object.entries(PROMPTS))("%s: uno o dos emojis como mucho", (_nombre, p) => {
    expect(p).toMatch(/uno o dos (?:emojis )?(?:cálidos |por mensaje )?como mucho|uno o dos como mucho/i);
  });

  it.each(Object.entries(PROMPTS))("%s: nunca pide el «+ ITBMS» siempre", (_nombre, p) => {
    expect(p).not.toMatch(/SIEMPRE con «\+ ITBMS»|Precios con «\+ ITBMS»|los precios son \+ ITBMS|\(con «\+ ITBMS»\)|subtotal, (?:el )?ITBMS y (?:el )?total/i);
  });

  it("los prompts con precios piden copiar precio_texto tal cual", () => {
    for (const nombre of ["Juan (mensajería)", "Andrés (chat de la web)", "Sugerencias del panel"]) {
      expect(PROMPTS[nombre], nombre).toContain("copia el campo precio_texto tal cual: si trae «+ ITBMS», va con eso; si no, sin nada.");
    }
  });

  it("con el nombre de fábrica tampoco queda nada de lo de D'CASA", () => {
    for (const p of [promptEstable(CONFIG_POR_DEFECTO), promptTienda(CONFIG_POR_DEFECTO)]) {
      expect(p).not.toMatch(/\btuteo\b|cero emojis/i);
      expect(p).toMatch(/de usted, siempre/i);
    }
  });
});
