from odoo import fields, models


class PartnerAccountApprovalHistory(models.Model):
    _name = "res.partner.account.approval.history"
    _description = "Partner Account Approval History"
    _order = "id desc"

    partner_id = fields.Many2one(
        "res.partner",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        index=True,
    )
    account_side = fields.Selection(
        [
            ("receivable", "Receivable"),
            ("payable", "Payable"),
        ],
        required=True,
        index=True,
    )
    previous_account_id = fields.Many2one(
        "account.account",
        string="Previous Account",
    )
    proposed_account_id = fields.Many2one(
        "account.account",
        string="Proposed Account",
        required=True,
    )
    approval_request_id = fields.Many2one(
        "approval.request",
        ondelete="set null",
        index=True,
    )
    state = fields.Selection(
        [
            ("baseline", "Approved Baseline"),
            ("pending", "Pending Approval"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
        ],
        required=True,
        default="pending",
        index=True,
    )
    requested_by_id = fields.Many2one(
        "res.users",
        default=lambda self: self.env.user,
        readonly=True,
    )
    requested_date = fields.Datetime(
        default=fields.Datetime.now,
        readonly=True,
    )
    resolved_by_id = fields.Many2one(
        "res.users",
        readonly=True,
    )
    resolved_date = fields.Datetime(
        readonly=True,
    )
