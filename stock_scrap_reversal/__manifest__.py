{
    "name": "Stock Scrap Reversal",
    "version": "17.0.1.0.1",
    "category": "Inventory/Inventory",
    "summary": "Reverse completed scrap operations with linked stock moves",
    "description": """
Stock Scrap Reversal
====================

Adds a controlled reversal action to completed stock scrap operations.
The reversal restores the product to the original source location by creating
and completing an opposite stock move linked to both the original scrap move
and the same scrap operation.

The module preserves lot/serial, owner, unit of measure, and package details.
For automated inventory valuation, the reversal uses the original move cost
and reverses the accounting account used by the original scrap move.
    """,
    "author": "Sana Ullah Khan",
    "license": "LGPL-3",
    "depends": [
        "stock",
        "stock_account",
    ],
    "data": [
        "views/stock_scrap_views.xml",
    ],
    "installable": True,
    "application": False,
}
