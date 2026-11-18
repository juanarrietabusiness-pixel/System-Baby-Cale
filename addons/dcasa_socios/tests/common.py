import copy
import json
import os
from unittest.mock import patch

from odoo import fields
from odoo.tests import TransactionCase

from ..models import reglas as R

CARGAR_REGLAS = 'odoo.addons.dcasa_socios.models.reglas.cargar_reglas'
PIN_DE_PRUEBA = '482915'

# CIFRAS DE PRUEBA (2026-11-18). El puntos.json de fábrica de esta copia trae TODAS las cifras en null (PENDIENTE): con
# él no se acredita ni se canjea nada (eso lo prueban ``test_pendiente.py`` y las pruebas de fábrica de cada módulo).
# Para seguir comprobando cómo se comporta el programa CUANDO tiene cifras, las pruebas ponen estas encima de la
# fábrica con ``reglas_de_prueba()``. No son las cifras de ninguna empresa ni una propuesta: son las que ya usaban
# estas pruebas, para que sigan comprobando exactamente lo mismo (p. ej. «107 puntos por una factura de $107»).
SOCIOS_DE_PRUEBA = {
    'acumulacion': {'puntosPorDolar': 1, 'baseDeCalculo': 'total', 'itbmsPorcentaje': 7, 'redondeo': 'abajo',
                    'compraMinimaCentavos': 2000, 'puntosMaximosPorCompra': 50000},
    'bienvenida': {'puntos': 0},
    'referido': {'niveles': 1, 'vestaCon': 'primera-compra-verificada', 'puntosAlPadrino': 500,
                 'puntosAlAhijado': 250, 'topeDeAhijadosPorPadrino': 50, 'topeDePuntosPorPadrinoAlMes': 5000},
    'canje': {'vigenciaDelCodigoHoras': 72, 'saldoMinimoParaCanjear': 500, 'puntosPorDolar': 100},
    'vencimiento': {'meses': None},
    'cumpleanos': {'puntos': 500},
}

# El programa de vendedores COMPLETO de prueba (con escalera, freno, retención…): lo que leen las pruebas que antes
# usaban la sección «vendedores» de fábrica tal cual (la pantalla de Ajustes, la escalera, Brian).
VENDEDORES_COMPLETOS_DE_PRUEBA = {
    'programaActivo': True,
    'comision': {
        'puntosPorDolarNeto': 4, 'baseDeCalculo': 'neto', 'compraMinimaCentavos': 2000, 'pagaEn': 'cada-compra',
        'factorDeRecompra': 0.5, 'factorClienteExistente': 0.5,
        'escalones': [
            {'desdeVentasNetasCentavos': 300000, 'puntosPorDolarNeto': 5, 'topeAlMesPuntos': 30000},
            {'desdeVentasNetasCentavos': 900000, 'puntosPorDolarNeto': 6.5, 'topeAlMesPuntos': 50000},
            {'desdeVentasNetasCentavos': 1800000, 'puntosPorDolarNeto': 8, 'topeAlMesPuntos': 90000},
        ],
        'diasParaEscalon': 90,
    },
    'patrocinio': {'puntosPorDolarNetoDelDirecto': 0.8, 'soloClientesNuevos': True, 'topeDeDirectos': 3,
                   'ventasPropiasMinimasAlMes': 2, 'topeComoMultiploDeSuComisionDelMes': 1},
    'vinculacion': {'meses': 12, 'pagaPatrocinio': False},
    'retencion': {'dias': 30, 'primerasVentas': 5, 'diasPrimerasVentas': 60},
    'techos': {'totalPorVentaPorcentajeDelNeto': 8.75, 'pesoDelPuntoDeVendedor': 0.7,
               'margenBrutoSupuestoPorcentaje': 35, 'porVendedorAlMesPuntos': 20000,
               'patrocinioPorPatrocinadorAlMesPuntos': None, 'frenoGlobalPorcentajeDeLaVentaNeta': 3},
    'canje': {'puntosMinimosParaCanjear': 3000, 'vigenciaDelCodigoHoras': 72, 'canjesPorVendedorAlMes': 4,
              'externosHabilitado': False, 'efectivoHabilitado': False},
    'bloquearComprasDentroDeLaColmena': True,
}


def reglas_de_fabrica():
    """``puntos.json`` tal cual está en el repositorio (leído del archivo, aunque ``cargar_reglas`` esté parchado)."""
    with open(R.PUNTOS_JSON, encoding='utf-8') as archivo:
        return json.load(archivo)


def reglas_de_prueba():
    """Las reglas de fábrica con las cifras de PRUEBA encima (Socios y el programa de vendedores completo). Cada
    llamada devuelve una copia nueva, como ``cargar_reglas``."""
    reglas = reglas_de_fabrica()
    for seccion, valores in SOCIOS_DE_PRUEBA.items():
        reglas[seccion] = {**reglas[seccion], **copy.deepcopy(valores)}
    reglas['vendedores'] = copy.deepcopy(VENDEDORES_COMPLETOS_DE_PRUEBA)
    return reglas


def parche_de_reglas_de_prueba():
    """Un ``patch`` de ``cargar_reglas`` que devuelve ``reglas_de_prueba()`` (una copia nueva en cada llamada)."""
    return patch(CARGAR_REGLAS, side_effect=lambda *_args, **_kwargs: reglas_de_prueba())


# Los premios de descuento de PRUEBA (el catálogo de fábrica arranca vacío desde el 2026-11-18): $5, $10, $25, $50 y
# $100, a 100 puntos por dólar, como los que ya usaban estas pruebas.
PREMIOS_DE_PRUEBA = (5, 10, 25, 50, 100)


def premios_de_prueba(env):
    """``{dólares: premio}`` con los premios de descuento de prueba (se crean una vez por transacción de prueba)."""
    Premio = env['dcasa.premio'].sudo()
    premios = {}
    for orden, dolares in enumerate(PREMIOS_DE_PRUEBA, 1):
        nombre = f'${dolares} de descuento'
        premio = Premio.search([('name', '=', nombre), ('libre', '=', False)], limit=1)
        premios[dolares] = premio or Premio.create({
            'name': nombre, 'descripcion': 'Se aplica en tu próxima compra.', 'tipo': 'descuento',
            'puntos': dolares * 100, 'valor': dolares, 'costo': dolares, 'sequence': orden})
    return premios


def premio_de_prueba(env, dolares):
    return premios_de_prueba(env)[dolares]


class ConReglasDePrueba:
    """Mezcla para una clase de pruebas: mientras corre, ``cargar_reglas`` devuelve ``reglas_de_prueba()`` y el
    catálogo tiene los premios de prueba. ``reglas_con`` y ``activar_vendedores`` siguen cambiando cifras encima.
    Con ``CON_CIFRAS_DE_PRUEBA = False`` rige ``puntos.json`` tal cual (todo PENDIENTE) y el catálogo de fábrica."""

    CON_CIFRAS_DE_PRUEBA = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if cls.CON_CIFRAS_DE_PRUEBA:
            cls.startClassPatcher(parche_de_reglas_de_prueba())
            cls.premios = premios_de_prueba(cls.env)


# Las reglas de VENDEDORES para probar el código (no son las cifras reales: esas viven en puntos.json y las decide
# la dueña). Cada prueba las cambia en ``self.reglas['vendedores']``.
VENDEDORES_DE_PRUEBA = {
    'programaActivo': True,
    'comision': {'puntosPorDolarNeto': 4, 'baseDeCalculo': 'neto', 'compraMinimaCentavos': 2000,
                 'pagaEn': 'cada-compra', 'escalones': [], 'diasParaEscalon': 90},
    'vinculacion': {'meses': 0},
    'patrocinio': {'puntosPorDolarNetoDelDirecto': 0.4, 'topeDeDirectos': 3},
    'retencion': {'dias': 30},
    'techos': {'totalPorVentaPorcentajeDelNeto': 8, 'porVendedorAlMesPuntos': None,
               'patrocinioPorPatrocinadorAlMesPuntos': None},
    'canje': {'puntosMinimosParaCanjear': 500, 'vigenciaDelCodigoHoras': 72, 'canjesPorVendedorAlMes': None,
              'externosHabilitado': True},
    'bloquearComprasDentroDeLaColmena': True,
}


class SociosCommon(ConReglasDePrueba, TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env.ref('base.main_company')
        # El ITBMS de venta por defecto de la empresa: se suma al precio, como en la factura real.
        cls.itbms = cls.company.account_sale_tax_id
        cls.producto = cls.env['product.product'].create({
            'name': 'CAMA QUEEN GREY CON ESTANTES', 'type': 'consu', 'invoice_policy': 'order',
            'list_price': 100.0, 'taxes_id': [(6, 0, cls.itbms.ids)],
        })
        Partner = cls.env['res.partner']
        # Con celular y correo: sin ellos la vendedora no confirma la venta (dcasa_contactos, 2026-10-16).
        cls.padrino = Partner.create({'name': 'Ana Pérez', 'phone': '+507 6000-0001', 'email': 'ana.perez@example.com'})
        cls.padrino._dcasa_asegurar_ficha()
        cls.cliente = Partner.create({'name': 'Eric Gómez', 'phone': '6000-0002', 'email': 'eric.gomez@example.com'})

    def setUp(self):
        super().setUp()
        patcher = patch.dict(os.environ, {'DCASA_PIN_PEPPER': 'pimienta-de-prueba'})
        patcher.start()
        self.addCleanup(patcher.stop)

    def reglas_con(self, **cambios):
        """Las reglas de prueba con algunos valores cambiados (p. ej. topes más bajos)."""
        reglas = R.cargar_reglas()
        for ruta, valor in cambios.items():
            seccion, clave = ruta.split('__')
            reglas[seccion][clave] = valor
        return patch(CARGAR_REGLAS, return_value=reglas)

    def factura(self, partner=None, precio=100.0, pagar=True, vendedor=None, vendedora=None):
        """Factura de cliente con ITBMS; pagada por defecto. Con ``vendedor``, el código va en la venta. Con
        ``vendedora`` (un usuario), la factura es suya («Vendedor» de la factura, ``invoice_user_id``)."""
        valores = {
            'move_type': 'out_invoice',
            'partner_id': (partner or self.cliente).id,
            'invoice_date': fields.Date.today(),
            'dcasa_vendedor_id': vendedor.id if vendedor else False,
            'invoice_line_ids': [(0, 0, {'product_id': self.producto.id, 'quantity': 1, 'price_unit': precio})],
        }
        if vendedora:
            valores['invoice_user_id'] = vendedora.id
        factura = self.env['account.move'].create(valores)
        factura.action_post()
        if pagar:
            self.pagar(factura)
        return factura

    def pagar(self, factura):
        self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=factura.ids,
        ).create({'payment_date': factura.invoice_date})._create_payments()

    def activar_vendedores(self, **cambios):
        """Enciende el programa de vendedores con las reglas de prueba (``seccion__clave=valor`` para variarlas).
        Devuelve el diccionario de reglas: la prueba lo puede seguir cambiando."""
        reglas = R.cargar_reglas()
        reglas['vendedores'] = copy.deepcopy(VENDEDORES_DE_PRUEBA)
        for ruta, valor in cambios.items():
            if '__' in ruta:
                seccion, clave = ruta.split('__')
                reglas['vendedores'][seccion][clave] = valor
            else:
                reglas['vendedores'][ruta] = valor
        patcher = patch(CARGAR_REGLAS, return_value=reglas)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.reglas = reglas
        return reglas

    def vendedor(self, nombre, cedula, celular, tipo='externo', patrocinador=None, correo=None):
        """Una persona afiliada como vendedor (con cédula, celular y términos aceptados)."""
        persona = self.env['res.partner'].create({
            'name': nombre, 'vat': cedula, 'phone': celular, 'email': correo or False})
        persona._dcasa_afiliar_vendedor(tipo, patrocinador, autor='prueba', acepto_terminos=True)
        return persona

    def comisiones(self, partner=None, tipo=None):
        dominio = ([('partner_id', '=', partner.id)] if partner else []) + ([('tipo', '=', tipo)] if tipo else [])
        return self.env['dcasa.vend.comision'].search(dominio)

    def movimientos(self, partner, tipo=None):
        dominio = [('partner_id', '=', partner.id)] + ([('tipo', '=', tipo)] if tipo else [])
        return self.env['dcasa.movimiento'].search(dominio)
