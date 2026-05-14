from odoo import models, fields

class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    show_picking_qr = fields.Boolean(
        string="Show Picking QR in Report",
        default=False,
        help="If enabled, the picking report will display QR code instead of barcode"
    )
