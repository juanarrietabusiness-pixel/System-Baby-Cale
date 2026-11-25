/*
 * El mapa para marcar el punto de entrega (docs/UBICACION.md). JavaScript simple, sin Odoo: lo usan la página del
 * enlace de un solo uso (/u/<secreto>) y el checkout de la tienda.
 *
 * Cómo funciona (la idea de Nébula, con lo que le faltaba):
 *   - El pin está FIJO en el centro y la clienta mueve el mapa debajo (con un dedo: gestureHandling «greedy»). El
 *     centro, cuando el mapa se detiene, es el punto.
 *   - «Usar mi ubicación» pide el GPS (alta precisión). Si el error es de más de 100 m, se le pide mover el mapa hasta
 *     su puerta: hasta entonces el punto no cuenta como bueno.
 *   - Buscar: la tabla de lugares de la tienda (barriadas, PH, lugares conocidos), con «buscar(texto)» que pone quien
 *     monta el mapa. Elegir uno centra el mapa ahí (origen «busqueda»): hay que acercarse y confirmar igual.
 *   - Sin clave de Google (o si Google no carga) no hay mapa, pero el GPS sigue funcionando.
 *
 * window.DcasaMapaEntrega.montar(opciones) → { punto(), listo(), centrar(lat, lon, zoom, origen), destruir() }
 *   opciones: { mapa: Element|null, clave: string, nonce: string, botonGps: Element, aviso: Element,
 *               alCambiar(estado) }  — estado: { lat, lon, origen, precision, zoom, bueno, motivo }
 */
(function () {
  "use strict";

  var PANAMA = { lat: 8.9824, lng: -79.5199 };
  var PRECISION_MAX_M = 100;
  var ZOOM_MINIMO = 16; // con el mapa, para confirmar hay que estar a nivel de calle
  var ESPERA_GOOGLE_MS = 15000;
  var cargando = null;

  function cargarGoogle(clave, nonce) {
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
        resolver(window.google.maps);
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

  function montar(op) {
    var estado = { lat: null, lon: null, origen: null, precision: null, zoom: null };
    var mapa = null;
    var porCodigo = false; // el próximo «idle» lo provocó el código (GPS, búsqueda), no la clienta
    var marcado = false; // hasta que haya GPS, búsqueda o la clienta mueva el mapa, no hay punto
    var vivo = true;

    function bueno() {
      if (estado.lat === null) return { bueno: false, motivo: "sin_punto" };
      if (mapa && (estado.zoom || 0) < ZOOM_MINIMO) return { bueno: false, motivo: "lejos" };
      if (estado.origen === "gps" && estado.precision !== null && estado.precision > PRECISION_MAX_M && mapa) {
        return { bueno: false, motivo: "impreciso" };
      }
      return { bueno: true, motivo: "" };
    }

    function avisar() {
      if (!vivo) return;
      var b = bueno();
      if (b.motivo === "lejos") texto(op.aviso, "Acérquese más (a nivel de calle) y deje el pin sobre su puerta.");
      else if (b.motivo === "impreciso")
        texto(op.aviso, "Su teléfono nos da el punto con un margen de ±" + estado.precision +
          " m. Mueva el mapa hasta que el pin quede sobre su puerta.");
      else if (estado.origen === "gps" && estado.precision > PRECISION_MAX_M)
        texto(op.aviso, "Su teléfono nos da el punto con un margen de ±" + estado.precision + " m.");
      else texto(op.aviso, "");
      if (op.alCambiar) {
        op.alCambiar({
          lat: estado.lat, lon: estado.lon, origen: estado.origen, precision: estado.precision,
          zoom: estado.zoom, bueno: b.bueno, motivo: b.motivo,
        });
      }
    }

    function tomarCentro() {
      var c = mapa.getCenter();
      estado.lat = Math.round(c.lat() * 1e7) / 1e7;
      estado.lon = Math.round(c.lng() * 1e7) / 1e7;
      estado.zoom = mapa.getZoom();
    }

    function centrar(lat, lon, zoom, origen, precision) {
      estado.origen = origen;
      estado.precision = precision === undefined ? null : precision;
      marcado = true;
      if (mapa) {
        porCodigo = true;
        mapa.setCenter({ lat: lat, lng: lon });
        mapa.setZoom(zoom || 18);
        // El «idle» de Google llega después; por si no llega (mismo centro y zoom), se toma ya.
        tomarCentro();
      } else {
        estado.lat = Math.round(lat * 1e7) / 1e7;
        estado.lon = Math.round(lon * 1e7) / 1e7;
        estado.zoom = null;
      }
      avisar();
    }

    if (op.mapa && op.clave) {
      cargarGoogle(op.clave, op.nonce).then(function (maps) {
        if (!vivo) return;
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
          if (!marcado) return;
          tomarCentro();
          if (!deCodigo && !estado.origen) estado.origen = "pin";
          avisar();
        });
        if (estado.lat !== null) centrar(estado.lat, estado.lon, 18, estado.origen, estado.precision);
      }).catch(function (error) {
        if (!vivo) return;
        op.mapa.classList.add("o_dcasa_mapa_sin_mapa");
        texto(op.aviso, "El mapa no cargó. Puede usar «Usar mi ubicación» o escribir la dirección.");
        if (op.alSinMapa) op.alSinMapa(error && error.message);
      });
    } else if (op.mapa) {
      op.mapa.classList.add("o_dcasa_mapa_sin_mapa");
    }

    function usarGps() {
      if (!navigator.geolocation) {
        texto(op.aviso, "Este navegador no deja leer la ubicación. " +
          (mapa ? "Mueva el mapa hasta su casa." : "Escríbanos la dirección."));
        return;
      }
      texto(op.aviso, "Buscando su ubicación…");
      if (op.botonGps) op.botonGps.disabled = true;
      navigator.geolocation.getCurrentPosition(
        function (pos) {
          if (op.botonGps) op.botonGps.disabled = false;
          var precision = Math.round(pos.coords.accuracy || 0);
          centrar(pos.coords.latitude, pos.coords.longitude, 18, "gps", precision);
        },
        function (error) {
          if (op.botonGps) op.botonGps.disabled = false;
          if (error && error.code === 1) {
            texto(op.aviso, "No nos dio permiso de ubicación. " +
              (mapa ? "Puede mover el mapa hasta su casa o buscar su barriada." : "Escríbanos la dirección."));
          } else {
            texto(op.aviso, "No pudimos leer su ubicación ahora. " +
              (mapa ? "Mueva el mapa hasta su casa o busque su barriada." : "Intente otra vez en un momento."));
          }
        },
        { enableHighAccuracy: true, timeout: 12000, maximumAge: 0 }
      );
    }

    if (op.botonGps) op.botonGps.addEventListener("click", usarGps);

    return {
      punto: function () {
        var b = bueno();
        return { lat: estado.lat, lon: estado.lon, origen: estado.origen, precision: estado.precision,
          zoom: estado.zoom, bueno: b.bueno, motivo: b.motivo };
      },
      conMapa: function () {
        return !!mapa;
      },
      centrar: centrar,
      destruir: function () {
        vivo = false;
        if (op.botonGps) op.botonGps.removeEventListener("click", usarGps);
      },
    };
  }

  window.DcasaMapaEntrega = { montar: montar, cargarGoogle: cargarGoogle, ZOOM_MINIMO: ZOOM_MINIMO };
})();
