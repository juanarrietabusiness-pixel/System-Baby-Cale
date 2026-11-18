# up media: buzón de Baby Caleb

Aquí se suben archivos desde GitHub (*Add file* → *Upload files* → *Commit changes*), sin terminal. GitHub los revisa
solo (`.github/workflows/up-media.yml`) y deja lo que pasó con cada uno en `RESUMEN.md`, en esta misma carpeta.

- **El catálogo se escribe a mano** con la lista del dueño (`addons/dcasa_catalogo/data/catalogo.json`; ver
  `docs/CATALOGO.md`). Este buzón no lo cambia.
- **Las fotos de los productos se ponen a mano en Odoo** (Inventario › Productos › la foto del producto). Si se suben
  aquí, quedan guardadas y anotadas como pendientes en `RESUMEN.md` hasta que alguien las ponga.
- Un Excel nuevo queda pendiente hasta que el programador registre cómo se lee (`scripts/importar_catalogo.py`).
- Nada se borra: lo que ya se procesó se va a `fuentes/<carpeta>/`; lo que no es de ningún producto, a
  `descartado/<fecha>/` (con el motivo).

Esta carpeta no se borra ni se renombra aunque esté vacía: es el buzón de entrada.
