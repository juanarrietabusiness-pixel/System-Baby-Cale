# Marca Baby Caleb en el sistema: el contrato de diseño

Pedido del dueño el **2026-11-19**: llevar el branding de la web de Baby Caleb **tal cual** a todo el sistema nuevo. Eso
incluye la web pública (portada, tienda, ficha, carrito, cuenta y Socios), el panel administrativo y los documentos y
correos. Lo que había era de D'CASA y «parece una mueblería».

En esta copia, este archivo **reemplaza** las «Reglas de marca» de D'CASA de `CLAUDE.md`: el azul y el amarillo, Anton y
Oswald y «el amarillo nunca toca el blanco».

**Las fuentes** son el repositorio `abrinay1997-stack/Baby-caleb`. Ninguno de esos valores se inventa:

- `brand.json`, con los colores y el contraste medido.
- `src/styles/themes/babycaleb.css` y `src/styles/tokens.css`, para la web.
- `sistema/panel/src/estilos.css`, para el panel propio de Baby Caleb.
- `content.json`, para los textos.

La web en vivo, para comparar, es `https://babycaleb.com`.

## Colores

| Nombre | Valor | Para qué |
|---|---|---|
| `bg` | `#F9F6ED` | Fondo de página (crema) |
| `surface` | `#F2EFE5` | Tarjetas, bandas suaves y campos sobre crema |
| `fg` | `#1B3246` | Texto, titulares, íconos y **aro de foco** (navy) |
| `muted` | `rgba(27, 50, 70, 0.7)` (sólido sobre `bg` ≈ `#5E6D78`) | Texto secundario: 4.95 sobre `bg`, 4.80 sobre `surface` |
| `line` | `rgba(27, 50, 70, 0.12)` | Filos que **separan**: el canto de una tarjeta, la raya entre filas |
| `control` | `rgba(27, 50, 70, 0.55)` | El borde de lo que se **toca o se llena**: campos y botones de contorno (3.26:1) |
| `accent` | `#EE924A` | **Relleno** naranja: el botón principal, la burbuja del chat, puntos y barras. **Nunca texto ni borde** (2.20) |
| `accent-fg` | `#1B3246` | Lo que se escribe **encima** del naranja: navy, 5.56. **Nunca blanco ni crema** |
| `accent-strong` | `#985D2F` | Texto en naranja sobre `bg` o `surface` (4.90 / 4.60): antetítulos, enlaces de acción y precios destacados |
| `accent-edge` | `#C3783D` | Bordes e íconos naranja (3.20 / 3.01) |
| `sage` | `#91C9A2` | **Relleno** verde: bandas grandes e insignias. **Nunca texto ni borde** (1.75) |
| `sage-strong` | `#53735C` | Texto verde sobre `bg` o `surface` (4.92 / 4.62) |
| `sage-edge` | `#6A9376` | Bordes e íconos verdes (3.22 / 3.03) |

- **Sobre el verde (`sage`)** el texto va en navy (6.96).
- **Sobre el naranja** el texto va en navy (5.56).
- **El blanco puro** casi no se usa: las superficies son crema. Un campo puede ir en blanco si su borde es `control`.
- **Los estados** (bien, falta, error) pueden quedarse con sus colores, pero hay que medirlos sobre el crema (AA: 4.5
  para texto y 3 para bordes e íconos).
- **No hay degradados**, salvo el resplandor suave del botón principal y los «blobs» de la portada de la web de Baby
  Caleb.

## Letra

- **Montserrat** para todo: titulares, cuerpo, botones y menú.
- **Archivos:**
  - Web y panel: `website_dcasa/static/src/fonts/montserrat-latin-var.woff2` y
    `dcasa_base/static/src/fonts/montserrat-latin-var.woff2` (variable, de 100 a 900).
  - PDF (wkhtmltopdf no lee woff2): `dcasa_base/static/src/fonts/Montserrat-{Regular,Medium,SemiBold,Bold}.ttf`, fijos.
  - Licencia: `OFL-Montserrat.txt`.
- **Titulares:** 700, `letter-spacing: -0.03em` y `line-height: 1.15`. **Nunca en caja alta**: se escriben como frase
  («Cuidado hipoalergénico para la piel de tu bebé»).
- **Antetítulos:** 12 px, 700, caja alta y `letter-spacing: .14em`, en `accent-strong` o `sage-strong` (por ejemplo,
  «03 / EXPERIENCIAS REALES»).
- **Cuerpo:** de 16 a 18 px, con `line-height: 1.6`. **El piso es 12 px**: nada más chico.
- **Los campos van a 16 px**, para que el iPhone no haga zoom.

## Formas

- **Botón principal:** pastilla (`border-radius: 999px`), fondo `accent`, letra navy en 700 y relleno generoso. Puede
  llevar un resplandor suave del mismo naranja.
- **Botón secundario:** pastilla de contorno (`accent-edge` o `control`), letra `accent-strong` o navy y fondo
  transparente.
- **Tarjetas:** fondo `surface`, borde `line`, radio de 16 px (24 px las grandes) y sombra casi nada:
  `0 4px 20px -2px rgba(27, 50, 70, 0.05)`.
- **Campos:** radio de 14 px, borde `control` y altura táctil de 44 px.
- **Píldoras e insignias:** fondo `sage` claro o `surface`, letra navy o `sage-strong`, en caja alta de 12 px y 700.
- **Íconos:** de línea fina (como lucide), en `sage-strong` o navy, dentro de un círculo crema.
- **Aro de foco:** `2px solid #1B3246` con `outline-offset: 2px`. Se ve sobre todos los fondos.

## La web pública

- **Cabecera:** una pastilla flotante de vidrio crema, con la marca «Baby Caleb» escrita en Montserrat 700 navy, los
  enlaces en navy 500 y el carrito. **No hay barra de anuncios encima** ni foto oscura detrás.
- **Portada**, en el orden de `Baby-caleb/src/pages/Home.tsx`:
  1. Hero en crema, con el titular navy, el antetítulo en píldora y la foto `hero-bebe` con esquinas redondeadas.
  2. Los cuatro sellos (`trust`): Hipoalergénico, Sin cloro, Biodegradable y Piel sensible.
  3. La banda verde de educación («¿Sabías que…?»).
  4. Los productos: el carrusel de la tienda, con los datos reales de Odoo.
  5. Lo que dicen las mamás (`testimonials` de `content.json`, **copiados tal cual**: son de la dueña).
  6. Cobertura.
  7. La banda verde final («Dale a tu bebé el cuidado que su piel merece.» y «Ver el catálogo»).
  8. Preguntas frecuentes.
- **Pie:** crema, con la marca, el lema, los enlaces y el contacto, igual que el de su web.
- **Nada de muebles:** ni fotos, ni categorías por espacio, ni «Para dormir mejor».

## El panel

Se tiene que parecer al panel propio de Baby Caleb (`sistema/panel/src/estilos.css`): fondo crema, letra navy, el botón
principal en naranja con letra navy, el verde para lo secundario, radio de 14 px y Montserrat. **Ajustes › Marca del
panel sigue funcionando**: cada empresa puede cambiar su logo y sus colores.

## Documentos y correos

Factura, cotización, abono, reportes y correos: Montserrat, navy para el texto y el logo de Baby Caleb. El naranja solo
en filetes y rellenos, nunca en texto. Nada de azul ni de amarillo de D'CASA.

- **En los PDF el papel queda blanco**, porque se imprime. El crema va solo en bloques.
- **La letra de los PDF es siempre navy.** Lo secundario va en navy al 70 % ya mezclado: `#5F707E`, 5.12 sobre blanco.
- **Los filetes** (bajo el logo, cabeceras y total) van en `#EE924A` o en `#91C9A2`, con letra navy encima.
- **En los correos y en el panel**, los enlaces y los precios destacados van en `accent-strong` (`#985D2F`).
- **Los correos** llevan estilos en línea, Montserrat con respaldo Arial/Helvetica y un solo botón en pastilla naranja
  con letra navy, que es texto y se lee sin imágenes.

## De D'CASA a Baby Caleb, por papel

| En D'CASA | Hacía de | En Baby Caleb |
|---|---|---|
| Azul `#1340B1` | Texto, titulares y enlaces | `fg` `#1B3246` (los enlaces de acción, en `accent-strong`) |
| Azul `#1340B1` | Fondo de botón con letra blanca | `accent` `#EE924A` con letra navy |
| Azul `#1340B1` | Bordes y foco | `control`, `accent-edge` o el aro navy |
| Amarillo `#FED00F` | Botón o banda | `accent` (relleno) con letra navy |
| Navy `#0E2A6B` | Bandas oscuras y pie | Banda `sage` con letra navy, o crema |
| Hueso `#F6F5F2` y blanco | Fondos | `surface` y `bg` |
| Tinta `#1B2233` y gris `#4A5163` | Texto | `fg` y `muted` |
| Anton y Oswald en caja alta | Titulares, menú y botones | Montserrat 700, como frase; botones en 700 |
| Inter | Cuerpo | Montserrat 400 o 500 |

## Lo que no cambia

- Los nombres técnicos: módulos `dcasa_*` y clases `o_dcasa_*`.
- La lógica, los textos legales (políticas: palabra por palabra) y las rutas.
- Las reglas de `CLAUDE.md` que no son de marca: no inventar contenido, todo cambio lleva prueba y `vendor/odoo` no se
  toca.
