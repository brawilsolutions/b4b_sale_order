from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    supplier_internal_reference = fields.Char(
        string="Referencia Interna Proveedor",
        compute="_compute_supplier_reference",
        inverse="_inverse_supplier_reference",
        store=True,
    )

    creado_b4b = fields.Boolean(
        string='Creado por B4B',
        default=False,
        store=True
    )
    
    # --------------------------------------------------
    # COMPUTE
    # --------------------------------------------------
    @api.depends('seller_ids.product_code', 'seller_ids.partner_id')
    def _compute_supplier_reference(self):
        for template in self:
            reference = False
            for seller in template.seller_ids:
                if (
                    seller.partner_id
                    and seller.partner_id.name
                    and 'distribuciones hoyostools' in seller.partner_id.name.lower()
                ):
                    reference = seller.product_code
                    break
            template.supplier_internal_reference = reference

    # --------------------------------------------------
    # INVERSE (bidireccional)
    # --------------------------------------------------
    def _inverse_supplier_reference(self):
        Partner = self.env['res.partner']
        SupplierInfo = self.env['product.supplierinfo']

        for template in self:
            if not template.supplier_internal_reference:
                continue

            seller = template.seller_ids.filtered(
                lambda s: s.partner_id
                and s.partner_id.name
                and 'distribuciones hoyostools' in s.partner_id.name.lower()
            )[:1]

            if seller:
                seller.product_code = template.supplier_internal_reference
            else:
                partner = Partner.search(
                    [('name', 'ilike', 'Distribuciones Hoyostools')],
                    limit=1
                )
                if not partner:
                    partner = Partner.create({
                        'name': 'Distribuciones Hoyostools',
                        'company_type': 'company',
                    })

                SupplierInfo.create({
                    'partner_id': partner.id,
                    'product_tmpl_id': template.id,
                    'product_code': template.supplier_internal_reference,
                })
