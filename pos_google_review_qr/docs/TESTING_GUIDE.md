# Testing Guide

## Test environment

Run the tests on an Odoo 17 staging database with:

- at least two PoS configurations when multi-shop behavior is relevant;
- one valid direct Google review link;
- one valid general Google Maps listing link;
- receipt preview access;
- the same printer model used in production, where possible.

## Functional test cases

### QR-01: Module installation

1. Install `pos_google_review_qr`.
2. Open the module information page.
3. Open Point of Sale Settings.

Expected:

- Installation completes without errors.
- The documentation appears on the module information page.
- **Google Review QR Code** appears under **Bills & Receipts**.

### QR-02: Required link validation

1. Enable **Google Review QR Code**.
2. Leave **Google review link** empty.
3. Save.

Expected:

- Odoo blocks the save and asks for a Google Maps review link.

### QR-03: URL security validation

Test each of the following:

| Input | Expected |
| --- | --- |
| `https://g.page/r/example/review` | Accepted |
| `https://search.google.com/local/writereview?placeid=example` | Accepted |
| `https://maps.app.goo.gl/example` | Accepted |
| `https://www.google.com/maps/place/example` | Accepted |
| `http://g.page/r/example/review` | Rejected |
| `https://example.com/review` | Rejected |
| `javascript:alert(1)` | Rejected |

Use real Google links for the end-to-end scan tests.

### QR-04: Configuration through PoS Settings

1. Select a PoS in **Point of Sale > Configuration > Settings**.
2. Enable the feature.
3. Enter a valid link, heading, and message.
4. Save and reopen the settings.

Expected:

- All values remain saved on the selected PoS.

### QR-05: Configuration through the PoS form

1. Open **Point of Sale > Configuration > Point of Sales**.
2. Open a PoS.
3. Change the review heading.
4. Save.
5. Return to the main PoS Settings page.

Expected:

- The changed heading appears for the same PoS in both interfaces.

### QR-06: Receipt preview

1. Reload the PoS frontend.
2. Complete a test order.
3. View the receipt.

Expected:

- The configured heading and message appear.
- The QR is centered and complete.
- No broken-image icon, alternate text, or empty image box appears.
- Existing receipt totals, payment information, footer, and order details are
  unchanged.

### QR-07: QR destination

1. Scan the preview QR with a phone.

Expected:

- The phone opens the correct shop.
- A direct **Ask for reviews** link opens the review flow.
- A general Maps link opens the correct listing.

### QR-08: Physical receipt

1. Print the receipt using the production printer.
2. Scan the physical QR with at least two phones or camera applications.

Expected:

- The QR is not cropped.
- It scans reliably.
- It opens the same destination as the preview.

### QR-08A: Self-contained image

1. Open the browser developer tools on the receipt screen.
2. Inspect the Google review QR `<img>` element.

Expected:

- Its `src` begins with `data:image/png;base64,`.
- The receipt does not request `/report/barcode` for the Google review QR.

### QR-09: Receipt reprint

1. Open a completed order from the PoS ticket/order history.
2. Reprint the receipt.

Expected:

- The review QR appears on the reprint.
- The current configuration loaded in the PoS is used.

### QR-10: Disabled state

1. Disable the feature in the backend.
2. Save and reload the PoS.
3. Print or reprint a receipt.

Expected:

- No Google review heading, message, or QR is shown.

### QR-11: Multi-shop isolation

1. Configure two PoS records with different links and receipt text.
2. Reload both PoS frontends.
3. Print one receipt from each.

Expected:

- Each receipt uses its own shop's text and link.
- No configuration leaks between PoS records.

### QR-12: Active frontend refresh

1. Keep a PoS frontend open.
2. Change its link in the backend.
3. Print before reloading.
4. Reload and print again.

Expected:

- The old frontend may use the previously loaded value.
- After reload, the receipt uses the new value.

## Regression checks

Confirm that the module does not interfere with:

- standard invoice-request QR codes;
- receipt headers and footers;
- fiscal localization receipt extensions;
- payment-terminal ticket text;
- automatic receipt printing;
- browser receipt printing;
- receipt reprints.

## Production acceptance criteria

- [ ] Module installs or upgrades successfully.
- [ ] Each PoS has the correct link.
- [ ] Invalid destinations are rejected.
- [ ] Preview QR scans correctly.
- [ ] Physical QR scans correctly.
- [ ] Reprints include the QR.
- [ ] Disabling the feature removes the QR.
- [ ] Existing receipt sections remain intact.
- [ ] All PoS browser tabs are reloaded after deployment.
