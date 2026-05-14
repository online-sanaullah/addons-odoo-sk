from collections import defaultdict
from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import fields, models


class MonthlyTrialBalanceReportHandler(models.AbstractModel):
    _name = 'monthly.trial.balance.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Monthly Trial Balance Report Handler'

    PNL_ACCOUNT_TYPES = (
        'income',
        'income_other',
        'expense',
        'expense_depreciation',
        'expense_direct_cost',
    )

    def _custom_options_initializer(self, report, options, previous_options=None):
        return

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals=None, warnings=None):
        lines = self._get_monthly_lines(report, options)
        return [(0, line) for line in lines]

    def _get_lines(self, report, options, line_id=None):
        return self._get_monthly_lines(report, options, line_id=line_id)

    def _get_monthly_lines(self, report, options, line_id=None):
        company_ids = self._get_company_ids(options)
        if not company_ids:
            company_ids = [self.env.company.id]

        date_from, date_to = self._get_date_range(options)
        months = list(self._iter_month_ranges(date_from, date_to))

        analytic_domain_sql, analytic_params = self._get_analytic_sql_filter(options)

        move_state_sql = "am.state = 'posted'"
        if options.get('all_entries'):
            move_state_sql = "am.state in ('draft', 'posted')"

        accounts = self.env['account.account'].with_context(active_test=False).search_read(
            [('company_id', 'in', company_ids)],
            ['code', 'name', 'company_id', 'account_type', 'deprecated'],
            order='code, id',
        )
        account_map = {acc['id']: acc for acc in accounts}

        unaffected_accounts = self.env['account.account'].with_context(active_test=False).search_read(
            [
                ('company_id', 'in', company_ids),
                ('account_type', '=', 'equity_unaffected'),
                ('deprecated', '=', False),
            ],
            ['code', 'name', 'company_id'],
            order='company_id, id',
        )
        unaffected_by_company = {}
        for acc in unaffected_accounts:
            company_id = acc['company_id'][0] if acc.get('company_id') else False
            if company_id and company_id not in unaffected_by_company:
                unaffected_by_company[company_id] = acc['id']
                account_map.setdefault(acc['id'], acc)

        lines = []
        company_currency = self.env.company.currency_id

        for month_start, month_end in months:
            query = f"""
                SELECT
                    aml.account_id,
                    SUM(CASE WHEN aml.date < %s THEN aml.debit ELSE 0 END) AS init_debit,
                    SUM(CASE WHEN aml.date < %s THEN aml.credit ELSE 0 END) AS init_credit,
                    SUM(CASE WHEN aml.date >= %s AND aml.date <= %s THEN aml.debit ELSE 0 END) AS period_debit,
                    SUM(CASE WHEN aml.date >= %s AND aml.date <= %s THEN aml.credit ELSE 0 END) AS period_credit
                FROM account_move_line aml
                JOIN account_move am ON am.id = aml.move_id
                WHERE aml.company_id IN %s
                  AND aml.date <= %s
                  AND {move_state_sql}
                  {analytic_domain_sql}
                GROUP BY aml.account_id
                HAVING
                    ABS(SUM(CASE WHEN aml.date < %s THEN aml.debit - aml.credit ELSE 0 END)) > 0.00001
                    OR ABS(SUM(CASE WHEN aml.date >= %s AND aml.date <= %s THEN aml.debit ELSE 0 END)) > 0.00001
                    OR ABS(SUM(CASE WHEN aml.date >= %s AND aml.date <= %s THEN aml.credit ELSE 0 END)) > 0.00001
                ORDER BY aml.account_id
            """

            params = [
                month_start, month_start,
                month_start, month_end,
                month_start, month_end,
                tuple(company_ids), month_end,
            ]
            params.extend(analytic_params)
            params.extend([
                month_start,
                month_start, month_end,
                month_start, month_end,
            ])

            self.env.cr.execute(query, params)
            rows = self.env.cr.dictfetchall()

            rows = self._apply_unaffected_earnings_adjustment(
                rows=rows,
                account_map=account_map,
                unaffected_by_company=unaffected_by_company,
                company_ids=company_ids,
            )

            month_label = fields.Date.to_date(month_start).strftime('%B')
            year_label = str(fields.Date.to_date(month_start).year)

            for row in rows:
                account = account_map.get(row['account_id'])
                if not account:
                    continue

                init_balance = (row['init_debit'] or 0.0) - (row['init_credit'] or 0.0)
                debit = row['period_debit'] or 0.0
                credit = row['period_credit'] or 0.0
                end_balance = init_balance + debit - credit

                lines.append({
                    'id': self._account_line_id(report, month_start, row['account_id']),
                    'name': f"{account.get('code', '')} {account.get('name', '')}".strip(),
                    'level': 2,
                    'unfoldable': False,
                    'caret_options': 'account.account',
                    'columns': self._build_columns(
                        report=report,
                        options=options,
                        year_label=year_label,
                        month_label=month_label,
                        init_balance=init_balance,
                        debit=debit,
                        credit=credit,
                        end_balance=end_balance,
                        company_currency=company_currency,
                    ),
                })

        return lines

    def _apply_unaffected_earnings_adjustment(self, rows, account_map, unaffected_by_company, company_ids):
        """
        Keep the current query/result shape, but rewrite init_debit/init_credit so that:
        - P&L accounts do not show opening balances
        - their opening net balance is moved to the company's equity_unaffected account
        """
        adjusted_rows = []
        pnl_opening_by_company = defaultdict(float)
        existing_row_map = {}

        for row in rows:
            row = dict(row)
            account = account_map.get(row['account_id'])
            if not account:
                adjusted_rows.append(row)
                continue

            company_id = account['company_id'][0] if account.get('company_id') else company_ids[0]
            init_debit = row.get('init_debit') or 0.0
            init_credit = row.get('init_credit') or 0.0
            init_balance = init_debit - init_credit

            if account.get('account_type') in self.PNL_ACCOUNT_TYPES:
                pnl_opening_by_company[company_id] += init_balance
                row['init_debit'] = 0.0
                row['init_credit'] = 0.0

            adjusted_rows.append(row)
            existing_row_map[row['account_id']] = row

        for company_id, pnl_balance in pnl_opening_by_company.items():
            if abs(pnl_balance) <= 0.00001:
                continue

            unaffected_account_id = unaffected_by_company.get(company_id)
            if not unaffected_account_id:
                continue

            target_row = existing_row_map.get(unaffected_account_id)
            if not target_row:
                target_row = {
                    'account_id': unaffected_account_id,
                    'init_debit': 0.0,
                    'init_credit': 0.0,
                    'period_debit': 0.0,
                    'period_credit': 0.0,
                }
                adjusted_rows.append(target_row)
                existing_row_map[unaffected_account_id] = target_row

            current_init_balance = (target_row.get('init_debit') or 0.0) - (target_row.get('init_credit') or 0.0)
            new_init_balance = current_init_balance + pnl_balance

            if new_init_balance >= 0:
                target_row['init_debit'] = new_init_balance
                target_row['init_credit'] = 0.0
            else:
                target_row['init_debit'] = 0.0
                target_row['init_credit'] = -new_init_balance

        filtered_rows = []
        for row in adjusted_rows:
            init_debit = row.get('init_debit') or 0.0
            init_credit = row.get('init_credit') or 0.0
            period_debit = row.get('period_debit') or 0.0
            period_credit = row.get('period_credit') or 0.0

            if (
                abs(init_debit - init_credit) <= 0.00001
                and abs(period_debit) <= 0.00001
                and abs(period_credit) <= 0.00001
            ):
                continue

            filtered_rows.append(row)

        filtered_rows.sort(key=lambda r: (
            account_map.get(r['account_id'], {}).get('code', ''),
            r['account_id'],
        ))
        return filtered_rows

    def _build_columns(
        self,
        report,
        options,
        year_label,
        month_label,
        init_balance,
        debit,
        credit,
        end_balance,
        company_currency,
    ):
        return [
            {'name': year_label or '', 'no_format_name': year_label or '', 'class': 'text'},
            {'name': month_label or '', 'no_format_name': month_label or '', 'class': 'text'},
            self._monetary_col(report, options, init_balance, company_currency),
            self._monetary_col(report, options, debit, company_currency),
            self._monetary_col(report, options, credit, company_currency),
            self._monetary_col(report, options, end_balance, company_currency),
        ]

    def _monetary_col(self, report, options, amount, currency):
        amount = amount or 0.0
        return {
            'name': report.format_value(options, amount, currency=currency),
            'no_format_name': amount,
            'class': 'number',
        }

    def _get_company_ids(self, options):
        if options.get('multi_company'):
            companies = options['multi_company']
            if companies.get('company_ids'):
                return companies['company_ids']
        return self.env.companies.ids or [self.env.company.id]

    def _get_date_range(self, options):
        date_options = options.get('date') or {}
        date_from = fields.Date.to_date(date_options.get('date_from')) if date_options.get('date_from') else date.today().replace(month=1, day=1)
        date_to = fields.Date.to_date(date_options.get('date_to')) if date_options.get('date_to') else date.today()
        return date_from, date_to

    def _iter_month_ranges(self, date_from, date_to):
        current = date_from.replace(day=1)
        while current <= date_to:
            month_start = max(current, date_from)
            month_end = min(current + relativedelta(months=1, days=-1), date_to)
            yield month_start, month_end
            current = current + relativedelta(months=1)

    def _get_analytic_sql_filter(self, options):
        analytic_options = options.get('analytic_accounts') or []
        ids = []

        if isinstance(analytic_options, list):
            for item in analytic_options:
                if isinstance(item, dict) and item.get('id'):
                    try:
                        ids.append(int(item['id']))
                    except Exception:
                        continue
                elif isinstance(item, int):
                    ids.append(item)

        if not ids:
            return "", []

        placeholders = ','.join(['%s'] * len(ids))
        return f"""
            AND EXISTS (
                SELECT 1
                FROM jsonb_each_text(COALESCE(aml.analytic_distribution, '{{}}'::jsonb)) AS dist(key, value)
                WHERE key::int IN ({placeholders})
            )
        """, ids

    def _account_line_id(self, report, month_start, account_id):
        month_key = fields.Date.to_string(month_start)
        return report._get_generic_line_id('account.account', account_id, markup=f'month_{month_key}')