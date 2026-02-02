from odoo import models, fields, api


class B4BSaleOrder(models.Model):
    _name = 'b4b.sale.order'
    _description = 'Orden B4B'

    cliente = fields.Char(string='Cliente')
    tipo_identificacion_id = fields.Char(string='Identificacion Id')
    tipo_identificacion = fields.Char(string='Tipo Identificación')
    identificacion = fields.Char(string='Identificación/NIT')
    direccion_cliente = fields.Char(string='Dirección Cliente')
    telefono_cliente = fields.Char(string='Teléfono del Cliente')
    ciudad_id = fields.Char(string='Ciudad Id')
    ciudad = fields.Char(string='Ciudad')
    departamento_id = fields.Char(string='Departamento Id')
    departamento = fields.Char(string='Departamento')
    pais = fields.Char(string='País')
    fecha_pedido_prov = fields.Date(string='Fecha Pedido Prov')
    email = fields.Char(string='Email')
    sincronizado = fields.Boolean(string='Sincronizado', default=False)

    numero_orden_id = fields.Many2one('sale.order', string='Cotización Relacionada')
    pedido_prov_id = fields.Char(string='Pedido Prov ID')
    notas_cliente = fields.Text(string='Notas del Cliente')
    guia = fields.Char(string='Guía')
    status = fields.Selection([
        ('draft', 'Borrador'),
        ('send', 'Enviado'),
        ('done', 'Sincronizado')
    ], string='Estado', default='draft', tracking=True)
    ciudad_2 = fields.Char(string='Ciudad')

    line_ids = fields.One2many('b4b.sale.order.line', 'sale_order_id', string='Productos')
    
    def write(self, vals):
        res = super(B4BSaleOrder, self).write(vals)
        for record in self:
            if vals.get('sincronizado') and record.status != 'done':
                record.status = 'done'
        return res    
    
    def action_set_send(self):
        for record in self:
            record.status = 'send'

    def action_set_done(self):
        for record in self:
            record.status = 'done'

    def action_set_draft(self):
        for record in self:
            record.status = 'draft'

    def action_create_quotation(self):
        Config = self.env['ir.config_parameter'].sudo()
        Partner = self.env['res.partner']
        SaleOrder = self.env['sale.order']
        SaleOrderLine = self.env['sale.order.line']
        ProductTemplate = self.env['product.template']
        City = self.env['res.city']
        State = self.env['res.country.state']
        Zip = self.env.get('res.partner.zip')
        IdentificationType = self.env['l10n_latam.identification.type']

        # Configuraciones
        use_bw_localization = Config.get_param(
            'b4b_sale_order.use_bw_localization', default='False'
        ) == 'True'
        con_impuesto = Config.get_param(
            'b4b_sale_order.con_impuesto', default='False'
        ) == 'True'

        country_co = self.env.ref('base.co')

        # Proveedor fijo
        proveedor_hoyos = Partner.search(
            [('name', 'ilike', 'Distribuciones Hoyostools')], limit=1
        )
        if not proveedor_hoyos:
            proveedor_hoyos = Partner.create({
                'name': 'Distribuciones Hoyostools',
                'company_type': 'company',
            })

        for record in self:
            if record.sincronizado:
                continue

            # -------------------------------
            # Tipo de identificación
            # -------------------------------
            tipo_ident = False
            if use_bw_localization:
                if record.tipo_identificacion_id:
                    try:
                        tipo_ident = self.env.ref(record.tipo_identificacion_id)
                    except ValueError:
                        tipo_ident = IdentificationType.search(
                            [('name', '=', record.tipo_identificacion)], limit=1
                        )
            else:
                tipo_ident = IdentificationType.search(
                    [('id', '=', record.tipo_identificacion_id)], limit=1
                )

            # -------------------------------
            # Localización (solo buscar, no crear)
            # -------------------------------
            ciudad = False
            estado = False
            zip_id = False

            if use_bw_localization and Zip:
                zip_id = Zip.search([('name', '=', record.ciudad)], limit=1)
            else:
                if record.departamento:
                    estado = State.search([
                        ('name', '=', record.departamento),
                        ('country_id', '=', country_co.id)
                    ], limit=1)

                if record.ciudad:
                    ciudad = City.search([
                        ('name', '=', record.ciudad),
                        ('state_id', '=', estado.id if estado else False)
                    ], limit=1)

            # -------------------------------
            # NORMALIZAR IDENTIFICACIÓN
            # -------------------------------
            raw_doc = (record.identificacion or '').strip()

            if not use_bw_localization and '-' in raw_doc:
                raw_doc = raw_doc.split('-')[0]

            # -------------------------------
            # BUSCAR CLIENTE
            # -------------------------------
            if use_bw_localization:
                domain = [('identification_document', '=', record.identificacion)]
            else:
                # 👇 CLAVE: buscar VAT con o sin DV
                domain = [
                    '|',
                    ('vat', '=', raw_doc),
                    ('vat', '=like', f'{raw_doc}-%')
                ]

            partner = Partner.search(domain, limit=1)

            # -------------------------------
            # CREAR CLIENTE SI NO EXISTE
            # -------------------------------
            if not partner:
                partner_vals = {
                    'name': record.cliente,
                    'street': record.direccion_cliente,
                    'phone': record.telefono_cliente,
                    'email': record.email,
                    'company_type': 'person',
                }

                if tipo_ident and 'document_type_id' in Partner._fields:
                    partner_vals['document_type_id'] = tipo_ident.id

                if use_bw_localization:
                    partner_vals['identification_document'] = record.identificacion
                    if zip_id:
                        partner_vals['zip_id'] = zip_id.id
                else:
                    partner_vals.update({
                        'vat': raw_doc,
                        'city_id': ciudad.id if ciudad else False,
                        'state_id': estado.id if estado else False,
                        'country_id': country_co.id,
                    })

                partner = Partner.create(partner_vals)

            # -------------------------------
            # CREAR COTIZACIÓN
            # -------------------------------
            sale_order = SaleOrder.create({
                'partner_id': partner.id,
                'client_order_ref': record.pedido_prov_id,
                'note': record.notas_cliente or '',
            })

            # -------------------------------
            # LÍNEAS
            # -------------------------------
            for line in record.line_ids:
                template = ProductTemplate.search([
                    ('seller_ids.product_code', '=', line.codigo_item),
                    ('seller_ids.partner_id', '=', proveedor_hoyos.id)
                ], limit=1)

                if not template:
                    iva_tax = self.env['account.tax'].search(
                        [('es_iva', '=', True)], limit=1
                    )

                    template = ProductTemplate.create({
                        'name': line.nombre_item,
                        'type': 'consu',
                        'creado_b4b': True,
                        'seller_ids': [(0, 0, {
                            'partner_id': proveedor_hoyos.id,
                            'product_code': line.codigo_item,
                        })],
                        'taxes_id': [(6, 0, [iva_tax.id])] if iva_tax else False,
                    })

                product = template.product_variant_id
                if not product:
                    continue

                base_price = line.precio_unitario
                final_price = base_price

                if con_impuesto:
                    taxes = product.taxes_id.filtered(
                        lambda t: t.type_tax_use == 'sale' and t.es_iva
                    )
                    if taxes:
                        final_price = base_price * (1 + taxes[0].amount / 100.0)

                SaleOrderLine.create({
                    'order_id': sale_order.id,
                    'product_id': product.id,
                    'name': line.nombre_item,
                    'product_uom_qty': line.cantidad,
                    'price_unit': final_price,
                    'discount': line.desc_asesor,
                })

            # -------------------------------
            # FINALIZAR
            # -------------------------------
            record.write({
                'numero_orden_id': sale_order.id,
                'sincronizado': True,
                'status': 'done',
            })