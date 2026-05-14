# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    account_move_count = fields.Integer(
        compute='_compute_account_move_count',
        string='Journal Entries'
    )

    def _get_related_account_moves(self):
        self.ensure_one()

        AccountMove = self.env['account.move']
        account_moves = AccountMove.browse()

        stock_moves = self.move_ids_without_package | self.move_ids

        # Direct links through stock.move.account_move_ids, if present.
        if 'account_move_ids' in self.env['stock.move']._fields:
            account_moves |= stock_moves.mapped('account_move_ids')

        # Standard Odoo stock valuation link.
        if 'stock.valuation.layer' in self.env and stock_moves:
            valuation_layers = self.env['stock.valuation.layer'].search([
                ('stock_move_id', 'in', stock_moves.ids)
            ])
            account_moves |= valuation_layers.mapped('account_move_id')

        return account_moves.exists()

    @api.depends('move_ids', 'move_ids_without_package')
    def _compute_account_move_count(self):
        for picking in self:
            picking.account_move_count = len(
                picking._get_related_account_moves()
            )

    def action_view_related_account_moves(self):
        self.ensure_one()

        account_moves = self._get_related_account_moves()

        action = {
            'type': 'ir.actions.act_window',
            'name': 'Journal Entries',
            'res_model': 'account.move',
            'target': 'current',
            'domain': [('id', 'in', account_moves.ids)],
            'context': dict(self.env.context),
        }

        if len(account_moves) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': account_moves.id,
                'views': [(False, 'form')],
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'views': [(False, 'tree'), (False, 'form')],
            })

        return action
