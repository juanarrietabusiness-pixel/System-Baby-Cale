/**
 * Checkout: «¿Dónde le entregamos?» (views/checkout_templates.xml, docs/UBICACION.md).
 *
 * Usa el mismo mapa que la página del enlace del chat (static/src/lib/mapa_entrega.js, que va en el paquete del sitio):
 * pin fijo, «Usar mi ubicación», buscador de barriadas y lugares de la tienda. Cuando el punto cambia, el servidor dice
 * la zona, el precio del envío y si lo escrito nombra otro distrito (/tienda/ubicacion/zona); con «Sí, aquí es» el punto
 * queda confirmado en los campos ocultos que viajan con el formulario. Mover el mapa después lo des-confirma.
 *
 * Lo escrito manda: la calle y la ciudad solo se llenan si están vacías (o si las llenó el mapa antes).
 */
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

export class CheckoutUbicacion extends Interaction {
    static selector = ".o_dcasa_ubicacion";

    setup() {
        this.form = this.el.closest("form");
        this.ultimo = null;
        this.zonaValida = false;
        this.pedido = 0;
        this.reloj = null;
        this.relojBuscar = null;
        this.llenadoPorElMapa = new Set();
    }

    start() {
        const q = (s) => this.el.querySelector(s);
        this.tarjeta = q(".o_dcasa_ubic_tarjeta");
        this.zona = q(".o_dcasa_ubic_zona");
        this.precio = q(".o_dcasa_ubic_precio");
        this.cruce = q(".o_dcasa_ubic_cruce");
        this.botonSi = q(".o_dcasa_ubic_si");
        this.ok = q(".o_dcasa_ubic_ok");
        this.referencia = q("[name=dcasa_referencia]");
        this.lista = q(".o_dcasa_ubic_lista");
        this.buscar = q(".o_dcasa_ubic_buscar");
        this.oculto = (n) => this.el.querySelector(`[name=dcasa_ubic_${n}]`);
        const Mapa = window.DcasaMapaEntrega;
        if (!Mapa) return;
        this.mapa = Mapa.montar({
            mapa: q(".o_dcasa_ubic_mapa"),
            clave: this.el.dataset.clave || "",
            botonGps: q(".o_dcasa_ubic_gps"),
            aviso: q(".o_dcasa_ubic_aviso"),
            alCambiar: (p) => this.cambio(p),
            alSinMapa: () => q(".o_dcasa_ubic_mapa_marco").classList.add("o_dcasa_sin_mapa"),
        });
        if (!this.el.dataset.clave) q(".o_dcasa_ubic_mapa_marco").classList.add("o_dcasa_sin_mapa");
        const lat = parseFloat(this.el.dataset.lat), lon = parseFloat(this.el.dataset.lon);
        if (Number.isFinite(lat) && Number.isFinite(lon)) {
            // El punto de la ficha o el que dio en el chat de la tienda: solo falta tocar «Sí, aquí es».
            const precision = parseInt(this.el.dataset.precision, 10);
            this.mapa.centrar(lat, lon, 18, this.el.dataset.origen || "pin", Number.isFinite(precision) ? precision : null);
        }
        this.addListener(this.botonSi, "click", () => this.confirmar());
        this.addListener(this.referencia, "input", () => this.actualizar());
        this.addListener(this.buscar, "input", () => this.alBuscar());
        for (const radio of this.el.querySelectorAll("[name=dcasa_ubic_modo]")) {
            this.addListener(radio, "change", () => this.modo());
        }
        for (const nombre of ["street", "city"]) {
            const campo = this.form && this.form.querySelector(`[name=${nombre}]`);
            if (campo) this.addListener(campo, "input", () => this.llenadoPorElMapa.delete(nombre));
        }
        this.modo();
    }

    destroy() {
        clearTimeout(this.reloj);
        clearTimeout(this.relojBuscar);
        this.mapa?.destruir();
    }

    modo() {
        const enMapa = this.el.querySelector("#o_dcasa_modo_mapa")?.checked;
        this.el.querySelector(".o_dcasa_ubic_parte_mapa").classList.toggle("d-none", !enMapa);
        // El número de casa y las indicaciones van siempre (en el mapa o escrita).
        this.referencia.required = true;
    }

    cambio(p) {
        this.ultimo = p;
        this.oculto("confirmada").value = "";
        this.ok.classList.add("d-none");
        this.botonSi.classList.remove("d-none");
        this.actualizar();
        clearTimeout(this.reloj);
        this.reloj = setTimeout(() => this.previa(), 500);
    }

    actualizar() {
        this.botonSi.disabled = !(this.ultimo && this.ultimo.bueno && this.zonaValida);
    }

    textoEscrito() {
        const valor = (n) => (this.form?.querySelector(`[name=${n}]`)?.value || "").trim();
        return [valor("street"), valor("street2"), valor("city")].filter(Boolean).join(", ");
    }

    async previa() {
        if (!this.ultimo || this.ultimo.lat === null) return;
        const n = ++this.pedido;
        this.tarjeta.classList.remove("d-none");
        this.zona.textContent = "…";
        this.precio.textContent = "";
        this.cruce.textContent = "";
        this.zonaValida = false;
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

    confirmar() {
        if (this.botonSi.disabled || !this.ultimo) return;
        this.oculto("lat").value = this.ultimo.lat;
        this.oculto("lon").value = this.ultimo.lon;
        this.oculto("origen").value = this.ultimo.origen || "pin";
        this.oculto("precision").value = this.ultimo.precision ?? "";
        this.oculto("confirmada").value = "1";
        this.ok.classList.remove("d-none");
        this.botonSi.classList.add("d-none");
        this.referencia.focus();
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
