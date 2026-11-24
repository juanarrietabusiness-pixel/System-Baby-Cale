"""El asistente saluda como Baby Caleb Panamá (decisión del dueño, 2026-11-24), con el saludo de su CRM.

El nombre público y la bienvenida viven en el registro de Ajustes de Juan: cambiar el valor por defecto no toca una base
que ya existe. Solo se reemplazan si todavía dicen lo de D'CASA: lo que alguien ya editó en Ajustes no se pisa.
"""
NOMBRE_ANTERIOR = "el equipo de D'CASA"
NOMBRE_NUEVO = 'Baby Caleb Panamá'
BIENVENIDA_ANTERIOR = "Hola, soy Juan de D'CASA."
BIENVENIDA_NUEVA = 'Buenas, un gusto atenderle. Somos Baby Caleb Panamá 👼🏻'


def migrate(cr, version):
    cr.execute('UPDATE dcasa_juan_ajustes SET nombre_publico = %s WHERE nombre_publico = %s',
               [NOMBRE_NUEVO, NOMBRE_ANTERIOR])
    cr.execute('UPDATE dcasa_juan_ajustes SET mensaje_bienvenida = %s WHERE mensaje_bienvenida = %s',
               [BIENVENIDA_NUEVA, BIENVENIDA_ANTERIOR])
