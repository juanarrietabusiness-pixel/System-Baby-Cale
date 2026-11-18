/**
 * El conocimiento del bot arranca en cero (pedido del dueño, 2026-11-18: «cada negocio le pone el conocimiento de su negocio
 * manualmente o vía MCP; nada de la información de D'CASA»).
 *
 * Lo que el negocio ES (su giro, su ciudad, su dominio, su catálogo) no vive en ningún prompt: lo dicen las herramientas de Odoo
 * (horario_y_tienda con los datos de la empresa, buscar_productos con su catálogo, buscar_conocimiento con lo que escriba su
 * equipo). Aquí se vigila que no vuelva a colarse en ninguno de los textos que lee un modelo: Juan, su seguimiento, Andrés (el chat
 * de la tienda), el borrador y el resumen del panel, y el clasificador de comentarios. El nombre de la marca y de los asistentes no
 * se vigila aquí: cambiarlo es otro trabajo.
 */
import { describe, expect, it } from "vitest";
import { CONFIG_POR_DEFECTO, normalizarConfig } from "../../src/config";
import { contextoDelChat, promptEstable, promptSeguimiento } from "../../src/dcasa/prompt";
import { TEXTO_FUGA } from "../../src/dcasa/salvaguardas";
import { PROMPT_DE_CLASIFICACION, notaDelTurnoDeComentario } from "../../src/motor/comentarios";
import { promptDelResumen } from "../../src/odoo-panel-resumir";
import { promptDelBorrador } from "../../src/odoo-panel-sugerir";
import { promptTienda } from "../../src/tienda/prompt";
import { AHORA_INICIAL } from "../helpers/mundo";

/** Hechos de D'CASA que un modelo no puede «saber» por su prompt: el giro, la ciudad, el dominio y su catálogo. */
const HECHOS_DE_DCASA: RegExp[] = [
  /mueble/i, // «muebles», «mueblería»
  /La Chorrera|Chorrera/i,
  /Panamá Oeste/i,
  /dcasapty/i,
  /Libertadores|Discoteca Seven|6026|1919|155779346|info@/i,
  /\bcolch[oó]n(es)?\b/i,
  /\bcamas?\b/i,
  /\bsof[aá]s?\b/i,
  /\bqueen\b|\bking\b|\btwin\b/i,
  /para qué cuarto|medidas del espacio/i,
  /Villa Lucre/i,
];

function sinHechosDeDcasa(nombre: string, texto: string) {
  for (const hecho of HECHOS_DE_DCASA) expect(texto, `${nombre}: ${hecho}`).not.toMatch(hecho);
}

describe("ningún prompt trae lo que el negocio es: eso lo dicen las herramientas", () => {
  const cfg = CONFIG_POR_DEFECTO;

  it("Juan: el bloque estable (con y sin lecciones) y el contexto del chat", () => {
    sinHechosDeDcasa("promptEstable", promptEstable(cfg));
    sinHechosDeDcasa("promptEstable con lecciones", promptEstable(normalizarConfig({ lecciones: ["Saluda con calma."] })));
    for (const permiso of [undefined, "activo", "sin_correo", "sin_permiso"]) {
      sinHechosDeDcasa(`contextoDelChat ${permiso}`, contextoDelChat(cfg, {
        canal: "whatsapp_qr", ahora: AHORA_INICIAL, presentacionEnviada: true, permisoDeCorreo: permiso, campanaDeCorreo: "Novedades",
      }));
    }
  });

  it("Juan: el seguimiento (el primero y el último)", () => {
    for (const numero of [1, 2] as const) {
      sinHechosDeDcasa(`seguimiento ${numero}`, promptSeguimiento(cfg, { numero, interes: "", ahora: AHORA_INICIAL }));
    }
  });

  it("Andrés, el chat de la tienda, con y sin el aviso de cerrado", () => {
    const tienda = normalizarConfig({ brian_tienda: { activo: true } });
    sinHechosDeDcasa("promptTienda", promptTienda(tienda));
    sinHechosDeDcasa("promptTienda siempre activo", promptTienda({ ...tienda, tienda: { ...tienda.tienda, avisar_cerrado: false } }));
  });

  it("el borrador y el resumen del panel", () => {
    const base = { conversacion_id: 1, canal: "whatsapp_qr" as const, mensajes: [{ autor: "cliente" as const, texto: "hola" }], nombre: "", etiquetas: [] };
    sinHechosDeDcasa("promptDelBorrador", promptDelBorrador(cfg, { ...base, interes: "" }));
    sinHechosDeDcasa("promptDelResumen", promptDelResumen(cfg, base));
  });

  it("los comentarios de Instagram y Facebook", () => {
    sinHechosDeDcasa("PROMPT_DE_CLASIFICACION", PROMPT_DE_CLASIFICACION);
    for (const red of ["facebook", "instagram"] as const) sinHechosDeDcasa(`notaDelTurnoDeComentario ${red}`, notaDelTurnoDeComentario(red));
  });

  it("el texto fijo con el que el sistema corta una fuga del prompt", () => {
    sinHechosDeDcasa("TEXTO_FUGA", TEXTO_FUGA);
  });

  it("lo que sí queda: las reglas de siempre siguen ahí (no se tocó cómo trabaja el bot)", () => {
    const p = promptEstable(cfg);
    expect(p).toMatch(/REGLA INQUEBRANTABLE/);
    expect(p).toContain("buscar_conocimiento");
    expect(p).toContain("registrar_pregunta_sin_respuesta");
    expect(p).toContain("horario_y_tienda: dirección, horario de atención, WhatsApp, cómo llegar");
    expect(promptTienda(normalizarConfig({ brian_tienda: { activo: true } }))).toContain("horario_y_tienda: dirección, horario, cómo llegar.");
  });
});
