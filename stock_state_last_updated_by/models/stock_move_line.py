from odoo import api, fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    state_last_updated_by_id = fields.Many2one(
        "res.users",
        string="State Updated By",
        compute="_compute_state_last_tracking_info",
        readonly=True,
        store=False,
    )
    state_last_updated_on = fields.Datetime(
        string="State Updated On",
        compute="_compute_state_last_tracking_info",
        readonly=True,
        store=False,
    )
    state_last_updated_source = fields.Char(
        string="State Updated Source",
        compute="_compute_state_last_tracking_info",
        readonly=True,
        store=False,
    )

    @api.depends(
        "state",
        "create_uid",
        "create_date",
        "write_uid",
        "write_date",
        "move_id.state",
        "move_id.write_uid",
        "move_id.write_date",
        "picking_id.state",
    )
    def _compute_state_last_tracking_info(self):
        helper = self.env["stock.state.tracking.helper"]

        own_values = helper._get_latest_state_tracking_values("stock.move.line", self.ids)
        lines_without_own_tracking = self.filtered(lambda line: line.id not in own_values)

        move_values = {}
        moves = lines_without_own_tracking.mapped("move_id")
        if moves:
            move_values = helper._get_latest_state_tracking_values("stock.move", moves.ids)

        lines_without_move_tracking = lines_without_own_tracking.filtered(
            lambda line: not line.move_id or line.move_id.id not in move_values
        )

        picking_values = {}
        pickings = lines_without_move_tracking.mapped("picking_id")
        if pickings:
            picking_values = helper._get_latest_state_tracking_values("stock.picking", pickings.ids)

        for line in self:
            vals = own_values.get(line.id)

            if not vals and line.move_id:
                vals = move_values.get(line.move_id.id)

            if not vals and line.picking_id:
                vals = picking_values.get(line.picking_id.id)

            if vals:
                line.state_last_updated_by_id = vals.get("user_id")
                line.state_last_updated_on = vals.get("date")
                line.state_last_updated_source = vals.get("source")
                continue

            if line._is_inventory_adjustment_state_fallback_line():
                line.state_last_updated_by_id = line.create_uid
                line.state_last_updated_on = line.create_date
                line.state_last_updated_source = "fallback:inventory_adjustment.create_uid"
                continue

            if line.write_uid and line.write_date:
                line.state_last_updated_by_id = line.write_uid
                line.state_last_updated_on = line.write_date
                line.state_last_updated_source = "fallback:stock.move.line.write_uid"
                continue

            if line.move_id and line.move_id.write_uid and line.move_id.write_date:
                line.state_last_updated_by_id = line.move_id.write_uid
                line.state_last_updated_on = line.move_id.write_date
                line.state_last_updated_source = "fallback:stock.move.write_uid"
                continue

            line.state_last_updated_by_id = False
            line.state_last_updated_on = False
            line.state_last_updated_source = False

    def _is_inventory_adjustment_state_fallback_line(self):
        self.ensure_one()

        if "is_inventory" in self._fields and self.is_inventory:
            return True

        if "inventory_quantity" in self._fields and self.inventory_quantity:
            return True

        if self.move_id and "inventory_id" in self.move_id._fields and self.move_id.inventory_id:
            return True

        if self.picking_id:
            return False

        usage_values = []
        if self.location_id:
            usage_values.append(self.location_id.usage)
        if self.location_dest_id:
            usage_values.append(self.location_dest_id.usage)

        return "inventory" in usage_values
