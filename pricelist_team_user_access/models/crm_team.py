# -*- coding: utf-8 -*-
from odoo import models


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    def write(self, vals):
        res = super().write(vals)
        watched_fields = {'user_id', 'member_ids', 'team_member_ids'}
        if watched_fields & set(vals):
            pricelists = self.env['product.pricelist'].sudo().search([
                ('access_team_ids', 'in', self.ids),
            ])
            if pricelists:
                pricelists._sync_access_granted_user_ids()
        return res
