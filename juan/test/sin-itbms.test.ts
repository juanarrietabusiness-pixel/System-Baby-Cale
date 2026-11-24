// Baby Caleb no cobra ITBMS (decisión del dueño, 2026-11-24): ningún precio le llega a la clienta con «+ ITBMS».
// Odoo lo dice en la configuración (`cobra_itbms: false`, con DCASA_COBRA_ITBMS=0) y cada producto lo dice en
// `mas_itbms: false`. Un negocio que sí lo cobra (D'CASA) sigue igual: test/dcasa/fuentes-de-verdad.test.ts.
import { describe, expect, it } from "vitest";
import { CONFIG_POR_DEFECTO, normalizarConfig } from "../src/config";
import { asegurarItbms } from "../src/dcasa/salvaguardas";
import { RegistroDelTurno, procesarResultado } from "../src/motor/herramientas";
import { crearMundo } from "./helpers/mundo";

describe("la configuración dice si el negocio cobra ITBMS", () => {
  it("cobra_itbms llega de Odoo; sin el dato (o con basura), se cobra como siempre", () => {
    expect(CONFIG_POR_DEFECTO.cobra_itbms).toBe(true);
    expect(normalizarConfig({ cobra_itbms: false }).cobra_itbms).toBe(false);
    expect(normalizarConfig({ cobra_itbms: true }).cobra_itbms).toBe(true);
    expect(normalizarConfig({}).cobra_itbms).toBe(true);
    expect(normalizarConfig({ cobra_itbms: "no" }).cobra_itbms).toBe(true);
  });
});

describe("un producto sin ITBMS no marca sus precios para el «+ ITBMS»", () => {
  it("son cifras conocidas (no se toman por inventadas), pero no precios con ITBMS", () => {
    const reg = new RegistroDelTurno();
    procesarResultado({ productos: [{ codigo: "NAT-M", precio: 50, mas_itbms: false, variantes: [{ precio: 45 }] }] }, reg, undefined);
    expect([...reg.preciosProducto]).toEqual([]);
    expect(reg.cifras.has(50) && reg.cifras.has(45)).toBe(true);
    const conItbms = new RegistroDelTurno();
    procesarResultado({ codigo: "X", precio: 10, mas_itbms: true }, conItbms, undefined);
    expect(conItbms.preciosProducto.has(10)).toBe(true);
  });

  it("el guardián solo agrega «+ ITBMS» a los precios marcados", () => {
    expect(asegurarItbms("La caja está en $45.00.", new Set())).toBe("La caja está en $45.00.");
    expect(asegurarItbms("La caja está en $45.00.", new Set([45]))).toContain("$45.00 + ITBMS");
  });
});

describe("de punta a punta: la clienta recibe el precio sin «+ ITBMS»", () => {
  const producto = { codigo: "NAT-M", nombre: "Pañales Nateen talla M", precio: 50, precio_texto: "$50.00", disponibilidad: "disponible" };

  it("con cobra_itbms: false, aunque la herramienta no diga mas_itbms", async () => {
    const m = crearMundo({ config: { cobra_itbms: false } });
    m.odoo.manejadores.buscar_productos = () => ({ productos: [producto] });
    m.guion([{ llamadas: [{ nombre: "buscar_productos", args: { consulta: "nateen" } }] }, { texto: "La caja de Nateen talla M está en $50.00. ¿Le sirve?" }]);
    await m.conversar("precio de nateen m");
    const texto = m.canal.textos.join("\n");
    expect(texto).toContain("$50.00");
    expect(texto).not.toContain("ITBMS");
  });

  it("con mas_itbms: false en el producto, también", async () => {
    const m = crearMundo();
    m.odoo.manejadores.buscar_productos = () => ({ productos: [{ ...producto, mas_itbms: false }] });
    m.guion([{ llamadas: [{ nombre: "buscar_productos", args: { consulta: "nateen" } }] }, { texto: "La caja de Nateen talla M está en $50.00. ¿Le sirve?" }]);
    await m.conversar("precio de nateen m");
    expect(m.canal.textos.join("\n")).not.toContain("ITBMS");
  });
});
