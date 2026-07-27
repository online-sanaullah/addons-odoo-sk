from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_google_review_qr_enabled = fields.Boolean(
        related="pos_config_id.google_review_qr_enabled",
        readonly=False,
    )
    pos_google_review_url = fields.Char(
        related="pos_config_id.google_review_url",
        readonly=False,
    )
    pos_google_review_qr_title = fields.Char(
        related="pos_config_id.google_review_qr_title",
        readonly=False,
    )
    pos_google_review_qr_message = fields.Char(
        related="pos_config_id.google_review_qr_message",
        readonly=False,
    )
