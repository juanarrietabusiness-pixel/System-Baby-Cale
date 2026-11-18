/**
 * La marca del panel en el navegador: el logo y el nombre que muestran la barra lateral y el menú del celular.
 *
 * Los manda el servidor en `session.dcasa_marca` (models/ir_http.py, Ajustes › Marca del panel). Sin logo propio
 * vienen vacíos y queda el de fábrica, el mismo de siempre: la barra no cambia ni un atributo.
 */
import { session } from "@web/session";
import { patch } from "@web/core/utils/patch";
import { NavBar } from "@web/webclient/navbar/navbar";

export const LOGO_DE_FABRICA = "/dcasa_base/static/img/logo.png";
// El de fábrica va con el logo de fábrica (dcasa_base/static/img/logo.png, el de la empresa: Baby Caleb).
export const NOMBRE_DE_FABRICA = "Baby Caleb";

export function logoDelPanel() {
    return session.dcasa_marca?.logo || LOGO_DE_FABRICA;
}

export function nombreDelPanel() {
    return session.dcasa_marca?.nombre || NOMBRE_DE_FABRICA;
}

// El cajón del menú del celular es una plantilla de NavBar (web.NavBar.AppsMenu.Sidebar, ver xml/menu_celular.xml).
patch(NavBar.prototype, {
    get dcasaLogo() {
        return logoDelPanel();
    },
    get dcasaNombre() {
        return nombreDelPanel();
    },
});
