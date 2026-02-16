# -*- coding: utf-8 -*-
# from odoo import http


# class SaleOrderLineCost(http.Controller):
#     @http.route('/sale_order_line_cost/sale_order_line_cost', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/sale_order_line_cost/sale_order_line_cost/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('sale_order_line_cost.listing', {
#             'root': '/sale_order_line_cost/sale_order_line_cost',
#             'objects': http.request.env['sale_order_line_cost.sale_order_line_cost'].search([]),
#         })

#     @http.route('/sale_order_line_cost/sale_order_line_cost/objects/<model("sale_order_line_cost.sale_order_line_cost"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('sale_order_line_cost.object', {
#             'object': obj
#         })

