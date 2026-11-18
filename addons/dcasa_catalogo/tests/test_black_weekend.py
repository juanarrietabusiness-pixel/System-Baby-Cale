import re

from odoo.addons.dcasa_catalogo.catalogo import BLACK_WEEKEND, atributo_con_valores, marcar_black_weekend
from odoo.tests import HttpCase, TransactionCase, tagged

# La selección de prueba: (código, de dónde salió). La de verdad (catalogo.BLACK_WEEKEND) la decide el dueño.
SELECCION = [('ZZBW-SIMPLE', 'prueba'), ('ZZBW-MED', 'prueba: la variante destacada'), ('ZZBW-NO-ESTA', 'prueba')]


class _ProductosDePrueba:

    @classmethod
    def crear_productos(cls, env):
        """Un producto simple y uno con tallas (la variante «MED» es la destacada), publicados y con su precio."""
        atributo, valores = atributo_con_valores(env, 'Talla de Black Weekend', ['CH', 'MED'])
        Plantilla = env['product.template']
        simple = Plantilla.create({'name': 'Producto BW simple', 'default_code': 'ZZBW-SIMPLE', 'list_price': 41.5,
                                   'is_published': True, 'type': 'consu', 'is_storable': True})
        tallas = Plantilla.create({
            'name': 'Producto BW con tallas', 'list_price': 30.0, 'is_published': True, 'type': 'consu',
            'is_storable': True, 'attribute_line_ids': [(0, 0, {
                'attribute_id': atributo.id, 'value_ids': [(6, 0, [valores['CH'].id, valores['MED'].id])]})],
        })
        for variante in tallas.product_variant_ids:
            variante.default_code = f"ZZBW-{variante.product_template_attribute_value_ids.name}"
        return simple, tallas


@tagged('post_install', '-at_install')
class TestBlackWeekendCatalogo(_ProductosDePrueba, TransactionCase):
    """La carga marca por su código los productos de la campaña, en su orden y sin tocar precios."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.simple, cls.tallas = cls.crear_productos(cls.env)

    def variante(self, codigo):
        return self.env['product.product'].with_context(active_test=False).search([('default_code', '=', codigo)])

    def test_la_seleccion_de_dcasa_ya_no_esta(self):
        self.assertEqual(BLACK_WEEKEND, [])
        self.assertEqual(marcar_black_weekend(self.env), 0)
        self.assertFalse(self.env['product.template'].search_count([('dcasa_black_weekend', '=', True)]))

    def test_marcados_en_su_orden_y_el_que_falta_se_anota(self):
        with self.assertLogs('odoo.addons.dcasa_catalogo.catalogo', 'WARNING') as registro:
            self.assertEqual(marcar_black_weekend(self.env, SELECCION), 2)
        self.assertIn('ZZBW-NO-ESTA no está en el catálogo', '\n'.join(registro.output))
        self.assertEqual((self.simple.dcasa_black_weekend, self.simple.dcasa_bw_orden), (True, 10))
        self.assertEqual((self.tallas.dcasa_black_weekend, self.tallas.dcasa_bw_orden), (True, 20))

    def test_la_variante_destacada_solo_si_tiene_varias(self):
        with self.assertLogs('odoo.addons.dcasa_catalogo.catalogo', 'WARNING'):
            marcar_black_weekend(self.env, SELECCION)
        self.assertEqual(self.tallas.dcasa_bw_variante_id, self.variante('ZZBW-MED'))
        self.assertFalse(self.simple.dcasa_bw_variante_id, 'Sin variantes no hace falta destacada')

    def test_idempotente_y_sin_tocar_precios(self):
        seleccion = SELECCION[:2]
        marcar_black_weekend(self.env, seleccion)
        marcados = self.simple | self.tallas
        self.env.flush_all()
        antes = {p.id: (p.list_price, p.write_date, p.dcasa_bw_orden) for p in marcados}
        self.assertEqual(marcar_black_weekend(self.env, seleccion), 2)
        self.assertEqual(self.env['product.template'].search([('dcasa_black_weekend', '=', True)]), marcados)
        self.assertEqual({p.id: (p.list_price, p.write_date, p.dcasa_bw_orden) for p in marcados}, antes,
                         'La segunda vez no escribe nada')
        self.assertEqual((self.simple.list_price, self.tallas.list_price), (41.5, 30.0))


@tagged('post_install', '-at_install')
class TestBlackWeekendWeb(_ProductosDePrueba, HttpCase):
    """/black-weekend con lo que marcó la carga: el precio del catálogo y el código público en WhatsApp."""

    def setUp(self):
        super().setUp()
        self.simple, self.tallas = self.crear_productos(self.env)
        marcar_black_weekend(self.env, SELECCION[:2])
        self.env['ir.config_parameter'].sudo().set_param('dcasa_black_weekend.activo', '1')

    def test_pagina_con_el_precio_del_catalogo(self):
        html = self.url_open('/black-weekend').text
        self.assertRegex(html, r'41[.,]50')
        self.assertIn(f'Código {self.simple.dcasa_codigo_publico}<', html, 'La tarjeta lleva el código público')
        self.assertIn(f'c%C3%B3digo%20{self.tallas.dcasa_codigo_publico}', html)
        for referencia in ('ZZBW-SIMPLE', 'ZZBW-MED'):
            self.assertNotIn(f'c%C3%B3digo%20{referencia}', html, 'la referencia interna no sale')
            self.assertNotIn(f'Código {referencia}<', html, 'la referencia interna no sale')
        visible = re.sub(r'<script.*?</script>|<style.*?</style>', '', html, flags=re.S).lower()
        for palabra in ('tafi', 'tiempo limitado', 'remate', 'cuotas'):
            self.assertNotIn(palabra, visible)

    def test_cambio_de_precio_se_ve(self):
        self.simple.list_price = 39.25
        html = self.url_open('/black-weekend').text
        self.assertRegex(html, r'39[.,]25')
        self.assertNotRegex(html, r'41[.,]50')
