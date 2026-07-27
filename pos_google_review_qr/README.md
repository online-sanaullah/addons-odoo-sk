# PoS Google Review QR Receipt

`pos_google_review_qr` is an Odoo 17 module that prints a shop-specific Google
review QR code on customer Point of Sale receipts. Each PoS configuration can
send customers to a different Google Maps or Google Business Profile location.

## Main features

- Independent enable/disable setting for every PoS.
- Independent Google review link for every shop.
- Custom receipt heading and instruction.
- Receipt preview, browser print, reprint, and standard PoS printer support.
- HTTPS and Google-domain validation for the configured destination.
- Configuration from the PoS form or the standard PoS Settings page.
- No external QR-code service or API key.
- Self-contained QR images with no receipt-time barcode HTTP request.

## Quick start

1. Install **PoS Google Review QR Receipt**.
2. Open **Point of Sale > Configuration > Settings**.
3. Select the relevant PoS.
4. Under **Bills & Receipts**, enable **Google Review QR Code**.
5. Paste that shop's Google **Ask for reviews** link.
6. Save and reload any PoS browser that was already open.
7. print or reprint a receipt and scan the QR code with a phone.

The recommended destination is the **Ask for reviews** link copied from the
shop's Google Business Profile. A general Google Maps listing link is also
accepted, but it normally opens the listing rather than the review form
directly.

## Documentation

- [User Guide](docs/USER_GUIDE.md)
- [Installation and Administration Guide](docs/ADMINISTRATOR_GUIDE.md)
- [Testing Guide](docs/TESTING_GUIDE.md)
- [Technical Reference](docs/TECHNICAL_REFERENCE.md)
- [Changelog](CHANGELOG.md)

The same essential setup and usage documentation is included in
`static/description/index.html`, so it appears on the module information page
inside Odoo.

## Compatibility

- Odoo 17.0 Community and Enterprise
- Required Odoo application: Point of Sale
- Module technical name: `pos_google_review_qr`

## Author

Sana Ullah Khan
