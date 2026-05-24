from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    rental_contract_id = fields.Many2one(
        'property.rental.contract', string='Rental Contract', copy=False,
    )
    sales_contract_id = fields.Many2one(
        'property.sales.contract', string='Sales Contract', copy=False,
    )
