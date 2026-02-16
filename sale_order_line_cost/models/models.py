# -*- coding: utf-8 -*-

from odoo import models, fields, api
 
class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    company_currency_id = fields.Many2one(comodel_name='res.currency', string='Company Currency', related='company_id.currency_id')
    cogs_journal_entry_ids = fields.Many2many(comodel_name='account.move', string='C.O.G.S. Journal Entry', compute='_cogs_journal_entry')
    cogs_journal_entry_names = fields.Char(string='C.O.G.S. Journal Entry', compute='_cogs_journal_entry')
    cogs_amount = fields.Monetary(string='C.O.G.S.', currency_field='company_currency_id', compute='_cogs_journal_entry')
    sales_journal_entry_ids = fields.Many2many(comodel_name='account.move', string='Sales Journal Entry', compute='_sales_journal_entry')
    sales_journal_entry_names = fields.Char(string='Sales Journal Entry', compute='_sales_journal_entry')
    revenue_amount = fields.Monetary(string='Sales Revenue', currency_field='company_currency_id', compute='_sales_journal_entry')
    team_id = fields.Many2one(comodel_name='crm.team', string='Sales Team', related='order_id.team_id', store=True)
    delivery_date = fields.Date(string='Delivery Date', compute='_cogs_journal_entry', store=True)
    invoice_date = fields.Date(string='Invoice Date', compute='_sales_journal_entry', store=True)
    date_order = fields.Datetime(string='Order Date', related='order_id.date_order', store=True)
    
    @api.depends('order_id.picking_ids.move_ids.sale_line_id')
    def _cogs_journal_entry(self):
        for line in self:
            delivery_date = None
            cogs_journal_entry_names = ''
            cogs_journal_entries = line.order_id.mapped('picking_ids.move_ids').filtered(lambda move:move.sale_line_id.id == line.id).mapped('stock_valuation_layer_ids.account_move_id')
            cogs_journal_entry_names = ', '.join(line.order_id.mapped('picking_ids.move_ids').filtered(lambda move:move.sale_line_id.id == line.id).mapped('stock_valuation_layer_ids.account_move_id.name'))
            line.cogs_journal_entry_ids = cogs_journal_entries.ids
            line.cogs_journal_entry_names = cogs_journal_entry_names
            cogs_amount = 0
            if cogs_journal_entries:
                cogs_amount = sum(cogs_journal_entries.mapped('line_ids').filtered(lambda l: l.account_id.account_type == 'expense_direct_cost').mapped('debit')) - sum(cogs_journal_entries.mapped('line_ids').filtered(lambda l: l.account_id.account_type == 'expense_direct_cost').mapped('credit'))
                delivery_date = min(cogs_journal_entries.mapped('date'))
            line.cogs_amount = cogs_amount
            line.delivery_date = delivery_date
            
    @api.depends('invoice_lines', 'invoice_lines.debit', 'invoice_lines.credit')
    def _sales_journal_entry(self):
        for line in self:
            sales_journal_entry_names = ''
            invoice_date = None
            line.sales_journal_entry_ids = line.mapped('invoice_lines.move_id') or None
            line.sales_journal_entry_names = ', '.join(line.mapped('invoice_lines.move_id.name'))
            line.revenue_amount = sum(line.mapped('invoice_lines.credit')) - sum(line.mapped('invoice_lines.debit'))
            if line.mapped('invoice_lines.move_id.date'):
                invoice_date = min(line.mapped('invoice_lines.move_id.date'))
            line.invoice_date = invoice_date


