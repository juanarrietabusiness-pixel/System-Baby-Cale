/**
 * Portada (2026-11-16): el hero con los productos que elige Gerencia (models/portada.py, views/homepage_templates.xml).
 *
 *   · DcasaVitrina  las fotos del marco del hero se funden unas en otras, en orden al azar, cada --vitrina-tiempo.
 *                   El visitante no maneja nada (no hay flechas, barras, pausa ni deslizar): es decorativo, no un
 *                   carrusel que se recorre. El zoom lento es del CSS y no para nunca; con movimiento reducido no
 *                   cambia de foto. Sin JavaScript se ve la primera, quieta.
 *
 * (La sección «de cine», con sus dos cintas de fotos de muebles, se quitó con la marca de Baby Caleb, 2026-11-19.)
 *
 * Como las demás Interactions del sitio, no corren en el editor y lo que agregan lo quitan al destruirse.
 */
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

const reducido = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/**
 * El fondo del hero (la dueña, 2026-11-17): las fotos se funden unas en otras, en orden al azar, sin que el visitante
 * maneje nada. No hay flechas, ni barras, ni pausa, ni deslizar: es un fondo, no un carrusel que se recorre.
 * El zoom lento lo hace el CSS y no para nunca; aquí solo se decide cuándo cambiar de foto.
 * Con movimiento reducido no cambia nunca: se queda la primera.
 */
export class DcasaVitrina extends Interaction {
    static selector = ".o_dcasa_vitrina";

    setup() {
        this.fotos = [...this.el.querySelectorAll(".o_dcasa_vitrina_foto")];
        this.total = this.fotos.length;
        this.actual = Math.max(0, this.fotos.findIndex((foto) => foto.classList.contains("is-activa")));
        // Orden al azar, empezando por la que ya se está viendo (es la que el navegador precargó: el LCP no cambia).
        this.orden = barajar(this.fotos.map((_, i) => i).filter((i) => i !== this.actual));
        this.paso = 0;
        this.temporizador = null;
    }

    start() {
        // (El botón flotante de WhatsApp ya no espera fuera mientras se ve el hero: con la marca de Baby Caleb el hero
        // no trae su propio botón de WhatsApp, y la burbuja de babycaleb.com está siempre a la vista.)
        // La limpieza se registra UNA vez (no con cada cambio de foto: a 2 s por foto serían unas 1800 por hora).
        this.registerCleanup(() => this.parar());
        if (this.total > 1 && !reducido()) {
            this.programar();
        }
    }

    destroy() {
        this.parar();
    }

    parar() {
        if (this.temporizador) {
            this.services.timer?.clearTimeout?.(this.temporizador);
            clearTimeout(this.temporizador);
            this.temporizador = null;
        }
    }

    programar() {
        this.parar();
        const ms = tiempoDeLaVitrina(this.el);
        this.temporizador = setTimeout(() => this.siguiente(), ms);
    }

    siguiente() {
        if (!this.orden.length) {
            // Otra vuelta, barajada de nuevo y sin repetir la que se está viendo de primera.
            this.orden = barajar(this.fotos.map((_, i) => i).filter((i) => i !== this.actual));
        }
        const proxima = this.orden.shift();
        this.fotos[this.actual]?.classList.remove("is-activa");
        this.fotos[proxima]?.classList.add("is-activa");
        this.actual = proxima;
        this.programar();
    }
}

/** Una copia barajada (Fisher-Yates). */
export function barajar(lista) {
    const copia = [...lista];
    for (let i = copia.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [copia[i], copia[j]] = [copia[j], copia[i]];
    }
    return copia;
}

/**
 * Lo que dura cada foto, en milisegundos, leído de `--vitrina-tiempo`: la plantilla lo escribe en el hero con los
 * segundos que Gerencia eligió en el panel (3 de fábrica; website_dcasa/models/portada.py) y las pruebas lo cambian
 * para acortarlo. Sin valor legible, los 3 segundos de fábrica.
 */
export function tiempoDeLaVitrina(el) {
    const valor = getComputedStyle(el).getPropertyValue("--vitrina-tiempo").trim();
    const numero = parseFloat(valor);
    if (!numero || Number.isNaN(numero)) {
        return 3000;
    }
    return valor.endsWith("ms") ? numero : numero * 1000;
}

const interacciones = registry.category("public.interactions");
interacciones.add("website_dcasa.vitrina", DcasaVitrina);
