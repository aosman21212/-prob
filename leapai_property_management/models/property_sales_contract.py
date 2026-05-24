from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PropertySalesContract(models.Model):
    _name = 'property.sales.contract'
    _description = 'Property Sales Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_contract desc'
    _rec_name = 'name'

    name = fields.Char(string='Contract Reference', required=True, copy=False, default='New')
    unit_id = fields.Many2one(
        'property.unit', string='Property Unit', required=True, tracking=True,
        domain=[('state', 'in', ['available', 'booked'])],
    )
    buyer_id = fields.Many2one('res.partner', string='Buyer', required=True, tracking=True)
    seller_id = fields.Many2one(
        'res.partner', string='Seller / Owner',
        related='unit_id.owner_id', store=True,
    )

    # Contract Details
    date_contract = fields.Date(
        string='Contract Date', required=True, default=fields.Date.today,
    )
    date_completion = fields.Date(string='Expected Completion Date')

    # Financial
    sale_price = fields.Monetary(
        string='Sale Price', related='unit_id.sale_price', store=True,
    )
    agreed_price = fields.Monetary(string='Agreed Price', required=True, tracking=True)
    booking_amount = fields.Monetary(string='Booking Amount / EOI')
    down_payment = fields.Monetary(string='Down Payment')
    admin_fee = fields.Monetary(string='Admin Fee')
    stamp_duty = fields.Monetary(string='Stamp Duty')
    registration_fee = fields.Monetary(string='Registration Fee')
    currency_id = fields.Many2one(
        'res.currency', related='unit_id.currency_id', store=True,
    )

    # Payment Plan
    payment_plan_ids = fields.One2many(
        'property.payment.plan', 'sales_contract_id', string='Payment Plan',
    )
    total_paid = fields.Monetary(
        compute='_compute_totals', string='Total Paid', store=False,
    )
    balance_due = fields.Monetary(
        compute='_compute_totals', string='Balance Due', store=False,
    )

    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('booked', 'Booked'),
        ('spa', 'SPA Signed'),
        ('completed', 'Completed / Transferred'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    invoice_ids = fields.One2many('account.move', 'sales_contract_id', string='Invoices')
    invoice_count = fields.Integer(compute='_compute_invoice_count', string='Invoices')
    notes = fields.Html(string='Terms & Notes')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('property.sales.contract') or 'New'
                )
        return super().create(vals_list)

    def _compute_totals(self):
        for rec in self:
            paid = sum(
                rec.payment_plan_ids.filtered(lambda p: p.state == 'paid').mapped('amount')
            )
            rec.total_paid = paid
            rec.balance_due = rec.agreed_price - paid

    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = len(rec.invoice_ids.filtered(lambda i: i.state != 'cancel'))

    def action_book(self):
        self.state = 'booked'
        self.unit_id.state = 'booked'

    def action_sign_spa(self):
        self.state = 'spa'

    def action_complete(self):
        self.state = 'completed'
        self.unit_id.state = 'sold'

    def action_cancel(self):
        self.state = 'cancelled'
        other_active = self.env['property.sales.contract'].search([
            ('unit_id', '=', self.unit_id.id),
            ('state', 'not in', ['cancelled', 'completed']),
            ('id', '!=', self.id),
        ])
        if not other_active:
            self.unit_id.state = 'available'

    def action_draft(self):
        self.state = 'draft'

    def action_generate_booking_invoice(self):
        self.ensure_one()
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.buyer_id.id,
            'invoice_date': self.date_contract,
            'sales_contract_id': self.id,
            'invoice_line_ids': [(0, 0, {
                'name': f'Booking Amount - {self.unit_id.name}',
                'quantity': 1,
                'price_unit': self.booking_amount or 0,
            })],
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
        }

    def action_view_invoices(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoices',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('sales_contract_id', '=', self.id)],
            'context': {
                'default_sales_contract_id': self.id,
                'default_move_type': 'out_invoice',
            },
        }


class PropertyPaymentPlan(models.Model):
    _name = 'property.payment.plan'
    _description = 'Payment Plan Installment'
    _order = 'due_date'

    sales_contract_id = fields.Many2one(
        'property.sales.contract', string='Sales Contract',
        required=True, ondelete='cascade',
    )
    name = fields.Char(string='Milestone', required=True)
    due_date = fields.Date(string='Due Date', required=True)
    amount = fields.Monetary(string='Amount', required=True, currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency', related='sales_contract_id.currency_id',
    )
    state = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
    ], default='pending', string='Status')
    notes = fields.Char(string='Notes')
