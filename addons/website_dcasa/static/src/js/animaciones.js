/**
 * Movimiento del sitio, como Interactions de Odoo 19.
 *
 * El framework las arranca en el sitio público y las DETIENE en el editor (no están
 * registradas en `public.interactions.edit`): ahí nada se esconde y los titulares no se
 * trocean, así el editor nunca guarda ese marcado.
 * Todo lo que agregan lo quitan al destruirse (`registerCleanup`, `insert`, `addListener`).
 *
 *   · DcasaRevelar     secciones y titulares que entran al hacer scroll (data-anim…).
 *   · DcasaCabecera    la refracción del vidrio de la pastilla y el movimiento lento de su ruido.
 *   · DcasaResenas     botón para pausar la cinta de opiniones (WCAG 2.2.2).
 *   · DcasaFotos       fotos de producto anchas: enteras («contain») en el cuadro de la tarjeta.
 *
 * Lo que está sobre el pliegue (el hero) usa [data-anim-entrada]: CSS puro, sin esperar a nadie.
 */
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

const reducido = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export class DcasaRevelar extends Interaction {
    static selector = "#wrapwrap";

    start() {
        if (reducido() || !("IntersectionObserver" in window)) {
            return;
        }
        const elementos = [...this.el.querySelectorAll("[data-anim], [data-anim-cascada], [data-titular]")];
        if (!elementos.length) {
            return;
        }
        // Primero todas las lecturas, después todas las escrituras: un solo cálculo de layout.
        const alto = window.innerHeight;
        const arriba = elementos.map((el) => el.getBoundingClientRect().top < alto * 0.9);

        this.observador = new IntersectionObserver(
            (entradas) => {
                for (const entrada of entradas) {
                    if (entrada.isIntersecting) {
                        entrada.target.classList.add("anim-dentro");
                        this.observador.unobserve(entrada.target);
                    }
                }
            },
            { rootMargin: "0px 0px -10% 0px", threshold: 0 }
        );
        elementos.forEach((el, i) => {
            // Lo que ya se ve al cargar no se esconde para volver a enseñarlo.
            if (arriba[i]) {
                el.classList.add("anim-dentro");
            } else {
                if (el.hasAttribute("data-titular")) {
                    this.trocear(el);
                }
                this.observador.observe(el);
            }
        });
        document.documentElement.classList.add("o_dcasa_anim");
        this.registerCleanup(() => {
            this.observador.disconnect();
            document.documentElement.classList.remove("o_dcasa_anim");
            elementos.forEach((el) => el.classList.remove("anim-dentro"));
        });
    }

    /** Titular palabra a palabra. Solo si es texto plano: no rompe el marcado del editor. */
    trocear(titular) {
        if (titular.children.length) {
            return;
        }
        const original = titular.textContent;
        // Espacios normales: el espacio duro (&nbsp;) mantiene juntas las palabras que deben ir juntas.
        const palabras = original.trim().split(/[ \t\n\r]+/);
        titular.setAttribute("aria-label", palabras.join(" "));
        titular.textContent = "";
        palabras.forEach((palabra, i) => {
            const caja = document.createElement("span");
            caja.className = "o_dcasa_palabra";
            caja.setAttribute("aria-hidden", "true");
            const dentro = document.createElement("span");
            dentro.textContent = palabra;
            dentro.style.setProperty("--i", i);
            caja.appendChild(dentro);
            titular.append(caja, i < palabras.length - 1 ? " " : "");
        });
        this.registerCleanup(() => {
            titular.textContent = original;
            titular.removeAttribute("aria-label");
        });
    }
}

export class DcasaCabecera extends Interaction {
    static selector = "header#top";

    /**
     * La pastilla de vidrio crema de babycaleb.com (src/styles/tokens.css, `.bc-vidrio`): siempre la misma, en todas
     * las páginas (con la marca de Baby Caleb no hay fotos oscuras detrás: ya no hay vidrio ahumado). Aquí solo se
     * enciende la refracción donde el navegador la sabe dibujar y se mueve el ruido del filtro.
     */
    start() {
        const raiz = document.documentElement;
        const filtro = document.querySelector(".o_dcasa_filtros");
        const conRefraccion =
            navigator.userAgentData?.brands?.some((b) => b.brand === "Chromium") &&
            window.CSS?.supports?.("backdrop-filter", "url(#a)");
        // La referencia va inline: dentro del CSS, el empaquetador de Odoo reescribiría
        // url(#dcasa-liquido) como una ruta de archivo y el filtro no se aplicaría.
        // Quien pidió menos movimiento se queda con el vidrio mate, quieto (tokens.css de su web).
        if (conRefraccion && filtro && !reducido()) {
            raiz.style.setProperty(
                "--dcasa-refraccion",
                "url(#dcasa-liquido) blur(3px) saturate(220%) brightness(1.06)"
            );
            raiz.classList.add("o_dcasa_refraccion");
            this.animarVidrio(filtro);
        }
        this.registerCleanup(() => {
            raiz.classList.remove("o_dcasa_refraccion");
            raiz.style.removeProperty("--dcasa-refraccion");
        });

        // Las transiciones internas de la pastilla no deben contar para el cálculo de altura
        // que Odoo hace en cada `transitionend` de la cabecera.
        this.addListener(this.el.querySelectorAll(".o_main_nav"), "transitionend", (ev) => ev.stopPropagation());
    }

    /**
     * El ruido del filtro se mueve lento: el vidrio «fluye», como en babycaleb.com (18 s, el mismo <animate> de su
     * index.html). En pausa con la pestaña oculta y nunca con prefers-reduced-motion.
     */
    animarVidrio(filtro) {
        const ruido = filtro.querySelector("feTurbulence");
        const anim = document.createElementNS("http://www.w3.org/2000/svg", "animate");
        anim.setAttribute("attributeName", "baseFrequency");
        anim.setAttribute("dur", "18s");
        anim.setAttribute("repeatCount", "indefinite");
        anim.setAttribute("values", "0.009 0.022;0.012 0.018;0.009 0.022");
        ruido.appendChild(anim);
        this.addListener(document, "visibilitychange", () => {
            if (document.hidden) {
                filtro.pauseAnimations();
            } else {
                filtro.unpauseAnimations();
            }
        });
        this.registerCleanup(() => {
            anim.remove();
            filtro.unpauseAnimations();
        });
    }
}

export class DcasaResenas extends Interaction {
    static selector = ".o_dcasa_resenas";
    dynamicContent = {
        ".o_dcasa_resenas_pausa": {
            "t-on-click": this.alternar,
            "t-att-aria-pressed": () => String(this.pausada),
        },
        ".o_dcasa_resenas_cinta": {
            "t-att-class": () => ({ "is-pausada": this.pausada }),
        },
    };

    setup() {
        this.pausada = reducido();
    }

    alternar() {
        this.pausada = !this.pausada;
    }
}

/**
 * Fotos de producto en un cuadro 3:4 que llenan («cover»): casi todas son verticales. Las anchas
 * (más de 4:5) perderían los lados del mueble, así que van enteras (.o_dcasa_foto_ancha).
 * El cuadro no cambia de tamaño: no hay salto de diseño.
 */
export class DcasaFotos extends Interaction {
    static selector = "#wrapwrap";

    start() {
        const fotos = this.el.querySelectorAll(
            ".o_dcasa_pcard_media img, #o_wsale_products_grid .oe_product_image_link img"
        );
        for (const foto of fotos) {
            if (foto.complete && foto.naturalWidth) {
                this.clasificar(foto);
            } else {
                this.addListener(foto, "load", () => this.clasificar(foto));
            }
        }
        this.registerCleanup(() => fotos.forEach((foto) => foto.classList.remove("o_dcasa_foto_ancha")));
    }

    clasificar(foto) {
        foto.classList.toggle("o_dcasa_foto_ancha", foto.naturalWidth / foto.naturalHeight > 0.8);
    }
}

const interacciones = registry.category("public.interactions");
interacciones.add("website_dcasa.revelar", DcasaRevelar);
interacciones.add("website_dcasa.cabecera", DcasaCabecera);
interacciones.add("website_dcasa.resenas", DcasaResenas);
interacciones.add("website_dcasa.fotos", DcasaFotos);
