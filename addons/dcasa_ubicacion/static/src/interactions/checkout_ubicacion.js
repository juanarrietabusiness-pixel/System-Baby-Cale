/**
 * Checkout: «¿Dónde le entregamos?» (views/checkout_templates.xml, docs/UBICACION.md).
 *
 * Usa el mismo mapa que la página del enlace del chat (static/src/lib/mapa_entrega.js, que va en el paquete del sitio):
 * pin fijo, «Usar mi ubicación», buscador de barriadas y lugares de la tienda. Cuando el punto cambia (y es bueno), el
 * servidor dice la zona, el precio del envío y si lo escrito nombra otro distrito (/tienda/ubicacion/zona); con «Sí,
 * aquí es» el punto queda confirmado en los campos ocultos que viajan con el formulario. Mover el mapa después lo
 * des-confirma.
 *
 * «Confirmar» (el botón de Odoo, abajo y fijo en el celular) cuenta como el «sí» si el punto es bueno y la zona salió
 * bien. Si falta algo, no se envía: la página baja hasta el bloque, dice ahí qué falta y lleva el foco (auditoría 1:
 * el aviso salía arriba, fuera de la vista, y parecía que «Confirmar» no hacía nada).
 *
 * Lo escrito manda: la calle y la ciudad solo se llenan si están vacías (o si las llenó el mapa antes), y lo que llenó
 * el mapa no cuenta como «lo que escribió» para el aviso de cruce.
 */
import { CustomerAddress } from "@portal/interactions/address";
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";

const CASA = "dcasa_referencia";
const BOTON_DE_ODOO = '[name="website_sale_main_button"]';
const FALTA_MOTIVO = {
    lejos: "🔍 Acérquese más en el mapa y ponga el pin en su puerta",
    buscado: "👆 Ahora mueva el mapa hasta su puerta",
    impreciso: "👆 Mueva el mapa hasta su puerta",
    impreciso_sin_mapa: "📍 Su ubicación no es exacta: toque «Mi ubicación» en su puerta o busque su barriada",
};

// El número de casa va siempre (el dueño, 2026-11-25, como en PedidosYa). Odoo, al cargar y al cambiar el país, le
// quita «required» a todo campo que no está en su lista (portal/interactions/address.js): aquí no se lo quita.
patch(CustomerAddress.prototype, {
    _markRequired(name, required) {
        return super._markRequired(name, name === CASA ? true : required);
    },
});

export class CheckoutUbicacion extends Interaction {
    // Solo el bloque del checkout: la tarjeta «Marcar mi casa» del pedido y de «¡Gracias por su compra!» lleva la misma
    // clase (para sus estilos) y sin el mapa esto fallaba («classList» de null) en esas páginas.
    static selector = "#div_dcasa_ubicacion";

    setup() {
        this.form = this.el.closest("form");
        this.ultimo = null;
        this.zonaValida = false;
        this.zonaError = false;
        this.pedido = 0;
        this.reloj = null;
        this.relojBuscar = null;
        this.llenadoPorElMapa = new Set();
        this.etiquetaCalle = null;
    }

    start() {
        const q = (s) => this.el.querySelector(s);
        this.tarjeta = q(".o_dcasa_ubic_tarjeta");
        this.zona = q(".o_dcasa_ubic_zona");
        this.precio = q(".o_dcasa_ubic_precio");
        this.cruce = q(".o_dcasa_ubic_cruce");
        this.botonSi = q(".o_dcasa_ubic_si");
        this.botonGps = q(".o_dcasa_ubic_gps");
        this.ok = q(".o_dcasa_ubic_ok");
        this.referencia = q(`[name=${CASA}]`);
        this.lista = q(".o_dcasa_ubic_lista");
        this.buscar = q(".o_dcasa_ubic_buscar");
        this.faltaPunto = q(".o_dcasa_ubic_falta_punto");
        this.faltaCasa = q(".o_dcasa_ubic_falta_casa");
        this.oculto = (n) => this.el.querySelector(`[name=dcasa_ubic_${n}]`);
        // «Confirmar» de Odoo: se revisa ANTES que Odoo (fase de captura) para llenar el «sí» o frenar el envío.
        this.addListener(document, "click", (ev) => this.alEnviar(ev), { capture: true });
        this.addListener(this.referencia, "input", () => this.quitarFalta(this.faltaCasa));
        for (const radio of this.el.querySelectorAll("[name=dcasa_ubic_modo]")) {
            this.addListener(radio, "change", () => this.modo());
        }
        for (const nombre of ["street", "city"]) {
            const campo = this.form && this.form.querySelector(`[name=${nombre}]`);
            if (campo) this.addListener(campo, "input", () => this.llenadoPorElMapa.delete(nombre));
        }
        this.modo();
        const Mapa = window.DcasaMapaEntrega;
        if (!Mapa) return;
        this.addListener(this.botonSi, "click", () => this.confirmar(true));
        this.addListener(this.buscar, "input", () => this.alBuscar());
        this.mapa = Mapa.montar({
            mapa: q(".o_dcasa_ubic_mapa"),
            clave: this.el.dataset.clave || "",
            botonGps: this.botonGps,
            aviso: q(".o_dcasa_ubic_aviso"),
            alCambiar: (p) => this.cambio(p),
            alSinMapa: () => q(".o_dcasa_ubic_mapa_marco").classList.add("o_dcasa_sin_mapa"),
        });
        if (!this.el.dataset.clave) q(".o_dcasa_ubic_mapa_marco").classList.add("o_dcasa_sin_mapa");
        const lat = parseFloat(this.el.dataset.lat), lon = parseFloat(this.el.dataset.lon);
        if (Number.isFinite(lat) && Number.isFinite(lon)) {
            // El punto de la ficha (o el del chat: «whatsapp», «enlace») o el que dio en el chat de la tienda: solo
            // falta tocar «Sí, aquí es» (o «Confirmar»).
            const precision = parseInt(this.el.dataset.precision, 10);
            this.mapa.centrar(lat, lon, 18, this.el.dataset.origen || "pin", Number.isFinite(precision) ? precision : null);
        }
    }

    destroy() {
        clearTimeout(this.reloj);
        clearTimeout(this.relojBuscar);
        this.mapa?.destruir();
        this.etiquetarCalle(false);
    }

    enMapa() {
        return !!this.el.querySelector("#o_dcasa_modo_mapa")?.checked;
    }

    modo() {
        const enMapa = this.enMapa();
        this.el.querySelector(".o_dcasa_ubic_parte_mapa").classList.toggle("d-none", !enMapa);
        // El número de casa y las indicaciones van siempre (en el mapa o escrita).
        this.referencia.required = true;
        this.quitarFalta(this.faltaPunto);
        this.etiquetarCalle(enMapa);
    }

    /** Con el mapa, el número de casa va abajo («Número de casa e indicaciones»): la calle de Odoo («Calle y número»)
     *  se llama «Barriada o calle» para no pedir el número dos veces (auditoría 1). Escrita, vuelve a la de Odoo. */
    etiquetarCalle(enMapa) {
        const campo = this.form?.querySelector("[name=street]");
        const etiqueta = campo?.id && this.form.querySelector(`label[for="${campo.id}"]`);
        if (!etiqueta) return;
        if (this.etiquetaCalle === null) this.etiquetaCalle = etiqueta.textContent.trim();
        etiqueta.textContent = enMapa ? "Barriada o calle" : this.etiquetaCalle;
    }

    cambio(p) {
        this.ultimo = p;
        this.oculto("confirmada").value = "";
        this.ok.classList.add("d-none");
        this.botonSi.classList.remove("d-none");
        this.zonaValida = false;
        this.zonaError = false;
        this.pedido++; // lo que estaba en camino ya no vale
        clearTimeout(this.reloj);
        if (p.bueno) {
            this.quitarFalta(this.faltaPunto);
            this.reloj = setTimeout(() => this.previa(), 500);
        } else {
            // Sin un punto bueno no hay zona ni precio que mostrar (auditoría 1): el aviso del mapa dice qué hacer.
            this.tarjeta.classList.add("d-none");
        }
        this.actualizar();
    }

    actualizar() {
        this.botonSi.disabled = !(this.ultimo && this.ultimo.bueno && this.zonaValida);
    }

    /** Lo que escribió la clienta (no lo que llenó el mapa: eso daba un aviso de cruce falso, auditoría 1). */
    textoEscrito() {
        const valor = (n) =>
            this.llenadoPorElMapa.has(n) ? "" : (this.form?.querySelector(`[name=${n}]`)?.value || "").trim();
        return ["street", "street2", "city"].map(valor).filter(Boolean).join(", ");
    }

    async previa() {
        if (!this.ultimo || !this.ultimo.bueno) return;
        const n = ++this.pedido;
        this.tarjeta.classList.remove("d-none");
        this.zona.textContent = "…";
        this.precio.textContent = "";
        this.cruce.textContent = "";
        this.actualizar();
        let r;
        try {
            r = await this.waitFor(rpc("/tienda/ubicacion/zona", {
                lat: this.ultimo.lat, lon: this.ultimo.lon, texto: this.textoEscrito(),
            }));
        } catch {
            r = { error: "Sin conexión: intente otra vez." };
        }
        if (n !== this.pedido) return;
        if (r.error) {
            this.zonaError = true;
            this.zona.textContent = r.error;
            return;
        }
        this.zonaValida = true;
        // De un vistazo: la barriada (o el corregimiento) y el distrito; el precio, grande, con el camión al lado.
        this.zona.textContent = [r.barriada || r.corregimiento, r.distrito].filter(Boolean).join(", ")
            || "Fuera de nuestra lista";
        this.precio.textContent = r.precio ? `Envío ${r.precio}` : "Envío: se lo confirmamos";
        this.cruce.textContent = r.aviso || "";
        this.llenarSiVacio("city", r.distrito || "");
        this.llenarSiVacio("street", [r.barriada, r.corregimiento].filter(Boolean).join(", "));
        this.actualizar();
    }

    llenarSiVacio(nombre, valor) {
        const campo = this.form?.querySelector(`[name=${nombre}]`);
        if (!campo || !valor) return;
        if (campo.value.trim() && !this.llenadoPorElMapa.has(nombre)) return;
        campo.value = valor;
        this.llenadoPorElMapa.add(nombre);
    }

    confirmar(conFoco) {
        if (this.botonSi.disabled || !this.ultimo) return;
        this.oculto("lat").value = this.ultimo.lat;
        this.oculto("lon").value = this.ultimo.lon;
        this.oculto("origen").value = this.ultimo.origen || "pin";
        this.oculto("precision").value = this.ultimo.precision ?? "";
        this.oculto("confirmada").value = "1";
        this.ok.classList.remove("d-none");
        this.botonSi.classList.add("d-none");
        this.quitarFalta(this.faltaPunto);
        if (conFoco && !this.referencia.value.trim()) this.referencia.focus();
    }

    /** ¿Qué le falta para poder seguir? ``null`` si nada (y, con el mapa, el «sí» ya quedó en los campos ocultos). */
    loQueFalta() {
        if (this.enMapa() && this.oculto("confirmada").value !== "1") {
            const p = this.ultimo;
            if (p && p.bueno && this.zonaValida) {
                this.confirmar(false); // «Confirmar» cuenta como «Sí, aquí es»
            } else {
                let texto;
                if (!p || p.lat === null) texto = "📍 Toque «Mi ubicación» o busque su barriada";
                else if (!p.bueno) texto = FALTA_MOTIVO[p.motivo] || "📍 Falta su ubicación";
                else if (this.zonaError) texto = `📍 ${this.zona.textContent}`;
                else texto = "⏳ Un momento: estamos viendo su zona";
                const alGps = !p || p.lat === null || p.motivo === "impreciso_sin_mapa";
                return { donde: this.faltaPunto, texto, foco: alGps ? this.botonGps : this.faltaPunto };
            }
        }
        if (!this.referencia.value.trim()) {
            return { donde: this.faltaCasa, texto: "🏠 Escriba su número de casa", foco: this.referencia };
        }
        return null;
    }

    alEnviar(ev) {
        if (!ev.target?.closest?.(BOTON_DE_ODOO) || !this.el.isConnected) return;
        const falta = this.loQueFalta();
        if (!falta) return; // todo bien: sigue Odoo (valida lo suyo y manda el formulario)
        ev.preventDefault();
        ev.stopPropagation();
        this.mostrarFalta(falta);
    }

    mostrarFalta({ donde, texto, foco }) {
        this.quitarFalta(this.faltaPunto);
        this.quitarFalta(this.faltaCasa);
        donde.textContent = texto;
        donde.classList.remove("d-none");
        if (foco === this.referencia) this.referencia.classList.add("is-invalid");
        const destino = donde === this.faltaPunto ? this.el : this.referencia;
        destino.scrollIntoView({ block: donde === this.faltaPunto ? "start" : "center", behavior: "smooth" });
        foco?.focus({ preventScroll: true });
    }

    quitarFalta(donde) {
        if (!donde) return;
        donde.textContent = "";
        donde.classList.add("d-none");
        if (donde === this.faltaCasa) this.referencia.classList.remove("is-invalid");
    }

    alBuscar() {
        clearTimeout(this.relojBuscar);
        const texto = this.buscar.value.trim();
        if (texto.length < 2) {
            this.lista.textContent = "";
            return;
        }
        this.relojBuscar = setTimeout(async () => {
            let r;
            try {
                r = await this.waitFor(rpc("/tienda/ubicacion/buscar", { texto }));
            } catch {
                r = { lugares: [] };
            }
            this.lista.textContent = "";
            const lugares = r.lugares || [];
            if (!lugares.length) {
                const li = document.createElement("li");
                li.className = "text-muted";
                li.textContent = "No lo encontramos. Pruebe otro nombre.";
                this.lista.appendChild(li);
                return;
            }
            for (const lugar of lugares) {
                const li = document.createElement("li");
                const b = document.createElement("button");
                const s = document.createElement("small");
                b.type = "button";
                b.className = "o_dcasa_ubic_opcion";
                b.textContent = lugar.nombre;
                s.textContent = lugar.zona;
                b.appendChild(s);
                this.addListener(b, "click", () => {
                    this.mapa.centrar(lugar.lat, lugar.lon, 17, "busqueda");
                    this.lista.textContent = "";
                    this.buscar.value = lugar.nombre;
                });
                li.appendChild(b);
                this.lista.appendChild(li);
            }
        }, 400);
    }
}

registry.category("public.interactions").add("dcasa_ubicacion.checkout", CheckoutUbicacion);
