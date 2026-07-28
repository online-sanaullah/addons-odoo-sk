# -*- coding: utf-8 -*-
{
    'name': "Company Divisions",

    'summary': "Allows us to define division within companies",

    'description': """
Create divisions within companies.
    """,

    'author': "Sanaullah Khan",
    #'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Sales',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        'views/res_company.xml',
        'views/division.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        #'demo/demo.xml',
    ],
}

