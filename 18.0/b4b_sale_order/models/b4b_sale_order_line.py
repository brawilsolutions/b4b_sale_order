from odoo import models, fields, api

class B4BSaleOrderLine(models.Model):
    _name = 'b4b.sale.order.line'
    _description = 'Línea de Orden B4B'

    sale_order_id = fields.Many2one('b4b.sale.order', string='Orden B4B')
    codigo_item = fields.Char(string='Código Item')
    nombre_item = fields.Char(string='Nombre Item')
    cantidad = fields.Float(string='Cantidad')
    precio_unitario = fields.Float(string='Precio Unitario')
    porcentaje_sl = fields.Float(string='Porcentaje SL')
    desc_asesor = fields.Integer(string='Descuento Asesor')
    total = fields.Float(string='Total', compute='_compute_total', store=True)

    @api.depends('cantidad', 'precio_unitario')
    def _compute_total(self):
        for line in self:
            line.total = line.cantidad * line.precio_unitario
