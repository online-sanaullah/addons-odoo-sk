# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval


class ProductPricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    @api.model
    def _skip_team_user_pricelist_filter(self):
        return bool(self.env.su or self.env.context.get('skip_pricelist_team_user_access'))

    @api.model
    def _get_pricelist_item_access_domain(self, user=None):
        accessible_ids = self.env['product.pricelist']._get_accessible_pricelist_ids(
            user=user,
            # Administrators may manage pricelist access, but restricted rule
            # visibility remains subject to the pricelist assignment.
            admin_bypass=False,
        )
        return [] if accessible_ids is False else [('pricelist_id', 'in', accessible_ids)]

    @api.model
    def _get_team_user_access_domain(self):
        return [] if self._skip_team_user_pricelist_filter() else self._get_pricelist_item_access_domain()

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

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = self._apply_team_user_access_domain(args)
        return super().name_search(name=name, args=args, operator=operator, limit=limit)

    @api.model
    def _safe_eval_action_value(self, value, default):
        if not value:
            return default
        if isinstance(value, str):
            try:
                return safe_eval(value, {
                    'uid': self.env.context.get('uid') or self.env.uid,
                    'user': self.env['res.users'].sudo().browse(self.env.context.get('uid') or self.env.uid),
                    'active_id': self.env.context.get('active_id'),
                    'active_ids': self.env.context.get('active_ids'),
                    'active_model': self.env.context.get('active_model'),
                    'context': self.env.context,
                })
            except Exception:
                return default
        return value

    @api.model
    def _inject_team_user_access_into_action(self, action):
        """Inject the rule-access domain into a returned action dictionary."""
        if not isinstance(action, dict) or self._skip_team_user_pricelist_filter():
            return action

        context = self._safe_eval_action_value(action.get('context'), {})
        if not isinstance(context, dict):
            context = {}
        if context.get('pricelist_team_user_access_ui_filter'):
            return action

        access_domain = self._get_pricelist_item_access_domain()
        if not access_domain:
            return action

        action = dict(action)
        domain = self._safe_eval_action_value(action.get('domain'), [])
        if not isinstance(domain, (list, tuple)):
            domain = []
        action['domain'] = expression.AND([list(domain), access_domain])

        context = dict(context)
        context.update({
            'pricelist_team_user_access_ui_filter': True,
            'allowed_pricelist_ids': access_domain[0][2] if access_domain else [],
        })
        action['context'] = context
        return action
