# -*- coding: utf-8 -*-
# from odoo import http


# class StockStorageLocation(http.Controller):
#     @http.route('/stock_storage_location/stock_storage_location', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/stock_storage_location/stock_storage_location/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('stock_storage_location.listing', {
#             'root': '/stock_storage_location/stock_storage_location',
#             'objects': http.request.env['stock_storage_location.stock_storage_location'].search([]),
#         })

#     @http.route('/stock_storage_location/stock_storage_location/objects/<model("stock_storage_location.stock_storage_location"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('stock_storage_location.object', {
#             'object': obj
#         })

