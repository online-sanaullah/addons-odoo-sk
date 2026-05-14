{
    "name": "Warehouse Stock Count (Audit)",
    "version": "1.13",
    "category": "Inventory",
    "summary": "Report-only warehouse stock counts with audit trail, count requests, analytics, and historical context",
    "depends": ["stock", "mail", "report_xlsx", "base_approval_division", "base_warehouse_division"],
    "author": "Sanaullah Khan",
    "data": [
        "security/ir.model.access.csv",
        "views/stock_count_views.xml",
        "views/stock_count_request_views.xml",
    ],
    "installable": True,
}
