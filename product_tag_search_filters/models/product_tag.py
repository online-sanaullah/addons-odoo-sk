# -*- coding: utf-8 -*-

from odoo import fields, models


class ProductTag(models.Model):
    _inherit = 'product.tag'

    show_in_product_search_filter = fields.Boolean(
        string='Show as Product Search Filter',
        default=True,
        help=(
            'If enabled, this tag is automatically injected as a search '
            'filter in Product Template and Product Variant search views.'
        ),
    )
