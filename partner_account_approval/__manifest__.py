{
    "name": "Partner Account Approval",
    "version": "17.0.4.0.0",
    "summary": "Approve partner receivable and payable account changes before transactions are created",

    "description": """
Partner Account Approval
========================

This module introduces a controlled approval workflow for customer and vendor
receivable/payable account changes using the standard Odoo Approvals app.

Key Features
------------

* Independent receivable and payable approval controls per company.
* Immediate approval request creation when an account is changed.
* Support for newly created partners.
* Posting warnings on invoices, bills, payments and journal entries.
* Configurable posting scope:

  * block only the account pending approval; or
  * block all receivable/payable accounts for the partner.

* Approval, rejection and cancellation audit messages in partner chatter.
* Reliable rollback using account approval history.
* Multi-company account-history security.
* Configuration available from both the company form and Accounting settings.
* Smart buttons for approval requests and account approval history.

Workflow
--------

1. A user changes the receivable or payable account on a partner.
2. The module records the proposed change and creates an Approval Request.
3. Draft accounting documents may be saved.
4. Posting is blocked according to the selected company blocking scope.
5. On approval, the proposed account becomes the latest approved account.
6. On rejection or cancellation, the latest approved account is restored.
7. Every outcome is recorded in chatter and account approval history.

See the Documentation tab for the complete configuration and usage guide.
""",
    "author": "Sana Ullah Khan",
    "depends": ["account", "contacts", "approvals"],
    "data": [
        "security/partner_account_history_security.xml",
        "security/ir.model.access.csv",
        "data/approval_category.xml",
        "views/res_company_views.xml",
        "views/res_config_settings_views.xml",
        "views/res_partner_views.xml",
        "views/partner_account_history_views.xml",
        "views/approval_request_views.xml",
        "views/account_move_views.xml",
        "views/account_payment_views.xml"
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False
}
