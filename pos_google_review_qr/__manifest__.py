{
    "name": "PoS Google Review QR Receipt",
    "version": "17.0.1.1.0",
    "category": "Sales/Point of Sale",
    "summary": "Print a shop-specific Google Maps review QR code on PoS receipts",
    "description": """
Print a configurable Google Maps review QR code on Point of Sale receipts.
Each PoS configuration can use its own Google review link, heading, and
customer-facing message.
""",
    "author": "Sana Ullah Khan",
    "maintainer": "Sana Ullah Khan",
    "license": "LGPL-3",
    "depends": ["point_of_sale"],
    "data": [
        "views/pos_config_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_google_review_qr/static/src/app/store/order.js",
            "pos_google_review_qr/static/src/app/screens/receipt_screen/receipt/order_receipt.xml",
            "pos_google_review_qr/static/src/app/screens/receipt_screen/receipt/order_receipt.css",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
