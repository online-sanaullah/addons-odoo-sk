# Installation and Administration Guide

## Requirements

- Odoo 17.0 Community or Enterprise
- The standard `point_of_sale` module
- Access to install or upgrade Odoo modules

There are no additional Python packages, external QR services, or Google API
credentials.

## Install on Odoo.sh

1. Extract the ZIP.
2. Copy the `pos_google_review_qr` directory into the custom-addons repository.
3. Commit and push the directory to the required Odoo.sh branch.
4. Wait for the build to complete.
5. Open **Apps**, update the Apps list if necessary, and search for
   **PoS Google Review QR Receipt**.
6. Install the module.
7. Configure each PoS and test a receipt on staging before production.

## Install on an on-premise server

1. Extract the ZIP.
2. Copy `pos_google_review_qr` into a directory listed in `addons_path`.
3. Make sure the Odoo service user can read the module files.
4. Restart Odoo.
5. Enable developer mode and update the Apps list.
6. Install **PoS Google Review QR Receipt**.

An administrator can also update the module from the command line:

```bash
./odoo-bin -d DATABASE_NAME -u pos_google_review_qr --stop-after-init
```

Use the correct Odoo executable, configuration file, and service account for
the deployment.

## Upgrade the module

1. Close or stop active PoS use where practical.
2. Deploy the updated module source.
3. Upgrade `pos_google_review_qr`.
4. Restart Odoo if required by the hosting environment.
5. Reload all open PoS browser tabs so the new frontend assets and settings are
   loaded.
6. Print and scan a test receipt.

## Access and configuration

The module introduces no new security groups. It follows the existing access
rights for Point of Sale configuration and Settings.

Configuration is available from:

- **Point of Sale > Configuration > Settings > Bills & Receipts**
- **Point of Sale > Configuration > Point of Sales**

The configured URL is validated when the PoS configuration is saved.

## Accepted destination rules

The destination must:

- use `https`;
- have no embedded username or password;
- use a recognized Google host, including `google.com`, supported Google
  country domains, `g.page`, or `goo.gl` subdomains such as
  `maps.app.goo.gl`.

Third-party URL shorteners are intentionally rejected.

## Operational notes

### Frontend refresh

PoS configuration is loaded into the frontend when the PoS starts. Saving a
new review link in the backend does not automatically replace the value inside
an already-open PoS browser. Reload or reopen the PoS.

### Existing orders

The review URL is not copied to `pos.order`. Reprints use the current
configuration loaded in the PoS frontend.

### Printing

The QR is encoded in the PoS browser by Odoo's bundled ZXing library and
converted to a self-contained PNG data URL. It therefore does not depend on a
`/report/barcode` request while the receipt is being previewed or printed.

The PNG source is generated at 256 by 256 pixels and displayed at 200 by 200
pixels on the receipt. The generated image is cached for the active PoS
configuration until its review URL changes or the PoS is reloaded.

## Troubleshooting

### The QR does not appear

Check the following:

1. **Google Review QR Code** is enabled for the correct PoS.
2. A valid Google review link is saved.
3. The PoS browser was reloaded after the change.
4. The updated module is installed and its frontend assets were deployed.
5. The receipt is the standard customer order receipt, not a preparation or
   kitchen ticket.
6. The browser console does not report that the Odoo ZXing QR encoder is
   unavailable.

If assets are stale, restart/update the Odoo deployment, upgrade the module,
and perform a hard refresh of the PoS browser.

### Odoo rejects the link

- Confirm that the link begins with `https://`.
- Use the original link supplied by Google.
- Do not use a third-party URL shortener.
- Prefer a `g.page`, `search.google.com`, `maps.app.goo.gl`, or Google Maps
  link.

### The link opens the wrong shop

The configured destination belongs to another Google Business Profile. Replace
it on the affected PoS configuration and reload that PoS.

### The scan opens Maps but not the review form

Replace the general Maps listing link with the Google Business Profile
**Ask for reviews** link.

### The physical QR is difficult to scan

- Clean the printer head.
- Confirm the printer is not scaling or cropping receipt content.
- Test with the standard 200-pixel printed QR before making custom CSS changes.
- Verify that the issue also occurs on the receipt preview; if the preview
  scans correctly, the likely cause is printer resolution or scaling.

### A broken-image icon or empty image box appears

Version `17.0.1.1.0` and later embeds the QR as a PNG data URL and does not use
the report-barcode image route. Upgrade the module, rebuild/deploy the PoS
assets, and perform a hard reload of the PoS browser.

### Changes appear in the backend but not the PoS

Reload or reopen the PoS. If the old frontend bundle persists after deployment,
upgrade the module and refresh the browser assets.

## Uninstall considerations

Uninstalling the module removes its receipt extension and configuration fields
from the active Odoo registry. It does not modify completed PoS orders or
Google reviews.

## Production checklist

- [ ] Correct link configured for every PoS.
- [ ] Direct review link used where available.
- [ ] Receipt preview verified.
- [ ] Physical receipt printed and scanned.
- [ ] Correct branch/shop confirmed on the phone.
- [ ] All active PoS browsers reloaded after deployment.
