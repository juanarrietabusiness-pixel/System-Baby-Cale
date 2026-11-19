/**
 * Las páginas que sirve el borde por su cuenta (mientras Odoo arranca y la de la puerta del equipo) llevan la marca
 * Baby Caleb (docs/MARCA_BABY_CALEB.md, 2026-11-19): crema, letra navy, titulares como frase, el naranja solo de
 * relleno con letra navy encima, y nada del azul, del amarillo ni de las letras de D'CASA.
 */
import { describe, expect, it } from "vitest";
import { respuestaArrancando } from "../src/arranque";
import { respuestaPuertaIncompleta, respuestaPuertaNoAbre } from "../src/puerta_aviso";

const DE_DCASA = /1340B1|FED00F|0B2160|0E2A6B|Anton|Oswald|text-transform:uppercase;letter-spacing:\.0/i;

function marcaBabyCaleb(html: string) {
  expect(html).toContain("background:#F9F6ED");
  expect(html).toContain("color:#1B3246");
  expect(html).toContain("font-family:Montserrat");
  // El botón: naranja de relleno con letra navy, en pastilla.
  expect(html).toMatch(/background:#EE924A;color:#1B3246;font-weight:700/);
  expect(html).toContain("border-radius:999px");
  // El naranja nunca va de letra: «color:#EE924A» no aparece.
  expect(html).not.toMatch(/(^|[;{\s])color:#EE924A/i);
  expect(html).not.toMatch(DE_DCASA);
}

describe("marca Baby Caleb en las páginas del borde", () => {
  it("la de «estamos abriendo la tienda»", async () => {
    const res = respuestaArrancando(new Request("https://babycaleb.com/", { headers: { Accept: "text/html" } }));
    marcaBabyCaleb(await res.text());
  });

  it("la de la puerta del equipo cuando no abre", async () => {
    const res = respuestaPuertaNoAbre(
      new Request("https://babycaleb.com/master"),
      { motivo: "sin token" },
      { ruta: "/master", modo: "1", entorno: "staging", ahora: () => 0 },
    );
    const html = await res.text();
    marcaBabyCaleb(html);
    expect(html).toContain("<title>Baby Caleb · Acceso del equipo</title>");
  });

  it("la de la puerta incompleta", async () => {
    const res = respuestaPuertaIncompleta(
      new Request("https://babycaleb.com/master"),
      { estado: "incompleta", modo: "0", faltan: ["DCASA_ACCESS_AUD"], ruta: "/master" },
      { entorno: "staging", ahora: () => 0 },
    );
    const html = await res.text();
    expect(html).toContain("background:#F9F6ED");
    expect(html).not.toMatch(DE_DCASA);
  });
});
