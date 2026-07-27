# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.osv import expression


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    access_team_ids = fields.Many2many(
        comodel_name='crm.team',
        relation='product_pricelist_access_team_rel',
        column1='pricelist_id',
        column2='team_id',
        string='Allowed Sales Teams',
        help=(
            'If sales teams are set, only the team leader or members of those teams '
            'can see this pricelist in views and selections. Leave empty together with '
            'Allowed Users to keep the pricelist public.'
        ),
    )
    access_user_ids = fields.Many2many(
        comodel_name='res.users',
        relation='product_pricelist_access_user_rel',
        column1='pricelist_id',
        column2='user_id',
        string='Allowed Users',
        help=(
            'If users are set, only these users can see this pricelist in views and selections. '
            'If sales teams are also set, visibility is granted to the union of users and teams.'
        ),
    )
    access_granted_user_ids = fields.Many2many(
        comodel_name='res.users',
        relation='product_pricelist_access_granted_user_rel',
        column1='pricelist_id',
        column2='user_id',
        string='Effective Access Users',
        readonly=True,
        copy=False,
        help='Technical field maintained from allowed teams and allowed users.',
    )
    is_restricted_by_team_user = fields.Boolean(
        string='Restricted',
        compute='_compute_is_restricted_by_team_user',
        search='_search_is_restricted_by_team_user',
    )

    @api.depends('access_team_ids', 'access_user_ids')
    def _compute_is_restricted_by_team_user(self):
        for pricelist in self:
            pricelist.is_restricted_by_team_user = bool(
                pricelist.access_team_ids or pricelist.access_user_ids
            )

    @api.model
    def _search_is_restricted_by_team_user(self, operator, value):
        restricted_domain = [
            '|',
            ('access_team_ids', '!=', False),
            ('access_user_ids', '!=', False),
        ]
        unrestricted_domain = [
            '&',
            ('access_team_ids', '=', False),
            ('access_user_ids', '=', False),
        ]
        if operator in ('=', '=='):
            return restricted_domain if value else unrestricted_domain
        if operator in ('!=', '<>'):
            return unrestricted_domain if value else restricted_domain
        return []

    @api.model
    def _skip_team_user_pricelist_filter(self):
        return bool(
            self.env.su
            or self.env.context.get('skip_pricelist_team_user_access')
            or self.env.user.has_group('base.group_system')
        )

    @api.model
    def _get_user_sales_team_ids(self, user=None):
        """Return teams led by or containing the user.

        This is evaluated directly from crm.team instead of relying solely on the
        synchronized technical M2M, so smart-button visibility cannot become stale.
        """
        user = user or self.env.user
        Team = self.env['crm.team'].sudo()
        domain_parts = [[('user_id', '=', user.id)]]
        if 'member_ids' in Team._fields:
            domain_parts.append([('member_ids', 'in', [user.id])])
        if 'team_member_ids' in Team._fields:
            domain_parts.append([('team_member_ids.user_id', '=', user.id)])
        return Team.search(expression.OR(domain_parts)).ids

    @api.model
    def _get_accessible_pricelist_ids(self, user=None, admin_bypass=True):
        """Return pricelist IDs visible to ``user``.

        ``False`` means no domain should be applied (sudo/context bypass or, when
        requested, Settings administrators).  An empty list means the user has no
        accessible pricelists.
        """
        user = user or self.env.user
        if self.env.su or self.env.context.get('skip_pricelist_team_user_access'):
            return False
        if admin_bypass and user.has_group('base.group_system'):
            return False

        team_ids = self._get_user_sales_team_ids(user=user)
        access_domain = expression.OR([
            [
                '&',
                ('access_team_ids', '=', False),
                ('access_user_ids', '=', False),
            ],
            [('access_user_ids', 'in', [user.id])],
            [('access_team_ids', 'in', team_ids)] if team_ids else [('id', '=', 0)],
        ])
        return self.sudo().with_context(
            skip_pricelist_team_user_access=True,
            active_test=False,
        ).search(access_domain).ids

    @api.model
    def _get_pricelist_access_domain(self, user=None):
        accessible_ids = self._get_accessible_pricelist_ids(
            user=user,
            admin_bypass=True,
        )
        return [] if accessible_ids is False else [('id', 'in', accessible_ids)]

    @api.model
    def _get_team_user_access_domain(self):
        return [] if self._skip_team_user_pricelist_filter() else self._get_pricelist_access_domain()

    @api.model
    def _apply_team_user_access_domain(self, domain):
        access_domain = self._get_team_user_access_domain()
        if not access_domain:
            return domain or []
        return expression.AND([domain or [], access_domain])

    @api.model
    def web_search_read(self, domain=None, specification=None, offset=0, limit=None, order=None, count_limit=None):
        domain = self._apply_team_user_access_domain(domain)
        return super().web_search_read(
            domain,
            specification,
            offset=offset,
            limit=limit,
            order=order,
            count_limit=count_limit,
        )

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = self._apply_team_user_access_domain(domain)
        return super().search_read(
            domain=domain,
            fields=fields,
            offset=offset,
            limit=limit,
            order=order,
        )

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = self._apply_team_user_access_domain(args)
        return super().name_search(name=name, args=args, operator=operator, limit=limit)

    def _get_access_team_users(self):
        self.ensure_one()
        teams = self.access_team_ids
        users = teams.mapped('user_id')
        if 'member_ids' in teams._fields:
            users |= teams.mapped('member_ids')
        if 'team_member_ids' in teams._fields:
            users |= teams.mapped('team_member_ids.user_id')
        return users

    def _sync_access_granted_user_ids(self):
        for pricelist in self.sudo():
            users = pricelist.access_user_ids | pricelist._get_access_team_users()
            pricelist.with_context(skip_pricelist_team_user_access=True).write({
                'access_granted_user_ids': [(6, 0, users.ids)],
            })

    def write(self, vals):
        res = super().write(vals)
        if {'access_team_ids', 'access_user_ids'} & set(vals):
            self._sync_access_granted_user_ids()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_access_granted_user_ids()
        return records
