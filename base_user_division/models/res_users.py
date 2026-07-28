# -*- coding: utf-8 -*-

from odoo import api, Command, fields, models, _
from odoo.exceptions import UserError, ValidationError

class Users(models.Model):
    _inherit = 'res.users'

    division_ids = fields.Many2many(comodel_name='company.division', relation='rel_user_company_division', column1='user_id', column2='division_id', string='Allowed Divisions', domain="[('company_id', 'in', company_ids)]")
            