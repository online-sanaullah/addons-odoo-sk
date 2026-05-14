# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    account_move_id = fields.Many2one(comodel_name='account.move', string='Journal Entry', compute='_get_journal_entry')
    total_value = fields.Monetary(string='Value', currency_field='currency_id', related='account_move_id.amount_total_signed')
    currency_id = fields.Many2one(comodel_name='res.currency', string='Currency', related='account_move_id.currency_id')
    move_direction = fields.Selection(selection=[('out', 'OUT'), ('in', 'IN'), ('internal', 'Internal')], string='Move Direction', compute='_get_move_direction')
    
    def _get_move_direction(self):
        for move_line in self:
            move_direction = 'internal'
            if move_line.picking_code == 'incoming' or move_line.location_id.usage in ('supplier', 'customer', 'inventory', 'transit'):
                move_direction = 'in'
            if move_line.picking_code == 'outgoing' or move_line.location_dest_id.usage in ('supplier', 'customer', 'inventory', 'transit'):
                move_direction = 'out'
            reference_location = self._context.get('reference_location')
            if reference_location:
                location = self.env['stock.location'].browse(reference_location)
                if move_line.location_id.id == location.id or move_line.location_id.id in location.sub_location_ids.ids and not move_line.location_dest_id.id in location.sub_location_ids.ids:
                    move_direction = 'out'
                if move_line.location_dest_id.id == location.id or move_line.location_dest_id.id in location.sub_location_ids.ids and not move_line.location_id.id in location.sub_location_ids.ids:
                    move_direction = 'in'
            reference_warehouse_id = self._context.get('reference_warehouse')
            if reference_warehouse_id:
                if move_line.location_id.warehouse_id and move_line.location_id.warehouse_id.id == reference_warehouse_id:
                    move_direction = 'out'
                if move_line.location_dest_id.warehouse_id and move_line.location_dest_id.warehouse_id.id == reference_warehouse_id:
                    move_direction = 'in'
            move_line.move_direction = move_direction
    
    @api.depends('move_id.account_move_ids')
    def _get_journal_entry(self):
        for move_line in self:
            move_line.account_move_id = self.env['account.move'].search([('stock_move_id', '=', move_line.move_id.id)], limit=1)

    def action_view_journal_entry(self):
        self.ensure_one()
        if not self.account_move_id:
            raise UserError('Journal Entry is missing!')
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "account.action_move_journal_line"
        )
        res = self.env.ref("account.view_move_form", False)
        action["views"] = [(res and res.id or False, "form")]
        action["res_id"] = self.account_move_id.id
        return action
    
    def action_view_picking(self):
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "stock.action_picking_tree_all"
        )
        res = self.env.ref("stock.view_picking_form", False)
        action["views"] = [(res and res.id or False, "form")]
        action["res_id"] = self.picking_id.id
        return action


