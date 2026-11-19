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
| [ ] | Nómina (`dcasa_nomina`) | Planilla de Panamá, décimo, vacaciones, liquidación, adelantos y préstamos | Memoria, 1 tarea | Empleados de Odoo se queda (lo pide Contactos) |
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
| [ ] | Juan y Conversaciones (`dcasa_conversaciones`) | La bandeja de WhatsApp, el reparto, el CRM automático y la conexión con Juan | Memoria, **11 tareas**, **IA** (tope de fábrica de Juan 30 USD al mes) | Hay que quitar también Sofía, Camila, Correo, Brian de la tienda y Busca con una foto. El Worker `sistemabk-chatbot` deja de tener a quién preguntar |
| [ ] | Envíos (`dcasa_envios`) | La calculadora de envíos, los lugares y la tarifa | Memoria | Hay que quitar también Juan y Conversaciones |
