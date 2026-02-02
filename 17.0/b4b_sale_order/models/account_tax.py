from odoo import fields, models

class AccountTax(models.Model):
    _inherit = 'account.tax'

    es_iva = fields.Boolean(string='¿Es IVA?', help="Marca este impuesto como IVA para incluirlo en los precios si aplica.")