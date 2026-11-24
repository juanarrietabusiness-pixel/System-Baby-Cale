// Lógica pura del puente de WhatsApp: tokens, salud y esperas.
//
// Vive aparte del Worker a propósito. Todo lo de aquí es determinista y sin red,
// así que se puede probar en CI — y cada función existe porque un fallo real nos
// costó una tarde en el CRM de origen (docs/bitacora-whatsapp-qr.md de crm-baby-caleb).

/** Espera base entre latidos del Durable Object, con el contenedor sano. */
export const LATIDO_MS = 60_000;

/** Cada cuánto el vigilante del contenedor revisa su propio socket. */
export const VIGILANTE_MS = 30_000;

// ── La paciencia del vigilante ─────────────────────────────────────────────
//
// Lección de la caída del CRM de Baby Caleb (24-nov-2026). Su vigilante daba por muerto al
// puente si el /estado tardaba más de 4 s, le pedía reconectar cada 30 s y lo destruía a los
// 2,5 min. Un puente LENTO porque estaba procesando lo que se acumuló mientras estuvo caído
// nunca terminaba: lo cortaban antes, y cada vuelta encontraba todavía más pendiente. Una caída
// de un rato se volvió un bucle de 14 horas. Aquí el martillo (destruir el contenedor) solo cae
// cuando NO hay progreso, y cada vez espera más.

/**
 * Gracia después de cada arranque del contenedor (incluido un reinicio forzado): ni se le pide
 * reconectar ni se le destruye. Arrancar Node, leer la sesión, iniciar sesión en WhatsApp,
 * reponer pre-keys y empezar a recibir lo atrasado toma minutos en un `lite` (1/16 de CPU).
 */
export const GRACIA_TRAS_ARRANQUE_MS = 10 * 60_000;

/**
 * Cuánto vale una señal de trabajo para decir «está ocupado, no caído». Trabajo = la sesión
 * escribió llaves de tráfico (sesiones, identidades, LID, pre-keys USADAS) o se le entregó un
 * mensaje de una clienta a Juan. Reponer pre-keys NO cuenta: era justo lo que hacía el bucle.
 */
export const PROGRESO_VIGENTE_MS = 5 * 60_000;

/**
 * Sin conexión y sin progreso durante esto, la primera vez se destruye el contenedor y se levanta
 * de cero. Antes eran 5 vigilancias (≈2,5 min). Se cuenta desde lo último que pasó: la caída, el
 * último progreso o el último reinicio forzado.
 */
export const REINICIAR_SIN_PROGRESO_MS = 10 * 60_000;

/**
 * Cada reinicio forzado SEGUIDO (sin un rato sano en medio) duplica la espera para el siguiente:
 * 10 → 20 → 40 → 60 min y ahí se queda. Si reiniciar no lo arregló, reiniciar más rápido tampoco
 * lo va a arreglar; lo que hace es cortar el trabajo a la mitad.
 */
export const REINICIO_ESPERA_MAX_MS = 60 * 60_000;

/**
 * «Ocupado» (no contesta o no conecta, pero hay progreso) no se cree para siempre: si dura más que
 * esto sin llegar a conectar, se trata como caído. Es la red para algo que escribe llaves sin parar
 * pero nunca termina.
 */
export const OCUPADO_MAXIMO_MS = 60 * 60_000;

/**
 * Cuánto espera la vigilancia la respuesta del /estado del contenedor. El CRM de origen esperaba
 * 4 s y con eso lo daba por muerto; aquí no contestar a tiempo NO es morir (con progreso es
 * «ocupado»), y el tope solo evita que una vigilancia se quede colgada.
 */
export const TOPE_ESTADO_VIGILANCIA_MS = 20_000;

/**
 * Cada cuántos SEGUNDOS el Durable Object vigila su contenedor (en segundos porque
 * `schedule()` los cuenta así). Sin retroceso: el retroceso exponencial alargaba
 * los huecos hasta quince minutos y fue parte de por qué las noches quedaban mudas.
 */
export const VIGILANCIA_S = 30;

/**
 * Cuánto puede tardar un latido antes de considerar que el latido MISMO está
 * muerto: tres veces la espera base (un latido perdido es ruido; tres seguidos es
 * que la alarma dejó de existir).
 */
export const LATIDO_VENCIDO_MS = LATIDO_MS * 3;

// ── Tokens ─────────────────────────────────────────────────────────────────

/**
 * Comparación de tiempo constante. Un token no se compara con `===`.
 *
 * Recorre siempre el largo del más largo y mezcla en el resultado la diferencia
 * de largos: ni el contenido ni el largo del token esperado se filtran por el tiempo
 * que tarda en responder.
 */
export function tokensIguales(presentado: string, esperado: string): boolean {
  if (esperado.length === 0) return false;
  const largo = Math.max(presentado.length, esperado.length);
  let diferencia = presentado.length ^ esperado.length;
  for (let i = 0; i < largo; i++) {
    diferencia |= (presentado.charCodeAt(i) || 0) ^ (esperado.charCodeAt(i) || 0);
  }
  return diferencia === 0;
}

export type ViaDelToken = "bearer" | "cabecera" | "cabecera-b64" | "nada";

/**
 * De dónde vino el token y cuál era. Se aceptan tres formas, ninguna en la URL
 * (un token en la URL queda en los registros de Cloudflare y en el historial):
 *
 *   · `Authorization: Bearer <token>`   (la normal, igual que Odoo ↔ Juan)
 *   · `x-wa-token: <token>`             (la del CRM de origen)
 *   · `x-wa-token-b64: <base64>`        (la del CRM de origen cuando viaja desde Node:
 *     Node escribe una cabecera en latin-1 y Cloudflare la lee como UTF-8, así que un
 *     carácter fuera de ASCII llega deformado y el largo no cambia — el «401 mudo»)
 */
export function tokenPresentado(request: Request): { via: ViaDelToken; valor: string } {
  const auth = request.headers.get("authorization");
  if (auth !== null) {
    const m = /^Bearer\s+(.+)$/i.exec(auth.trim());
    if (m) return { via: "bearer", valor: m[1] };
  }
  const plano = request.headers.get("x-wa-token");
  if (plano !== null) return { via: "cabecera", valor: plano };
  const b64 = request.headers.get("x-wa-token-b64");
  if (b64 !== null) {
    try {
      const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
      return { via: "cabecera-b64", valor: new TextDecoder().decode(bytes) };
    } catch {
      return { via: "cabecera-b64", valor: "" };
    }
  }
  return { via: "nada", valor: "" };
}

export function autorizado(request: Request, esperado: string): boolean {
  return tokensIguales(tokenPresentado(request).valor, esperado);
}

/**
 * Un token apto: mínimo 24 caracteres y solo ASCII imprimible. Se valida al
 * desplegar y se reporta en el diagnóstico (un token con ñ o tilde pasa toda prueba
 * hecha por navegador y falla solo en la máquina).
 */
export function tokenEsApto(token: string): { apto: boolean; motivo?: string } {
  if (token.length < 24) return { apto: false, motivo: "demasiado corto (mínimo 24)" };
  if (!/^[\x21-\x7E]+$/.test(token)) {
    return { apto: false, motivo: "tiene caracteres fuera de ASCII imprimible" };
  }
  return { apto: true };
}

const codificador = new TextEncoder();

function aHex(bytes: ArrayBuffer): string {
  return [...new Uint8Array(bytes)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/**
 * El token que se le entrega al CONTENEDOR: HMAC-SHA256(WA_TOKEN, etiqueta), en
 * hexadecimal.
 *
 * Por qué no darle el WA_TOKEN tal cual: el contenedor es el pedazo más expuesto del
 * sistema (descarga archivos de clientes y los pasa por librerías de terceros). Con
 * un token derivado, aunque alguien lo comprometiera solo abre las rutas `/puente/*`
 * (sus credenciales y su entrega de mensajes) y NO puede hablar como el Worker `juan`
 * (`/api/*`), ni deducir el WA_TOKEN. Además es hexadecimal: solo ASCII, así que el
 * «401 mudo» de las cabeceras no puede ocurrir en este tramo.
 */
export async function derivarTokenContenedor(waToken: string): Promise<string> {
  const llave = await crypto.subtle.importKey(
    "raw",
    codificador.encode(waToken),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const firma = await crypto.subtle.sign("HMAC", llave, codificador.encode("dcasa-puente-wa/contenedor/v1"));
  return aHex(firma);
}

// ── Salud real del canal ───────────────────────────────────────────────────

export type Veredicto = "sano" | "esperando-a-una-persona" | "ocupado" | "caido";

/**
 * Qué hacer con lo que contesta el contenedor.
 *
 * Existe aparte y con pruebas porque es EL juicio que el latido se equivocaba en
 * hacer: la versión anterior preguntaba «¿el proceso está prendido?» cuando lo que
 * importa es «¿WhatsApp está conectado?». Un contenedor prendido con el socket
 * muerto salía sano y el canal se quedaba mudo sin que nada lo notara.
 *
 * `esperando-a-una-persona` no es un estado sano, pero TAMPOCO es un fallo que se
 * arregle reiniciando: si nadie ha escaneado el QR, reiniciar solo genera un código
 * nuevo y le tumba al dueño el que está mirando.
 *
 * `ocupado` (caída del 24-nov): no está conectado —o no contestó a tiempo— PERO hay progreso
 * reciente (la sesión escribe llaves de tráfico o se le entregan mensajes a Juan). Está
 * trabajando en lo atrasado: se le deja en paz.
 */
export function veredictoDeSalud(
  conexion: string | null | undefined,
  { progresoReciente = false }: { progresoReciente?: boolean } = {},
): Veredicto {
  if (conexion === "conectada") return "sano";
  if (conexion === "esperando-qr" || conexion === "desvinculada") return "esperando-a-una-persona";
  return progresoReciente ? "ocupado" : "caido";
}

/**
 * ¿El latido está llegando? Es la señal que faltó el 16-sep-2026: la alarma del
 * Durable Object se había apagado y NADA lo decía.
 */
export function latidoVencido(ultimoLatidoEn: number | null | undefined, ahora: number): boolean {
  if (!ultimoLatidoEn) return false; // todavía no ha latido ninguna vez
  return ahora - ultimoLatidoEn > LATIDO_VENCIDO_MS;
}

/** Los campos que un reinicio pedido por una persona deja en el diario. */
export interface ReinicioPedido {
  ultimaMuerteVista: string;
  desconectadoSeguidos: 0;
  reiniciosSeguidos: 0;
  ocupadoDesde: null;
}

/**
 * Cómo queda el diario cuando una PERSONA pide «Reiniciar». Un reinicio pedido es un
 * punto y aparte, no la continuación de la racha de fallos anterior: si heredara el
 * conteo, el siguiente tropiezo lo destruiría de inmediato (en el CRM de origen el
 * botón «Reiniciar» tampoco reiniciaba nada por heredar el castigo del retroceso).
 * Tampoco hereda la espera creciente entre reinicios forzados.
 */
export function reinicioPedido(ahora: Date): ReinicioPedido {
  return { ultimaMuerteVista: ahora.toISOString(), desconectadoSeguidos: 0, reiniciosSeguidos: 0, ocupadoDesde: null };
}
