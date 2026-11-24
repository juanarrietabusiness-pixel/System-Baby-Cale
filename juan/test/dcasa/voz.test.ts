/**
 * Regla 11 y voz de la marca, vistas desde el CLIENTE: sea lo que sea que diga el modelo, lo que llega por el canal es alguien
 * de la tienda que conoce bien los productos: de usted (el dueño de Baby Caleb, 2026-11-24, con la voz de su CRM), uno o dos
 * emojis como mucho, sin gritos, sin «remate», burbujas cortas.
 * (Reescritura de las pruebas de «trato» del CRM de Baby Caleb.)
 */
import { describe, expect, it } from "vitest";
import { CONFIG_POR_DEFECTO } from "../../src/config";
import { marcaDe, presentacionPorDefecto } from "../../src/dcasa/prompt";
import { TEXTO_FUGA, TEXTO_SIN_DATO } from "../../src/dcasa/salvaguardas";
import { TEXTO_ARCHIVO_RECIBIDO, TEXTO_FALLO_TECNICO, TEXTO_TOPE_DIARIO, textoPasoAVendedora } from "../../src/dcasa/textos";
import { crearMundo } from "../helpers/mundo";

const EMOJI = /\p{Extended_Pictographic}/u;
const EMOJIS = /\p{Extended_Pictographic}/gu;

describe("lo que llega al cliente", () => {
  it("uno o dos emojis como mucho, ningún «visto», sin signos dobles y sin formato de documento", async () => {
    const m = crearMundo();
    m.guion([{ texto: "¡¡Claro que sí!! 👼🏻🙌🏻😁 ✅ ¿Qué talla busca??\n## Opciones\n**de cierre** o pants ✨" }]);
    await m.conversar("hola");
    const todo = m.canal.textos.join("\n");
    expect(todo.match(EMOJIS) ?? []).toEqual(["👼", "🙌"]);
    expect(todo).toContain("👼🏻🙌🏻");
    expect(todo).not.toMatch(/[✓✔✅☑]/u);
    expect(todo).not.toMatch(/[¡!]{2}|[¿?]{2}|##|\*\*/);
    expect(todo).toContain("¿Qué talla busca?");
  });

  it("«remate» y «¡corre!» no salen: el modelo reescribe sin presión", async () => {
    const m = crearMundo();
    const g = m.guion([{ texto: "Esta caja de pañales está de REMATE, ¡CORRE antes de que se acabe!" }, { texto: "Esos pañales te pueden gustar. ¿Quieres que te cuente de las tallas?" }]);
    await m.conversar("¿qué pañales tienen?");
    const todo = m.canal.textos.join("\n");
    expect(todo).not.toMatch(/remate|corre/i);
    expect(todo).toContain("¿Quieres que te cuente de las tallas?");
    expect(g.prompts()[1]).toMatch(/palabra que la marca no usa/i);
  });

  it("si lo único que dijo fue presión de venta, no sale esa oración", async () => {
    const m = crearMundo();
    m.guion([{ texto: "¡Corre, última oportunidad! ¿Qué talla usa tu bebé?" }]);
    await m.conversar("hola");
    const todo = m.canal.textos.join("\n");
    expect(todo).not.toMatch(/corre|oportunidad/i);
    expect(todo).toContain("¿Qué talla usa tu bebé?");
  });

  it("las palabras que la dueña prohíbe en Odoo tampoco salen, aunque el modelo las use", async () => {
    const m = crearMundo({ config: { palabras_prohibidas: ["ganga", "regalado"] } });
    m.guion([{ texto: "Está regalado, es una ganga." }, { texto: "Es una buena opción para tu bebé." }]);
    await m.conversar("¿cómo están las toallitas?");
    const todo = m.canal.textos.join("\n");
    expect(todo).not.toMatch(/ganga|regalado/i);
    expect(todo).toContain("buena opción");
  });

  it("las palabras prohibidas viajan al prompt, para que el modelo no las intente", async () => {
    const m = crearMundo({ config: { palabras_prohibidas: ["ganga"] } });
    const g = m.guion([{ texto: "Dime qué buscas." }]);
    await m.conversar("hola");
    expect(g.prompts()[0]).toContain("«ganga»");
  });
});

describe("burbujas cortas (2 a 4 líneas)", () => {
  const parrafo = "Tenemos varias opciones de pañales para tu bebé y te cuento de cada una con calma. ";

  it("una respuesta larga sale en varias burbujas, cada una de máximo 4 líneas", async () => {
    const m = crearMundo();
    m.guion([{ texto: Array.from({ length: 6 }, (_, i) => `${parrafo.trim()} Punto ${i + 1}.`).join("\n\n") }]);
    await m.conversar("cuéntame de los pañales");
    const burbujas = m.canal.textos;
    expect(burbujas.length).toBeGreaterThan(1);
    for (const b of burbujas) expect(b.split("\n").length).toBeLessThanOrEqual(4);
  });

  it("nunca más de 4 burbujas por respuesta; lo que sobra se junta en la última, sin perder nada", async () => {
    const m = crearMundo();
    const partes = Array.from({ length: 10 }, (_, i) => `Párrafo ${i + 1}: ${parrafo.repeat(2).trim()}`);
    m.guion([{ texto: partes.join("\n\n") }]);
    await m.conversar("cuéntame todo");
    // La presentación del primer mensaje es aparte; el resto de la respuesta no pasa de 4.
    const todo = m.canal.textos.join("\n");
    for (const p of partes) expect(todo).toContain(`Párrafo ${partes.indexOf(p) + 1}:`);
    expect(m.canal.salidas.every((s) => s.burbujas.length <= 5)).toBe(true);
  });

  it("una respuesta corta es una sola burbuja", async () => {
    const m = crearMundo();
    m.guion([{ texto: "Claro. ¿Qué talla buscas?" }]);
    await m.conversar("hola");
    expect(m.canal.textos.at(-1)).toBe("Claro. ¿Qué talla buscas?");
  });
});

/** Lo que delata el tuteo en un texto dirigido al cliente. */
const TUTEO = /\b(?:te|tu|tus|ti|tú|contigo|quieres|prefieres|buscas|puedes|tienes|dime|cuéntame|escríbeme|mira)\b/i;

describe("de usted y presentación", () => {
  it("los textos fijos del sistema le hablan de usted al cliente", () => {
    const fijos = [TEXTO_TOPE_DIARIO, TEXTO_FALLO_TECNICO, TEXTO_ARCHIVO_RECIBIDO, TEXTO_FUGA, TEXTO_SIN_DATO, textoPasoAVendedora(true, CONFIG_POR_DEFECTO.horario), textoPasoAVendedora(false, CONFIG_POR_DEFECTO.horario)];
    for (const t of fijos) {
      expect(t, t).not.toMatch(TUTEO);
      expect(t, t).toMatch(/\b(?:le|su|se lo|prefiere|desea|indíqueme|escríbame|busca)\b/i);
      expect(t, t).not.toMatch(EMOJI);
    }
    expect(textoPasoAVendedora(true, CONFIG_POR_DEFECTO.horario)).toBe("Listo, ya le pasé su consulta a una vendedora. Le escribe por aquí en un momento.");
    expect(textoPasoAVendedora(false, CONFIG_POR_DEFECTO.horario)).toBe("Listo, dejé su consulta para una vendedora. Le escribe por aquí cuando abramos, a partir de las 8:00 a. m.");
    expect(TEXTO_ARCHIVO_RECIBIDO).toBe("Recibí su archivo. Una vendedora lo revisa y le confirma por aquí.");
  });

  it("el saludo va primero, sin emojis ni tuteo", async () => {
    const m = crearMundo();
    m.guion([{ texto: "¿Qué estás buscando?" }]);
    await m.conversar("hola");
    const primera = m.canal.textos[0];
    expect(primera).toBe("Buenas, un gusto atenderle. Somos Baby Caleb.");
    expect(primera).not.toMatch(EMOJI);
    expect(primera).not.toMatch(TUTEO);
  });

  it("solo se presenta una vez: el segundo mensaje no repite la presentación", async () => {
    const m = crearMundo();
    m.guion([{ texto: "¿Qué estás buscando?" }, { texto: "Dime la talla." }]);
    await m.conversar("hola");
    const antes = m.canal.textos.length;
    await m.conversar("busco pañales");
    const nuevos = m.canal.textos.slice(antes);
    expect(nuevos.join(" ")).not.toMatch(/Somos Baby Caleb/i);
  });

  it("la bienvenida de Odoo manda; si afirma ser una persona real, se usa la nuestra", async () => {
    const propia = crearMundo({ config: { mensaje_bienvenida: "Buenas, un gusto atenderle. Somos Baby Caleb Panamá 👼🏻 ¿Qué busca para su bebé?" } });
    propia.guion([{ texto: "Dime la medida." }]);
    await propia.conversar("hola");
    expect(propia.canal.textos[0]).toBe("Buenas, un gusto atenderle. Somos Baby Caleb Panamá 👼🏻 ¿Qué busca para su bebé?");

    const enganosa = crearMundo({ config: { mensaje_bienvenida: "Hola, soy una persona real, no un robot." } });
    enganosa.guion([{ texto: "Dime la medida." }]);
    await enganosa.conversar("hola");
    expect(enganosa.canal.textos[0]).toBe("Buenas, un gusto atenderle. Somos Baby Caleb.");
  });
});

describe("el nombre del negocio", () => {
  it("«el equipo de …» (la forma del nombre público) se lee bien en «Somos ...»", () => {
    expect(marcaDe("el equipo de Baby Caleb")).toBe("Baby Caleb");
    expect(marcaDe("  El equipo de Baby Caleb Panamá ")).toBe("Baby Caleb Panamá");
    expect(marcaDe("Casa y Más")).toBe("Casa y Más");
    expect(marcaDe("el equipo de")).toBe("el equipo de"); // nada que quitar sin dejarlo vacío
    expect(presentacionPorDefecto("el equipo de Baby Caleb")).toBe("Buenas, un gusto atenderle. Somos Baby Caleb.");
    expect(presentacionPorDefecto("el equipo de Baby Caleb")).not.toContain("equipo");
  });

  it("sin Odoo, el nombre de respaldo es neutro: ninguna empresa escrita a mano", () => {
    expect(presentacionPorDefecto(CONFIG_POR_DEFECTO.nombre_publico)).toBe("Buenas, un gusto atenderle. Somos la tienda.");
    expect(CONFIG_POR_DEFECTO.nombre_publico).not.toMatch(/D'CASA|Baby Caleb/i);
  });

  it("el prompt con el nombre por defecto tampoco dice «de el equipo de»", async () => {
    const m = crearMundo();
    const g = m.guion([{ texto: "Dime qué buscas." }]);
    await m.conversar("hola");
    expect(g.prompts()[0]).not.toMatch(/de «?el equipo de/);
  });

  it("usa el nombre público que fija Odoo en el prompt", async () => {
    const m = crearMundo({ config: { nombre_publico: "Baby Caleb Panamá" } });
    const g = m.guion([{ texto: "Dime qué buscas." }]);
    await m.conversar("hola");
    expect(g.prompts()[0]).toContain("Baby Caleb Panamá");
    expect(m.canal.textos[0]).toBe("Buenas, un gusto atenderle. Somos Baby Caleb Panamá.");
    expect(g.prompts()[0]).not.toContain("D'CASA");
  });
});
