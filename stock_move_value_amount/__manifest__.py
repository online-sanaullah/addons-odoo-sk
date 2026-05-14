# -*- coding: utf-8 -*-
{
    'name': "Stock Move Journal Entry Amount",

    'summary': "Show journal entry amount for products in stock operations",

    'description': """
Show accounting entry amount for products in stock operations.
    """,

    'author': "Noble Unicom",
    #'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.3',

    # any module necessary for this one to work correctly
    'depends': ['base', 'stock_account'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/stock.xml',
        #'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

