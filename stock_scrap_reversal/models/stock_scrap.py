from markupsafe import Markup

from odoo import Command, _, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from odoo.tools.misc import clean_context


class StockScrap(models.Model):
    _inherit = "stock.scrap"

    is_reversed = fields.Boolean(
        string="Reversed",
        copy=False,
        readonly=True,
        tracking=True,
        index=True,
    )
    reversal_move_id = fields.Many2one(
        comodel_name="stock.move",
        string="Reversal Move",
        copy=False,
        readonly=True,
        check_company=True,
        tracking=True,
    )
    reversal_date = fields.Datetime(
        string="Reversal Date",
        copy=False,
        readonly=True,
        tracking=True,
    )
    reversed_by_id = fields.Many2one(
        comodel_name="res.users",
        string="Reversed By",
        copy=False,
        readonly=True,
        tracking=True,
    )

    def _get_original_scrap_move(self):
        self.ensure_one()

        original_moves = self.move_ids.filtered(
            lambda move: (
                move.state == "done"
                and move.scrapped
                and not move.origin_returned_move_id
                and not move.is_scrap_reversal
            )
        )

        if not original_moves:
            raise UserError(
                _(
                    "No completed original stock move could be found for "
                    "scrap operation %s."
                )
                % self.display_name
            )

        if len(original_moves) > 1:
            raise UserError(
                _(
                    "More than one original completed scrap move was found "
                    "for %s. The operation cannot be reversed automatically."
                )
                % self.display_name
            )

        return original_moves

    def _prepare_scrap_reversal_move_lines(self, original_move):
        self.ensure_one()

        move_line_commands = []
        for original_line in original_move.move_line_ids:
            if float_is_zero(
                original_line.quantity,
                precision_rounding=original_line.product_uom_id.rounding,
            ):
                continue

            move_line_commands.append(
                Command.create(
                    {
                        "product_id": original_line.product_id.id,
                        "product_uom_id": original_line.product_uom_id.id,
                        "quantity": original_line.quantity,
                        "location_id": original_line.location_dest_id.id,
                        "location_dest_id": original_line.location_id.id,
                        "lot_id": original_line.lot_id.id,
                        "lot_name": original_line.lot_name,
                        "owner_id": original_line.owner_id.id,
                        # What was the destination package becomes the source
                        # package when moving the stock back.
                        "package_id": original_line.result_package_id.id,
                        # Restore the stock to its original source package.
                        "result_package_id": original_line.package_id.id,
                        "company_id": original_line.company_id.id,
                        "picked": True,
                    }
                )
            )

        if not move_line_commands:
            raise UserError(
                _(
                    "The original scrap move has no completed move-line "
                    "quantity to reverse."
                )
            )

        return move_line_commands

    def _prepare_scrap_reversal_move_values(self, original_move):
        self.ensure_one()

        return {
            "name": _("Reversal of %s") % self.name,
            "origin": _("Reversal of scrap %s") % self.name,
            "company_id": original_move.company_id.id,
            "product_id": original_move.product_id.id,
            "product_uom": original_move.product_uom.id,
            "product_uom_qty": original_move.quantity,
            "state": "draft",
            "date": fields.Datetime.now(),
            "location_id": original_move.location_dest_id.id,
            "location_dest_id": original_move.location_id.id,
            "procure_method": "make_to_stock",
            "picking_id": False,
            "scrap_id": self.id,
            "origin_returned_move_id": original_move.id,
            "is_scrap_reversal": True,
            "picked": True,
            "move_line_ids": self._prepare_scrap_reversal_move_lines(
                original_move
            ),
        }

    def action_reverse_scrap(self):
        self.ensure_one()

        if self.state != "done":
            raise UserError(
                _("Only completed scrap operations can be reversed.")
            )

        # Serialize reversal attempts on the same scrap record. This prevents
        # two users from creating two reversal moves at the same time.
        self.env.cr.execute(
            "SELECT id FROM stock_scrap WHERE id = %s FOR UPDATE",
            [self.id],
        )
        self.invalidate_recordset(
            ["is_reversed", "reversal_move_id", "move_ids"]
        )

        if self.is_reversed:
            raise UserError(
                _("This scrap operation has already been reversed.")
            )

        if self.reversal_move_id and self.reversal_move_id.state != "cancel":
            raise UserError(
                _("A reversal move already exists: %s")
                % self.reversal_move_id.display_name
            )

        original_move = self._get_original_scrap_move()

        existing_reversal = original_move.returned_move_ids.filtered(
            lambda move: (
                move.state != "cancel"
                and move.scrap_id == self
                and move.location_id == original_move.location_dest_id
                and move.location_dest_id == original_move.location_id
            )
        )
        if existing_reversal:
            raise UserError(
                _("The original scrap move has already been reversed by %s.")
                % existing_reversal[0].display_name
            )

        reversal_move = (
            self.with_context(clean_context(self.env.context))
            .env["stock.move"]
            .create(self._prepare_scrap_reversal_move_values(original_move))
        )
        reversal_move.with_context(is_scrap=True)._action_done()

        if reversal_move.state != "done":
            raise UserError(
                _("The reversal stock move could not be completed.")
            )

        reversal_date = fields.Datetime.now()
        self.write(
            {
                "is_reversed": True,
                "reversal_move_id": reversal_move.id,
                "reversal_date": reversal_date,
                "reversed_by_id": self.env.user.id,
            }
        )

        message = Markup(
            _(
                "Scrap operation reversed.<br/>"
                "Original move: <b>{original}</b><br/>"
                "Reversal move: <b>{reversal}</b><br/>"
                "Reversed by: <b>{user}</b>"
            )
        ).format(
            original=original_move.display_name,
            reversal=reversal_move.display_name,
            user=self.env.user.display_name,
        )
        self.message_post(body=message)

        return self.action_view_reversal_move()

    def action_view_reversal_move(self):
        self.ensure_one()

        if not self.reversal_move_id:
            raise UserError(
                _("There is no reversal move for this scrap operation.")
            )

        return {
            "type": "ir.actions.act_window",
            "name": _("Scrap Reversal Move"),
            "res_model": "stock.move",
            "view_mode": "form",
            "res_id": self.reversal_move_id.id,
            "target": "current",
        }
