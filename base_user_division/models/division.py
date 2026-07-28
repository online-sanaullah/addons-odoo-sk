# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)

class CompanyDivision(models.Model):
    _inherit = 'company.division'
    
    user_ids = fields.Many2many(comodel_name='res.users', relation='rel_user_company_division', column1='division_id', column2='user_id', string='Allowed Divisions', domain="[('company_id', 'in', 'company_ids')]")
    