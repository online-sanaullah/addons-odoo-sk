from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    is_scrap_reversal = fields.Boolean(
        string="Scrap Reversal",
        copy=False,
        readonly=True,
        index=True,
        help="Indicates that this move reverses a completed scrap operation.",
    )

    def _is_returned(self, valued_type):
        """Treat a scrap reversal as an incoming returned move.

        Standard Odoo only identifies customer and supplier returns here.
        A scrap location has inventory usage, so an explicit marker is needed
        to make the valuation journal entry reverse the original scrap entry.
        """
        self.ensure_one()

        if super()._is_returned(valued_type):
            return True

        return bool(
            valued_type == "in"
            and self.is_scrap_reversal
            and self.origin_returned_move_id
            and self.origin_returned_move_id.scrapped
        )

    def _get_dest_account(self, accounts_data):
        """Reuse the account debited by the original scrap move.

        For an incoming returned move Odoo credits ``acc_dest`` and debits the
        stock valuation account. Returning the original scrap move's
        destination account therefore creates the exact opposite accounting
        entry, including a valuation account configured on the scrap location.
        """
        self.ensure_one()

        original_move = self.origin_returned_move_id
        if (
            self.is_scrap_reversal
            and original_move
            and original_move.scrapped
        ):
            return original_move._get_dest_account(accounts_data)

        return super()._get_dest_account(accounts_data)
