# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    """Extends the product.template model to generate QR codes for all
    related product variants."""
    _inherit = 'product.template'
    
    qr = fields.Binary('QRcode', compute='_compute_qrcode', search='_search_barcode')
    
    @api.depends('product_variant_ids.barcode', 'product_variant_ids.qr')
    def _compute_qrcode(self):
        self._compute_template_field_from_variant_field('qr')
        
    #def _set_qrcode(self):
    #    self._set_product_variant_field('qr')

    def generate_qr(self):
        """Generate QR codes for all product variants associated with the
        product template."""
        for rec in self.product_variant_ids:
            return rec.generate_qr()