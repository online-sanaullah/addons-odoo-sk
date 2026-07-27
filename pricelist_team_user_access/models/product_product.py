# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.osv import expression


class ProductProduct(models.Model):
    _inherit = 'product.product'

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
                '&',
                ('product_tmpl_id', '=', product.product_tmpl_id.id),
                ('applied_on', '=', '1_product'),
                '&',
                ('product_id', '=', product.id),
                ('applied_on', '=', '0_product_variant'),
            ]
            product.accessible_pricelist_item_count = PricelistItem.search_count(
                expression.AND([product_domain, access_domain])
                if access_domain else product_domain
            )

    def open_pricelist_rules(self):
        action = super().open_pricelist_rules()
        return self.env['product.pricelist.item']._inject_team_user_access_into_action(action)

    def open_accessible_pricelist_rules(self):
        action = self.open_pricelist_rules()
        return self.env['product.pricelist.item']._inject_team_user_access_into_action(action)
