import base64
from io import BytesIO
import qrcode
from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = "stock.picking"

    picking_qr = fields.Binary(
        string="Picking QR Code",
        compute="_compute_picking_qr"
    )

    @api.depends("name")
    def _compute_picking_qr(self):
        for picking in self:
            if picking.name:
                qr_img = qrcode.make(picking.name)
                buffer = BytesIO()
                qr_img.save(buffer, format="PNG")
                picking.picking_qr = base64.b64encode(buffer.getvalue())
            else:
                picking.picking_qr = False
