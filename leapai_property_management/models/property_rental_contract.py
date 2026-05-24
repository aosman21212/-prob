from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta


class PropertyRentalContract(models.Model):
    _name = 'property.rental.contract'
    _description = 'Property Rental Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'
    _rec_name = 'name'

    name = fields.Char(string='Contract Reference', required=True, copy=False, default='New')
    unit_id = fields.Many2one(
        'property.unit', string='Property Unit', required=True, tracking=True,
        domain=[('state', 'in', ['available', 'booked'])],
    )
    tenant_id = fields.Many2one('res.partner', string='Tenant', required=True, tracking=True)
    owner_id = fields.Many2one(
        'res.partner', string='Landlord / Owner',
        related='unit_id.owner_id', store=True,
    )

    # Contract Period
    date_start = fields.Date(string='Start Date', required=True, tracking=True)
    date_end = fields.Date(string='End Date', required=True, tracking=True)
    payment_term = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly (3 months)'),
        ('biannual', 'Bi-Annual (6 months)'),
        ('yearly', 'Yearly'),
    ], string='Payment Terms', default='monthly', required=True)

    # Financial
    rent_amount = fields.Monetary(
        string='Rent Amount', related='unit_id.rent_amount', store=True,
    )
    security_deposit = fields.Monetary(string='Security Deposit', tracking=True)
    admin_fee = fields.Monetary(string='Administrative Fee')
    currency_id = fields.Many2one(
        'res.currency', related='unit_id.currency_id', store=True,
    )

    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('terminated', 'Terminated'),
        ('renewed', 'Renewed'),
    ], string='Status', default='draft', tracking=True)

    # Invoice tracking
    invoice_ids = fields.One2many('account.move', 'rental_contract_id', string='Invoices')
    invoice_count = fields.Integer(compute='_compute_invoice_count', string='Invoices')
    total_invoiced = fields.Monetary(compute='_compute_invoice_count', string='Total Invoiced')

    notes = fields.Html(string='Terms & Notes')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('property.rental.contract') or 'New'
                )
        return super().create(vals_list)

    def _compute_invoice_count(self):
        for rec in self:
            invoices = rec.invoice_ids.filtered(lambda i: i.state != 'cancel')
            rec.invoice_count = len(invoices)
            rec.total_invoiced = sum(invoices.mapped('amount_total'))

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_end <= rec.date_start:
                raise ValidationError(_('End date must be after start date.'))

    def action_activate(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft contracts can be activated.'))
            rec.unit_id.state = 'rented'
            rec.state = 'active'

    def action_terminate(self):
        for rec in self:
            rec.state = 'terminated'
            other = self.search([
                ('unit_id', '=', rec.unit_id.id),
                ('state', '=', 'active'),
                ('id', '!=', rec.id),
            ])
            if not other:
                rec.unit_id.state = 'available'

    def action_expire(self):
        for rec in self:
            rec.state = 'expired'
            other = self.search([
                ('unit_id', '=', rec.unit_id.id),
                ('state', '=', 'active'),
                ('id', '!=', rec.id),
            ])
            if not other:
                rec.unit_id.state = 'available'

    def action_draft(self):
        self.state = 'draft'

    def action_generate_invoices(self):
        """Generate rent invoices based on payment term."""
        self.ensure_one()
        if self.state != 'active':
            raise UserError(_('Contract must be active to generate invoices.'))

        AccountMove = self.env['account.move']
        interval_map = {'monthly': 1, 'quarterly': 3, 'biannual': 6, 'yearly': 12}
        months = interval_map.get(self.payment_term, 1)

        current = self.date_start
        created = 0
        while current < self.date_end:
            period_end = current + relativedelta(months=months) - relativedelta(days=1)
            if period_end > self.date_end:
                period_end = self.date_end

            existing = AccountMove.search([
                ('rental_contract_id', '=', self.id),
                ('invoice_date', '=', current),
                ('state', '!=', 'cancel'),
            ])
            if not existing:
                AccountMove.create({
                    'move_type': 'out_invoice',
                    'partner_id': self.tenant_id.id,
                    'invoice_date': current,
                    'rental_contract_id': self.id,
                    'invoice_line_ids': [(0, 0, {
                        'name': f'Rent: {self.unit_id.name} ({current} to {period_end})',
                        'quantity': 1,
                        'price_unit': self.rent_amount,
                    })],
                })
                created += 1
            current = current + relativedelta(months=months)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Invoices Generated'),
                'message': _('%s invoice(s) created.') % created,
                'type': 'success',
            },
        }

    def action_view_invoices(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoices',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('rental_contract_id', '=', self.id)],
            'context': {
                'default_rental_contract_id': self.id,
                'default_move_type': 'out_invoice',
            },
        }
