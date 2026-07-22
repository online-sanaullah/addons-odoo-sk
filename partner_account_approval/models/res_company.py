from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    enforce_partner_receivable_account_approval = fields.Boolean(
        string="Require Receivable Account Approval",
    )
    enforce_partner_payable_account_approval = fields.Boolean(
        string="Require Payable Account Approval",
    )

    receivable_account_approval_trigger = fields.Selection(
        [
            ("immediate", "Immediately After Account Change"),
            ("first_transaction_initial_then_immediate", "First Transaction for New Partner, Then Immediate"),
            ("next_transaction_after_change", "Next Transaction After Every Account Change"),
        ],
        string="Receivable Approval Request Trigger",
        default="immediate",
        required=True,
    )
    payable_account_approval_trigger = fields.Selection(
        [
            ("immediate", "Immediately After Account Change"),
            ("first_transaction_initial_then_immediate", "First Transaction for New Partner, Then Immediate"),
            ("next_transaction_after_change", "Next Transaction After Every Account Change"),
        ],
        string="Payable Approval Request Trigger",
        default="immediate",
        required=True,
    )

    partner_account_approval_category_id = fields.Many2one(
        "approval.category",
        string="Partner Account Approval Category",
    )

    partner_account_approval_blocking_scope = fields.Selection(
        [
            ("pending_account_only", "Block Only the Pending Account"),
            (
                "all_partner_accounts",
                "Block All Receivable/Payable Accounts for the Partner",
            ),
        ],
        string="Pending Approval Blocking Scope",
        default="pending_account_only",
        required=True,
        help=(
            "Block Only the Pending Account: posting is blocked only when the "
            "journal item uses the account currently pending approval. "
            "Block All Receivable/Payable Accounts: while approval is pending, "
            "all receivable/payable journal items for the partner are blocked."
        ),
    )
