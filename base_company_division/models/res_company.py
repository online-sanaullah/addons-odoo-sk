# -*- coding: utf-8 -*-

from odoo import api, Command, fields, models, _
from odoo.exceptions import UserError, ValidationError

class ResCompany(models.Model):
    _inherit = 'res.company'

    division_ids = fields.One2many(comodel_name='company.division', inverse_name='company_id', string='Divisions')
            