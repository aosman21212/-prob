{
    'name': 'Property Management',
    'version': '19.0.1.0.0',
    'category': 'Real Estate',
    'summary': 'Manage Rent/Lease, Sales | Property Rental Contract Management | Property Sales Contract Management',
    'description': """
Property Management
===================
Complete property management solution for Odoo 19:
* Property & Unit Management (apartments, villas, commercial)
* Rental/Lease Contract Management with automated invoicing
* Sales Contract & Booking Management
* Tenant & Owner tracking
* Document management
* Dashboard with occupancy stats
    """,
    'author': 'leapai.ai',
    'website': 'https://leapai.ai',
    'license': 'LGPL-3',
    'depends': ['account', 'mail', 'contacts'],
    'data': [
        'security/property_security.xml',
        'security/ir.model.access.csv',
        'data/property_sequences.xml',
        'views/property_amenity_views.xml',
        'views/property_unit_views.xml',
        'views/property_rental_contract_views.xml',
        'views/property_sales_contract_views.xml',
        'reports/property_rental_contract_report.xml',
        'reports/property_sales_contract_report.xml',
        'views/property_menus.xml',
    ],
    'demo': ['demo/property_demo.xml'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
