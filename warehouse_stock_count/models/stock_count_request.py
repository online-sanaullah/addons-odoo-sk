from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class WarehouseStockCountRequest(models.Model):
    """
    A request to conduct stock counts of one or more products across one or
    more warehouses, on planned dates, assigned to responsible users.

    Workflow:
        draft  ->  confirmed  ->  generated
                              -->  cancel

    On generation, this creates the actual warehouse.stock.count records and
    schedules a mail.activity ("To Do") for each responsible user on each
    warehouse, with the planned date as the deadline.
    """
    _name = 'warehouse.stock.count.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Stock Count Request'
    _order = 'planned_date desc, id desc'

    name = fields.Char(required=True, default='New', readonly=True, copy=False, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('generated', 'Counts Generated'),
        ('cancel', 'Cancelled'),
    ], default='draft', tracking=True, required=True)

    # Defaults applied to every warehouse line on add. Overridable per warehouse.
    planned_date = fields.Date(
        string='Planned Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        help="Default date used for each warehouse. Can be overridden per warehouse.",
    )
    user_ids = fields.Many2many(
        'res.users',
        'rel_count_request_users', 'request_id', 'user_id',
        string='Responsible Users',
        help="Default responsible users. Can be overridden per warehouse.",
    )
    product_ids = fields.Many2many(
        'product.product',
        'rel_count_request_products', 'request_id', 'product_id',
        string='Products to Count',
    )
    warehouse_line_ids = fields.One2many(
        'warehouse.stock.count.request.warehouse',
        'request_id',
        string='Warehouses',
        copy=True,
    )
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    generated_count_ids = fields.Many2many(
        'warehouse.stock.count',
        compute='_compute_generated_counts',
        string='Generated Counts',
    )
    generated_count_count = fields.Integer(compute='_compute_generated_counts')

    @api.depends('warehouse_line_ids.count_id')
    def _compute_generated_counts(self):
        for rec in self:
            counts = rec.warehouse_line_ids.mapped('count_id')
            rec.generated_count_ids = counts
            rec.generated_count_count = len(counts)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'warehouse.stock.count.request'
                ) or _('New')
        return super().create(vals_list)

    # --- workflow ------------------------------------------------------- #

    def action_confirm(self):
        for rec in self:
            if not rec.product_ids:
                raise UserError(_("Add at least one product before confirming."))
            if not rec.warehouse_line_ids:
                raise UserError(_("Add at least one warehouse before confirming."))
            for wh_line in rec.warehouse_line_ids:
                effective_date = wh_line.planned_date or rec.planned_date
                if not effective_date:
                    raise UserError(_(
                        "Warehouse %s has no planned date and no default is set."
                    ) % wh_line.warehouse_id.display_name)
            rec.state = 'confirmed'

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_generate_counts(self):
        Count = self.env['warehouse.stock.count']
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError(_("Confirm the request before generating counts."))
            for wh_line in rec.warehouse_line_ids:
                if wh_line.count_id:
                    # Already generated previously; skip without raising so the
                    # action remains re-runnable if some lines were added late.
                    continue
                planned = wh_line.planned_date or rec.planned_date
                users = wh_line.user_ids or rec.user_ids
                # Default location = the warehouse's main stock location.
                # Users can change per-line on the count form if needed.
                default_loc = wh_line.warehouse_id.lot_stock_id
                line_vals = [(0, 0, {
                    'product_id': p.id,
                    'location_id': default_loc.id,
                }) for p in rec.product_ids]
                count = Count.create({
                    'date': planned,
                    'warehouse_id': wh_line.warehouse_id.id,
                    'line_ids': line_vals,
                })
                wh_line.count_id = count.id

                # Notify: subscribe + activity-to-do per user. Activities give
                # users a real dashboard task with a deadline rather than just
                # an email they may ignore.
                if users:
                    count.message_subscribe(partner_ids=users.mapped('partner_id').ids)
                    for user in users:
                        count.activity_schedule(
                            'mail.mail_activity_data_todo',
                            date_deadline=planned,
                            summary=_("Conduct stock count at %s") % wh_line.warehouse_id.display_name,
                            note=_(
                                "Stock count requested via %s. "
                                "Please conduct the count of the listed products "
                                "at %s on %s."
                            ) % (rec.name, wh_line.warehouse_id.display_name, planned),
                            user_id=user.id,
                        )
                    count.message_post(
                        body=_("Generated from stock count request <b>%s</b>. Assigned to: %s")
                             % (rec.name, ", ".join(users.mapped('name')))
                    )
                else:
                    count.message_post(
                        body=_("Generated from stock count request <b>%s</b>. No responsible users assigned.")
                             % rec.name
                    )
            rec.state = 'generated'

    def action_view_counts(self):
        self.ensure_one()
        return {
            'name': _('Generated Stock Counts'),
            'type': 'ir.actions.act_window',
            'res_model': 'warehouse.stock.count',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.generated_count_ids.ids)],
        }


class WarehouseStockCountRequestWarehouse(models.Model):
    """Per-warehouse line on a stock count request. Holds the optional
    overrides for date and responsible users, plus the back-link to the
    generated warehouse.stock.count record (once produced)."""
    _name = 'warehouse.stock.count.request.warehouse'
    _description = 'Stock Count Request - Warehouse Line'

    request_id = fields.Many2one(
        'warehouse.stock.count.request',
        required=True, ondelete='cascade', index=True,
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        required=True,
        domain="[('daily_stock_count', '=', True)]",
    )
    planned_date = fields.Date(
        string='Date',
        help="Date this warehouse will be counted. Prefilled from the request's "
             "main date when the warehouse is added; edit freely to override.",
    )
    user_ids = fields.Many2many(
        'res.users',
        'rel_count_request_wh_users', 'wh_line_id', 'user_id',
        string='Responsible Users',
        help="Users responsible for conducting this count. Prefilled from the "
             "request's main users when the warehouse is added; edit freely to override.",
    )
    count_id = fields.Many2one(
        'warehouse.stock.count',
        string='Generated Count',
        readonly=True, copy=False,
    )
    parent_state = fields.Selection(related='request_id.state', store=False)

    _sql_constraints = [
        ('unique_warehouse_per_request',
         'unique(request_id, warehouse_id)',
         'A warehouse can only appear once per request.'),
    ]

    @api.constrains('warehouse_id', 'request_id')
    def _check_unique_warehouse(self):
        # SQL constraint above is the DB-level safety net. This Python check
        # fires earlier in the ORM validation cycle and shows a friendly
        # message instead of Postgres' raw "duplicate key" output (which leaks
        # through when constraint names are auto-hashed by the ORM).
        for line in self:
            if not line.warehouse_id or not line.request_id:
                continue
            duplicate = self.search([
                ('request_id', '=', line.request_id.id),
                ('warehouse_id', '=', line.warehouse_id.id),
                ('id', '!=', line.id),
            ], limit=1)
            if duplicate:
                raise ValidationError(_(
                    "Warehouse '%s' appears more than once on this request. "
                    "Each warehouse can only have a single entry — remove the duplicate row."
                ) % line.warehouse_id.display_name)

    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        # Pre-fill date and users from the parent when the warehouse is picked,
        # but only if the line doesn't already have its own values. The user
        # can still freely overwrite either field afterwards.
        if self.request_id and self.warehouse_id:
            if not self.planned_date and self.request_id.planned_date:
                self.planned_date = self.request_id.planned_date
            if not self.user_ids and self.request_id.user_ids:
                self.user_ids = self.request_id.user_ids
