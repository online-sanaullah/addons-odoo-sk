{
    "name": "Product Variant Template Merge",
    "summary": "Combine existing product variants under a newly created product template",
    "version": "17.0.1.0.8",
    "category": "Sales/Products",
    "author": "Sana Ullah Khan",
    "license": "LGPL-3",
    "depends": ["product", "sale_product_configurator", "purchase_product_matrix"],
    "data": [
        "security/ir.model.access.csv",
        "views/sale_order_views.xml",
        "views/purchase_order_views.xml",
        "wizard/product_variant_combine_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
}
