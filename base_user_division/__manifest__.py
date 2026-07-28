# -*- coding: utf-8 -*-
{
    'name': "Users Divisions",

    'summary': "Allows us to set allowed company divisions for the users",

    'description': """
Define allowed company divisions for the users.
    """,

    'author': "Sanaullah Khan",
    #'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Sales',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base_company_division'],

    # always loaded
    'data': [
        'views/division.xml',
        'views/res_users.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        #'demo/demo.xml',
    ],
    'auto_install': True,
}

