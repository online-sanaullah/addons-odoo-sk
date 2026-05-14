{
    "name": "Stock State Last Updated By",
    "version": "17.0.1.6.0",
    "summary": "Show who last changed the state/status of stock records",
    "category": "Inventory/Inventory",
    "author": "ChatGPT",
    "license": "LGPL-3",
    "depends": ["stock", "mail"],
    "data": [
        "views/stock_picking_views.xml",
        "views/stock_move_views.xml",
        "views/stock_move_line_views.xml"
    ],
    "installable": True,
    "application": False
}
