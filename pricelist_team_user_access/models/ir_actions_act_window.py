# -*- coding: utf-8 -*-
from odoo import models
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval


class IrActionsActWindow(models.Model):
    _inherit = 'ir.actions.act_window'

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

    def _inject_pricelist_team_user_filter(self, action):
        """Inject runtime filters into executable window action dictionaries only.

        Keep ir.actions.act_window.read() untouched.  Odoo.sh and Odoo's menu/action
        crawler tests read action records directly and expect normal database-shaped
        values.  Returning dynamically modified text fields from read() can make tests
        treat the action definition itself as changed/invalid.  The actual executed
        action dictionary still receives the domain/context here through
        _get_action_dict(), while model-level web_search_read/search_read/name_search
        continue to hide restricted records in normal views.
        """
        if not isinstance(action, dict):
            return action

        res_model = action.get('res_model')
        if res_model not in ('product.pricelist', 'product.pricelist.item', 'sale.order', 'sale.order.line'):
            return action

        try:
            Model = self.env[res_model]
        except KeyError:
            return action

        if not hasattr(Model, '_get_team_user_access_domain'):
            return action

        access_domain = Model._get_team_user_access_domain()
        if not access_domain:
            return action

        action = dict(action)

        domain = self._safe_eval_action_value(action.get('domain'), [])
        if not isinstance(domain, (list, tuple)):
            domain = []
        action['domain'] = expression.AND([list(domain), access_domain])

        # UI-level form protection only. This is not a record rule and it does
        # not write anything to the action record. It just avoids opening a
        # hidden pricelist/rule/order directly from a window action res_id.
        res_id = action.get('res_id')
        if res_id:
            matching_count = Model.with_context(active_test=False).search_count(
                expression.AND([[('id', '=', res_id)], access_domain])
            )
            if not matching_count:
                action['res_id'] = False
                action['domain'] = [('id', '=', 0)]

        context = self._safe_eval_action_value(action.get('context'), {})
        if not isinstance(context, dict):
            context = {}
        context = dict(context)
        context['pricelist_team_user_access_ui_filter'] = True
        action['context'] = context
        return action

    def _get_action_dict(self):
        action = super()._get_action_dict()
        return self._inject_pricelist_team_user_filter(action)
