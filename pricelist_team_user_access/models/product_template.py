# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.osv import expression


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    accessible_pricelist_item_count = fields.Integer(
        string='Accessible Extra Prices',
        compute='_compute_accessible_pricelist_item_count',
    )

    @api.depends_context('uid')
    def _compute_accessible_pricelist_item_count(self):
        PricelistItem = self.env['product.pricelist.item']
        access_domain = PricelistItem._get_team_user_access_domain()
        for product in self:
            product_domain = [
                '|',
                ('product_tmpl_id', '=', product.id),
                ('product_id', 'in', product.product_variant_ids.ids),
            ]
            product.accessible_pricelist_item_count = PricelistItem.search_count(
                expression.AND([product_domain, access_domain])
                if access_domain else product_domain
            )

    def open_pricelist_rules(self):
        action = super().open_pricelist_rules()
        return self.env['product.pricelist.item']._inject_team_user_access_into_action(action)

    def open_accessible_pricelist_rules(self):
        """Dedicated target for the product smart button.

        Re-inject after calling ``open_pricelist_rules`` so the restriction still
        applies if another addon overrides the original method without calling super.
        """
        action = self.open_pricelist_rules()
        return self.env['product.pricelist.item']._inject_team_user_access_into_action(action)
