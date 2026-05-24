from odoo import fields, models


class PropertyAmenity(models.Model):
    _name = 'property.amenity'
    _description = 'Property Amenity'
    _order = 'name'

    name = fields.Char(string='Amenity', required=True)
    icon = fields.Char(string='Icon (FA class)', default='fa-check')
    active = fields.Boolean(default=True)
