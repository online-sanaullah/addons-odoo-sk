# -*- coding: utf-8 -*-
{
    'name': 'Product QR Code Generator',
    'version': '17.0.1.0.1',
    'category': 'Extra Tools',
    'summary': 'Generate Unique QR Codes for Products',
    'description': '''QR Code, QR Code Generator, Odoo QR Code Generator,
    Product QR Code, QR, QR Code Odoo''',
    'author': 'Sanaullah Khan',
    'company': 'Noble Unicom Lda.',
    'depends': ['base', 'sale_management', 'stock'],
    'data': [
        'data/ir_actions_server_data.xml',
        'views/product_product_view.xml',
        'views/product_template_view.xml',
        'report/paperformat.xml',
        'report/report_action.xml',
        'report/customer_product_qrcode_template.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
