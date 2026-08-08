# Odoo 17 Custom Addons

[![Odoo](https://img.shields.io/badge/Odoo-17.0-714B67.svg)](https://www.odoo.com/)
[![Addons](https://img.shields.io/badge/addons-16-blue.svg)](#addon-catalog)
[![License](https://img.shields.io/badge/license-mixed-lightgrey.svg)](#licensing)

A collection of custom Odoo 17 addons covering accounting reports, partner
account approvals, inventory auditing, product and pricelist management, sales
analysis, Point of Sale receipts, and user notifications.

The repository's default branch is `17.0`. Install only the addons required for
your database and test them on a staging copy before deploying to production.

## Contents

- [Addon catalog](#addon-catalog)
- [Detailed feature overview](#detailed-feature-overview)
  - [Accounting and finance](#accounting-and-finance)
  - [Inventory and warehouse](#inventory-and-warehouse)
  - [Products and pricing](#products-and-pricing)
  - [Sales, Point of Sale, and productivity](#sales-point-of-sale-and-productivity)
- [Requirements and dependencies](#requirements-and-dependencies)
- [Installation](#installation)
- [Updating an addon](#updating-an-addon)
- [Important implementation notes](#important-implementation-notes)
- [Licensing](#licensing)
- [Author and maintenance](#author-and-maintenance)

## Addon catalog

| Technical name | Version | Area | Purpose |
| --- | ---: | --- | --- |
| [`account_stock_move_smart_buttons`](account_stock_move_smart_buttons/) | 17.0.1.0.2 | Accounting / Inventory | Adds navigation between journal entries, stock moves, and stock pickings. |
| [`activity_dm_notification`](activity_dm_notification/) | 17.0.1.1.0 | Discuss / Activities | Sends the assignee an OdooBot direct message when an activity is assigned or reassigned. |
| [`monthly_trial_balance`](monthly_trial_balance/) | 17.0.1.0.0 | Accounting | Adds a month-by-month trial balance with opening, debit, credit, and ending balances. |
| [`monthly_trial_balance_analytic`](monthly_trial_balance_analytic/) | 17.0.1.0.0 | Accounting / Analytic | Adds a monthly trial balance broken down by analytic plan, analytic account, and general ledger account. |
| [`odoo_sale_order_line_views`](odoo_sale_order_line_views/) | 17.0.1.0.0 | Sales | Adds dedicated quotation-line and sale-order-line analysis menus and views. |
| [`partner_account_approval`](partner_account_approval/) | 17.0.4.0.0 | Accounting / Approvals | Controls changes to partner receivable and payable accounts through an approval workflow. |
| [`pos_google_review_qr`](pos_google_review_qr/) | 17.0.1.1.0 | Point of Sale | Prints a shop-specific Google review QR code on customer receipts. |
| [`pricelist_team_user_access`](pricelist_team_user_access/) | 17.0.1.14.0 | Sales / Pricing | Restricts pricelist visibility and modification by sales team and user. |
| [`product_qrcode`](product_qrcode/) | 17.0.1.0.1 | Products | Generates product QR codes from barcodes and prints compact QR labels. |
| [`product_tag_search_filters`](product_tag_search_filters/) | 17.0.1.0.0 | Products | Turns selected product tags into dynamic product search filters. |
| [`product_variant_template_merge`](product_variant_template_merge/) | 17.0.1.0.8 | Products | Combines existing product records into variants of a new product template while preserving product IDs. |
| [`sale_order_line_cost`](sale_order_line_cost/) | 0.1 | Sales / Accounting | Adds COGS, revenue, journal-entry, and accounting-date information to sale order lines. |
| [`stock_move_value_amount`](stock_move_value_amount/) | 0.3 | Inventory / Accounting | Shows accounting value, direction, journal entry, and transfer navigation on stock move lines. |
| [`stock_picking_qr`](stock_picking_qr/) | 1.0 | Inventory / Reports | Replaces picking-report barcodes with QR codes when enabled per warehouse. |
| [`stock_state_last_updated_by`](stock_state_last_updated_by/) | 17.0.1.6.0 | Inventory / Audit | Shows the user and date responsible for the latest stock status change. |
| [`warehouse_stock_count`](warehouse_stock_count/) | 1.13 | Inventory / Approvals | Adds controlled warehouse stock counts, count requests, variance analysis, approvals, and inventory adjustments. |

## Detailed feature overview

### Accounting and finance

#### `account_stock_move_smart_buttons`

Connects inventory valuation activity to its accounting entries.

- Adds **Stock Moves** and **Pickings** smart buttons to journal entries.
- Adds a **Journal Entries** smart button to stock pickings.
- Resolves standard links through stock valuation layers.
- Also supports installations that expose `account_move_ids` directly on
  `stock.move`.
- Opens a form directly when one related record exists and a filtered list when
  several records exist.

**Main dependencies:** `account`, `stock`

#### `monthly_trial_balance`

Adds **Accounting → Reporting → Monthly Trial Balance** using Odoo's accounting
report engine.

- Produces one line per general ledger account for every month in the selected
  date range.
- Shows year, month, initial balance, debit, credit, and ending balance.
- Supports date-range, posted/draft, analytic-account, multi-company, and search
  options.
- Prevents profit-and-loss accounts from carrying an opening balance into the
  report.
- Transfers prior profit-and-loss balances to the company's unaffected earnings
  account for opening-balance presentation.
- Uses SQL aggregation for large journal-item datasets.

**Main dependency:** `account_reports`

**Edition note:** `account_reports` is normally supplied by Odoo Enterprise.

#### `monthly_trial_balance_analytic`

Provides a detailed analytic allocation view of the monthly trial balance.

- Shows year, month, analytic plan, analytic account, account code, account,
  account type, opening balance, debit, credit, and ending balance.
- Expands the JSON analytic distribution stored on journal items.
- Applies analytic distribution percentages to debit, credit, and balance.
- Handles compound analytic-distribution keys containing accounts from more
  than one analytic plan.
- Carries balances month by month and handles current-year earnings through the
  unaffected earnings account.
- Supports date, journal, analytic, account, search/favorite, and multi-company
  filtering.
- Uses a PostgreSQL SQL view and window functions for reporting performance.
- Restricts report access to accounting users with read access.

**Main dependencies:** `account_reports`, `analytic`

**Edition note:** `account_reports` is normally supplied by Odoo Enterprise.

#### `partner_account_approval`

Adds a multi-company approval workflow for partner receivable and payable
account changes.

- Enables receivable and payable approval independently per company.
- Provides three independent trigger modes for each account side:
  - create a request immediately after an account change;
  - wait for the first relevant transaction for a new partner, then use
    immediate approval for later changes;
  - wait for the next relevant transaction after every account change.
- Creates and confirms requests in Odoo's standard **Approvals** application.
- Updates the existing open request, its reason, proposed account, and pending
  history when an account is corrected before approval.
- Shows approval status, warning banners, latest request, approval count, and
  account-history smart buttons on the partner.
- Allows draft invoices, bills, journal entries, and payments to be saved while
  approval is pending.
- Blocks posting of affected invoices, credit notes, vendor bills, vendor
  credits, manual journal entries, and payments.
- Can block only the exact account pending approval or all receivable/payable
  accounts for the partner.
- Marks approved accounts as the new baseline.
- Restores the latest approved account after refusal or an eligible
  cancellation.
- Logs request, update, approval, rejection, and cancellation events in partner
  chatter.
- Stores a permanent company-aware history of previous and proposed accounts,
  requesting/resolving users, dates, status, and approval request.
- Exposes configuration on both the company form and Accounting settings.

**Main dependencies:** `account`, `contacts`, `approvals`

**Documentation:** [module README](partner_account_approval/README.rst),
[workflow and configuration guides](partner_account_approval/doc/)

#### `sale_order_line_cost`

Extends the sale order line analysis supplied by
`odoo_sale_order_line_views`.

- Links each sale order line to its COGS journal entries through delivery stock
  valuation layers.
- Calculates COGS from journal items posted to direct-cost accounts.
- Links invoice journal entries and calculates recognized sales revenue from
  their debit/credit values.
- Stores order, earliest delivery, and earliest invoice dates for searching and
  grouping.
- Adds sales team and warehouse dimensions.
- Adds optional list columns for COGS and sales journal entries, COGS amount,
  revenue, delivery date, and invoice date.
- Adds order/delivery/invoice date filters and sales-team/warehouse groupings.
- Adds **Revenue** and **C.O.G.S.** filters to the Journal Items search view.

**Main dependencies:** `odoo_sale_order_line_views`, `account`

### Inventory and warehouse

#### `stock_move_value_amount`

Adds accounting context to individual stock move lines.

- Resolves the related stock journal entry.
- Displays its signed total value and currency.
- Classifies a movement as **IN**, **OUT**, or **Internal**.
- Can calculate direction relative to a location or warehouse supplied in the
  action context.
- Provides buttons to open the related journal entry and stock picking.
- Supplies a reusable movement list view with incoming/outgoing row decoration.

**Main dependency:** `stock_account`

#### `stock_picking_qr`

Adds QR codes to warehouse transfer documents.

- Computes a QR image containing the picking reference.
- Adds a warehouse-level **Show Picking QR in Report** toggle.
- Displays the generated QR on the picking form.
- Replaces the picking barcode on the delivery document with the QR when the
  warehouse setting is enabled.
- Can replace product barcodes in operation lines with each product's stored QR
  image when used together with `product_qrcode`.

**Main dependency:** `stock`

**Python requirement:** `qrcode` and its image backend

**Recommended companion addon:** `product_qrcode`

#### `stock_state_last_updated_by`

Adds audit information to stock lists without adding stored tracking columns.

- Shows **State Updated By**, **State Updated On**, and a technical source on:
  - stock pickings;
  - stock moves;
  - stock move lines.
- Reads the latest `state` change from Odoo chatter tracking values.
- Displays the responsible user with the standard user-avatar widget.
- For move lines without direct state tracking, falls back to their stock move
  and then their picking.
- Includes inventory-adjustment and create/write-user fallbacks when chatter
  tracking is unavailable.
- Keeps the fields non-stored so existing stock tables do not require a data
  backfill.

**Main dependencies:** `stock`, `mail`

#### `warehouse_stock_count`

Introduces a complete warehouse-counting and inventory-adjustment workflow.

- Enables daily stock counting per warehouse.
- Configures responsible users and an optional default product list on each
  warehouse.
- Restricts warehouse selection to enabled warehouses assigned to the current
  user.
- Builds count lines by product and internal location using:
  - the previous completed count;
  - the warehouse's configured count products; or
  - products with positive stock in the warehouse.
- Captures theoretical quantity, counted quantity, and variance for every
  product/location pair.
- Prevents duplicate active counts for the same warehouse and date and duplicate
  product/location lines inside one count.
- Provides a manager-controlled workflow:
  **Draft → Validated → Submitted → Approved → Adjusted**, with refusal and
  cancellation states.
- Creates an inventory-adjustment Approval Request containing product,
  warehouse, location, on-hand quantity, and counted quantity.
- Applies approved variances through Odoo's inventory-adjustment mechanism.
- Links the resulting stock moves and move lines back to the stock count.
- Logs adjustments in chatter and supports followers and activities.
- Adds multi-warehouse **Count Requests** with per-warehouse date and responsible
  user overrides.
- Generates one count per requested warehouse and schedules To Do activities
  with the planned count date as the deadline.
- Provides tree, form, calendar, graph, and pivot analysis.
- Adds a searchable **Counted Products** explorer with variance, product type,
  warehouse, location, date, category, and state filters.
- Adds product-template and product-variant smart buttons for historical count
  analysis.
- Optionally calculates the previous count, previous counted quantity, and units
  moved in/out since the prior count.

**Main dependencies:** `stock`, `mail`, `report_xlsx`,
`base_approval_division`, `base_warehouse_division`

**Runtime integration:** uses the stock movement view supplied by
`stock_move_value_amount`

### Products and pricing

#### `product_qrcode`

Generates and prints product QR codes based on the product barcode.

- Adds a binary QR image to product variants and exposes it on product forms.
- Generates or refreshes the QR when a barcode is assigned during create or
  write.
- Uses the internal reference as the barcode when QR generation is requested
  and no barcode exists.
- Adds **Print QR** actions to product-template and product-variant forms.
- Adds a bulk **Generate QR** server action to the product variant list.
- Prints a compact 100 mm × 100 mm PDF label containing the barcode text and QR
  image.

**Main dependencies:** `sale_management`, `stock`

**Python requirement:** `qrcode` and its image backend

#### `product_tag_search_filters`

Turns product tags into one-click filters.

- Adds **Show as Product Search Filter** to product tags.
- Enables the option by default for newly created product tags.
- Dynamically injects enabled tags into product-template search views.
- Dynamically injects the same tags into product-variant search views.
- Filters variants through their template's product tags.
- Supports both Odoo 17's `get_view` path and the compatibility
  `fields_view_get` path.

**Main dependency:** `product`

#### `product_variant_template_merge`

Combines existing `product.product` records under a newly created product
template.

- Adds **Combine into New Product Template** to the product variant list for
  Inventory Managers.
- Preserves existing product IDs, retaining variant-level references such as
  stock, sales, purchase, and accounting history.
- Creates a dedicated variant-generating attribute and one value per selected
  product.
- Derives the proposed template name from the common portion of selected product
  names.
- Derives clean, unique variant values from the portions that differ, with
  internal-reference and numbered fallbacks.
- Lets the user choose a base product for template-level settings.
- Validates template-level behavior that cannot safely differ between variants,
  including product type, units of measure, taxes, routes, tracking, and
  invoicing/purchase policies.
- Allows shared products (`company_id = False`) to be combined with products
  belonging to one specific company.
- Preserves Point of Sale availability when any selected source product is
  available in PoS.
- Optionally preserves effective sale prices using variant price extras.
- Optionally migrates variant-specific vendor records and copies
  template-level vendor records as variant-specific records.
- Preserves effective product images that originated on source templates.
- Optionally archives source templates only after no active or archived variants
  remain under them.
- Shows concrete product variants by default on sale and purchase order lines,
  while keeping template selectors optional and hidden.
- Allows exact internal-reference or barcode searches to select a variant
  directly instead of opening the configurator/matrix flow.

> **Important:** links made directly to an old `product.template` cannot be
> migrated universally. Template-wide BOMs, template-only pricelist rules, and
> custom template relations may need project-specific migration. Back up the
> database and test the operation on a copy first.

**Main dependencies:** `product`, `sale_product_configurator`,
`purchase_product_matrix`

**Documentation:** [module README](product_variant_template_merge/README.md)

#### `pricelist_team_user_access`

Controls pricelist access using sales teams and explicitly selected users.

- Adds **Allowed Sales Teams** and **Allowed Users** to pricelists.
- Treats a pricelist with no team/user assignments as public.
- Grants restricted access to the union of:
  - explicit users;
  - sales team leaders;
  - sales team members.
- Recalculates effective users when pricelist assignments or sales-team
  membership changes.
- Filters pricelists and pricing rules from normal list, selection, name-search,
  and executable window-action results.
- Filters sale orders and sale order lines whose pricelist is not available to
  the current user.
- Protects create, write, and delete operations on pricelists, pricing rules,
  sale orders, and sale order lines with record rules and model checks.
- Leaves low-level read permission unrestricted while applying the intended
  restrictions to normal Odoo user-interface searches.
- Replaces the product **Extra Prices** smart button with an accessible-rule
  count and filtered action.
- Adds public/restricted, team, and user filters to pricelist search.
- Preserves hidden pricelists when a user saves unrelated Point of Sale settings,
  including while a PoS session is open.
- Allows Settings administrators to manage pricelist assignments.

**Main dependencies:** `product`, `sales_team`, `sale`, `point_of_sale`,
`base_pricelist_division`

### Sales, Point of Sale, and productivity

#### `odoo_sale_order_line_views`

Adds dedicated, read-only analysis interfaces for quotation and sale order
lines.

- Adds **Quotation Line Views** for draft, sent, and cancelled quotation lines.
- Adds **Order Line Views** for confirmed, completed, and cancelled order
  lines.
- Provides list, form, kanban, pivot, graph, and calendar views.
- Adds filters for salesperson, customer, product, status, invoice status, and
  creation date.
- Adds grouping by product, order, salesperson, customer, and date.
- Shows product images on sale order lines.
- Exposes customer email and phone on line forms.
- Displays quantities ordered, delivered, invoiced, and remaining to invoice.

**Main dependency:** `sale_management`

**Upstream credit:** based on the Cybrosys Sale Order Line Views addon; see the
module source and [module README](odoo_sale_order_line_views/README.rst).

#### `pos_google_review_qr`

Prints a configurable Google review QR code on Point of Sale receipts.

- Enables the feature independently on every PoS configuration.
- Stores a separate Google review link, heading, and customer message per shop.
- Exposes configuration on both the PoS form and the standard PoS Settings page.
- Requires HTTPS and validates that the destination belongs to a supported
  Google, `g.page`, or `goo.gl` domain.
- Generates a self-contained PNG in the PoS browser with Odoo's bundled ZXing
  encoder.
- Caches the generated image per PoS configuration and URL.
- Works in receipt preview, browser print, receipt reprint, and standard PoS
  printing without a receipt-time external QR service.
- Does not require a Google API key and does not send review data back to Odoo.

An open PoS browser must be reloaded after installation, upgrade, or a
configuration change.

**Main dependency:** `point_of_sale`

**Documentation:** [module README](pos_google_review_qr/README.md) and
[administrator, user, technical, and testing guides](pos_google_review_qr/docs/)

#### `activity_dm_notification`

Makes newly assigned activities difficult to miss.

- Sends an OdooBot direct message after activity creation.
- Sends another direct message when the assignee changes.
- Includes activity type, summary, deadline, optional note, and a link to the
  related record.
- Reuses the recipient's existing one-to-one OdooBot chat and never creates a
  new channel.
- Pins the existing chat for the recipient when necessary.
- Sends a bus event that opens and focuses the chat window in the recipient's
  browser.
- Logs notification failures without blocking creation or reassignment of the
  underlying activity.

**Main dependencies:** `mail`, `bus`

## Requirements and dependencies

### Odoo version

- Target branch: **Odoo 17.0**
- Add the repository root to `addons_path`.
- Community/Enterprise compatibility depends on each addon's manifest
  dependencies.

### Addons not included in this repository

Install the following before installing addons that depend on them:

- `base_pricelist_division`: required by `pricelist_team_user_access`; custom
  division/pricelist access module.
- `base_approval_division`: required by `warehouse_stock_count`; custom
  division extension for Odoo Approvals.
- `base_warehouse_division`: required by `warehouse_stock_count`; custom
  division extension for warehouses.
- `report_xlsx`: required by `warehouse_stock_count`; commonly supplied by
  OCA's `reporting-engine` repository.

The accounting reports require `account_reports`, and partner account approval
requires `approvals`; these are normally Enterprise addons.

`warehouse_stock_count` also opens a view from `stock_move_value_amount`, so
install both together unless that integration is removed or replaced.

`stock_picking_qr` uses the `qr` product field when replacing product barcodes
on the picking report. Install `product_qrcode` alongside it for that behavior.

### Python packages

The QR image addons import the Python `qrcode` library:

```bash
python3 -m pip install qrcode[pil]
```

Install it in the same Python environment used by the Odoo service. On managed
platforms such as Odoo.sh, add the package to the deployment's
`requirements.txt`.

## Installation

Clone the Odoo 17 branch:

```bash
git clone --branch 17.0 --single-branch \
  https://github.com/online-sanaullah/addons-odoo-sk.git
```

Add the cloned repository directory to `addons_path`, for example:

```ini
[options]
addons_path = /opt/odoo/odoo/addons,/opt/odoo/custom/addons-odoo-sk
```

Then:

1. Install any external/custom dependencies listed above.
2. Restart Odoo.
3. Enable developer mode.
4. Open **Apps → Update Apps List**.
5. Search for and install the required addon by its display name.

For a command-line installation:

```bash
./odoo-bin -c /etc/odoo.conf -d DATABASE_NAME \
  -i MODULE_TECHNICAL_NAME --stop-after-init
```

Replace the executable, configuration path, database, and module name for your
deployment.

## Updating an addon

After deploying a newer source revision, upgrade the affected addon:

```bash
./odoo-bin -c /etc/odoo.conf -d DATABASE_NAME \
  -u MODULE_TECHNICAL_NAME --stop-after-init
```

Restart the Odoo service when required. For addons with JavaScript or CSS
assets—particularly `activity_dm_notification`,
`odoo_sale_order_line_views`, and `pos_google_review_qr`—hard-refresh or reopen
affected browser sessions after the upgrade.

For Point of Sale asset changes, finish active transactions where practical,
upgrade the addon, and reload every open PoS browser.

## Important implementation notes

- Back up the database before installing data-changing tools such as
  `product_variant_template_merge` or applying stock adjustments.
- Validate accounting and inventory behavior on a staging database with the
  same localization and custom addons as production.
- Several addons intentionally integrate with custom models, fields, groups, or
  XML IDs supplied by the dependency modules listed above.
- The two monthly trial balance addons are separate reports:
  `monthly_trial_balance` is the general-ledger monthly view, while
  `monthly_trial_balance_analytic` allocates balances by analytic account.
- Some addons include their own module-specific documentation. Follow those
  guides for configuration, workflow, testing, and operational limitations.

## Licensing

This is a mixed-license addon repository.

- The repository-level [`LICENSE`](LICENSE) file contains the GNU GPL version 3.
- Most addon manifests explicitly declare LGPL-3.
- `monthly_trial_balance` and `monthly_trial_balance_analytic` declare OPL-1.
- Some legacy addon manifests do not contain a correctly named `license` key.
- Third-party-derived code retains its attribution in the relevant addon.

Review the root license, each addon's `__manifest__.py`, and any embedded
third-party notices before redistribution or commercial use.

## Author and maintenance

Repository maintained by **Sana Ullah Khan**.

Issues and proposed changes should include:

- the addon technical name;
- the exact Odoo 17 revision/edition;
- the complete traceback or browser-console error;
- steps to reproduce;
- whether the issue also occurs on a clean staging database.
