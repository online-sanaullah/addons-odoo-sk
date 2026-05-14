from odoo import models, tools


class MonthlyTrialBalanceAnalyticBase(models.Model):
    _name = 'monthly.trial.balance.analytic.base'
    _description = 'Monthly Trial Balance Analytic Base View'
    _auto = False

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    row_number() OVER () AS id,
                    aml.id AS move_line_id,
                    aml.company_id,
                    aml.account_id,
                    aml.date,
                    aml.debit,
                    aml.credit,
                    aml.balance,
                    am.state AS move_state,
                    COALESCE(NULLIF(trim(analytic_key), ''), NULL)::int AS analytic_account_id,
                    COALESCE(dist_json.value::numeric / 100.0, 1.0) AS analytic_factor
                FROM account_move_line aml
                JOIN account_move am ON am.id = aml.move_id
                LEFT JOIN LATERAL (
                    SELECT key, value
                    FROM jsonb_each_text(COALESCE(aml.analytic_distribution, '{{}}'::jsonb))
                ) dist_json ON TRUE
                LEFT JOIN LATERAL (
                    SELECT unnest(string_to_array(dist_json.key, ',')) AS analytic_key
                ) split_key ON TRUE
            )
        """)
