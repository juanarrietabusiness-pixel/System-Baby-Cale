# Herramientas del sistema: cuáles se pueden quitar

Lista para que el dueño marque qué se queda y qué se va (pedido del 2026-11-19: bajar el consumo sin dormir el sistema).
Sacada de los `__manifest__.py` y de las tareas programadas de cada módulo. Si algo no coincide con el código, manda el
código. Qué hace cada módulo en detalle: [MODULOS.md](MODULOS.md).

**Cómo leer la columna «Gasta»:**

- **Memoria:** lo que ocupa por estar instalado. Las herramientas propias ocupan poco.
- **Tareas:** las tareas automáticas que corren solas (gastan procesador, que se cobra por uso).
- **IA:** gasta en Meta cada vez que se usa.

## Lo que hay que saber antes de quitar

- **Lo pesado en memoria no se puede quitar.** Las piezas grandes de Odoo (tienda web, contabilidad, inventario, compras,
  CRM y Empleados) las piden los cimientos (`dcasa_base` pide CRM, ventas, compras, inventario y contabilidad;
  `dcasa_contactos` pide Empleados; `dcasa_interfaz` pide el sitio web). Se quedan aunque se quiten herramientas. Por eso
  quitar herramientas ahorra **poca memoria**. Lo que sí ahorra es en tareas, en IA y en desorden. Cuánta memoria baja hay
  que **medirlo**, no adivinarlo.
- **Las llamadas y videollamadas no son una herramienta aparte.** Son parte de Conversaciones de Odoo (`mail`, en
  `vendor/odoo/addons/mail/models/discuss/`), y de eso depende todo: el historial de cada venta y factura, la bandeja de
  Juan y los avisos en vivo. No se puede desinstalar. Las llamadas van de navegador a navegador y solo gastan mientras hay
  una. Lo que sí se puede es **esconder los botones**: el panel queda más limpio, pero eso no cambia la memoria.
- **OdooBot ya está apagado** para todos los usuarios (`dcasa_interfaz`, prueba `test_inicio_sin_recorrido_ni_odoobot`).
- Si Brian tiene herramientas de un módulo que no está instalado, contesta que ese módulo no está y no se rompe
  (`dcasa_brian/models/herramientas_bodega_nomina.py`).
- **Quitar una herramienta** = sacarla de `ODOO_MODULES` (`docker/entrypoint.sh`), del `Makefile` y de las pruebas, en la
  rama, con el CI verde. Conviene hacerlo **antes de instalar producción**: en una base nueva simplemente no se instala.
  Quitarla de una base con datos es otro trabajo, más delicado.

## Cimientos: se quedan

`dcasa_base` (empresa, ITBMS, roles) · `dcasa_invoice` (factura y cotización) · `dcasa_socios` (el programa está
apagado, pero muchos dependen de él) · `dcasa_contactos` (una persona, una ficha) · `website_dcasa` (la tienda) ·
`dcasa_catalogo` · `dcasa_interfaz` (el Inicio y el panel) · `dcasa_contabilidad` · `dcasa_brian` (el asistente del
panel y el MCP; varios dependen de él) · `dcasa_seguridad` · `dcasa_sesiones` · `dcasa_adjuntos_r2` (fotos y PDF en R2;
el contenedor no tiene disco) · `dcasa_tienda_borde` (la caché de la tienda).

`dcasa_fe_pa` (factura electrónica) ya **no se instala**.

## Se pueden quitar

| ¿Se queda? | Herramienta | Qué hace | Gasta | Si la quitas |
|---|---|---|---|---|
| [ ] | Consolidación (`dcasa_consolidacion`) | Estados financieros de varias empresas en uno | Memoria | Nada más. Baby Caleb es una sola empresa |
| [ ] | Migración (`dcasa_migracion`) | Carga única desde el sistema viejo **de D'CASA** | Memoria | Nada más |
| [ ] | Nómina (`dcasa_nomina`) | Planilla de Panamá, décimo, vacaciones, liquidación, adelantos y préstamos | Memoria, 1 tarea | Empleados de Odoo se queda (lo pide Contactos). Hay que quitar también Comisión del sitio |
| [ ] | Equipo (`dcasa_equipo`) | Ícono y quién ve el menú Empleados | Memoria (muy poca) | El menú Empleados queda como lo trae Odoo |
| [ ] | Existencias (`dcasa_existencias`) | Mermas, daños, muestras y regalos; bitácora de bodega; alertas diarias por Telegram | Memoria, 1 tarea | Nada más |
| [ ] | Guía (`dcasa_guia`) | «¿Qué necesitas hacer hoy?»: atajos en palabras sencillas | Memoria (muy poca) | Nada más |
| [ ] | Mi cuenta (`dcasa_mi_cuenta`) | El panel del cliente en `/mi-cuenta` | Memoria | Los clientes se quedan sin panel propio |
| [ ] | Brian de la tienda (`dcasa_brian_tienda`) | El chat con IA en la tienda web, en lugar del botón de WhatsApp | Memoria, 1 tarea, **IA** (tope de fábrica 30 USD al mes) | Vuelve el botón de WhatsApp |
| [ ] | Busca con una foto (`dcasa_buscar_foto`) | Buscar productos con la cámara en la tienda | Memoria, 1 tarea, **IA** (tope 5 USD al mes) | Nada más |
| [ ] | Catálogo para anuncios (`dcasa_meta_catalogo`) | El catálogo por enlace para los anuncios de Facebook e Instagram | Memoria | Nada más (viene apagado) |
| [ ] | Píxel de Meta (`dcasa_meta_eventos`) | Píxel con consentimiento y ventas pagadas a Meta | Memoria, 2 tareas | Nada más (viene apagado) |
| [ ] | Camila (`dcasa_camila`) | Campañas de correo cada 15 días; una persona las aprueba | Memoria, 2 tareas, **IA** | Nada más (sin clave de Resend no envía) |
| [ ] | Sofía (`dcasa_sofia`) | Revisa el CRM cada mañana y propone; una persona aprueba | Memoria, 1 tarea, **IA** | Hay que quitar también Camila |
| [ ] | Marketing (`dcasa_marketing`) | Fotos en grande y la app Marketing (stock por categoría, más vendidos, quietos, fotos que faltan) | Memoria | Hay que quitar también Camila |
| [ ] | Códigos de barras y Bodega (`dcasa_barras`) | Escáner, etiquetas y el panel de Bodega para despachar | Memoria | Hay que quitar también Marketing y Camila |
| [ ] | Correo a clientes (`dcasa_correo`) | Factura, abono y bienvenida por correo (Resend) | Memoria, 2 tareas | Hay que quitar también Camila |
| [ ] | Abonos (`dcasa_abonos`) | La hoja «Condiciones de abono» | Memoria, 1 tarea | Hay que quitar también Correo y Camila |
| [ ] | Juan y Conversaciones (`dcasa_conversaciones`) | La bandeja de WhatsApp, el reparto, el CRM automático y la conexión con Juan | Memoria, **11 tareas**, **IA** (tope de fábrica de Juan 30 USD al mes) | Hay que quitar también Sofía, Camila, Correo, Brian de la tienda, Busca con una foto y Comisión del sitio. El Worker `sistemabk-chatbot` deja de tener a quién preguntar |
| [ ] | Envíos (`dcasa_envios`) | La calculadora de envíos, los lugares y la tarifa | Memoria | Hay que quitar también Juan y Conversaciones |
| [ ] | Tilopay (`dcasa_pago_tilopay`, de D'CASA el 2026-11-24) | Cobrar con tarjeta en la página segura de Tilopay ([TILOPAY.md](TILOPAY.md)) | Memoria, 1 tarea | Nada más (viene apagado: sin claves en Cloudflare no aparece) |
| [ ] | Yappy directo (`dcasa_pago_yappy`, de D'CASA el 2026-11-24) | El Botón de Pago de Yappy Comercial en la tienda ([YAPPY.md](YAPPY.md)) | Memoria, 1 tarea | Sigue el «Yappy» de siempre, el que se confirma a mano (viene apagado) |
| [ ] | Comisión del sitio (`dcasa_comision_web`, de D'CASA el 2026-11-24) | Mide las ventas por internet como una sucursal y calcula, libra y liquida su comisión ([COMISION_WEB.md](COMISION_WEB.md)); sin porcentaje no paga nada | Memoria, 1 tarea | Nada más |

## Cuánta memoria gasta cada función (medido el 2026-11-19)

**Cómo se midió.** En una copia local, sin datos reales: 6 productos, sin fotos y un solo usuario. Se instaló todo paso a
paso, en el orden de las dependencias, en una sola base:
- Primero, 12 piezas de Odoo.
- Después, las 32 propias.

Tras cada paso, un proceso nuevo cargó Odoo y se anotó su memoria (RSS). Se midió dos veces, en paralelo, y se tomó el
promedio. La diferencia con el paso anterior es lo que suma esa función **por estar instalada**. El ruido es de unos
0,3 MB. PostgreSQL no está incluido: tiene su propia memoria, fijada por `docker/pg.sh` (`shared_buffers` 128 MB).

**Odoo pelado** (Python y el corazón de Odoo) ocupa 109 MB. **Con todo instalado** ocupa 171 MB.

| # | Función | Suma | ¿Se puede quitar? |
|---|---|---|---|
| 1 | Contabilidad de Odoo y lo de Panamá | 13,3 MB | No (cimiento) |
| 2 | Conversaciones de Odoo: chat, **llamadas, videollamadas**, avisos en vivo y OdooBot | 7,5 MB | No: todo depende de ella |
| 3 | Inventario y entregas de Odoo | 5,8 MB | No (cimiento) |
| 4 | Motor del sitio web | 3,8 MB | No (cimiento) |
| 5 | Interfaz: Inicio y panel (`dcasa_interfaz`) | 2,9 MB | No (cimiento) |
| 6 | Juan y Conversaciones (`dcasa_conversaciones`) | 2,7 MB | Sí, arrastrando a otras 5 |
| 7 | Empleados de Odoo | 2,7 MB | No: la pide Contactos |
| 8 | CRM de Odoo | 2,4 MB | No: la pide la base |
| 9 | Ventas y cotizaciones de Odoo | 2,1 MB | No (cimiento) |
| 10 | Brian (`dcasa_brian`) | 2,1 MB | No (cimiento) |
| 11 | Tienda en línea de Odoo: carrito, pagos y registro | 2,1 MB | No (cimiento) |
| 12 | Compras de Odoo | 1,7 MB | No: la pide la base |
| 13 | Socios (`dcasa_socios`) | 1,6 MB | No (cimiento) |
| 14 | Camila | 1,3 MB | Sí |
| 15 | La tienda propia (`website_dcasa`) | 1,0 MB | No (cimiento) |
| 16 | Envíos | 0,9 MB | Sí, junto con Juan |
| 17 | Correo a clientes | 0,9 MB | Sí |
| 18 | Contabilidad propia (`dcasa_contabilidad`) | 0,9 MB | No (cimiento) |
| 19 | Base: empresa, ITBMS y roles (`dcasa_base`) | 0,8 MB | No (cimiento) |
| 20 | Nómina | 0,6 MB | Sí |
| 21 | Migración | 0,6 MB | Sí |
| 22 | Sofía | 0,5 MB | Sí |
| — | Menos de 0,5 MB cada una, dentro del ruido: Consolidación, Contactos propio, Abonos, Códigos de barras, Existencias, Brian de la tienda, Factura con la marca, Sesiones, Catálogo, Catálogo para anuncios, Seguridad propia, Marketing, Mi cuenta, Píxel de Meta, Contactos de Odoo, Busca con una foto, Seguridad de Odoo, Tienda en el borde, Adjuntos en R2, Equipo y Guía | ≤ 0,4 MB | Varias sí |

**Las 19 que se pueden quitar, juntas, suman unos 10 MB** de los 171.

### En uso

Se arrancó el servidor como en producción: un solo proceso, sin tareas programadas para que no metan ruido. Luego se
abrieron la tienda y el panel (ventas, productos, contactos, facturas, entregas y CRM) y se lanzaron 40 visitas a la vez a
la tienda. Se comparó con una copia que tiene **solo los cimientos** (las 13).

| Momento | Con todo | Solo cimientos |
|---|---|---|
| Recién arrancado | 187 MB | 177 MB |
| Un día normal, tras usar tienda y panel | **249 MB** (pico 259) | **214 MB** (pico 246) |
| La primera vez que se abre el panel tras una versión nueva, cuando arma sus archivos de pantalla | **450 MB** (pico 455) | **362 MB** (pico 388) |

**Conclusión.** Quitar todo lo que se puede quitar ahorra unos **35 MB** en un día normal y unos **90 MB** en el pico
tras una versión nueva. Las llamadas y videollamadas son parte de la función n.º 2 y no se pueden separar.

Esta medición no decide sola el tamaño de la caja. Con datos reales y varias personas a la vez se gasta más, y
PostgreSQL va aparte. La decisión de caja sale de la gráfica de memoria y procesador de staging en el panel de
Cloudflare.
