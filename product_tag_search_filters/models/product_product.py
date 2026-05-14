# -*- coding: utf-8 -*-

from odoo import models

from .product_search_filter_utils import inject_product_tag_filters


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _ptsf_inject_product_tag_filters(self, arch):
        return inject_product_tag_filters(self.env, arch, 'product_tmpl_id.product_tag_ids')

    def get_view(self, view_id=None, view_type='form', **options):
        res = super().get_view(view_id=view_id, view_type=view_type, **options)
        if view_type == 'search' and res.get('arch'):
            res['arch'] = self._ptsf_inject_product_tag_filters(res['arch'])
        return res

    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super().fields_view_get(
            view_id=view_id,
            view_type=view_type,
            toolbar=toolbar,
            submenu=submenu,
        )
        if view_type == 'search' and res.get('arch'):
            res['arch'] = self._ptsf_inject_product_tag_filters(res['arch'])
        return res
