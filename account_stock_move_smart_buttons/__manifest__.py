# -*- coding: utf-8 -*-
{
    'name': 'Account Stock Move Smart Buttons',
    'version': '17.0.1.0.2',
    'summary': 'Smart buttons between journal entries, stock moves, and pickings',
    'author': 'Sana Ullah Khan',
    'website': '',
    'category': 'Accounting/Inventory',
    'license': 'LGPL-3',
    'depends': ['account', 'stock'],
    'data': [
        'views/account_move_views.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'application': False,
}
