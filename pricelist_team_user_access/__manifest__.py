# -*- coding: utf-8 -*-
{
    'name': 'Pricelist Team/User Access',
    'version': '17.0.1.14.0',
    'category': 'Sales/Sales',
    'summary': 'Hide pricelists/rules in views and protect create/write/delete by sales teams and users.',
    'author': 'Sanaullah Khan',
    'license': 'LGPL-3',
    'depends': [
        'product',
        'sales_team',
        'sale',
        'point_of_sale',
        'base_pricelist_division',
    ],
    'data': [
        'security/ir_rule.xml',
        'views/product_pricelist_views.xml',
        'views/product_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
