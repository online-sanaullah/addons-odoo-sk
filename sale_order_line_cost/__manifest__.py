# -*- coding: utf-8 -*-
{
    'name': "Sale Order Line Cost",

    'summary': "Show cost of goods sold for sale order lines.",

    'description': """
Show cost of goods sold and revenue against each sale order line.
    """,

    'author': "Sanaullah Khan",
    #'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['odoo_sale_order_line_views', 'account'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

