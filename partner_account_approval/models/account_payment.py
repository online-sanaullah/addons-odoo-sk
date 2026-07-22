from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    partner_account_approval_warning = fields.Boolean(
        compute="_compute_partner_account_approval_warning",
    )
    partner_account_approval_message = fields.Char(
        compute="_compute_partner_account_approval_warning",
    )

    def _payment_account_side(self):
        self.ensure_one()

        # Standard Odoo values.
        if self.partner_type == "customer":
            return "receivable"
        if self.partner_type == "supplier":
            return "payable"

        # Fallback for payments created through wizards or custom flows where
        # partner_type may not yet be available consistently.
        if self.payment_type == "inbound":
            return "receivable"
        if self.payment_type == "outbound":
            return "payable"
        return False

    def _partner_has_pending_account_approval(self):
        self.ensure_one()
        if not self.partner_id or not self.company_id:
            return False

        partner = self.partner_id.with_company(self.company_id)
        side = self._payment_account_side()
        if not side:
            return False

        destination_account = getattr(self, "destination_account_id", False)
        if not destination_account:
            destination_account = (
                partner.property_account_receivable_id
                if side == "receivable"
                else partner.property_account_payable_id
            )

        return partner._is_account_blocked_by_pending_approval(
            self.company_id,
            destination_account,
            side,
        )

    def _ensure_partner_account_request(self):
        for payment in self.filtered(lambda record: record.partner_id and record.company_id):
            side = payment._payment_account_side()
            payment.partner_id._ensure_account_approval_request(
                payment.company_id,
                receivable=side == "receivable",
                payable=side == "payable",
                source=payment,
            )

    @api.depends(
        "partner_id",
        "partner_type",
        "payment_type",
        "company_id",
        "partner_id.receivable_account_approval_state",
        "partner_id.payable_account_approval_state",
    )
    def _compute_partner_account_approval_warning(self):
        for payment in self:
            blocked = payment._partner_has_pending_account_approval()
            payment.partner_account_approval_warning = blocked
            payment.partner_account_approval_message = (
                _(
                    "The partner account approval is pending. You may save this "
                    "draft, but it cannot be posted until the approval is approved, "
                    "rejected, or cancelled."
                )
                if blocked
                else False
            )

    @api.model_create_multi
    def create(self, vals_list):
        payments = super().create(vals_list)
        payments._ensure_partner_account_request()
        return payments

    def write(self, vals):
        result = super().write(vals)
        if {
            "partner_id",
            "partner_type",
            "payment_type",
            "company_id",
        }.intersection(vals):
            self._ensure_partner_account_request()
        return result

    def action_post(self):
        self._ensure_partner_account_request()

        blocked = self.filtered(
            lambda payment: payment._partner_has_pending_account_approval()
        )
        if blocked:
            partner_names = ", ".join(
                sorted(set(blocked.mapped("partner_id.display_name")))
            )
            raise UserError(
                _(
                    "The partner account approval is pending for: %s. "
                    "The payment cannot be posted until the relevant approval is "
                    "approved, rejected, or cancelled."
                )
                % partner_names
            )

        return super().action_post()
