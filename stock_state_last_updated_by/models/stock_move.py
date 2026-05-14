from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

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

    @api.depends("state")
    def _compute_state_last_tracking_info(self):
        helper = self.env["stock.state.tracking.helper"]
        values_by_id = helper._get_latest_state_tracking_values("stock.move", self.ids)
        for move in self:
            vals = values_by_id.get(move.id)
            move.state_last_updated_by_id = vals.get("user_id") if vals else False
            move.state_last_updated_on = vals.get("date") if vals else False
            move.state_last_updated_source = vals.get("source") if vals else False
