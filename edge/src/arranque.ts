/**
 * Respuesta 503 «amable» mientras Odoo arranca o restaura la base desde R2 (I-07). Vive aparte de
 * handler.ts porque también la usa la caché de páginas (src/tienda/paginas.ts): una página guardada
 * cuyos estilos y JS no están en el borde se cambia por esta cuando Odoo no puede servirlos.
 */
import { withSecurityHeaders } from "./routing";

/** Segundos que se le piden al navegador/cliente antes de reintentar. */
export const REINTENTO_SEGUNDOS = 15;

/**
 * La empresa y su WhatsApp de ventas (Baby Caleb, decisión del dueño del 2026-11-18): esta página sale sin Odoo, así
 * que no puede leerlos del sitio. El número va en formato internacional, sin «+» (wa.me).
 */
export const EMPRESA = "Baby Caleb";
export const WHATSAPP_WA_ME = "50767575065";

/**
 * En vez de un error pelado, una página corta que se recarga sola. Nunca se guarda en caché. A
 * quien no pide HTML (Brian, Telegram, JSON-RPC, POST) se le da texto.
 */
export function respuestaArrancando(request: Request, reintento = REINTENTO_SEGUNDOS): Response {
  const headers = new Headers({
    "Retry-After": String(reintento),
    "Cache-Control": "no-store",
    "X-Dcasa-Estado": "arrancando",
  });
  const aceptaHtml = (request.headers.get("Accept") || "").includes("text/html");
  if (!aceptaHtml || request.method !== "GET") {
    headers.set("Content-Type", "text/plain; charset=utf-8");
    return withSecurityHeaders(
      new Response(`${EMPRESA} está arrancando. Vuelve a intentar en ${reintento} segundos.\n`, { status: 503, headers }),
    );
  }
  headers.set("Content-Type", "text/html; charset=utf-8");
  return withSecurityHeaders(new Response(paginaArrancando(reintento), { status: 503, headers }));
}

function paginaArrancando(reintento: number): string {
  // Marca Baby Caleb (docs/MARCA_BABY_CALEB.md): crema, letra navy, titular como frase en Montserrat 700 y el botón en
  // pastilla naranja con letra navy (el naranja es relleno: nunca letra). Mientras Odoo arranca no hay quien sirva la
  // Montserrat del sitio: si el teléfono no la tiene, sale la letra del sistema.
  return `<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="${reintento}">
<meta name="robots" content="noindex">
<title>${EMPRESA} · Un momento</title>
<style>
  body{margin:0;background:#F9F6ED;color:#1B3246;font-family:Montserrat,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
    min-height:100vh;display:flex;align-items:center;justify-content:center;padding:16px;box-sizing:border-box}
  main{max-width:420px;text-align:center}
  h1{font-weight:700;color:#1B3246;font-size:2rem;line-height:1.15;letter-spacing:-.03em;margin:0 0 12px}
  p{line-height:1.6;margin:0 0 12px;color:rgba(27,50,70,.7)}
  a{display:inline-block;margin-top:8px;background:#EE924A;color:#1B3246;font-weight:700;text-decoration:none;
    padding:12px 24px;border-radius:999px;min-height:44px;box-sizing:border-box}
  a:focus-visible{outline:2px solid #1B3246;outline-offset:2px}
</style>
</head>
<body>
<main>
  <h1>Estamos abriendo la tienda</h1>
  <p>Dame un momento: la página se recarga sola en ${reintento} segundos.</p>
  <p>¿Tienes prisa?</p>
  <a href="https://wa.me/${WHATSAPP_WA_ME}">Escríbenos por WhatsApp</a>
</main>
</body>
</html>
`;
}
