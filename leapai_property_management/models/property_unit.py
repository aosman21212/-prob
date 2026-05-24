from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PropertyUnit(models.Model):
    _name = 'property.unit'
    _description = 'Property Unit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    # Basic Info
    name = fields.Char(string='Unit Name / Reference', required=True, tracking=True)
    ref = fields.Char(string='Reference Code', copy=False)
    property_type = fields.Selection([
        ('apartment', 'Apartment'),
        ('villa', 'Villa'),
        ('commercial', 'Commercial'),
        ('office', 'Office'),
        ('shop', 'Shop'),
        ('warehouse', 'Warehouse'),
        ('land', 'Land'),
    ], string='Property Type', required=True, default='apartment', tracking=True)

    # Status
    state = fields.Selection([
        ('available', 'Available'),
        ('booked', 'Booked'),
        ('rented', 'Rented'),
        ('sold', 'Sold'),
        ('maintenance', 'Under Maintenance'),
    ], string='Status', default='available', tracking=True, required=True)

    # Location
    street = fields.Char(string='Street')
    city = fields.Char(string='City')
    state_id = fields.Many2one('res.country.state', string='State')
    country_id = fields.Many2one('res.country', string='Country')
    zip_code = fields.Char(string='ZIP')

    # Building details
    building = fields.Char(string='Building / Block')
    floor = fields.Integer(string='Floor / Level')
    unit_number = fields.Char(string='Unit Number')

    # Specifications
    area_sqft = fields.Float(string='Area (sqft)')
    area_sqm = fields.Float(string='Area (sqm)', compute='_compute_sqm', store=True)
    bedrooms = fields.Integer(string='Bedrooms')
    bathrooms = fields.Integer(string='Bathrooms')
    parking_spaces = fields.Integer(string='Parking Spaces')
    balconies = fields.Integer(string='Balconies')
    facing = fields.Selection([
        ('north', 'North'), ('south', 'South'),
        ('east', 'East'), ('west', 'West'),
        ('north_east', 'North-East'), ('north_west', 'North-West'),
        ('south_east', 'South-East'), ('south_west', 'South-West'),
    ], string='Facing')
    furnishing = fields.Selection([
        ('fully_furnished', 'Fully Furnished'),
        ('semi_furnished', 'Semi Furnished'),
        ('unfurnished', 'Unfurnished'),
    ], string='Furnishing Type', default='unfurnished')

    # Financial
    sale_price = fields.Monetary(string='Sale Price', currency_field='currency_id')
    rent_amount = fields.Monetary(string='Monthly Rent', currency_field='currency_id')
    security_deposit = fields.Monetary(string='Security Deposit', currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    # Relations
    owner_id = fields.Many2one('res.partner', string='Owner / Landlord', tracking=True)
    amenity_ids = fields.Many2many('property.amenity', string='Amenities')
    active = fields.Boolean(default=True)
    notes = fields.Html(string='Notes')
    image = fields.Image(string='Property Image', max_width=1920, max_height=1920)
    image_small = fields.Image(
        string='Thumbnail', related='image',
        max_width=128, max_height=128, store=True,
    )

    # Computed
    rental_contract_count = fields.Integer(
        compute='_compute_contract_counts', string='Rental Contracts',
    )
    sales_contract_count = fields.Integer(
        compute='_compute_contract_counts', string='Sales Contracts',
    )
    current_tenant_id = fields.Many2one(
        'res.partner', compute='_compute_current_tenant',
        string='Current Tenant', store=False,
    )

    @api.depends('area_sqft')
    def _compute_sqm(self):
        for rec in self:
            rec.area_sqm = rec.area_sqft * 0.092903 if rec.area_sqft else 0.0

    def _compute_contract_counts(self):
        RentalContract = self.env['property.rental.contract']
        SalesContract = self.env['property.sales.contract']
        for rec in self:
            rec.rental_contract_count = RentalContract.search_count([('unit_id', '=', rec.id)])
            rec.sales_contract_count = SalesContract.search_count([('unit_id', '=', rec.id)])

    def _compute_current_tenant(self):
        for rec in self:
            contract = self.env['property.rental.contract'].search([
                ('unit_id', '=', rec.id),
                ('state', '=', 'active'),
            ], limit=1, order='date_start desc')
            rec.current_tenant_id = contract.tenant_id if contract else False

    def action_set_available(self):
        self.state = 'available'

    def action_set_maintenance(self):
        self.state = 'maintenance'

    def action_view_rental_contracts(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Rental Contracts',
            'res_model': 'property.rental.contract',
            'view_mode': 'list,form',
            'domain': [('unit_id', '=', self.id)],
            'context': {'default_unit_id': self.id},
        }

    def action_view_sales_contracts(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sales Contracts',
            'res_model': 'property.sales.contract',
            'view_mode': 'list,form',
            'domain': [('unit_id', '=', self.id)],
            'context': {'default_unit_id': self.id},
        }
