# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)

class CompanyDivision(models.Model):
    _name = 'company.division'
    
    name = fields.Char(string='Name')
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=False, default=lambda self: self.env.company)
    
    @api.constrains('name')
    def _unique_name(self):
        divisions = self.search([('id', 'not in', self.ids)])
        for rec in self:
            duplicate = divisions.filtered(lambda d: d.name.strip().lower() == rec.name.strip().lower())
            if duplicate:
                raise ValidationError(f"Division {duplicate[0].name} already exists!")