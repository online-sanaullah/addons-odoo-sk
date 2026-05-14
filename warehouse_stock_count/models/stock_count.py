from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError, ValidationError
from markupsafe import Markup
import json
import logging
_logger = logging.getLogger('Stock-Count')

class ApprovalProductLine(models.Model):
    _inherit = 'approval.product.line'
    
    location_id = fields.Many2one('stock.location', string='Location')
    warehouse_id = fields.Many2one(comodel_name='stock.warehouse', string='Warehouse')
    show_location = fields.Boolean(string='Show Location')

class ApprovalCategory(models.Model):
    _inherit = 'approval.category'
    
    inventory_adjustment = fields.Boolean(string='Inventory Adjustment')
    
class ApprovalRequest(models.Model):
    _inherit = 'approval.request'
    
    hide_product_location = fields.Boolean(string='Hide Product Location', default=True)
    
    def action_approve(self, approver=None):
        result = super().action_approve(approver=approver)
        self.ensure_one()
        if self.category_id.inventory_adjustment:
            warehouse_stock_count_found = self.env['warehouse.stock.count'].search([('approval_request_id', '=', self.id)])
            warehouse_stock_count_found.action_apply_inventory_adjustment()
        return result

class Warehouse(models.Model):
    _inherit = 'stock.warehouse'
    
    daily_stock_count = fields.Boolean(string='Daily Stock Count')
    daily_count_product_ids = fields.Many2many(comodel_name='product.product', relation='rel_warehouse_daily_count_products', column1='warehouse_id', column2='product_id', string='Daily Count Products')
    daily_count_user_ids = fields.Many2many(comodel_name='res.users', relation='rel_warehouse_daily_count_users', column1='warehouse_id', column2='user_id', string='Users Allowed for Stock Count')
    
class Products(models.Model):
    _inherit = 'product.product'

    daily_count_warehouse_ids = fields.Many2many(comodel_name='stock.warehouse', relation='rel_warehouse_daily_count_products', column1='product_id', column2='warehouse_id', string='Daily Count Warehouse')

    # Variant-level smart button: scoped to this specific product.product so users
    # can drill in directly from a variant form (no group-by gymnastics).
    stock_count_line_count = fields.Integer(
        string='Stock Count Lines',
        compute='_compute_stock_count_line_count',
    )

    def _compute_stock_count_line_count(self):
        line_model = self.env['warehouse.stock.count.line']
        for rec in self:
            rec.stock_count_line_count = line_model.search_count(
                [('product_id', '=', rec.id)]
            )

    def action_view_stock_count_lines(self):
        self.ensure_one()
        return {
            'name': _('Stock Count History — %s') % self.display_name,
            'type': 'ir.actions.act_window',
            'res_model': 'warehouse.stock.count.line',
            'view_mode': 'graph,pivot,tree',
            'views': [
                (self.env.ref('warehouse_stock_count.product_stock_count_line_graph_view').id, 'graph'),
                (self.env.ref('warehouse_stock_count.warehouse_stock_count_line_pivot_view').id, 'pivot'),
                (self.env.ref('warehouse_stock_count.warehouse_stock_count_line_tree_view').id, 'tree'),
            ],
            'search_view_id': self.env.ref('warehouse_stock_count.warehouse_stock_count_line_search_view').id,
            'domain': [('product_id', '=', self.id)],
            'context': {},
        }

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    stock_count_line_count = fields.Integer(
        string='Stock Count Lines',
        compute='_compute_stock_count_line_count',
    )

    def _compute_stock_count_line_count(self):
        # Count across all variants of each template. search_count traverses
        # product_id.product_tmpl_id via JOIN; smart-button compute is per-form
        # so N is typically 1 — no need to batch.
        line_model = self.env['warehouse.stock.count.line']
        for rec in self:
            rec.stock_count_line_count = line_model.search_count(
                [('product_id.product_tmpl_id', '=', rec.id)]
            )

    def action_view_stock_count_lines(self):
        self.ensure_one()
        return {
            'name': _('Stock Count History — %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'warehouse.stock.count.line',
            'view_mode': 'graph,pivot,tree',
            # Explicit view tuples: graph uses the product-specific graph view
            # (line chart, counted qty per location over time); pivot and tree
            # reuse the line-explorer views.
            'views': [
                (self.env.ref('warehouse_stock_count.product_stock_count_line_graph_view').id, 'graph'),
                (self.env.ref('warehouse_stock_count.warehouse_stock_count_line_pivot_view').id, 'pivot'),
                (self.env.ref('warehouse_stock_count.warehouse_stock_count_line_tree_view').id, 'tree'),
            ],
            'search_view_id': self.env.ref('warehouse_stock_count.warehouse_stock_count_line_search_view').id,
            'domain': [('product_id.product_tmpl_id', '=', self.id)],
            'context': {},
            'help': '<p class="o_view_nocontent_smiling_face">%s</p><p>%s</p>' % (
                _('No stock count records for this product yet'),
                _('Stock count lines appear here once this product is included in a daily warehouse count.'),
            ),
        }
    
class StockMove(models.Model):
    _inherit = 'stock.move'
    
    stock_count_id = fields.Many2one(comodel_name='warehouse.stock.count', string='Daily Stock Count')
    
    @api.model_create_multi
    def create(self, vals_list):
        if vals_list and self._context.get('apply_stock_count_id', False):
            for vals in vals_list:
                vals.update({'stock_count_id': self._context.get('apply_stock_count_id')})
        return super().create(vals_list)
    
class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'
    
    stock_count_id = fields.Many2one(comodel_name='warehouse.stock.count', string='Daily Stock Count')
    
    @api.model_create_multi
    def create(self, vals_list):
        if vals_list and self._context.get('apply_stock_count_id', False):
            for vals in vals_list:
                vals.update({'stock_count_id': self._context.get('apply_stock_count_id')})
        return super().create(vals_list)

class WarehouseStockCount(models.Model):
    _name = 'warehouse.stock.count'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Warehouse Stock Count'

    name = fields.Char(default='Stock Count', tracking=True, compute='_get_name')
    date = fields.Date(required=True, default=fields.Date.today, tracking=True, copy=False)
    warehouse_id = fields.Many2one('stock.warehouse', required=True, tracking=True, domain="[('daily_stock_count', '=', True)]")
    state = fields.Selection([('draft', 'Draft'), ('validated', 'Validated'), ('pending', 'Submitted'), ('approved', 'Approved'), ('refused', 'Refused'), ('adjusted', 'Adjusted'), ('cancel', 'Cancel')], default='draft', tracking=True, copy=False)
    barcode = fields.Char()
    line_ids = fields.One2many('warehouse.stock.count.line', 'count_id')
    adjustment_move_ids = fields.One2many(comodel_name='stock.move', inverse_name='stock_count_id', string='Adjustment Moves')
    adjustment_move_line_ids = fields.One2many(comodel_name='stock.move.line', inverse_name='stock_count_id', string='Adjusment Product Moves')
    adjustment_moves_count = fields.Integer(string='Adjustment Moves Count', compute='_get_moves_count')
    line_ids_count = fields.Integer(string='Lines Count', compute='_compute_line_ids_count')
    approval_request_id = fields.Many2one(comodel_name='approval.request', string='Approval Request')
    warehouse_id_domain = fields.Char(compute="_compute_warehouse_id_domain", readonly=True)

    @api.constrains('date', 'warehouse_id', 'state')
    def _check_unique_active_count(self):
        # Only one active (non-cancelled) count per (warehouse, date). Cancelled
        # records are excluded so a count can be cancelled and re-entered the
        # same day for the same warehouse without hitting the constraint.
        #
        # ORM-level @api.constrains rather than a SQL unique index because the
        # exclusion 'state != cancel' would require a partial index, which
        # makes migrations and DB portability messier. The Python check runs
        # on every create/write touching these three fields, which is the
        # only path that can introduce a duplicate.
        for rec in self:
            if rec.state == 'cancel':
                continue
            if not rec.warehouse_id or not rec.date:
                continue
            duplicate = self.search([
                ('id', '!=', rec.id),
                ('warehouse_id', '=', rec.warehouse_id.id),
                ('date', '=', rec.date),
                ('state', '!=', 'cancel'),
            ], limit=1)
            if duplicate:
                raise ValidationError(_(
                    "An active stock count for warehouse '%(warehouse)s' on "
                    "%(date)s already exists (%(existing)s). Cancel it first "
                    "or pick a different date."
                ) % {
                    'warehouse': rec.warehouse_id.display_name,
                    'date': rec.date,
                    'existing': duplicate.display_name,
                })

    @api.depends('date', 'state')
    def _compute_warehouse_id_domain(self):
        for rec in self:
            # Find warehouses with daily stock count enabled where user is allowed access
            warehouse_ids = self.env['stock.warehouse'].search([('daily_stock_count', '=', True),
                                                ('daily_count_user_ids', '=', self.env.user.id)])
            # Format as a standard Odoo domain string
            #if warehouse_ids:
            rec.warehouse_id_domain = json.dumps([('id', 'in', warehouse_ids.ids)])
            #else:
            #    rec.warehouse_id_domain = json.dumps([])
    
    @api.depends('state', 'adjustment_move_ids')
    def _get_moves_count(self):
        for rec in self:
            rec.adjustment_moves_count = len(rec.adjustment_move_line_ids)

    @api.depends('line_ids')
    def _compute_line_ids_count(self):
        for rec in self:
            rec.line_ids_count = len(rec.line_ids)

    def action_view_lines(self):
        """Open this count's product lines in a full-screen searchable list.
        Inline tree on the form is fine for short counts but gets unwieldy at
        scale; this gives users the explorer-style search, multi-edit, and
        column-toggle UX while staying scoped to a single count.

        UI affordances (add line / edit / delete) are suppressed via context
        keys when the parent count is not in draft. Model-level guards on the
        line model provide the authoritative enforcement."""
        self.ensure_one()
        is_draft = self.state == 'draft'
        return {
            'name': _('Product Lines — %s') % self.display_name,
            'type': 'ir.actions.act_window',
            'res_model': 'warehouse.stock.count.line',
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref('warehouse_stock_count.warehouse_stock_count_line_editable_tree_view').id, 'tree'),
                (False, 'form'),
            ],
            'search_view_id': self.env.ref('warehouse_stock_count.warehouse_stock_count_line_search_view').id,
            'domain': [('count_id', '=', self.id)],
            # default_count_id ties newly created lines to this count automatically.
            # default_state mirrors the count's state onto the line for any
            # readonly logic that depends on it.
            # create/edit/delete flags are framework-respected hints that hide
            # the matching UI affordances. Not authoritative — model-level
            # overrides enforce the rule for API/automated paths.
            'context': {
                'default_count_id': self.id,
                'default_state': self.state,
                'create': is_draft,
                'edit': is_draft,
                'delete': is_draft,
            },
        }

    @api.depends('date', 'warehouse_id')
    def _get_name(self):
        for rec in self:
            name = ""
            if rec.date:
                name += f"{rec.date.strftime('%Y-%m-%d')}"
            if rec.warehouse_id:
                name += f" {rec.warehouse_id.name}"
            rec.name = name
    
    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        if not self.warehouse_id:
            self.line_ids = [(5, 0, 0)]
            return
        location = self.warehouse_id.lot_stock_id
        previous_stock_count = self.search([('warehouse_id', '=', self.warehouse_id.id), ('state', 'not in', ['draft', 'cancel'])], limit=1, order="date desc, create_date desc")
        if previous_stock_count:
            products = previous_stock_count.mapped('line_ids.product_id')
        elif self.warehouse_id.daily_count_product_ids:
            products = self.warehouse_id.daily_count_product_ids
        else:
            quants = self.env['stock.quant'].search([
            ('location_id', 'child_of', location.id),
            ('quantity', '>', 0)
            ])
            
            products = quants.mapped('product_id')
        
        if products:
            lines = []
            #warehouse_locations = self.env['stock.location'].search([('usage', '=', 'internal'), ('id', 'child_of', self.warehouse_id.lot_stock_id.id)])
            
            for product in products:
                product_quants = self.env['stock.quant'].search([('location_id', 'child_of', location.id),
                                                                 ('quantity', '>', 0), ('product_id', '=', product.id)])
                for quant in product_quants:
                    lines.append((0, 0, {
                        'product_id': quant.product_id.id,
                        'location_id': quant.location_id.id,
                        'theoretical_qty': quant.product_id.with_context(location=quant.location_id.id, to_date=self.date.strftime('%Y-%m-%d 23:59:59')).qty_available,
                        }))
                if not product_quants:
                    lines.append((0, 0, {
                        'product_id': product.id,
                        'location_id': location.id,
                        'theoretical_qty': product.with_context(location=location.id, to_date=self.date.strftime('%Y-%m-%d 23:59:59')).qty_available,
                        }))
            
            self.line_ids = [(5, 0, 0)] + lines

    def action_validate(self):
        if not self.env.user.has_group('stock.group_stock_manager'):
            raise AccessError('Only Inventory Managers can validate stock counts.')
        self.state = 'validated'
        self.message_post(body="Stock count validated and locked by manager.")
        
    def action_approval_request(self):
        self.ensure_one()
        if not self.approval_request_id or (self.approval_request_id and self.approval_request_id.request_status in ('refused', 'cancel')):
            product_ids = self.line_ids
            reason = "Daily stock count"
            lines = []
            name = ''
            #location = self.warehouse_id.lot_stock_id
            for line in product_ids:
                product = line
                quant = self.env['stock.quant'].search([
                        ('location_id', 'child_of', line.location_id.id),
                        ('product_id', '=', line.product_id.id)
                        ])
                name = name +'/'+product.product_id.name
                lines.append([0,0,{'product_id':product.product_id.id,
                                   'show_location': True,
                                   'location_id': line.location_id.id,
                                   'warehouse_id': self.warehouse_id.id,
                                   'on_hand': product.theoretical_qty,
                                   'quantity':product.counted_qty,
                                   'adjustment':True
                                   }])
                
            approval_params = [('inventory_adjustment', '=', True), ('company_id', '=', self.warehouse_id.company_id.id)]
            if self.warehouse_id.division_id:
                #name_search = 'Product Adjustment NHL'
                approval_params.append(('division_ids', '=', self.warehouse_id.division_id.id))
            
            approval_type = self.env['approval.category'].search(approval_params, limit=1)
            if approval_type:
                approval_request = self.env['approval.request'].create({
                    'category_id': approval_type.id,
                    'name': approval_type.name + name,
                    'request_owner_id': self.env.user.id,
                    'reason': reason,
                    'product_line_ids': lines,  # Link to the product
                    'hide_product_location': False,
                })
                self.approval_request_id = approval_request.id
                approval_request.action_confirm()
                
                # # If a file was uploaded, create an attachment
                # if self.file_ids:
                #     # Create attachments for each file uploaded
                #     for file in self.file_ids:
                #         self.env['ir.attachment'].create({
                #
                #             'type': 'binary',
                #             'datas': file.file_upload,
                #             'res_model': 'approval.request',
                #             'res_id': approval_request.id,
                #             'mimetype': 'application/octet-stream'  # Adjust the mimetype if necessary
                #         })
                # else:
                #     raise ValidationError(_("Please upload the approval files while generating the request."))
            else:
                raise ValidationError(_("Please create a suitable Approval category.\nPlease Contact the Administrator."))
        if self.approval_request_id and self.approval_request_id.request_status != 'new':
            self.state = self.approval_request_id.request_status
        
    def action_apply_inventory_adjustment(self):
        self.ensure_one()

        # 🔐 Manager only
        if not self.env.user.has_group("stock.group_stock_manager"):
            raise UserError(_("Only Stock Managers can apply inventory adjustments."))

        if self.state not in ["validated", "pending"]:
            raise UserError(_("Stock count must be validated first."))

        Quant = self.env["stock.quant"]
        location = self.warehouse_id.lot_stock_id

        for line in self.line_ids.filtered(lambda l: l.difference != 0):

            # 1️⃣ Find quant (or create virtual one)
            quant = Quant.search([
                        ('location_id', '=', line.location_id.id),
                        ('product_id', '=', line.product_id.id)
                        ])
            
            if not quant:
                _logger.info(f'stock not found for {line.product_id.name} on {line.location_id.name}')
                quant = Quant.create({'location_id': line.location_id.id, 'product_id': line.product_id.id})

            # 2️⃣ Set inventory quantity
            quant.inventory_quantity = line.counted_qty
            quant.inventory_quantity_set = True

            # 3️⃣ Apply adjustment (creates stock.move internally)
            quant.with_context(force_system_operation=True, apply_stock_count_id=self.id).action_apply_inventory()

            # 🧾 Chatter log
            self.message_post(
                body=Markup(f"Inventory adjusted for <b>{line.product_id.display_name}</b><br/>"
                    f"System Qty: {line.theoretical_qty}<br/>"
                    f"Counted Qty: {line.counted_qty}<br/>"
                    f"Variance: {line.difference}"),
                subject="Inventory Adjustment",
                message_type="notification",
                subtype_xmlid="mail.mt_note")

        self.state = "adjusted"

    def action_adjustment_product_moves(self):
        self.ensure_one()
        action = {
            "name": _(
                "Stock Adjustment: %(location_name)s",
                location_name=f"{self.warehouse_id.name}",
            ),
            "view_mode": "list,form",
            "res_model": "stock.move.line",
            "views": [
                (
                    self.env.ref(
                        "stock_move_value_amount.view_stock_move_line_location_tree"
                    ).id,
                    "list",
                ),
                (False, "form"),
            ],
            "type": "ir.actions.act_window",
            "context": {'create':False, 'edit': False},
            "domain": [
                ("stock_count_id", "in", self.ids),
            ],
        }
        return action

class WarehouseStockCountLine(models.Model):
    _name = 'warehouse.stock.count.line'
    _description = 'Warehouse Stock Count Line'
    _order = 'date desc, count_id desc, id desc'

    count_id = fields.Many2one('warehouse.stock.count', ondelete='cascade')
    # Stored related fields enable group-by, ordering, and pivot/graph aggregation
    # directly on the line model without forcing a JOIN on every query. Indexes
    # on the high-cardinality dimensions used in filters and sorts.
    state = fields.Selection(related='count_id.state', string='State', store=True)
    date = fields.Date(related='count_id.date', string='Date', store=True, index=True)
    warehouse_id = fields.Many2one(related='count_id.warehouse_id', string='Warehouse', store=True, index=True)
    company_id = fields.Many2one(related='count_id.warehouse_id.company_id', string='Company', store=True)
    product_id = fields.Many2one('product.product', required=True, index=True)
    product_categ_id = fields.Many2one(related='product_id.categ_id', string='Product Category', store=True)
    location_id_domain = fields.Char(compute="_compute_location_id_domain", readonly=True)
    location_id = fields.Many2one(comodel_name='stock.location', string='Location', index=True)
    theoretical_qty = fields.Float(string="On Hand Qty.")
    counted_qty = fields.Float(tracking=True)
    difference = fields.Float(compute='_compute_difference', store=True)
    source_location_id = fields.Many2one(comodel_name='stock.location', string='Source Location')
    add_new_product = fields.Boolean(string='Filter Product Locations', default=False)

    # User-editable fields. A write that only touches fields outside this set
    # is treated as automated/internal (e.g. related-field sync when the
    # parent transitions state, or compute store refreshes) and bypasses the
    # "draft-only" guard. Includes count_id so a line can't be re-parented
    # to a non-draft count either.
    _USER_EDITABLE_FIELDS = frozenset({
        'product_id', 'location_id', 'counted_qty', 'theoretical_qty',
        'source_location_id', 'add_new_product', 'count_id',
    })

    def _ensure_count_in_draft(self, action_verb):
        """Block the operation if any record's parent count is not draft."""
        for line in self:
            count = line.count_id
            if count and count.state and count.state != 'draft':
                state_label = dict(
                    count._fields['state']._description_selection(self.env)
                ).get(count.state, count.state)
                raise UserError(_(
                    "Cannot %(verb)s product lines: stock count "
                    "'%(count)s' is no longer in Draft (current state: "
                    "%(state)s). Product lines can only be modified while "
                    "the count is in Draft."
                ) % {
                    'verb': action_verb,
                    'count': count.display_name,
                    'state': state_label,
                })

    @api.model_create_multi
    def create(self, vals_list):
        # Check parent state before creating. When lines are created via the
        # parent's o2m write — e.g. Count.create({'line_ids': [(0,0,{...})]})
        # — the framework injects count_id into each line's vals. Untethered
        # lines (no count_id at all) skip the check.
        for vals in vals_list:
            count_id = vals.get('count_id') or self.env.context.get('default_count_id')
            if count_id:
                count = self.env['warehouse.stock.count'].browse(count_id)
                if count.state and count.state != 'draft':
                    state_label = dict(
                        count._fields['state']._description_selection(self.env)
                    ).get(count.state, count.state)
                    raise UserError(_(
                        "Cannot add product lines: stock count "
                        "'%(count)s' is no longer in Draft (current state: "
                        "%(state)s)."
                    ) % {'count': count.display_name, 'state': state_label})
        return super().create(vals_list)

    def write(self, vals):
        # Only block writes that actually touch user-editable fields. Writes
        # that only update related/computed columns (e.g. line.state syncing
        # when the parent transitions, or product_categ_id refreshing) pass
        # through untouched so workflow transitions still work.
        if set(vals) & self._USER_EDITABLE_FIELDS:
            self._ensure_count_in_draft('modify')
        return super().write(vals)

    def unlink(self):
        self._ensure_count_in_draft('remove')
        return super().unlink()

    @api.constrains('product_id', 'location_id', 'count_id')
    def _check_unique_product_location(self):
        # Within a single stock count, each (product, location) pair can only
        # appear once. Skip lines that aren't fully populated yet — partial
        # lines arise during inline editing and shouldn't trigger the check
        # until both fields are set.
        for line in self:
            if not line.product_id or not line.location_id or not line.count_id:
                continue
            duplicate = self.search([
                ('id', '!=', line.id),
                ('count_id', '=', line.count_id.id),
                ('product_id', '=', line.product_id.id),
                ('location_id', '=', line.location_id.id),
            ], limit=1)
            if duplicate:
                raise ValidationError(_(
                    "Product '%(product)s' at location '%(location)s' is "
                    "already on this stock count. Each product/location pair "
                    "can only appear once per count."
                ) % {
                    'product': line.product_id.display_name,
                    'location': line.location_id.display_name,
                })

    # ---- Historical context (non-stored, optional='hide' in tree view) ---- #
    # These are deliberately NOT stored: a stored compute would force a backfill
    # on module update and would re-trigger on every stock.move validation,
    # which doesn't scale on busy databases. As optional='hide' columns they
    # only compute when the user actively toggles them on in the list view.
    last_count_date = fields.Date(
        string='Last Count Date',
        compute='_compute_history_fields',
        help="Date of the most recent prior count for this product at this location.",
    )
    last_count_qty = fields.Float(
        string='Last Counted Qty',
        compute='_compute_history_fields',
        help="Counted quantity recorded at the previous count.",
    )
    in_qty_since_last_count = fields.Float(
        string='Units In Since Last Count',
        compute='_compute_history_fields',
        help="Total quantity received into this location for this product since the previous count.",
    )
    out_qty_since_last_count = fields.Float(
        string='Units Out Since Last Count',
        compute='_compute_history_fields',
        help="Total quantity dispatched from this location for this product since the previous count.",
    )

    @api.depends('product_id', 'location_id', 'date')
    def _compute_history_fields(self):
        """Shared compute for all four history columns. Per record:
          1. Find the most recent prior line for the same (product, location).
          2. Aggregate stock.move.line in/out between that line's date and this one.
        Step 2 uses read_group to do all the aggregation in a single SQL pass."""
        Line = self.env['warehouse.stock.count.line']
        StockMoveLine = self.env['stock.move.line']

        # Initialize to defaults so even records missing data return well-defined values.
        for rec in self:
            rec.last_count_date = False
            rec.last_count_qty = 0.0
            rec.in_qty_since_last_count = 0.0
            rec.out_qty_since_last_count = 0.0

        # Filter to records that can meaningfully have history.
        candidates = self.filtered(lambda l: l.product_id and l.location_id and l.date)
        if not candidates:
            return

        # Phase 1: previous-count lookup per record. Strict 'date <' so a line
        # never pairs with another line on the same day (avoids ambiguity).
        prev_by_id = {}
        for rec in candidates:
            prev = Line.search([
                ('product_id', '=', rec.product_id.id),
                ('location_id', '=', rec.location_id.id),
                ('date', '<', rec.date),
            ], order='date desc, id desc', limit=1)
            if prev:
                prev_by_id[rec.id] = prev
                rec.last_count_date = prev.date
                rec.last_count_qty = prev.counted_qty

        if not prev_by_id:
            return

        # Phase 2: aggregate stock moves. One read_group per direction across
        # all relevant (product, location) combos, then attribute totals to
        # each line in Python. Bounded by the number of visible rows.
        product_ids = list({prev_by_id[rid].product_id.id for rid in prev_by_id} |
                           {candidates.browse(rid).product_id.id for rid in prev_by_id})
        location_ids = list({prev_by_id[rid].location_id.id for rid in prev_by_id})
        earliest = min(prev_by_id[rid].date for rid in prev_by_id)
        latest = max(candidates.browse(rid).date for rid in prev_by_id)

        base_domain = [
            ('product_id', 'in', product_ids),
            ('state', '=', 'done'),
            ('date', '>', earliest),
            ('date', '<=', latest),
        ]
        in_groups = StockMoveLine.read_group(
            domain=base_domain + [('location_dest_id', 'in', location_ids)],
            fields=['product_id', 'location_dest_id', 'date:day', 'quantity:sum'],
            groupby=['product_id', 'location_dest_id', 'date:day'],
            lazy=False,
        )
        out_groups = StockMoveLine.read_group(
            domain=base_domain + [('location_id', 'in', location_ids)],
            fields=['product_id', 'location_id', 'date:day', 'quantity:sum'],
            groupby=['product_id', 'location_id', 'date:day'],
            lazy=False,
        )

        # Index the aggregates: {(product_id, location_id): [(date, qty), ...]}
        def _index(groups, loc_field):
            idx = {}
            for g in groups:
                pid = g['product_id'][0] if g['product_id'] else False
                lid = g[loc_field][0] if g[loc_field] else False
                # date:day comes back as 'YYYY-MM-DD' string in some versions
                # and as a date in others; normalize.
                d = g['date:day']
                if isinstance(d, str):
                    d = fields.Date.to_date(d)
                idx.setdefault((pid, lid), []).append((d, g['quantity'] or 0.0))
            return idx

        in_idx = _index(in_groups, 'location_dest_id')
        out_idx = _index(out_groups, 'location_id')

        for rec in candidates.browse(list(prev_by_id.keys())):
            prev = prev_by_id[rec.id]
            key = (rec.product_id.id, rec.location_id.id)
            # Slice the aggregates by the per-record date window (prev.date, rec.date]
            rec.in_qty_since_last_count = sum(
                qty for (d, qty) in in_idx.get(key, []) if prev.date < d <= rec.date
            )
            rec.out_qty_since_last_count = sum(
                qty for (d, qty) in out_idx.get(key, []) if prev.date < d <= rec.date
            )
    
    
    @api.depends('product_id')
    def _compute_location_id_domain(self):
        for rec in self:
            if rec.product_id:
                # Find locations with stock for this product
                quants = self.env['stock.quant'].search([
                    ('product_id', '=', rec.product_id.id),
                    ('quantity', '>', 0), ('location_id', 'child_of', rec.count_id.warehouse_id.lot_stock_id.id),
                    ('location_id.usage', '=', 'internal')
                ])
                location_ids = quants.mapped('location_id').ids
                # Format as a standard Odoo domain string
                if location_ids:
                    rec.location_id_domain = json.dumps([('id', 'in', location_ids)])    
                elif rec.product_id and rec.count_id and rec.count_id.warehouse_id:
                    rec.location_id_domain = json.dumps([('id', 'child_of', rec.count_id.warehouse_id.lot_stock_id.id)])
            else:
                rec.location_id_domain = json.dumps([])
                
    @api.onchange('product_id')
    def _onchange_product(self):
        location_id = False
        rec = self
        if self.product_id:
            
            quants = self.env['stock.quant'].search([
                    ('product_id', '=', rec.product_id.id),
                    ('quantity', '>', 0), ('location_id', 'child_of', rec.count_id.warehouse_id.lot_stock_id.id),
                    ('location_id.usage', '=', 'internal')
                ])
            location_ids = quants.mapped('location_id').ids
            if len(location_ids) == 1:
                location_id = location_ids[0]
            elif not location_ids:
                location_ids = self.env['stock.location'].search([('id', 'child_of', rec.count_id.warehouse_id.lot_stock_id.id)])
                if len(location_ids) == 1:
                    location_id = location_ids.ids[0]
        self.location_id = location_id

    @api.depends('product_id', 'location_id')
    def _get_quantity(self):
        for rec in self:
            theoretical_qty = 0
            if rec.product_id and rec.location_id:
                location = rec.location_id#rec.count_id.warehouse_id.lot_stock_id
                quants = self.env['stock.quant'].search([
                        ('location_id', 'child_of', location.id),
                        ('product_id', '=', rec.product_id.id)
                        ])
                theoretical_qty = sum(quants.mapped('quantity'))
            rec.theoretical_qty = theoretical_qty
            
    @api.model_create_multi
    def create(self, vals_list):
        result = super().create(vals_list)
        if result:
            result._get_quantity()
        return result

    @api.depends('theoretical_qty', 'counted_qty')
    def _compute_difference(self):
        for line in self:
            line.difference = (line.counted_qty or 0) - (line.theoretical_qty or 0)
            
            


