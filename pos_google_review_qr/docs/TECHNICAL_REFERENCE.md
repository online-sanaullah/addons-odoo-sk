# Technical Reference

## Module information

| Item | Value |
| --- | --- |
| Technical name | `pos_google_review_qr` |
| Odoo version | 17.0 |
| Dependency | `point_of_sale` |
| License | LGPL-3 |
| Author | Sana Ullah Khan |

## Architecture

The module has three small integration layers:

1. Backend configuration fields on `pos.config`.
2. A frontend patch that encodes and adds review data to the receipt export.
3. An OWL/QWeb receipt extension that displays the text and QR image.

No review data is added to `pos.order`, and no external HTTP API is called by
the module. QR rendering also requires no receipt-time HTTP image request.

## Backend models

### `pos.config`

| Field | Type | Purpose |
| --- | --- | --- |
| `google_review_qr_enabled` | Boolean | Controls whether the QR is included on receipts for this PoS. |
| `google_review_url` | Char | Stores the Google review or Maps destination. |
| `google_review_qr_title` | Char | Heading printed above the QR. |
| `google_review_qr_message` | Char | Instruction printed with the QR. |

The `_check_google_review_url` constraint requires a URL when the feature is
enabled and rejects insecure or non-Google destinations.

### `res.config.settings`

The following editable related fields expose the PoS values in the standard
Settings interface:

- `pos_google_review_qr_enabled`
- `pos_google_review_url`
- `pos_google_review_qr_title`
- `pos_google_review_qr_message`

The `pos_` naming follows the standard Odoo 17 Point of Sale settings mapping
to the selected `pos_config_id`.

## Views

`views/pos_config_views.xml` adds the configuration to the direct
`pos.config` form.

`views/res_config_settings_views.xml` adds the configuration to the
**Bills & Receipts** block of the standard Point of Sale Settings page.

Both views use Odoo 17 inline `invisible` and `required` expressions.

## PoS data flow

Odoo 17 loads the active `pos.config` record into the PoS frontend. The custom
fields therefore become available as properties of `this.pos.config`.

`static/src/app/store/order.js` patches `Order.export_for_printing()`:

1. Call the standard method with `super`.
2. Read the active PoS configuration.
3. Use Odoo's bundled `window.ZXing.QRCodeWriter` to create a QR bit matrix.
4. Render that matrix into an off-screen canvas.
5. Convert the canvas to a self-contained PNG data URL.
6. Cache the PNG by PoS configuration and review URL.
7. Add the following receipt-only values:
   - `google_review_qr_code`
   - `google_review_qr_title`
   - `google_review_qr_message`

The QR image source has the form:

```text
data:image/png;base64,<PNG data>
```

The QR matrix is generated at a requested size of 256 by 256 pixels. The
receipt CSS displays it at 200 by 200 pixels.

## Receipt template

`static/src/app/screens/receipt_screen/receipt/order_receipt.xml` extends
`point_of_sale.OrderReceipt`.

The review block is inserted immediately before the standard `after-footer`
container. It is rendered only when `props.data.google_review_qr_code` is
present.

The CSS:

- centers the content;
- keeps the block together when possible;
- prints the QR at 200 by 200 pixels;
- preserves hard QR edges when the browser scales the 256-pixel PNG;
- uses compact text sizing suitable for thermal receipts.

## Asset bundle

The manifest adds the JavaScript, XML, and CSS files to:

```text
point_of_sale._assets_pos
```

An open PoS frontend must be reloaded after installing, upgrading, or changing
the active configuration.

## URL validation

The validation accepts recognized Google hosts, including:

- `google.com` and subdomains;
- supported Google country domains;
- `g.page` and subdomains;
- `goo.gl` and subdomains, including `maps.app.goo.gl`.

The URL must use HTTPS and cannot contain embedded credentials.

## Data retention behavior

The module intentionally does not persist the review link on the order.
Consequences:

- no database growth per order;
- configuration remains simple and shop-specific;
- reprints use the currently loaded PoS configuration;
- historical receipts do not retain the link that was active at order time.

If historical link retention is required in a future version, the link should
be stored on `pos.order`, exported with order data, and loaded for reprints.

## Extending the module

### Change the QR size

Update `QR_IMAGE_SIZE` in `order.js` and keep the CSS image dimensions
synchronized. Use a square size and retain sufficient quiet space around the
QR code.

### Change receipt placement

Change the XPath target in `order_receipt.xml`. Use a stable class or component
hook from `point_of_sale.OrderReceipt`.

### Add translations

Export the module terms from Odoo, add an `i18n/<language>.po` file, and import
or deploy it with the module.

### Support another review platform

The current constraint intentionally permits only Google URLs. Supporting
another platform requires updating the validation policy, field labels,
documentation, and receipt wording.

## File layout

```text
pos_google_review_qr/
├── __init__.py
├── __manifest__.py
├── CHANGELOG.md
├── README.md
├── docs/
│   ├── ADMINISTRATOR_GUIDE.md
│   ├── TESTING_GUIDE.md
│   ├── TECHNICAL_REFERENCE.md
│   └── USER_GUIDE.md
├── models/
│   ├── __init__.py
│   ├── pos_config.py
│   └── res_config_settings.py
├── static/
│   ├── description/index.html
│   └── src/app/
│       ├── screens/receipt_screen/receipt/
│       │   ├── order_receipt.css
│       │   └── order_receipt.xml
│       └── store/order.js
└── views/
    ├── pos_config_views.xml
    └── res_config_settings_views.xml
```
