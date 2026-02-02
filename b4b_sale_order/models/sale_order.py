from odoo import models, api
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def action_confirm(self):
        for order in self:
            productos_b4b = order.order_line.filtered(lambda l: l.product_id.product_tmpl_id.creado_b4b)
            if productos_b4b:
                nombres = "\n".join(productos_b4b.mapped('product_id.name'))
                raise UserError(
                    "La orden tiene productos creados por B4B que no se han revisado:\n\n%s" % nombres
                )
        return super(SaleOrder, self).action_confirm()