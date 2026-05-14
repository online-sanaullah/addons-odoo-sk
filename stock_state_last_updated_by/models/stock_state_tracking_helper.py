from odoo import models


class StockStateTrackingHelper(models.AbstractModel):
    _name = "stock.state.tracking.helper"
    _description = "Stock State Tracking Helper"

    def _get_latest_state_tracking_values(self, model_name, res_ids):
        res_ids = [rid for rid in res_ids if rid]
        if not model_name or not res_ids:
            return {}

        state_field = self.env["ir.model.fields"].sudo().search(
            [("model", "=", model_name), ("name", "=", "state")],
            limit=1,
        )
        if not state_field:
            return {}

        self.env.cr.execute(
            """
            SELECT DISTINCT ON (msg.res_id)
                   msg.res_id,
                   msg.create_uid,
                   msg.date
              FROM mail_tracking_value tv
              JOIN mail_message msg
                ON msg.id = tv.mail_message_id
             WHERE msg.model = %s
               AND msg.res_id = ANY(%s)
               AND tv.field_id = %s
             ORDER BY msg.res_id, msg.date DESC, msg.id DESC
            """,
            [model_name, res_ids, state_field.id],
        )

        return {
            row[0]: {
                "user_id": row[1],
                "date": row[2],
                "source": "tracking:%s" % model_name,
            }
            for row in self.env.cr.fetchall()
        }
