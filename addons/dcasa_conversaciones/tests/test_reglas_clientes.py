"""Las reglas de Socios para el cliente: ninguna cifra fuera de puntos.json, y lo ``null`` no se rellena a ojo."""
import copy
import re

from odoo.addons.dcasa_socios.models import reglas as R
from odoo.addons.dcasa_socios.tests.common import reglas_de_prueba
from odoo.tests import BaseCase, tagged

from ..models.reglas_clientes import redactar


def numeros_del_json(valor, acumulado=None):
    """Todos los números que existen en puntos.json (en cualquier nivel), como texto, más sus formas de lectura."""
    acumulado = set() if acumulado is None else acumulado
    if isinstance(valor, dict):
        for clave, sub in valor.items():
            if not clave.startswith('$'):
                numeros_del_json(sub, acumulado)
    elif isinstance(valor, (int, float)) and not isinstance(valor, bool):
        acumulado.add(str(valor))
        acumulado.add(R.como_puntos(int(valor)))                 # 5,000
        acumulado.add(f'{valor / 100:,.2f}')                      # 2000 centavos → 20.00
        acumulado.add(f'{int(valor) // 100}')                     # 2000 → 20
    return acumulado


@tagged('post_install', '-at_install')
class TestReglasParaClientes(BaseCase):

    def setUp(self):
        super().setUp()
        # Cifras de PRUEBA encima de puntos.json (que de fábrica está todo en PENDIENTE: ver la última prueba).
        self.reglas = reglas_de_prueba()

    def test_explica_el_programa_con_las_cifras_reales(self):
        texto = ' '.join(redactar(self.reglas, 'https://dcasapty.com')['resumen'])
        self.assertIn('1 punto por cada dólar', texto)
        self.assertIn('ITBMS incluido', texto)
        self.assertIn('$20.00', texto)                  # compra mínima
        self.assertIn('500 puntos', texto)              # padrino / canje mínimo / cumpleaños
        self.assertIn('250 puntos', texto)              # invitado
        self.assertIn('72 horas', texto)
        self.assertIn('100 puntos valen $1', texto)
        self.assertIn('hasta 50 personas', texto)
        self.assertIn('5,000 puntos al mes', texto)
        self.assertIn('no tienen fecha de vencimiento', texto)

    def test_ninguna_cifra_sale_de_la_cabeza(self):
        """Cada número de las frases existe en puntos.json (o es el «$1» de la equivalencia)."""
        permitidos = numeros_del_json(self.reglas) | {'1'}
        for linea in redactar(self.reglas)['resumen']:
            for numero in re.findall(r'\d[\d,]*(?:\.\d+)?', linea):
                with self.subTest(linea=linea, numero=numero):
                    self.assertIn(numero, permitidos)

    def test_las_cifras_estructuradas_son_las_del_json(self):
        cifras = redactar(self.reglas)['cifras']
        self.assertEqual(cifras['puntos_por_dolar'], self.reglas['acumulacion']['puntosPorDolar'])
        self.assertEqual(cifras['puntos_al_padrino'], self.reglas['referido']['puntosAlPadrino'])
        self.assertEqual(cifras['puntos_al_invitado'], self.reglas['referido']['puntosAlAhijado'])
        self.assertEqual(cifras['saldo_minimo_para_canjear'], self.reglas['canje']['saldoMinimoParaCanjear'])
        self.assertEqual(cifras['vigencia_del_codigo_horas'], self.reglas['canje']['vigenciaDelCodigoHoras'])
        self.assertEqual(cifras['puntos_de_cumpleanos'], self.reglas['cumpleanos']['puntos'])
        self.assertEqual(cifras['puntos_de_bienvenida'], 0)

    def test_si_el_json_cambia_el_texto_cambia(self):
        cambiadas = copy.deepcopy(self.reglas)
        cambiadas['referido']['puntosAlPadrino'] = 700
        cambiadas['acumulacion']['puntosPorDolar'] = 2
        texto = ' '.join(redactar(cambiadas)['resumen'])
        self.assertIn('700 puntos', texto)
        self.assertIn('2 puntos por cada dólar', texto)

    def test_un_valor_null_no_se_rellena_a_ojo(self):
        pendientes = copy.deepcopy(self.reglas)
        pendientes['referido']['puntosAlPadrino'] = None
        pendientes['cumpleanos']['puntos'] = None
        pendientes['canje']['saldoMinimoParaCanjear'] = 'PENDIENTE DE CONFIRMAR'
        resultado = redactar(pendientes)
        self.assertTrue(resultado['disponible'], 'con la acumulación decidida, el programa existe')
        texto = ' '.join(resultado['resumen'])
        self.assertIn('por cada dólar', texto)
        self.assertNotIn('tú ganas', texto)
        self.assertNotIn('cumpleaños', texto)
        self.assertNotIn('Para canjear necesitas', texto)
        self.assertNotIn('PENDIENTE', texto)
        self.assertEqual(sorted(resultado['pendientes']), [
            'canje.saldoMinimoParaCanjear', 'cumpleanos.puntos', 'referido.puntosAlPadrino'])
        for clave in ('puntos_al_padrino', 'saldo_minimo_para_canjear', 'puntos_de_cumpleanos'):
            self.assertNotIn(clave, resultado['cifras'])

    def test_sin_puntos_por_dolar_el_programa_no_esta_disponible(self):
        pendientes = copy.deepcopy(self.reglas)
        pendientes['acumulacion']['puntosPorDolar'] = None
        resultado = redactar(pendientes, 'https://tienda.example.com')
        self.assertFalse(resultado['disponible'])
        self.assertEqual(resultado['resumen'], [R.NO_DISPONIBLE])
        self.assertEqual((resultado['cifras'], resultado['enlaces']), ({}, {}))
        self.assertEqual(resultado['pendientes'], ['acumulacion.puntosPorDolar'])

    def test_con_el_puntos_json_de_fabrica_dice_que_no_esta_disponible_y_no_da_cifras(self):
        """Todo en PENDIENTE (decisión del dueño, 2026-11-18): el asistente dice que el programa todavía no está
        disponible, no da ninguna cifra y sabe que no debe prometer puntos, premios ni cumpleaños."""
        resultado = redactar(R.cargar_reglas(), 'https://tienda.example.com')
        self.assertFalse(resultado['disponible'])
        self.assertEqual(resultado['resumen'], [R.NO_DISPONIBLE])
        self.assertEqual(resultado['cifras'], {})
        self.assertEqual(resultado['enlaces'], {}, 'no manda a registrarse a un programa sin cifras')
        self.assertIn('acumulacion.puntosPorDolar', resultado['pendientes'])
        self.assertIn('referido.puntosAlPadrino', resultado['pendientes'])
        for texto in (*resultado['resumen'], resultado['aviso']):
            self.assertFalse(re.findall(r'\d', texto), texto)
        self.assertIn('no prometas puntos', resultado['aviso'])

    def test_el_json_real_no_tiene_pendientes_de_cifras_que_se_expliquen(self):
        # El tope por compra («PENDIENTE DE CONFIRMAR POR MARCIAL») es un comentario interno, no una cifra pendiente.
        self.assertEqual(redactar(self.reglas)['pendientes'], [])

    def test_vencimiento_con_cifra_se_dice(self):
        con_vencimiento = copy.deepcopy(self.reglas)
        con_vencimiento['vencimiento']['meses'] = 12
        texto = ' '.join(redactar(con_vencimiento)['resumen'])
        self.assertIn('vencen a los 12 meses', texto)

    def test_nunca_promete_puntos_sin_factura(self):
        resultado = redactar(self.reglas)
        self.assertIn('factura queda pagada', ' '.join(resultado['resumen']))
        self.assertIn('nunca se prometen por una compra sin facturar', resultado['aviso'])

    def test_enlaces(self):
        enlaces = redactar(self.reglas, 'https://dcasapty.com/')['enlaces']
        self.assertEqual(enlaces, {'registro': 'https://dcasapty.com/socios',
                                   'premios': 'https://dcasapty.com/socios/premios'})
