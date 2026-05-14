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
    date = fields.Date(required=True, default=fields.Date.today, tracking=True)
    warehouse_id = fields.Many2one('stock.warehouse', required=True, tracking=True, domain="[('daily_stock_count', '=', True)]")
    state = fields.Selection([('draft', 'Draft'), ('validated', 'Validated'), ('pending', 'Submitted'), ('approved', 'Approved'), ('refused', 'Refused'), ('adjusted', 'Adjusted'), ('cancel', 'Cancel')], default='draft', tracking=True)
    barcode = fields.Char()
    line_ids = fields.One2many('warehouse.stock.count.line', 'count_id')
    adjustment_move_ids = fields.One2many(comodel_name='stock.move', inverse_name='stock_count_id', string='Adjustment Moves')
    adjustment_move_line_ids = fields.One2many(comodel_name='stock.move.line', inverse_name='stock_count_id', string='Adjusment Product Moves')
    adjustment_moves_count = fields.Integer(string='Adjustment Moves Count', compute='_get_moves_count')
    approval_request_id = fields.Many2one(comodel_name='approval.request', string='Approval Request')
    warehouse_id_domain = fields.Char(compute="_compute_warehouse_id_domain", readonly=True)

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
    

    count_id = fields.Many2one('warehouse.stock.count', ondelete='cascade')
    state = fields.Selection(related='count_id.state', string='state')
    product_id = fields.Many2one('product.product', required=True)
    location_id_domain = fields.Char(compute="_compute_location_id_domain", readonly=True)
    location_id = fields.Many2one(comodel_name='stock.location', string='Location')
    theoretical_qty = fields.Float(string="On Hand Qty.")
    counted_qty = fields.Float(tracking=True)
    difference = fields.Float(compute='_compute_difference', store=True)
    source_location_id = fields.Many2one(comodel_name='stock.location', string='Source Location')
    add_new_product = fields.Boolean(string='Filter Product Locations', default=False)
    
    
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
            
            


