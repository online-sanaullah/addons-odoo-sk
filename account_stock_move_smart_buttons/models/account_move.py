# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    stock_move_count = fields.Integer(
        compute='_compute_stock_links_count',
        string='Stock Moves'
    )
    stock_picking_count = fields.Integer(
        compute='_compute_stock_links_count',
        string='Stock Pickings'
    )

    def _get_related_stock_moves(self):
        self.ensure_one()

        StockMove = self.env['stock.move']
        stock_moves = StockMove.browse()

        # Direct links through stock.move.account_move_ids, if present.
        if 'account_move_ids' in StockMove._fields:
            stock_moves |= StockMove.search([
                ('account_move_ids', 'in', self.id)
            ])

        # Standard Odoo stock valuation link.
        if 'stock.valuation.layer' in self.env:
            valuation_layers = self.env['stock.valuation.layer'].search([
                ('account_move_id', '=', self.id)
            ])
            stock_moves |= valuation_layers.mapped('stock_move_id')

        return stock_moves.exists()

    def _get_related_stock_pickings(self):
        self.ensure_one()
        stock_moves = self._get_related_stock_moves()
        return stock_moves.mapped('picking_id').exists()

    @api.depends('line_ids')
    def _compute_stock_links_count(self):
        for move in self:
            stock_moves = move._get_related_stock_moves()
            move.stock_move_count = len(stock_moves)
            move.stock_picking_count = len(stock_moves.mapped('picking_id').exists())

    def action_view_related_stock_moves(self):
        self.ensure_one()

        stock_moves = self._get_related_stock_moves()

        action = {
            'type': 'ir.actions.act_window',
            'name': 'Stock Moves',
            'res_model': 'stock.move',
            'target': 'current',
            'domain': [('id', 'in', stock_moves.ids)],
            'context': dict(self.env.context),
        }

        if len(stock_moves) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': stock_moves.id,
                'views': [(False, 'form')],
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'views': [(False, 'tree'), (False, 'form')],
            })

        return action

    def action_view_related_stock_pickings(self):
        self.ensure_one()

        pickings = self._get_related_stock_pickings()

        action = {
            'type': 'ir.actions.act_window',
            'name': 'Stock Pickings',
            'res_model': 'stock.picking',
            'target': 'current',
            'domain': [('id', 'in', pickings.ids)],
            'context': dict(self.env.context),
        }

        if len(pickings) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': pickings.id,
                'views': [(False, 'form')],
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'views': [(False, 'tree'), (False, 'form')],
            })

        return action
