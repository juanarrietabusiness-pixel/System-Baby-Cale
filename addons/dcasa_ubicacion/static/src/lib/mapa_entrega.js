/*
 * El mapa para marcar el punto de entrega (docs/UBICACION.md). JavaScript simple, sin Odoo: lo usan la página del
 * enlace de un solo uso (/u/<secreto>) y el checkout de la tienda.
 *
 * Cómo funciona (la idea de Nébula, con lo que le faltaba):
 *   - El pin está FIJO en el centro y la clienta mueve el mapa debajo (con un dedo: gestureHandling «greedy»). El
 *     centro, cuando el mapa se detiene, es el punto.
 *   - «Usar mi ubicación» pide el GPS (alta precisión). Si el error es de más de 100 m, se le pide mover el mapa hasta
 *     su puerta: hasta entonces el punto no cuenta como bueno. Sin mapa, ese GPS no sirve: que lo intente en su puerta
 *     con la ubicación precisa o que busque su barriada (y la página no le muestra precio).
 *   - Buscar: la tabla de lugares de la tienda (barriadas, PH, lugares conocidos), con «buscar(texto)» que pone quien
 *     monta el mapa. Elegir uno centra el mapa ahí (origen «busqueda»), pero eso es la barriada, no su puerta: con
 *     mapa, el punto no es bueno hasta que lo MUEVA (auditoría 1); sin mapa vale, avisándole que es aproximado.
 *   - Sin clave de Google, si Google no carga o si RECHAZA la clave (``gm_authFailure``, o un mapa que no da su
 *     centro) no hay mapa: queda el modo «sin mapa» (GPS y búsqueda) y se avisa con ``alSinMapa``. Antes, con una
 *     clave mala, «Mi ubicación» se quedaba en «Buscando…» para siempre (auditoría 1).
 *
 * window.DcasaMapaEntrega.montar(opciones) → { punto(), conMapa(), centrar(lat, lon, zoom, origen, precision),
 *                                              destruir() }
 *   opciones: { mapa: Element|null, clave: string, nonce: string, botonGps: Element, aviso: Element,
 *               alCambiar(estado), alSinMapa(motivo) }
 *   estado: { lat, lon, origen, precision, zoom, bueno, motivo, aproximado }
 *   motivo (si no es bueno): sin_punto, lejos, buscado, impreciso, impreciso_sin_mapa.
 */
(function () {
  "use strict";

  var PANAMA = { lat: 8.9824, lng: -79.5199 };
  var PRECISION_MAX_M = 100;
  var ZOOM_MINIMO = 16; // con el mapa, para confirmar hay que estar a nivel de calle
  var ESPERA_GOOGLE_MS = 15000;
  var cargando = null;
  var claveRechazada = false;
  var alRechazarClave = [];

  // Google llama a window.gm_authFailure cuando la clave no sirve (otro dominio, sin facturación, API apagada). El
  // mapa ya se creó y se ve gris con «algo salió mal»: hay que pasar al modo sin mapa.
  function escucharClaveRechazada() {
    if (window.gm_authFailure && window.gm_authFailure.dcasa) return;
    var anterior = window.gm_authFailure;
    var alFallar = function () {
      claveRechazada = true;
      alRechazarClave.slice().forEach(function (fn) {
        try {
          fn();
        } catch (e) {
          // una página ya cerrada no detiene a las demás
        }
      });
      if (typeof anterior === "function") anterior();
    };
    alFallar.dcasa = true;
    window.gm_authFailure = alFallar;
  }

  function cargarGoogle(clave, nonce) {
    escucharClaveRechazada();
    if (claveRechazada) return Promise.reject(new Error("clave"));
    if (window.google && window.google.maps && window.google.maps.Map) return Promise.resolve(window.google.maps);
    if (cargando) return cargando;
    cargando = new Promise(function (resolver, rechazar) {
      var nombre = "dcasaMapaListo" + Math.random().toString(36).slice(2);
      var reloj = setTimeout(function () {
        rechazar(new Error("teselas"));
      }, ESPERA_GOOGLE_MS);
      window[nombre] = function () {
        clearTimeout(reloj);
        try {
          delete window[nombre];
        } catch (e) {
          window[nombre] = undefined;
        }
        if (claveRechazada) rechazar(new Error("clave"));
        else resolver(window.google.maps);
      };
      var s = document.createElement("script");
      s.src =
        "https://maps.googleapis.com/maps/api/js?key=" + encodeURIComponent(clave) +
        "&v=weekly&language=es&region=PA&loading=async&callback=" + nombre;
      s.async = true;
      if (nonce) s.nonce = nonce;
      s.onerror = function () {
        clearTimeout(reloj);
        rechazar(new Error("libreria"));
      };
      document.head.appendChild(s);
    });
    cargando.catch(function () {
      cargando = null;
    });
    return cargando;
  }

  function texto(el, valor) {
    if (el) el.textContent = valor || "";
  }

  function redondo(n) {
    return Math.round(n * 1e7) / 1e7;
  }

  function montar(op) {
    var estado = { lat: null, lon: null, origen: null, precision: null, zoom: null };
    var mapa = null;
    var porCodigo = false; // el próximo «idle» lo provocó el código (GPS, búsqueda), no la clienta
    var marcado = false; // hasta que haya GPS, búsqueda o la clienta mueva el mapa, no hay punto
    var vivo = true;
    var sinMapaYa = false;
    var ultimoPuesto = null; // el último punto que dio el GPS o la búsqueda (por si Google no da el centro)

    function bueno() {
      if (estado.lat === null) return { bueno: false, motivo: "sin_punto" };
      if (mapa && (estado.zoom || 0) < ZOOM_MINIMO) return { bueno: false, motivo: "lejos" };
      // Lo buscado es la barriada, no la puerta: con el mapa, hay que moverlo hasta la casa.
      if (mapa && estado.origen === "busqueda") return { bueno: false, motivo: "buscado" };
      if (estado.origen === "gps" && estado.precision !== null && estado.precision > PRECISION_MAX_M) {
        // Con mapa se corrige moviéndolo; sin mapa no hay cómo: en una computadora el «GPS» sale de la conexión a
        // internet y puede errar por kilómetros. Que lo intente en su puerta o busque su barriada.
        return { bueno: false, motivo: mapa ? "impreciso" : "impreciso_sin_mapa" };
      }
      return { bueno: true, motivo: "" };
    }

    function estadoParaFuera() {
      var b = bueno();
      return {
        lat: estado.lat, lon: estado.lon, origen: estado.origen, precision: estado.precision, zoom: estado.zoom,
        bueno: b.bueno, motivo: b.motivo, aproximado: b.bueno && estado.origen === "busqueda",
      };
    }

    function avisar() {
      if (!vivo) return;
      var p = estadoParaFuera();
      // Avisos cortos y con ícono: la gente no lee párrafos (el dueño, 2026-11-25).
      if (p.motivo === "lejos") texto(op.aviso, "🔍 Acérquese más y ponga el pin en su puerta");
      else if (p.motivo === "buscado") texto(op.aviso, "👆 Ahora mueva el mapa hasta su puerta");
      else if (p.motivo === "impreciso") texto(op.aviso, "👆 Mueva el mapa: ponga el pin en su puerta");
      else if (p.motivo === "impreciso_sin_mapa")
        texto(op.aviso, "📍 Su teléfono no da la ubicación exacta. Active la ubicación precisa y toque «Mi ubicación» " +
          "en su puerta, o busque su barriada 👇");
      else if (p.aproximado)
        texto(op.aviso, "📍 Es aproximado (su barriada). En su puerta, toque «Mi ubicación» para que sea exacto");
      else texto(op.aviso, "");
      if (op.alCambiar) op.alCambiar(p);
    }

    // Sin mapa de aquí en adelante (no cargó, Google rechazó la clave o el mapa no da su centro). El punto que ya
    // había (GPS o búsqueda) se queda; la página lo sabe por ``alSinMapa`` y esconde el marco.
    function sinMapa(motivo) {
      if (!vivo || sinMapaYa) return;
      sinMapaYa = true;
      mapa = null;
      if (op.mapa) op.mapa.classList.add("o_dcasa_mapa_sin_mapa");
      if (op.alSinMapa) op.alSinMapa(motivo);
      if (estado.lat === null) {
        texto(op.aviso, "🗺️ El mapa no cargó. Toque «Mi ubicación» o busque su barriada 👇");
        if (op.alCambiar) op.alCambiar(estadoParaFuera());
      } else {
        estado.zoom = null;
        avisar();
      }
    }

    function alFallarLaClave() {
      sinMapa("clave");
    }
    alRechazarClave.push(alFallarLaClave);

    function tomarCentro() {
      var c = null;
      try {
        c = mapa && mapa.getCenter();
      } catch (e) {
        c = null;
      }
      if (!c || typeof c.lat !== "function") {
        // Google no da el centro (clave rechazada o mapa roto): vale el último punto del GPS o de la búsqueda.
        if (ultimoPuesto) {
          estado.lat = ultimoPuesto.lat;
          estado.lon = ultimoPuesto.lon;
        }
        sinMapa("centro");
        return;
      }
      estado.lat = redondo(c.lat());
      estado.lon = redondo(c.lng());
      estado.zoom = mapa.getZoom();
    }

    function centrar(lat, lon, zoom, origen, precision) {
      estado.origen = origen;
      estado.precision = precision === undefined ? null : precision;
      marcado = true;
      ultimoPuesto = { lat: redondo(lat), lon: redondo(lon) };
      if (mapa) {
        porCodigo = true;
        try {
          mapa.setCenter({ lat: lat, lng: lon });
          mapa.setZoom(zoom || 18);
        } catch (e) {
          // el mapa se rompió: tomarCentro (aquí abajo) pasa al modo sin mapa con este mismo punto
        }
        // El «idle» de Google llega después; por si no llega (mismo centro y zoom), se toma ya.
        tomarCentro();
        if (!mapa) return; // pasó al modo sin mapa: ya avisó
      } else {
        estado.lat = ultimoPuesto.lat;
        estado.lon = ultimoPuesto.lon;
        estado.zoom = null;
      }
      avisar();
    }

    if (op.mapa && op.clave) {
      cargarGoogle(op.clave, op.nonce).then(function (maps) {
        if (!vivo || sinMapaYa) return;
        mapa = new maps.Map(op.mapa, {
          center: PANAMA, zoom: 12, gestureHandling: "greedy", clickableIcons: false,
          disableDefaultUI: true, zoomControl: true, mapTypeControl: true,
          mapTypeControlOptions: { mapTypeIds: ["roadmap", "hybrid"] },
        });
        op.mapa.classList.add("o_dcasa_mapa_listo");
        mapa.addListener("dragstart", function () {
          porCodigo = false;
          marcado = true;
          estado.origen = "pin";
          estado.precision = null;
        });
        mapa.addListener("zoom_changed", function () {
          if (!porCodigo && marcado && estado.origen !== "gps") estado.origen = estado.origen || "pin";
        });
        mapa.addListener("idle", function () {
          var deCodigo = porCodigo;
          porCodigo = false;
          if (!marcado || !mapa) return;
          tomarCentro();
          if (!mapa) return;
          if (!deCodigo && !estado.origen) estado.origen = "pin";
          avisar();
        });
        if (claveRechazada) {
          sinMapa("clave");
          return;
        }
        if (estado.lat !== null) centrar(estado.lat, estado.lon, 18, estado.origen, estado.precision);
      }).catch(function (error) {
        sinMapa((error && error.message) || "libreria");
      });
    } else if (op.mapa) {
      op.mapa.classList.add("o_dcasa_mapa_sin_mapa");
    }

    function usarGps() {
      if (!navigator.geolocation) {
        texto(op.aviso, mapa ? "👆 Mueva el mapa hasta su casa" : "Busque su barriada aquí abajo 👇");
        return;
      }
      texto(op.aviso, "📍 Buscando…");
      if (op.botonGps) op.botonGps.disabled = true;
      navigator.geolocation.getCurrentPosition(
        function (pos) {
          if (op.botonGps) op.botonGps.disabled = false;
          try {
            var precision = Math.round(pos.coords.accuracy || 0);
            centrar(pos.coords.latitude, pos.coords.longitude, 18, "gps", precision);
          } catch (e) {
            // Nunca dejar «Buscando…» colgado.
            texto(op.aviso, "No la encontramos: intente otra vez o busque su barriada 👇");
          }
        },
        function (error) {
          if (op.botonGps) op.botonGps.disabled = false;
          if (error && error.code === 1) {
            texto(op.aviso, mapa ? "Sin permiso de ubicación: 👆 mueva el mapa o busque su barriada"
              : "Sin permiso de ubicación: busque su barriada aquí abajo 👇");
          } else {
            texto(op.aviso, mapa ? "No la encontramos: 👆 mueva el mapa o busque su barriada"
              : "No la encontramos: intente otra vez o busque su barriada 👇");
          }
        },
        { enableHighAccuracy: true, timeout: 12000, maximumAge: 0 }
      );
    }

    if (op.botonGps) op.botonGps.addEventListener("click", usarGps);

    return {
      punto: estadoParaFuera,
      conMapa: function () {
        return !!mapa;
      },
      centrar: centrar,
      destruir: function () {
        vivo = false;
        var i = alRechazarClave.indexOf(alFallarLaClave);
        if (i >= 0) alRechazarClave.splice(i, 1);
        if (op.botonGps) op.botonGps.removeEventListener("click", usarGps);
      },
    };
  }

  window.DcasaMapaEntrega = { montar: montar, cargarGoogle: cargarGoogle, ZOOM_MINIMO: ZOOM_MINIMO };
})();
