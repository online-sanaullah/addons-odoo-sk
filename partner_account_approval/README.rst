Partner Account Approval
========================

Overview
--------

``partner_account_approval`` adds a controlled approval process for changes to
partner receivable and payable accounts in Odoo 17.

The module integrates with the standard **Approvals** application and prevents
accounting transactions from being posted while a relevant account change is
pending approval.

Main Features
-------------

* Separate approval toggles for receivable and payable accounts.
* Immediate approval request creation when a partner account is changed.
* Support for both existing and newly created partners.
* Partner chatter audit trail for request, approval, rejection and cancellation.
* Dedicated account approval history model.
* Configurable journal-item blocking scope.
* Warning banners on invoices, vendor bills, payments and journal entries.
* Draft documents remain editable while posting is blocked.
* Multi-company configuration and history record rules.
* Configuration available on both the Company form and Accounting settings.
* Smart buttons for Approval Requests and Account History.

Installation
------------

1. Copy the ``partner_account_approval`` folder to an Odoo addons path.
2. Restart Odoo.
3. Update the Apps list.
4. Install **Partner Account Approval**.
5. Ensure the standard **Approvals** and **Accounting** applications are installed.

Configuration
-------------

Configuration is available from either:

* **Accounting → Configuration → Settings → Partner Account Approval**
* **Settings → Companies → open a company → Partner Account Approval**

The following settings are available.

Require Receivable Account Approval
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When enabled, changes to a partner's receivable account require approval.

Require Payable Account Approval
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When enabled, changes to a partner's payable account require approval.

Approval Category
~~~~~~~~~~~~~~~~~

Select the standard Approval Category that will receive partner account approval
requests.

Pending Approval Blocking Scope
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Two modes are available:

**Block Only the Pending Account**

Posting is blocked only when a journal item uses the exact receivable/payable
account that is pending approval.

**Block All Receivable/Payable Accounts for the Partner**

While approval is pending, all journal items on the relevant account side are
blocked for that partner.

Usage
-----

Changing a Partner Account
~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Open a customer or vendor.
2. Change the Receivable Account or Payable Account.
3. Save the partner.
4. The module creates an Approval Request immediately.
5. The partner displays the pending approval status and the related request.

Accounting Documents
~~~~~~~~~~~~~~~~~~~~

The workflow applies to:

* Customer invoices
* Customer credit notes
* Vendor bills
* Vendor credit notes
* Customer payments
* Vendor payments
* Manual journal entries

Draft documents may be created and saved. A warning appears at the top of the
form when approval is pending. Posting is blocked until the request is resolved.

Approval Outcomes
-----------------

Approved
~~~~~~~~

* The proposed account remains effective.
* The history entry becomes approved.
* The account becomes the latest approved rollback account.
* Posting restrictions are removed.
* The event is logged in partner chatter.

Rejected
~~~~~~~~

* The latest approved account is restored.
* The history entry becomes rejected.
* Posting restrictions are removed.
* The event is logged in partner chatter.

Cancelled from the Partner
~~~~~~~~~~~~~~~~~~~~~~~~~~

Cancellation is available only when an open request exists and a previously
approved account is available for every account side covered by the request.

On cancellation:

* The latest approved account is restored.
* The pending history entry becomes cancelled.
* The approval request is cancelled, withdrawn, or removed depending on the
  methods available in the installed Approvals build.
* The event is logged in partner chatter.

Account Approval History
------------------------

The module creates ``res.partner.account.approval.history`` records containing:

* Partner
* Company
* Receivable or payable side
* Previous approved account
* Proposed account
* Approval request
* Status
* Requesting user and date
* Resolving user and date

The partner form includes an **Account History** smart button.

Multi-Company Security
----------------------

Users can only view history records for companies included in their allowed
companies. History records from other companies are hidden through a record rule.

Troubleshooting
---------------

The warning does not appear
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Verify that:

* the relevant company approval toggle is enabled;
* the partner approval status is Pending;
* the current company matches the partner approval company;
* the module has been upgraded after replacing its source.

The cancel link is hidden
~~~~~~~~~~~~~~~~~~~~~~~~~

The cancel link is hidden when there is no previously approved account to restore,
which commonly occurs on a newly created partner awaiting its first approval.

A draft can be saved
~~~~~~~~~~~~~~~~~~~~

This is expected. The module blocks posting, not draft creation or editing.

Technical Summary
-----------------

Models extended:

* ``res.partner``
* ``res.company``
* ``res.config.settings``
* ``approval.request``
* ``account.move``
* ``account.payment``

Model added:

* ``res.partner.account.approval.history``

License
-------

LGPL-3


Approval Request Timing
-----------------------

Receivable and payable timing are configured independently:

* **Immediately After Account Change** — current account-change behaviour.
* **First Transaction for New Partner, Then Immediate** — the first request for
  a newly created partner is generated by the first relevant transaction. Once
  that approval is processed, subsequent changes generate requests immediately.
* **Next Transaction After Every Account Change** — each changed account waits
  for the next relevant transaction before a request is generated.

If an account is corrected while an Approval Request is open, the same request,
its proposed account, reason and pending history record are updated. Approval
therefore applies to the latest corrected account.
