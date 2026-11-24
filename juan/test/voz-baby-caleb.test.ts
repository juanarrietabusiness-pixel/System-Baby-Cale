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
import { presentacionPorDefecto, promptEstable, promptSeguimiento } from "../src/dcasa/prompt";
import { notaDeCorreccion } from "../src/dcasa/salvaguardas";
import { RegistroDelTurno, procesarResultado } from "../src/motor/herramientas";
import { promptDelBorrador, validarPeticion, type PeticionSugerir } from "../src/odoo-panel-sugerir";
import { promptTienda } from "../src/tienda/prompt";
import { AHORA_INICIAL, crearMundo } from "./helpers/mundo";

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

  // El dueño, 2026-11-24: con la clienta el asistente no tiene nombre propio; habla en nombre de la tienda («Somos Baby Caleb
  // Panamá»). «Juan» y «Andrés» quedan como nombres internos del código y del panel.
  it.each(Object.entries(PROMPTS))("%s: no le da al asistente un nombre propio («Soy Juan», «Soy Andrés»)", (_nombre, p) => {
    expect(p).not.toMatch(/\bsoy (?:Juan|Andrés|Brian)\b/i);
    expect(p).not.toMatch(/\beres (?:Juan|Andrés|Brian)\b/i);
    expect(p).not.toMatch(/te presentas como (?:Juan|Andrés)/i);
  });

  it("si preguntan si es un bot: «Soy el asistente virtual de …» (el nombre de Ajustes) y ofrece una persona del equipo", () => {
    expect(PROMPTS["Juan (mensajería)"]).toContain("Tú: Soy el asistente virtual de Baby Caleb. Si prefiere, le paso con una persona del equipo.");
    expect(PROMPTS["Andrés (chat de la web)"]).toContain("Tú (whatsapp=true): Soy el asistente virtual de Baby Caleb. Si prefiere, una persona del equipo le atiende por WhatsApp.");
    for (const nombre of ["Juan (mensajería)", "Andrés (chat de la web)"]) expect(PROMPTS[nombre], nombre).toMatch(/no tienes nombre propio/);
    expect(PROMPTS["Juan (seguimiento 1)"]).toMatch(/sin nombre propio \(«somos Baby Caleb»\)/);
  });

  it("el saludo de respaldo (sin Odoo) tiene la forma del CRM: «Buenas, un gusto atenderle. Somos …»", () => {
    expect(presentacionPorDefecto("Baby Caleb Panamá")).toBe("Buenas, un gusto atenderle. Somos Baby Caleb Panamá.");
    expect(presentacionPorDefecto("el equipo de Baby Caleb")).toBe("Buenas, un gusto atenderle. Somos Baby Caleb.");
  });

  it("con el nombre de fábrica tampoco queda nada de lo de D'CASA", () => {
    for (const p of [promptEstable(CONFIG_POR_DEFECTO), promptTienda(CONFIG_POR_DEFECTO)]) {
      expect(p).not.toMatch(/\btuteo\b|cero emojis/i);
      expect(p).toMatch(/de usted, siempre/i);
    }
  });
});

describe("un precio sin mas_itbms sale de la herramienta sin «+ ITBMS» (Baby Caleb no lo cobra)", () => {
  // OJO: esto es lo que VE el modelo. El guardián (`asegurarItbms`) todavía le agrega «+ ITBMS» a todo número que llegó en un campo
  // «precio», lleve o no el impuesto: arreglarlo toca la lógica de herramientas.ts (anotado en el informe de esta rama).
  it("lo que ve el modelo: precio_texto tal cual, sin «+ ITBMS», también en las tallas; con mas_itbms, igual que siempre", () => {
    const reg = new RegistroDelTurno();
    const visto = procesarResultado(
      {
        productos: [
          { codigo: "NAT-M", nombre: "Pañales Nateen de cierre", precio: 45, precio_texto: "$45.00", mas_itbms: false, variantes: [{ nombre: "Talla M", precio: 45, precio_texto: "$45.00" }] },
          { codigo: "DANY-AW600", nombre: "Toallitas Dany Baby", precio: 18, mas_itbms: false },
        ],
      },
      reg,
      undefined,
    ) as { productos: { precio_texto?: string; variantes?: { precio_texto: string }[] }[] };
    expect(visto.productos[0].precio_texto).toBe("$45.00");
    expect(visto.productos[0].variantes![0].precio_texto).toBe("$45.00");
    expect(visto.productos[1].precio_texto).toBeUndefined();
    expect(JSON.stringify(visto)).not.toContain("ITBMS");
    const conItbms = procesarResultado({ codigo: "X", precio: 10, mas_itbms: true }, new RegistroDelTurno(), undefined) as { precio_texto: string };
    expect(conItbms.precio_texto).toBe("$10.00 + ITBMS");
  });

  it("de punta a punta, el modelo recibe el precio sin «+ ITBMS» y el prompt le pide copiarlo tal cual", async () => {
    const m = crearMundo();
    m.odoo.manejadores.buscar_productos = () => ({ productos: [{ codigo: "NAT-M", nombre: "Pañales Nateen talla M", precio: 45, precio_texto: "$45.00", mas_itbms: false, disponibilidad: "disponible" }] });
    const g = m.guion([{ llamadas: [{ nombre: "buscar_productos", args: { consulta: "nateen" } }] }, { texto: "La caja de Nateen talla M está en $45.00. ¿Le sirve?" }]);
    await m.conversar("precio de nateen m");
    expect(g.prompts()[1]).toContain('"precio_texto":"$45.00"');
    expect(g.prompts()[1]).not.toContain('"precio_texto":"$45.00 + ITBMS"');
    expect(g.prompts()[1]).toContain("copia el campo precio_texto tal cual: si trae «+ ITBMS», va con eso; si no, sin nada.");
  });
});
