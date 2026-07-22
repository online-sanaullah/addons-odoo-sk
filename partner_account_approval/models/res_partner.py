from odoo import _, api, fields, models
from odoo.exceptions import UserError
from markupsafe import Markup, escape


class ResPartner(models.Model):
    _inherit = "res.partner"

    previous_receivable_account_id = fields.Many2one(
        "account.account",
        string="Previous Receivable Account",
        company_dependent=True,
        domain=[("account_type", "=", "asset_receivable")],
        copy=False,
        readonly=True,
    )
    previous_payable_account_id = fields.Many2one(
        "account.account",
        string="Previous Payable Account",
        company_dependent=True,
        domain=[("account_type", "=", "liability_payable")],
        copy=False,
        readonly=True,
    )
    receivable_account_approval_state = fields.Selection(
        [
            ("none", "No Pending Change"),
            ("waiting_transaction", "Waiting for Transaction"),
            ("pending", "Pending Approval"),
            ("approved", "Approved"),
            ("refused", "Rejected"),
        ],
        default="none",
        copy=False,
        string="Receivable Approval Status",
    )
    payable_account_approval_state = fields.Selection(
        [
            ("none", "No Pending Change"),
            ("waiting_transaction", "Waiting for Transaction"),
            ("pending", "Pending Approval"),
            ("approved", "Approved"),
            ("refused", "Rejected"),
        ],
        default="none",
        copy=False,
        string="Payable Approval Status",
    )
    last_account_approval_request_id = fields.Many2one(
        "approval.request",
        string="Last Account Approval Request",
        copy=False,
    )
    account_approval_request_count = fields.Integer(
        compute="_compute_account_approval_request_count",
    )
    account_approval_history_count = fields.Integer(
        compute="_compute_account_approval_history_count",
    )
    show_account_approval_warning = fields.Boolean(
        compute="_compute_show_account_approval_warning",
    )
    has_open_account_approval_request = fields.Boolean(
        compute="_compute_has_open_account_approval_request",
    )
    can_cancel_account_approval_request = fields.Boolean(
        compute="_compute_can_cancel_account_approval_request",
    )
    receivable_account_approval_enabled = fields.Boolean(
        compute="_compute_account_approval_configuration",
    )
    payable_account_approval_enabled = fields.Boolean(
        compute="_compute_account_approval_configuration",
    )

    def _compute_account_approval_configuration(self):
        company = self.env.company
        for partner in self:
            partner.receivable_account_approval_enabled = bool(
                company.enforce_partner_receivable_account_approval
            )
            partner.payable_account_approval_enabled = bool(
                company.enforce_partner_payable_account_approval
            )

    @api.depends(
        "previous_receivable_account_id",
        "previous_payable_account_id",
        "receivable_account_approval_state",
        "payable_account_approval_state",
    )
    def _compute_show_account_approval_warning(self):
        company = self.env.company
        for partner in self:
            partner.show_account_approval_warning = bool(
                (
                    company.enforce_partner_receivable_account_approval
                    and partner.property_account_receivable_id
                    and partner.receivable_account_approval_state in ("waiting_transaction", "pending")
                )
                or (
                    company.enforce_partner_payable_account_approval
                    and partner.property_account_payable_id
                    and partner.payable_account_approval_state in ("waiting_transaction", "pending")
                )
            )

    def _compute_has_open_account_approval_request(self):
        request_model = self.env["approval.request"]
        for partner in self:
            partner.has_open_account_approval_request = bool(
                request_model.search_count([
                    ("partner_id", "=", partner.id),
                    ("company_id", "=", self.env.company.id),
                    ("request_status", "in", ["new", "pending"]),
                    "|",
                    ("approve_receivable_account", "=", True),
                    ("approve_payable_account", "=", True),
                ])
            )

    def _compute_can_cancel_account_approval_request(self):
        company = self.env.company
        for partner in self:
            request = partner._get_open_account_approval_requests(company)[:1]
            can_cancel = bool(request)
            if request and request.approve_receivable_account:
                can_cancel = can_cancel and bool(
                    partner._get_last_approved_account(company, "receivable")
                )
            if request and request.approve_payable_account:
                can_cancel = can_cancel and bool(
                    partner._get_last_approved_account(company, "payable")
                )
            partner.can_cancel_account_approval_request = can_cancel


    def _compute_account_approval_history_count(self):
        grouped = self.env["res.partner.account.approval.history"].read_group(
            [("partner_id", "in", self.ids)],
            ["partner_id"],
            ["partner_id"],
        )
        counts = {
            item["partner_id"][0]: item["partner_id_count"]
            for item in grouped
            if item.get("partner_id")
        }
        for partner in self:
            partner.account_approval_history_count = counts.get(partner.id, 0)

    def action_view_account_approval_history(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Account Approval History"),
            "res_model": "res.partner.account.approval.history",
            "view_mode": "tree,form",
            "domain": [("partner_id", "=", self.id)],
            "context": {"default_partner_id": self.id},
        }

    def _get_last_approved_history(self, company, side):
        self.ensure_one()
        return self.env["res.partner.account.approval.history"].search(
            [
                ("partner_id", "=", self.id),
                ("company_id", "=", company.id),
                ("account_side", "=", side),
                ("state", "in", ["approved", "baseline"]),
            ],
            order="id desc",
            limit=1,
        )

    def _get_last_approved_account(self, company, side):
        history = self._get_last_approved_history(company, side)
        return history.proposed_account_id if history else self.env["account.account"]

    def _ensure_account_baseline_history(self, company, side, account):
        self.ensure_one()
        if not account or self._get_last_approved_history(company, side):
            return self.env["res.partner.account.approval.history"]
        return self.env["res.partner.account.approval.history"].create(
            {
                "partner_id": self.id,
                "company_id": company.id,
                "account_side": side,
                "previous_account_id": False,
                "proposed_account_id": account.id,
                "state": "baseline",
                "resolved_by_id": self.env.user.id,
                "resolved_date": fields.Datetime.now(),
            }
        )

    def _compute_account_approval_request_count(self):
        grouped = self.env["approval.request"].read_group(
            [("partner_id", "in", self.ids)],
            ["partner_id"],
            ["partner_id"],
        )
        counts = {
            item["partner_id"][0]: item["partner_id_count"]
            for item in grouped if item.get("partner_id")
        }
        for partner in self:
            partner.account_approval_request_count = counts.get(partner.id, 0)

    def init(self):
        self.env.cr.execute(
            """
            UPDATE res_partner
               SET receivable_account_approval_state = 'pending'
             WHERE receivable_account_approval_state = 'changed'
            """
        )
        self.env.cr.execute(
            """
            UPDATE res_partner
               SET payable_account_approval_state = 'pending'
             WHERE payable_account_approval_state = 'changed'
            """
        )

    def _get_account_approval_trigger(self, company, side):
        self.ensure_one()
        return (
            company.receivable_account_approval_trigger
            if side == "receivable"
            else company.payable_account_approval_trigger
        )

    def _account_change_requires_immediate_request(
        self, company, side, is_new_partner=False
    ):
        self.ensure_one()
        trigger = self._get_account_approval_trigger(company, side)
        if trigger == "immediate":
            return True
        if trigger == "next_transaction_after_change":
            return False
        if trigger == "first_transaction_initial_then_immediate":
            return False if is_new_partner else bool(
                self._get_last_approved_history(company, side)
            )
        return True

    def _prepare_account_approval_reason(
        self, company, receivable=False, payable=False, source=None
    ):
        self.ensure_one()
        partner = self.with_company(company)
        lines = [
            _("Partner: %s") % partner.display_name,
            _("Company: %s") % company.display_name,
        ]
        if receivable:
            previous = partner._get_last_approved_account(company, "receivable")
            lines.append(
                _("Receivable account: %s → %s")
                % (
                    previous.display_name if previous else "-",
                    partner.property_account_receivable_id.display_name or "-",
                )
            )
        if payable:
            previous = partner._get_last_approved_account(company, "payable")
            lines.append(
                _("Payable account: %s → %s")
                % (
                    previous.display_name if previous else "-",
                    partner.property_account_payable_id.display_name or "-",
                )
            )
        if source:
            lines.append(_("Triggered by: %s") % source.display_name)
        return "\n".join(lines)

    def _is_account_blocked_by_pending_approval(
        self,
        company,
        account,
        side,
    ):
        self.ensure_one()
        partner = self.with_company(company)

        if side == "receivable":
            if not company.enforce_partner_receivable_account_approval:
                return False
            if partner.receivable_account_approval_state != "pending":
                return False
            pending_account = partner.property_account_receivable_id
        elif side == "payable":
            if not company.enforce_partner_payable_account_approval:
                return False
            if partner.payable_account_approval_state != "pending":
                return False
            pending_account = partner.property_account_payable_id
        else:
            return False

        if company.partner_account_approval_blocking_scope == "all_partner_accounts":
            return True

        return bool(account and pending_account and account == pending_account)

    def action_view_account_approval_requests(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Account Approval Requests"),
            "res_model": "approval.request",
            "view_mode": "tree,form",
            "domain": [("partner_id", "=", self.id)],
            "context": {"default_partner_id": self.id},
        }

    def _get_partner_account_approval_category(self, company):
        category = company.partner_account_approval_category_id
        if not category:
            category = self.env.ref(
                "partner_account_approval.approval_category_partner_account_change",
                raise_if_not_found=False,
            )
        if not category:
            raise UserError(
                _("Please configure a Partner Account Approval Category on company %s.")
                % company.display_name
            )
        return category

    def _get_open_account_approval_requests(self, company):
        self.ensure_one()
        return self.env["approval.request"].search([
            ("partner_id", "=", self.id),
            ("company_id", "=", company.id),
            ("request_status", "in", ["new", "pending"]),
            "|",
            ("approve_receivable_account", "=", True),
            ("approve_payable_account", "=", True),
        ])

    def _ensure_account_approval_request(
        self, company, receivable=False, payable=False, source=None
    ):
        self.ensure_one()
        partner = self.with_company(company)

        receivable = bool(
            receivable
            and company.enforce_partner_receivable_account_approval
            and partner.property_account_receivable_id
            and partner.receivable_account_approval_state in ("waiting_transaction", "pending")
        )
        payable = bool(
            payable
            and company.enforce_partner_payable_account_approval
            and partner.property_account_payable_id
            and partner.payable_account_approval_state in ("waiting_transaction", "pending")
        )
        if not receivable and not payable:
            return self.env["approval.request"]

        existing = partner._get_open_account_approval_requests(company).filtered(
            lambda req: (
                (not receivable or req.approve_receivable_account)
                and (not payable or req.approve_payable_account)
            )
        )
        if existing:
            request = existing[:1]
            update_vals = {}
            if receivable:
                update_vals.update({
                    "approve_receivable_account": True,
                    "previous_receivable_account_id":
                        partner._get_last_approved_account(company, "receivable").id,
                    "proposed_receivable_account_id":
                        partner.property_account_receivable_id.id,
                })
            if payable:
                update_vals.update({
                    "approve_payable_account": True,
                    "previous_payable_account_id":
                        partner._get_last_approved_account(company, "payable").id,
                    "proposed_payable_account_id":
                        partner.property_account_payable_id.id,
                })
            update_vals["reason"] = partner._prepare_account_approval_reason(
                company,
                receivable=receivable,
                payable=payable,
                source=source,
            )
            if update_vals:
                request.write(update_vals)
                if receivable and request.receivable_history_id:
                    request.receivable_history_id.write({
                        "previous_account_id": request.previous_receivable_account_id.id,
                        "proposed_account_id": request.proposed_receivable_account_id.id,
                    })
                if payable and request.payable_history_id:
                    request.payable_history_id.write({
                        "previous_account_id": request.previous_payable_account_id.id,
                        "proposed_account_id": request.proposed_payable_account_id.id,
                    })
            state_vals = {"last_account_approval_request_id": request.id}
            if receivable:
                state_vals["receivable_account_approval_state"] = "pending"
            if payable:
                state_vals["payable_account_approval_state"] = "pending"
            partner.with_context(
                bypass_partner_account_approval=True
            ).write(state_vals)
            return request

        category = partner._get_partner_account_approval_category(company)
        reason = partner._prepare_account_approval_reason(
            company,
            receivable=receivable,
            payable=payable,
            source=source,
        )

        request_vals = {
            "name": _("Partner account approval - %s") % partner.display_name,
            "request_owner_id": self.env.user.id,
            "category_id": category.id,
            "reason": reason,
            "partner_id": partner.id,
            "company_id": company.id,
            "approve_receivable_account": receivable,
            "approve_payable_account": payable,
            "previous_receivable_account_id": (
                partner._get_last_approved_account(company, "receivable").id
                if receivable
                else False
            ),
            "previous_payable_account_id": (
                partner._get_last_approved_account(company, "payable").id
                if payable
                else False
            ),
            "proposed_receivable_account_id": (
                partner.property_account_receivable_id.id if receivable else False
            ),
            "proposed_payable_account_id": (
                partner.property_account_payable_id.id if payable else False
            ),
        }
        request = self.env["approval.request"].create(request_vals)

        history_model = self.env["res.partner.account.approval.history"]
        request_history_vals = {}
        if receivable:
            history = history_model.create(
                {
                    "partner_id": partner.id,
                    "company_id": company.id,
                    "account_side": "receivable",
                    "previous_account_id": request.previous_receivable_account_id.id,
                    "proposed_account_id": request.proposed_receivable_account_id.id,
                    "approval_request_id": request.id,
                    "state": "pending",
                }
            )
            request_history_vals["receivable_history_id"] = history.id
        if payable:
            history = history_model.create(
                {
                    "partner_id": partner.id,
                    "company_id": company.id,
                    "account_side": "payable",
                    "previous_account_id": request.previous_payable_account_id.id,
                    "proposed_account_id": request.proposed_payable_account_id.id,
                    "approval_request_id": request.id,
                    "state": "pending",
                }
            )
            request_history_vals["payable_history_id"] = history.id
        if request_history_vals:
            request.write(request_history_vals)

        if hasattr(request, "action_confirm"):
            request.action_confirm()

        vals = {"last_account_approval_request_id": request.id}
        if receivable:
            vals["receivable_account_approval_state"] = "pending"
        if payable:
            vals["payable_account_approval_state"] = "pending"
        partner.with_context(bypass_partner_account_approval=True).write(vals)

        partner._message_log_account_approval_event(
            _("requested and pending approval"),
            receivable_old=(
                partner.previous_receivable_account_id if receivable else False
            ),
            receivable_new=(
                partner.property_account_receivable_id if receivable else False
            ),
            payable_old=(
                partner.previous_payable_account_id if payable else False
            ),
            payable_new=(
                partner.property_account_payable_id if payable else False
            ),
            request=request,
        )
        return request

    @api.model_create_multi
    def create(self, vals_list):
        company = self.env.company
        prepared_vals = []
        requested_accounts = []

        for vals in vals_list:
            create_vals = dict(vals)
            requested = {}
            if (
                company.enforce_partner_receivable_account_approval
                and "property_account_receivable_id" in create_vals
            ):
                requested["receivable_id"] = create_vals.pop(
                    "property_account_receivable_id"
                )
            if (
                company.enforce_partner_payable_account_approval
                and "property_account_payable_id" in create_vals
            ):
                requested["payable_id"] = create_vals.pop(
                    "property_account_payable_id"
                )
            prepared_vals.append(create_vals)
            requested_accounts.append(requested)

        partners = super().create(prepared_vals)

        for partner, requested in zip(partners, requested_accounts):
            record = partner.with_company(company)
            update_vals = {}
            immediate_receivable = False
            immediate_payable = False

            receivable_id = requested.get("receivable_id")
            if receivable_id:
                account = self.env["account.account"].browse(receivable_id)
                if account.account_type != "asset_receivable":
                    raise UserError(_("The receivable account must be of type Receivable."))
                immediate_receivable = record._account_change_requires_immediate_request(
                    company, "receivable", is_new_partner=True
                )
                update_vals.update({
                    "previous_receivable_account_id": False,
                    "property_account_receivable_id": account.id,
                    "receivable_account_approval_state":
                        "pending" if immediate_receivable else "waiting_transaction",
                })

            payable_id = requested.get("payable_id")
            if payable_id:
                account = self.env["account.account"].browse(payable_id)
                if account.account_type != "liability_payable":
                    raise UserError(_("The payable account must be of type Payable."))
                immediate_payable = record._account_change_requires_immediate_request(
                    company, "payable", is_new_partner=True
                )
                update_vals.update({
                    "previous_payable_account_id": False,
                    "property_account_payable_id": account.id,
                    "payable_account_approval_state":
                        "pending" if immediate_payable else "waiting_transaction",
                })

            if update_vals:
                record.with_context(
                    bypass_partner_account_approval=True
                ).write(update_vals)

            if immediate_receivable or immediate_payable:
                record._ensure_account_approval_request(
                    company,
                    receivable=immediate_receivable,
                    payable=immediate_payable,
                )

        return partners

    def write(self, vals):
        if self.env.context.get("bypass_partner_account_approval"):
            return super().write(vals)

        account_fields = {
            "property_account_receivable_id",
            "property_account_payable_id",
        }
        if not account_fields.intersection(vals):
            return super().write(vals)

        company = self.env.company

        for partner in self:
            record = partner.with_company(company)
            open_request = record._get_open_account_approval_requests(company)[:1]
            state_vals = {}
            request_receivable = False
            request_payable = False
            corrected_receivable = False
            corrected_payable = False

            if (
                "property_account_receivable_id" in vals
                and company.enforce_partner_receivable_account_approval
            ):
                account = self.env["account.account"].browse(
                    vals.get("property_account_receivable_id")
                )
                if account and account.account_type != "asset_receivable":
                    raise UserError(_("The receivable account must be of type Receivable."))
                corrected_receivable = account != record.property_account_receivable_id
                if corrected_receivable:
                    record._ensure_account_baseline_history(
                        company, "receivable", record.property_account_receivable_id
                    )
                    immediate = bool(
                        open_request and open_request.approve_receivable_account
                    ) or record._account_change_requires_immediate_request(
                        company, "receivable"
                    )
                    state_vals.update({
                        "previous_receivable_account_id":
                            record._get_last_approved_account(company, "receivable").id,
                        "receivable_account_approval_state":
                            "pending" if immediate else "waiting_transaction",
                    })
                    request_receivable = immediate

            if (
                "property_account_payable_id" in vals
                and company.enforce_partner_payable_account_approval
            ):
                account = self.env["account.account"].browse(
                    vals.get("property_account_payable_id")
                )
                if account and account.account_type != "liability_payable":
                    raise UserError(_("The payable account must be of type Payable."))
                corrected_payable = account != record.property_account_payable_id
                if corrected_payable:
                    record._ensure_account_baseline_history(
                        company, "payable", record.property_account_payable_id
                    )
                    immediate = bool(
                        open_request and open_request.approve_payable_account
                    ) or record._account_change_requires_immediate_request(
                        company, "payable"
                    )
                    state_vals.update({
                        "previous_payable_account_id":
                            record._get_last_approved_account(company, "payable").id,
                        "payable_account_approval_state":
                            "pending" if immediate else "waiting_transaction",
                    })
                    request_payable = immediate

            super(ResPartner, partner).write(vals)

            if state_vals:
                record.with_context(
                    bypass_partner_account_approval=True
                ).write(state_vals)

            if request_receivable or request_payable:
                request = record._ensure_account_approval_request(
                    company,
                    receivable=request_receivable,
                    payable=request_payable,
                )
                if open_request and request:
                    record._message_log_account_approval_event(
                        _("updated while pending approval"),
                        receivable_old=(
                            open_request.previous_receivable_account_id
                            if corrected_receivable else False
                        ),
                        receivable_new=(
                            record.property_account_receivable_id
                            if corrected_receivable else False
                        ),
                        payable_old=(
                            open_request.previous_payable_account_id
                            if corrected_payable else False
                        ),
                        payable_new=(
                            record.property_account_payable_id
                            if corrected_payable else False
                        ),
                        request=request,
                    )

        return True

    def _message_log_account_approval_event(
        self,
        outcome,
        receivable_old=False,
        receivable_new=False,
        payable_old=False,
        payable_new=False,
        request=False,
    ):
        self.ensure_one()

        body = Markup("<strong>%s</strong>") % escape(
            _("Partner account approval %s") % outcome
        )

        if request:
            body += Markup("<br/><strong>%s</strong> %s") % (
                escape(_("Approval Request:")),
                escape(request.display_name),
            )

        if receivable_old or receivable_new:
            body += Markup("<br/><strong>%s</strong> %s &#8594; %s") % (
                escape(_("Receivable Account:")),
                escape(
                    receivable_old.display_name if receivable_old else "-"
                ),
                escape(
                    receivable_new.display_name if receivable_new else "-"
                ),
            )

        if payable_old or payable_new:
            body += Markup("<br/><strong>%s</strong> %s &#8594; %s") % (
                escape(_("Payable Account:")),
                escape(payable_old.display_name if payable_old else "-"),
                escape(payable_new.display_name if payable_new else "-"),
            )

        self.message_post(body=body)


    def action_cancel_partner_account_approval(self):
        for partner in self:
            company = self.env.company
            partner_company = partner.with_company(company)
            requests = partner._get_open_account_approval_requests(company)
            request = requests[:1]

            if not request:
                raise UserError(_("There is no open account approval request to cancel."))

            receivable_old = (
                partner._get_last_approved_account(company, "receivable")
                if request.approve_receivable_account
                else self.env["account.account"]
            )
            payable_old = (
                partner._get_last_approved_account(company, "payable")
                if request.approve_payable_account
                else self.env["account.account"]
            )
            receivable_new = request.proposed_receivable_account_id
            payable_new = request.proposed_payable_account_id

            if request.approve_receivable_account and not receivable_old:
                raise UserError(
                    _(
                        "This receivable account approval cannot be cancelled because "
                        "the partner has no previously approved receivable account."
                    )
                )
            if request.approve_payable_account and not payable_old:
                raise UserError(
                    _(
                        "This payable account approval cannot be cancelled because "
                        "the partner has no previously approved payable account."
                    )
                )

            revert_vals = {"last_account_approval_request_id": False}
            if request.approve_receivable_account:
                revert_vals.update({
                    "property_account_receivable_id": receivable_old.id,
                    "previous_receivable_account_id": False,
                    "receivable_account_approval_state": "none",
                })
            if request.approve_payable_account:
                revert_vals.update({
                    "property_account_payable_id": payable_old.id,
                    "previous_payable_account_id": False,
                    "payable_account_approval_state": "none",
                })

            partner_company.with_context(
                bypass_partner_account_approval=True
            ).write(revert_vals)

            now = fields.Datetime.now()
            histories = (
                request.receivable_history_id
                | request.payable_history_id
            )
            histories.write({
                "state": "cancelled",
                "resolved_by_id": self.env.user.id,
                "resolved_date": now,
            })

            partner_company._message_log_account_approval_event(
                _("cancelled"),
                receivable_old=receivable_old if request.approve_receivable_account else False,
                receivable_new=receivable_new if request.approve_receivable_account else False,
                payable_old=payable_old if request.approve_payable_account else False,
                payable_new=payable_new if request.approve_payable_account else False,
                request=request,
            )

            for approval_request in requests:
                if hasattr(approval_request, "action_cancel"):
                    approval_request.action_cancel()
                elif hasattr(approval_request, "action_withdraw"):
                    approval_request.action_withdraw()
                else:
                    approval_request.unlink()

        return {"type": "ir.actions.client", "tag": "reload"}

