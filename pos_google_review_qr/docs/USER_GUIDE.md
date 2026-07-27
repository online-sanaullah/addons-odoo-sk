# User Guide

## Purpose

The module adds a Google review QR code to the customer receipt. When the QR is
scanned, the customer's phone opens the Google link configured for that shop.

Configuration is stored per Point of Sale. If a company operates several
branches, each branch can direct customers to its own Google Maps location.

## Before configuration

Obtain the correct Google link for each shop. The best choice is the
**Ask for reviews** link from the shop's Google Business Profile because it is
designed to open the review flow for that exact location.

Supported examples include:

- `https://g.page/r/.../review`
- `https://search.google.com/local/writereview?placeid=...`
- `https://maps.app.goo.gl/...`
- `https://www.google.com/maps/...`
- Equivalent HTTPS links on a Google country domain

Only secure HTTPS links on recognized Google domains are accepted.

### Direct review link versus Maps listing link

| Link type | Customer experience |
| --- | --- |
| Google **Ask for reviews** link | Opens the review flow with the location already selected. |
| General Google Maps shop link | Opens the shop listing; the customer then chooses **Write a review**. |

Use the direct **Ask for reviews** link whenever possible.

## Configure a shop

### From Point of Sale Settings

1. Open **Point of Sale > Configuration > Settings**.
2. Select the PoS to configure in the selector at the top of the page.
3. Find **Bills & Receipts**.
4. Enable **Google Review QR Code**.
5. Enter the shop's link in **Google review link**.
6. Set the optional receipt text:
   - **Heading** defaults to `How was your visit?`
   - **Message** defaults to `Scan the QR code to review us on Google`
7. Save the settings.
8. Reload or reopen any PoS browser that was already running.

### From the Point of Sale form

1. Open **Point of Sale > Configuration > Point of Sales**.
2. Open the required PoS.
3. Enable **Google Review QR**.
4. Enter the review link, heading, and message.
5. Save and reload the PoS frontend.

## Configure multiple branches

Repeat the configuration for every PoS. Do not copy one branch's link to
another branch unless both PoS configurations intentionally represent the same
Google Business Profile location.

Example:

| PoS configuration | Google destination |
| --- | --- |
| Islamabad Shop | Islamabad Google Business Profile review link |
| Rawalpindi Shop | Rawalpindi Google Business Profile review link |
| Lahore Shop | Lahore Google Business Profile review link |

## Test the result

Perform this test before using the feature in production:

1. Open or reload the PoS.
2. Complete a test order, or reprint an existing receipt.
3. Confirm that the heading, message, and QR code are visible.
4. Scan the code with a phone.
5. Verify that the correct shop opens.
6. If a direct review link was configured, verify that the review flow opens.
7. Print a physical receipt and scan it again to confirm printer quality.

## Receipt and reprint behavior

- The QR code is created when the receipt is rendered.
- The module does not store a separate review URL on each PoS order.
- A reprinted receipt uses the review settings currently loaded by the PoS.
- If the shop link changes, reload the PoS before printing or reprinting.
- Disabling the feature removes the QR from newly rendered receipts after the
  PoS is reloaded.

## Recommended receipt wording

Short wording prints best on thermal receipts. Examples:

**Heading**

- How was your visit?
- Tell us what you think
- We value your feedback

**Message**

- Scan to review us on Google
- Share your experience on Google
- Scan here to leave a review

## Common questions

### Can each PoS use a different link?

Yes. All settings are stored on the individual PoS configuration.

### Does the module require a Google API key?

No. It encodes the configured Google URL in the QR code.

### Does it send review data back to Odoo?

No. The QR only opens the configured Google destination. Reviews are submitted
to Google and are not copied into Odoo by this module.

### Can the heading or message be changed?

Yes. Both values are configurable per PoS.

### Why does the scan open the shop listing instead of the review form?

A general Maps sharing link was probably configured. Replace it with the
Google Business Profile **Ask for reviews** link.
