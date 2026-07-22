from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    enforce_partner_receivable_account_approval = fields.Boolean(
        related="company_id.enforce_partner_receivable_account_approval",
        readonly=False,
    )
    enforce_partner_payable_account_approval = fields.Boolean(
        related="company_id.enforce_partner_payable_account_approval",
        readonly=False,
    )
    receivable_account_approval_trigger = fields.Selection(
        related="company_id.receivable_account_approval_trigger",
        readonly=False,
    )
    payable_account_approval_trigger = fields.Selection(
        related="company_id.payable_account_approval_trigger",
        readonly=False,
    )
    partner_account_approval_category_id = fields.Many2one(
        related="company_id.partner_account_approval_category_id",
        readonly=False,
    )
    partner_account_approval_blocking_scope = fields.Selection(
        related="company_id.partner_account_approval_blocking_scope",
        readonly=False,
    )
