"""El Worker sabe si el negocio cobra ITBMS (``cobra_itbms`` en la configuración, Baby Caleb: no).

Con ``DCASA_COBRA_ITBMS=0`` el arranque corre ``dcasa_base.aplicar_sin_itbms``; desde ahí la configuración que lee el
Worker dice ``cobra_itbms: false`` y ningún precio le llega a la clienta con «+ ITBMS» (juan/test/sin-itbms.test.ts)."""
from odoo.addons.dcasa_base import aplicar_sin_itbms
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestCobraItbmsEnLaConfiguracion(TransactionCase):

    def test_la_configuracion_dice_si_se_cobra(self):
        ajustes = self.env.ref('dcasa_conversaciones.ajustes_juan')
        self.assertIs(ajustes.como_json()['cobra_itbms'], True, 'de fábrica, como D’CASA')
        aplicar_sin_itbms(self.env)
        self.assertIs(ajustes.como_json()['cobra_itbms'], False)
