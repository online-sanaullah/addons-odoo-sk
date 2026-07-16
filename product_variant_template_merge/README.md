# Product Variant Template Merge (Odoo 17)

This module adds **Combine into New Product Template** to the **Action** menu of the product variant list.

## What it does

- Creates a new `product.template`.
- Creates one dedicated variant-generating attribute and one value per selected product.
- Moves the existing `product.product` records to the new template instead of creating replacement products.
- Preserves product IDs and therefore product-level history such as stock moves, quants, sales lines, purchase lines and accounting references.
- Preserves effective images that previously came from a source template.
- Optionally preserves current sale prices using `product.template.attribute.value.price_extra`.
- Optionally preserves vendor pricelists:
  - variant-specific supplier records are moved to the new template;
  - template-wide supplier records are copied as variant-specific records.
- Archives a source template only when no active or archived product variants remain under it.

## Safety checks

The wizard blocks the operation when selected products differ on important template-level settings such as two different non-empty companies, product type, units of measure, taxes, routes, tracking, invoicing policy or purchase policy. These settings cannot differ between variants of one template.

## Important limitation

References that point directly to an old `product.template` are not universally migratable because installed standard and custom modules can add arbitrary template relationships. For example, template-wide BOMs or template-only pricelist rules remain linked to the archived source template. Extend these hooks for project-specific migrations:

- `_get_fields_requiring_same_value()`
- `_get_template_fields_to_copy()`
- `_after_products_combined()`

## Usage

1. Open **Sales / Products / Product Variants** or **Inventory / Products / Product Variants**.
2. Select at least two products.
3. Open **Action → Combine into New Product Template**.
4. Enter the new template name and review the generated variant value names.
5. Click **Combine Products**.

Always test on a duplicated database and take a backup before production use.


## Version 17.0.1.0.5

- The common portion of the selected product names is used as the default new template name.
- The unique portion of each name is used as its generated variant value.
- Wizard product references are force-saved to prevent required `product_id` errors.


## Version 17.0.1.0.5

- The Variant Attribute field starts empty and must be entered before combining.
- Product Category and Vendor Taxes may differ; the new template uses those settings from the selected Base Product.


## Version 17.0.1.0.6

- Products with no company can be merged with products assigned to one company.
- The sole non-empty company is assigned to the new template; if all are shared, the new template remains shared.
- The new template is available in POS when any selected source product was available in POS.

## Version 17.0.1.0.7

- The concrete Product Variant field is shown by default on sale order lines.
- The Product Template field is hidden by default but remains available as an optional column.
- Entering an exact internal reference or barcode selects the matching `product.product` variant directly instead of opening the variant configurator.

## Version 17.0.1.0.8

- The concrete Product Variant field is shown by default on purchase order lines.
- The Product Template field added by `purchase_product_matrix` is hidden by default but remains available as an optional column.
- Exact internal-reference or barcode searches can select the matching `product.product` variant directly on a purchase order line.

