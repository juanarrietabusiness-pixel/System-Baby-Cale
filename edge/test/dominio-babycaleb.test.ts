/**
 * Candado del día del dominio (docs/DOMINIO.md, pedido del dueño el 2026-11-18: «recuérdamelo paso a paso»).
 *
 * El repositorio Baby-caleb despliega su web (`babycaleb-web`) en CADA push a su main (.github/workflows/web.yml) con
 * `babycaleb.com` en su wrangler.jsonc, y wrangler sin terminal se lleva un dominio que ya usa otro Worker sin preguntar.
 * Si este sistema toma babycaleb.com y ese repositorio no lo soltó, el siguiente arreglo de esa web se lo vuelve a quitar.
 *
 * Por eso: en cuanto babycaleb.com aparezca en edge/wrangler.jsonc (fuera de un comentario), esta prueba exige que la
 * casilla del repositorio Baby-caleb esté marcada en docs/DOMINIO.md. No se marca a ojo: se marca cuando el commit que
 * quita esas rutas ya está en el main de Baby-caleb.
 */
import { describe, expect, it } from "vitest";
import dominioMd from "../../docs/DOMINIO.md?raw";
import wranglerJsonc from "../wrangler.jsonc?raw";

const lineasSinComentarios = wranglerJsonc
  .split("\n")
  .filter((linea) => !linea.trim().startsWith("//"))
  .join("\n");

describe("día del dominio babycaleb.com", () => {
  it("la guía tiene la casilla del repositorio Baby-caleb", () => {
    expect(dominioMd).toMatch(/^- \[[ x]\] \*\*Repositorio Baby-caleb:\*\*/m);
  });

  it("si este sistema toma babycaleb.com, el repositorio Baby-caleb ya lo soltó (casilla marcada)", () => {
    if (!lineasSinComentarios.includes("babycaleb.com")) return;
    expect(dominioMd, "Antes de poner babycaleb.com en edge/wrangler.jsonc: quitarlo de Baby-caleb/wrangler.jsonc (docs/DOMINIO.md, Fase B paso 2) y marcar su casilla").toMatch(
      /^- \[x\] \*\*Repositorio Baby-caleb:\*\*/m,
    );
  });
});
