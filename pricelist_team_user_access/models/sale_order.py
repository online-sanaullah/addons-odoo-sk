# -*- coding: utf-8 -*-
from odoo import api, models, _
from odoo.exceptions import AccessError
from odoo.osv import expression


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _skip_pricelist_team_user_sale_order_check(self):
        return bool(
            self.env.su
            or self.env.context.get('skip_pricelist_team_user_access')
            or self.env.user.has_group('base.group_system')
        )

    @api.model
    def _get_sale_order_pricelist_access_domain(self):
        accessible_ids = self.env['product.pricelist']._get_accessible_pricelist_ids(
            admin_bypass=True,
        )
        return [] if accessible_ids is False else [('id', 'in', accessible_ids)]

    @api.model
    def _get_team_user_access_domain(self):
        if self._skip_pricelist_team_user_sale_order_check():
            return []
        accessible_ids = self.env['product.pricelist']._get_accessible_pricelist_ids(
            admin_bypass=True,
        )
        if accessible_ids is False:
            return []
        return [
            '|',
            ('pricelist_id', '=', False),
            ('pricelist_id', 'in', accessible_ids),
        ]

    @api.model
    def _apply_team_user_access_domain(self, domain):
        access_domain = self._get_team_user_access_domain()
        if not access_domain:
            return domain or []
        return expression.AND([domain or [], access_domain])

    @api.model
    def web_search_read(self, domain=None, specification=None, offset=0, limit=None, order=None, count_limit=None):
        domain = self._apply_team_user_access_domain(domain)
        return super().web_search_read(
            domain,
            specification,
            offset=offset,
            limit=limit,
            order=order,
            count_limit=count_limit,
        )

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = self._apply_team_user_access_domain(domain)
        return super().search_read(
            domain=domain,
            fields=fields,
            offset=offset,
            limit=limit,
            order=order,
        )

    def _check_sale_order_pricelist_team_user_access(self, operation):
        if self._skip_pricelist_team_user_sale_order_check():
            return

        Pricelist = self.env['product.pricelist'].with_context(
            skip_pricelist_team_user_access=True,
            active_test=False,
        )
        access_domain = self._get_sale_order_pricelist_access_domain()

        for order in self:
            pricelist = order.pricelist_id
            if not pricelist:
                continue

            allowed = Pricelist.search_count(expression.AND([
                [('id', '=', pricelist.id)],
                access_domain,
            ]))
            if not allowed:
                raise AccessError(_(
                    "You are not allowed to %(operation)s sale order %(order)s because "
                    "the selected pricelist %(pricelist)s is restricted to another sales team/user."
                ) % {
                    'operation': operation,
                    'order': order.display_name,
                    'pricelist': pricelist.display_name,
                })

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._check_sale_order_pricelist_team_user_access(_('create'))
        return records

    def write(self, vals):
        self._check_sale_order_pricelist_team_user_access(_('edit'))
        res = super().write(vals)
        self._check_sale_order_pricelist_team_user_access(_('edit'))
        return res

    def unlink(self):
        self._check_sale_order_pricelist_team_user_access(_('delete'))
        return super().unlink()
