# fuentes: originales ya procesados (Baby Caleb)

Aquí `scripts/procesar_up_media.py` guarda los originales que ya entraron al catálogo desde el buzón `up media/`, en
una carpeta por carga, con su LEEME histórico. Hoy está vacía: el catálogo de Baby Caleb se escribe a mano
(`addons/dcasa_catalogo/data/catalogo.json`) y las fotos se ponen en Odoo. Los originales de D'CASA ya no están en el
repositorio (siguen en su historial de git y no son de este negocio).

No se edita ni se borra a mano. Si algún día pesa demasiado, `scripts/archivar_fuentes.sh` pasa los originales a R2
(docs/OPERACION.md).
