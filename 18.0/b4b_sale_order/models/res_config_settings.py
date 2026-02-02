from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    use_bw_localization = fields.Boolean(
        string="Ubicación personalizada BW",
        config_parameter='b4b_sale_order.use_bw_localization',
    )

    con_impuesto = fields.Boolean(
        string="Aplicar precio con impuesto",
        config_parameter='b4b_sale_order.con_impuesto',
    )