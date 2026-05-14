import ast
from collections import defaultdict
from datetime import timedelta

from odoo import _, fields, models


PL_ACCOUNT_TYPES = {
    'income',
    'income_other',
    'expense',
    'expense_depreciation',
    'expense_direct_cost',
}


class MonthlyTrialBalanceAnalyticReportHandler(models.AbstractModel):
    _name = 'monthly.trial.balance.analytic.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Monthly Trial Balance by Analytic Report Handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options['unfold_all'] = True
        options['hierarchy'] = False

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals=None, warnings=None):
        return [(0, line) for line in self._get_monthly_lines(report, options)]

    def _get_lines(self, report, options, line_id=None):
        return self._get_monthly_lines(report, options, line_id=line_id)

    def _get_monthly_lines(self, report, options, line_id=None):
        company_ids = self._get_company_ids(options) or [self.env.company.id]
        date_from, date_to = self._get_date_range(options)
        months = list(self._iter_month_ranges(date_from, date_to))
        if not months:
            return []

        account_ids = self._get_filtered_account_ids(options, company_ids)
        analytic_ids = self._get_filtered_analytic_account_ids(options)

        monthly_rows = self._get_monthly_sql_data(
            report,
            options,
            company_ids,
            months,
            date_from,
            date_to,
            account_ids=account_ids,
            analytic_ids=analytic_ids,
        )
        earnings_rows = self._get_current_year_earnings_sql_data(
            report,
            options,
            company_ids,
            months,
            account_ids=account_ids,
            analytic_ids=analytic_ids,
        )

        account_ids_needed = set()
        analytic_account_ids_needed = set()
        for rows in monthly_rows.values():
            for row in rows:
                account_ids_needed.add(row['account_id'])
                if row['analytic_account_id']:
                    analytic_account_ids_needed.add(row['analytic_account_id'])
        for rows in earnings_rows.values():
            for row in rows:
                account_ids_needed.add(row['account_id'])
                if row['analytic_account_id']:
                    analytic_account_ids_needed.add(row['analytic_account_id'])

        accounts = self.env['account.account'].browse(list(account_ids_needed)).exists()
        account_map = {account.id: account for account in accounts}
        analytic_accounts = self.env['account.analytic.account'].browse(list(analytic_account_ids_needed)).exists()
        analytic_map = {analytic.id: analytic for analytic in analytic_accounts}
        account_type_labels = dict(self.env['account.account']._fields['account_type'].selection)

        lines = []
        for month in months:
            month_key = month['key']
            month_name = fields.Date.to_date(month['date_from']).strftime('%B')
            month_rows = monthly_rows.get(month_key, [])

            for row in month_rows:
                account = account_map.get(row['account_id'])
                if not account:
                    continue
                analytic_account = analytic_map.get(row['analytic_account_id']) if row['analytic_account_id'] else None
                opening = row['opening'] or 0.0
                debit = row['debit'] or 0.0
                credit = row['credit'] or 0.0

                if account.account_type in PL_ACCOUNT_TYPES:
                    opening = 0.0

                ending = opening + debit - credit
                if self._is_zero(opening) and self._is_zero(debit) and self._is_zero(credit) and self._is_zero(ending):
                    continue

                lines.append({
                    'id': self._make_line_id('monthly', account.id, month_key, row.get('analytic_account_id')),
                    'name': account.name or '',
                    'level': 2,
                    'caret_options': 'account.account',
                    'columns': self._build_columns(
                        report,
                        month['year'],
                        month_name,
                        analytic_account.plan_id.name if analytic_account and analytic_account.plan_id else '',
                        analytic_account.name if analytic_account else '',
                        account.code or '',
                        account.name or '',
                        account_type_labels.get(account.account_type, account.account_type or ''),
                        opening,
                        debit,
                        credit,
                        ending,
                    ),
                    'unfoldable': False,
                    'unfolded': False,
                })

            for row in earnings_rows.get(month_key, []):
                account = account_map.get(row['account_id'])
                if not account:
                    continue
                balance = row['balance'] or 0.0
                if self._is_zero(balance):
                    continue
                analytic_account = analytic_map.get(row['analytic_account_id']) if row['analytic_account_id'] else None
                lines.append({
                    'id': self._make_line_id('cye', account.id, month_key, row.get('analytic_account_id'), row.get('company_id')),
                    'name': account.name or '',
                    'level': 2,
                    'caret_options': 'account.account',
                    'columns': self._build_columns(
                        report,
                        month['year'],
                        month_name,
                        analytic_account.plan_id.name if analytic_account and analytic_account.plan_id else '',
                        analytic_account.name if analytic_account else '',
                        account.code or '',
                        account.name or '',
                        account_type_labels.get(account.account_type, account.account_type or ''),
                        balance,
                        0.0,
                        0.0,
                        balance,
                    ),
                    'unfoldable': False,
                    'unfolded': False,
                })

            if not month_rows and not earnings_rows.get(month_key):
                lines.append({
                    'id': self._make_line_id('empty', 0, month_key),
                    'name': f"{month_name} {month['year']}",
                    'level': 1,
                    'columns': self._build_columns(report, month['year'], month_name, '', '', '', _('No data'), '', 0.0, 0.0, 0.0, 0.0),
                    'unfoldable': False,
                    'unfolded': False,
                })

        return lines

    def _make_line_id(self, kind, account_id, month_key, analytic_account_id=None, company_id=None):
        analytic_part = analytic_account_id or 0
        company_part = company_id or 0
        markup = f"{kind}_{month_key}_{analytic_part}_{company_part}"
        return f"{markup}~account.account~{int(account_id or 0)}"

    def _get_monthly_sql_data(self, report, options, company_ids, months, date_from, date_to, account_ids=None, analytic_ids=None):
        if not months:
            return {}

        month_values_sql, month_params = self._build_month_values_sql(months)
        account_filter_sql, account_filter_params = self._build_account_filter_sql('base', account_ids)
        analytic_filter_sql, analytic_filter_params = self._build_analytic_filter_sql('base', analytic_ids)
        aml_cte_sql, aml_join_sql, aml_where_params = self._build_move_line_filter_cte(report, options, date_scope='strict_range')

        sql = f"""
            WITH months (month_key, month_seq, period_start, period_end) AS (
                VALUES {month_values_sql}
            ){aml_cte_sql},
            pre_range AS (
                SELECT
                    base.company_id,
                    base.account_id,
                    base.analytic_account_id,
                    SUM(base.balance * base.analytic_factor) AS opening
                FROM monthly_trial_balance_analytic_base base
                {aml_join_sql}
                WHERE base.company_id = ANY(%s)
                  AND base.date < %s
                  AND base.move_state = 'posted'
                  {account_filter_sql}
                  {analytic_filter_sql}
                GROUP BY base.company_id, base.account_id, base.analytic_account_id
            ),
            monthly AS (
                SELECT
                    m.month_key,
                    m.month_seq,
                    base.company_id,
                    base.account_id,
                    base.analytic_account_id,
                    SUM(base.debit * base.analytic_factor) AS debit,
                    SUM(base.credit * base.analytic_factor) AS credit,
                    SUM(base.balance * base.analytic_factor) AS balance
                FROM months m
                JOIN monthly_trial_balance_analytic_base base
                  ON base.date >= m.period_start
                 AND base.date <= m.period_end
                {aml_join_sql}
                WHERE base.company_id = ANY(%s)
                  AND base.date >= %s
                  AND base.date <= %s
                  AND base.move_state = 'posted'
                  {account_filter_sql}
                  {analytic_filter_sql}
                GROUP BY m.month_key, m.month_seq, base.company_id, base.account_id, base.analytic_account_id
            ),
            keys AS (
                SELECT company_id, account_id, analytic_account_id FROM pre_range
                UNION
                SELECT company_id, account_id, analytic_account_id FROM monthly
            ),
            grid AS (
                SELECT
                    m.month_key,
                    m.month_seq,
                    k.company_id,
                    k.account_id,
                    k.analytic_account_id
                FROM months m
                CROSS JOIN keys k
            ),
            joined AS (
                SELECT
                    g.month_key,
                    g.month_seq,
                    g.company_id,
                    g.account_id,
                    g.analytic_account_id,
                    COALESCE(pr.opening, 0.0) AS base_opening,
                    COALESCE(mon.debit, 0.0) AS debit,
                    COALESCE(mon.credit, 0.0) AS credit,
                    COALESCE(mon.balance, 0.0) AS month_balance
                FROM grid g
                LEFT JOIN pre_range pr
                  ON pr.company_id = g.company_id
                 AND pr.account_id = g.account_id
                 AND COALESCE(pr.analytic_account_id, 0) = COALESCE(g.analytic_account_id, 0)
                LEFT JOIN monthly mon
                  ON mon.month_key = g.month_key
                 AND mon.company_id = g.company_id
                 AND mon.account_id = g.account_id
                 AND COALESCE(mon.analytic_account_id, 0) = COALESCE(g.analytic_account_id, 0)
            ),
            final_rows AS (
                SELECT
                    month_key,
                    company_id,
                    account_id,
                    analytic_account_id,
                    base_opening
                    + COALESCE(
                        SUM(month_balance) OVER (
                            PARTITION BY company_id, account_id, analytic_account_id
                            ORDER BY month_seq
                            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                        ),
                        0.0
                    ) AS opening,
                    debit,
                    credit
                FROM joined
            )
            SELECT month_key, company_id, account_id, analytic_account_id, opening, debit, credit
            FROM final_rows
            WHERE NOT (
                COALESCE(opening, 0.0) = 0.0
                AND COALESCE(debit, 0.0) = 0.0
                AND COALESCE(credit, 0.0) = 0.0
            )
            ORDER BY month_key, account_id, analytic_account_id
        """
        params = []
        params.extend(month_params)
        params.extend(aml_where_params)
        params.extend([[int(x) for x in company_ids], date_from])
        params.extend(account_filter_params)
        params.extend(analytic_filter_params)
        params.extend([[int(x) for x in company_ids], date_from, date_to])
        params.extend(account_filter_params)
        params.extend(analytic_filter_params)

        self.env.cr.execute(sql, params)
        result = defaultdict(list)
        for row in self.env.cr.dictfetchall():
            result[row['month_key']].append({
                'company_id': row['company_id'],
                'account_id': row['account_id'],
                'analytic_account_id': row['analytic_account_id'],
                'opening': row['opening'] or 0.0,
                'debit': row['debit'] or 0.0,
                'credit': row['credit'] or 0.0,
            })
        return result

    def _get_current_year_earnings_sql_data(self, report, options, company_ids, months, account_ids=None, analytic_ids=None):
        company_month_rows = []
        for company in self.env['res.company'].browse(company_ids):
            earnings_account = self.env['account.account'].search([
                ('company_id', '=', company.id),
                ('account_type', '=', 'equity_unaffected'),
                ('deprecated', '=', False),
            ], order='code, id', limit=1)
            if not earnings_account:
                continue
            for month in months:
                fiscal_dates = company.compute_fiscalyear_dates(month['date_from'])
                prior_day = month['date_from'] - timedelta(days=1)
                if fiscal_dates['date_from'] > prior_day:
                    continue
                company_month_rows.append((
                    month['key'],
                    company.id,
                    earnings_account.id,
                    fiscal_dates['date_from'],
                    prior_day,
                ))

        if not company_month_rows:
            return {}

        values_sql = ', '.join(['(%s, %s, %s, %s, %s)'] * len(company_month_rows))
        params = []
        for row in company_month_rows:
            params.extend(row)

        account_filter_sql, account_filter_params = self._build_account_filter_sql('base', account_ids)
        analytic_filter_sql, analytic_filter_params = self._build_analytic_filter_sql('base', analytic_ids)
        aml_cte_sql, aml_join_sql, aml_where_params = self._build_move_line_filter_cte(report, options, ignore_report_dates=True)

        sql = f"""
            WITH cye (month_key, company_id, earnings_account_id, fiscal_date_from, prior_day) AS (
                VALUES {values_sql}
            ){aml_cte_sql}
            SELECT
                cye.month_key,
                cye.company_id,
                cye.earnings_account_id AS account_id,
                base.analytic_account_id,
                SUM(base.balance * base.analytic_factor) AS balance
            FROM cye
            JOIN monthly_trial_balance_analytic_base base
              ON base.company_id = cye.company_id
             AND base.date >= cye.fiscal_date_from
             AND base.date <= cye.prior_day
             AND base.move_state = 'posted'
            {aml_join_sql}
            JOIN account_account acc ON acc.id = base.account_id
            WHERE acc.account_type = ANY(%s)
              {account_filter_sql}
              {analytic_filter_sql}
            GROUP BY cye.month_key, cye.company_id, cye.earnings_account_id, base.analytic_account_id
            HAVING SUM(base.balance * base.analytic_factor) != 0.0
            ORDER BY cye.month_key, base.analytic_account_id
        """
        params.extend(aml_where_params)
        params.extend([list(PL_ACCOUNT_TYPES)])
        params.extend(account_filter_params)
        params.extend(analytic_filter_params)

        self.env.cr.execute(sql, params)
        result = defaultdict(list)
        for row in self.env.cr.dictfetchall():
            result[row['month_key']].append({
                'month_key': row['month_key'],
                'company_id': row['company_id'],
                'account_id': row['account_id'],
                'analytic_account_id': row['analytic_account_id'],
                'balance': row['balance'] or 0.0,
            })
        return result

    def _build_month_values_sql(self, months):
        placeholders = []
        params = []
        for seq, month in enumerate(months, start=1):
            placeholders.append('(%s, %s, %s, %s)')
            params.extend([month['key'], seq, month['date_from'], month['date_to']])
        return ', '.join(placeholders), params

    def _build_columns(self, report, year, month_name, analytic_plan_name, analytic_account_name, account_code, account_name, account_type_name, opening, debit, credit, ending):
        return [
            self._build_text_column(report, str(year)),
            self._build_text_column(report, month_name),
            self._build_text_column(report, analytic_plan_name),
            self._build_text_column(report, analytic_account_name),
            self._build_text_column(report, account_code),
            self._build_text_column(report, account_name),
            self._build_text_column(report, account_type_name),
            report._build_column_dict(opening, {'no_format': opening}),
            report._build_column_dict(debit, {'no_format': debit}),
            report._build_column_dict(credit, {'no_format': credit}),
            report._build_column_dict(ending, {'no_format': ending}),
        ]

    def _build_text_column(self, report, value):
        value = value or ''
        return report._build_column_dict(value, {'name': value, 'no_format': value})

    def _get_company_ids(self, options):
        multi_company = options.get('multi_company') or []
        selected_ids = []
        if isinstance(multi_company, dict):
            selected_ids.extend(self._normalize_ids(multi_company.get('ids') or multi_company.get('selected_ids')))
        else:
            selected_ids.extend(self._normalize_ids([c.get('id') for c in multi_company if isinstance(c, dict) and c.get('selected')]))
        return selected_ids or [self.env.company.id]

    def _get_date_range(self, options):
        date_options = options.get('date') or {}
        date_from = fields.Date.to_date(date_options.get('date_from')) if date_options.get('date_from') else fields.Date.context_today(self)
        date_to = fields.Date.to_date(date_options.get('date_to')) if date_options.get('date_to') else date_from
        if date_from > date_to:
            date_from, date_to = date_to, date_from
        return date_from, date_to

    def _iter_month_ranges(self, date_from, date_to):
        cursor = date_from.replace(day=1)
        while cursor <= date_to:
            next_month = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
            month_end = min(next_month - timedelta(days=1), date_to)
            yield {
                'key': cursor.strftime('%Y-%m'),
                'year': cursor.year,
                'month': cursor.month,
                'date_from': max(cursor, date_from),
                'date_to': month_end,
            }
            cursor = next_month

    def _normalize_ids(self, values):
        if values in (None, False, ''):
            return []
        if isinstance(values, (int, str)):
            values = [values]
        result = []
        for value in values:
            if value in (None, False, ''):
                continue
            if isinstance(value, int):
                result.append(value)
                continue
            if isinstance(value, str):
                parts = [part.strip() for part in value.split(',') if part.strip()]
                for part in parts:
                    if part.isdigit() or (part.startswith('-') and part[1:].isdigit()):
                        result.append(int(part))
                continue
            if isinstance(value, dict):
                for key in ('id', 'ids', 'selected_ids', 'res_id'):
                    if key in value:
                        result.extend(self._normalize_ids(value.get(key)))
                continue
            if isinstance(value, (list, tuple, set)):
                result.extend(self._normalize_ids(value))
                continue
            try:
                result.append(int(value))
            except (TypeError, ValueError):
                continue
        return list(dict.fromkeys(result))

    def _build_account_filter_sql(self, table_alias, account_ids):
        normalized_ids = self._normalize_ids(account_ids)
        if not normalized_ids:
            return '', []
        return f" AND {table_alias}.account_id = ANY(%s)", [normalized_ids]

    def _build_analytic_filter_sql(self, table_alias, analytic_ids):
        normalized_ids = self._normalize_ids(analytic_ids)
        if not normalized_ids:
            return '', []
        return f" AND {table_alias}.analytic_account_id = ANY(%s)", [normalized_ids]

    def _get_filtered_account_ids(self, options, company_ids):
        account_codes = options.get('account_codes') or []
        if not account_codes:
            return None
        return self.env['account.account'].search([
            ('company_id', 'in', company_ids),
            ('code', 'in', account_codes),
        ]).ids

    def _get_filtered_analytic_account_ids(self, options):
        candidates = []
        analytic_options = options.get('analytic_accounts') or []
        if isinstance(analytic_options, dict):
            candidates.extend(self._normalize_ids(analytic_options.get('ids') or analytic_options.get('selected_ids')))
        else:
            for item in analytic_options:
                if isinstance(item, dict) and item.get('selected'):
                    candidates.extend(self._normalize_ids(item.get('id')))
        candidates.extend(self._normalize_ids(options.get('analytic_account_ids')))
        candidates.extend(self._normalize_ids(options.get('selected_analytic_account_ids')))
        return list(dict.fromkeys(candidates)) or None

    def _build_move_line_filter_cte(self, report, options, date_scope='strict_range', ignore_report_dates=False):
        # Only apply explicit Journal Items favorite/search domains here.
        # Core report filters (date/company/analytic/account) are already applied
        # separately in this handler; injecting the full account.report option domain
        # here can over-filter AML rows and make valid analytic rows disappear.
        domain = []
        domain.extend(self._normalize_domain(options.get('forced_domain')))
        domain.extend(self._normalize_domain(options.get('search_domain')))
        domain.extend(self._normalize_domain(options.get('domain')))
        domain = self._strip_report_managed_domains(domain, keep_dates=not ignore_report_dates)

        if not domain:
            return '', '', []

        aml_model = self.env['account.move.line'].with_context(active_test=False)
        query = aml_model._where_calc(domain)
        aml_model._apply_ir_rules(query, 'read')
        from_clause, where_clause, where_params = query.get_sql()
        from_clause = from_clause or 'account_move_line'
        where_clause = where_clause or 'TRUE'
        return f', filtered_aml AS (SELECT account_move_line.id FROM {from_clause} WHERE {where_clause})', 'JOIN filtered_aml ON filtered_aml.id = base.move_line_id', where_params

    def _normalize_domain(self, domain):
        if not domain:
            return []
        if isinstance(domain, str):
            try:
                domain = ast.literal_eval(domain)
            except (ValueError, SyntaxError):
                return []
        if isinstance(domain, tuple):
            domain = list(domain)
        if not isinstance(domain, list):
            return []
        return domain

    def _strip_date_domains(self, domain):
        cleaned = []
        date_fields = {'date', 'date_maturity', 'create_date', 'write_date'}
        for item in domain:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                field_name = item[0]
                if isinstance(field_name, str) and field_name.split('.')[0] in date_fields:
                    continue
            cleaned.append(item)
        return cleaned

    def _strip_report_managed_domains(self, domain, keep_dates=True):
        cleaned = []
        managed_fields = {
            'company_id', 'account_id', 'account_code', 'analytic_account_id',
            'analytic_distribution', 'parent_state', 'move_id.state',
        }
        date_fields = {'date', 'date_maturity', 'create_date', 'write_date'}
        for item in domain:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                field_name = item[0]
                if isinstance(field_name, str):
                    base_name = field_name.split('.')[0]
                    if field_name in managed_fields or base_name in managed_fields:
                        continue
                    if not keep_dates and base_name in date_fields:
                        continue
            cleaned.append(item)
        return cleaned

    def _is_zero(self, amount):
        currency = self.env.company.currency_id
        return currency.is_zero(amount)
