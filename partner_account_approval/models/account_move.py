from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    partner_account_approval_warning = fields.Boolean(
        compute="_compute_partner_account_approval_warning",
    )
    partner_account_approval_message = fields.Char(
        compute="_compute_partner_account_approval_warning",
    )


    def _required_partner_account_sides(self):
        self.ensure_one()
        receivable = self.move_type in ("out_invoice", "out_refund", "out_receipt")
        payable = self.move_type in ("in_invoice", "in_refund", "in_receipt")
        if self.move_type == "entry":
            receivable = any(
                line.partner_id and line.account_id.account_type == "asset_receivable"
                for line in self.line_ids
            )
            payable = any(
                line.partner_id and line.account_id.account_type == "liability_payable"
                for line in self.line_ids
            )
        return receivable, payable

    def _approval_partners(self):
        self.ensure_one()
        if self.move_type == "entry":
            return self.line_ids.filtered(
                lambda line: line.partner_id
                and line.account_id.account_type in ("asset_receivable", "liability_payable")
            ).mapped("partner_id")
        return self.partner_id

    def _ensure_partner_account_requests(self):
        for move in self:
            receivable, payable = move._required_partner_account_sides()
            for partner in move._approval_partners():
                partner._ensure_account_approval_request(
                    move.company_id,
                    receivable=receivable,
                    payable=payable,
                    source=move,
                )

    def _get_pending_partner_account_sides(self):
        self.ensure_one()
        blocked = []

        if self.move_type == "entry":
            for line in self.line_ids.filtered(
                lambda record: record.partner_id
                and record.account_id.account_type
                in ("asset_receivable", "liability_payable")
            ):
                side = (
                    "receivable"
                    if line.account_id.account_type == "asset_receivable"
                    else "payable"
                )
                partner = line.partner_id.with_company(self.company_id)
                if partner._is_account_blocked_by_pending_approval(
                    self.company_id,
                    line.account_id,
                    side,
                ):
                    blocked.append(_(side))
            return sorted(set(blocked))

        if not self.partner_id:
            return blocked

        partner = self.partner_id.with_company(self.company_id)
        if self.move_type in ("out_invoice", "out_refund", "out_receipt"):
            side = "receivable"
            account_type = "asset_receivable"
            fallback_account = partner.property_account_receivable_id
        elif self.move_type in ("in_invoice", "in_refund", "in_receipt"):
            side = "payable"
            account_type = "liability_payable"
            fallback_account = partner.property_account_payable_id
        else:
            return blocked

        account_lines = self.line_ids.filtered(
            lambda line: line.account_id.account_type == account_type
        )
        account = account_lines[:1].account_id if account_lines else fallback_account

        if partner._is_account_blocked_by_pending_approval(
            self.company_id,
            account,
            side,
        ):
            blocked.append(_(side))

        return sorted(set(blocked))

    @api.depends(
        "partner_id",
        "move_type",
        "line_ids.partner_id",
        "line_ids.account_id",
        "company_id",
        "partner_id.receivable_account_approval_state",
        "partner_id.payable_account_approval_state",
    )
    def _compute_partner_account_approval_warning(self):
        for move in self:
            sides = move._get_pending_partner_account_sides()
            move.partner_account_approval_warning = bool(sides)
            move.partner_account_approval_message = (
                _("The partner's %s account approval is pending. You may save this draft, but it cannot be posted until the approval is approved, rejected, or cancelled.")
                % " / ".join(sides)
                if sides else False
            )

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        moves._ensure_partner_account_requests()
        return moves

    def write(self, vals):
        res = super().write(vals)
        if {"partner_id", "move_type", "line_ids"}.intersection(vals):
            self._ensure_partner_account_requests()
        return res

    def action_post(self):
        self._ensure_partner_account_requests()

        blocked_messages = []
        for move in self:
            if move.move_type == "entry":
                relevant_lines = move.line_ids.filtered(
                    lambda line: line.partner_id
                    and line.account_id.account_type
                    in ("asset_receivable", "liability_payable")
                )
                for line in relevant_lines:
                    side = (
                        "receivable"
                        if line.account_id.account_type == "asset_receivable"
                        else "payable"
                    )
                    partner = line.partner_id.with_company(move.company_id)
                    if partner._is_account_blocked_by_pending_approval(
                        move.company_id,
                        line.account_id,
                        side,
                    ):
                        blocked_messages.append(
                            _("%(partner)s — %(side)s account %(account)s")
                            % {
                                "partner": partner.display_name,
                                "side": side,
                                "account": line.account_id.display_name,
                            }
                        )
            else:
                for side in move._get_pending_partner_account_sides():
                    blocked_messages.append(
                        _("%(partner)s — %(side)s account")
                        % {
                            "partner": move.partner_id.display_name,
                            "side": side,
                        }
                    )

        if blocked_messages:
            raise UserError(
                _(
                    "Posting is blocked because partner account approval is pending.\n\n"
                    "%s\n\nResolve the approval request by approving, rejecting, "
                    "or cancelling it before posting."
                )
                % "\n".join(sorted(set(blocked_messages)))
            )

        return super().action_post()
