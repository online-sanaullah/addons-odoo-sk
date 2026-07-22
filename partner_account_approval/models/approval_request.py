from odoo import _, fields, models


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    partner_id = fields.Many2one("res.partner", string="Partner", copy=False, index=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
        copy=False,
    )
    approve_receivable_account = fields.Boolean(copy=False)
    approve_payable_account = fields.Boolean(copy=False)
    previous_receivable_account_id = fields.Many2one(
        "account.account",
        string="Previous Receivable Account",
        copy=False,
    )
    previous_payable_account_id = fields.Many2one(
        "account.account",
        string="Previous Payable Account",
        copy=False,
    )
    proposed_receivable_account_id = fields.Many2one(
        "account.account",
        string="Proposed Receivable Account",
        copy=False,
    )
    proposed_payable_account_id = fields.Many2one(
        "account.account",
        string="Proposed Payable Account",
        copy=False,
    )
    receivable_history_id = fields.Many2one(
        "res.partner.account.approval.history",
        copy=False,
    )
    payable_history_id = fields.Many2one(
        "res.partner.account.approval.history",
        copy=False,
    )

    def _is_partner_account_approval(self):
        self.ensure_one()
        return bool(
            self.partner_id
            and (self.approve_receivable_account or self.approve_payable_account)
        )

    def _complete_partner_account_approval(self):
        for request in self.filtered(lambda r: r._is_partner_account_approval()):
            partner = request.partner_id.with_company(request.company_id)
            receivable_old = request.previous_receivable_account_id
            receivable_new = request.proposed_receivable_account_id
            payable_old = request.previous_payable_account_id
            payable_new = request.proposed_payable_account_id

            vals = {"last_account_approval_request_id": request.id}
            if request.approve_receivable_account:
                vals.update({
                    "previous_receivable_account_id": False,
                    "receivable_account_approval_state": "approved",
                })
            if request.approve_payable_account:
                vals.update({
                    "previous_payable_account_id": False,
                    "payable_account_approval_state": "approved",
                })
            partner.with_context(bypass_partner_account_approval=True).write(vals)

            histories = request.receivable_history_id | request.payable_history_id
            histories.write({
                "state": "approved",
                "resolved_by_id": self.env.user.id,
                "resolved_date": fields.Datetime.now(),
            })

            partner._message_log_account_approval_event(
                _("approved"),
                receivable_old=receivable_old if request.approve_receivable_account else False,
                receivable_new=receivable_new if request.approve_receivable_account else False,
                payable_old=payable_old if request.approve_payable_account else False,
                payable_new=payable_new if request.approve_payable_account else False,
                request=request,
            )

    def _revert_partner_account_change(self):
        for request in self.filtered(lambda r: r._is_partner_account_approval()):
            partner = request.partner_id.with_company(request.company_id)

            receivable_old = (
                partner._get_last_approved_account(
                    request.company_id, "receivable"
                )
                if request.approve_receivable_account
                else self.env["account.account"]
            )
            payable_old = (
                partner._get_last_approved_account(
                    request.company_id, "payable"
                )
                if request.approve_payable_account
                else self.env["account.account"]
            )
            receivable_new = request.proposed_receivable_account_id
            payable_new = request.proposed_payable_account_id

            vals = {"last_account_approval_request_id": request.id}
            if request.approve_receivable_account:
                vals.update({
                    "property_account_receivable_id": (
                        receivable_old.id if receivable_old else False
                    ),
                    "previous_receivable_account_id": False,
                    "receivable_account_approval_state": "refused",
                })
            if request.approve_payable_account:
                vals.update({
                    "property_account_payable_id": (
                        payable_old.id if payable_old else False
                    ),
                    "previous_payable_account_id": False,
                    "payable_account_approval_state": "refused",
                })

            partner.with_context(bypass_partner_account_approval=True).write(vals)

            histories = request.receivable_history_id | request.payable_history_id
            histories.write({
                "state": "rejected",
                "resolved_by_id": self.env.user.id,
                "resolved_date": fields.Datetime.now(),
            })

            partner._message_log_account_approval_event(
                _("rejected"),
                receivable_old=receivable_old if request.approve_receivable_account else False,
                receivable_new=receivable_new if request.approve_receivable_account else False,
                payable_old=payable_old if request.approve_payable_account else False,
                payable_new=payable_new if request.approve_payable_account else False,
                request=request,
            )


    def action_approve(self, approver=None):
        res = super().action_approve(approver=approver)
        self.filtered(
            lambda request: request.request_status == "approved"
        )._complete_partner_account_approval()
        return res

    def action_refuse(self, approver=None):
        res = super().action_refuse(approver=approver)
        self._revert_partner_account_change()
        return res
