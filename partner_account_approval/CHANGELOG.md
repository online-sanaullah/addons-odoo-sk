# Changelog

## 17.0.4.0.0

### Added

- Independent receivable and payable approval trigger modes.
- Immediate, first-transaction-initial, and next-transaction-after-change options.
- Waiting for Transaction approval state.
- Synchronization of corrected accounts to open approval requests and history.


## 17.0.3.5.0

### Fixed

- Approval requests are now created for newly created partners even when no previously approved account exists.
- Pending approval warnings now appear for newly created partners.
- Cancellation remains unavailable until an approved rollback account exists.

## 17.0.3.4.0

### Added

- Rich module documentation for the Odoo Apps module form.
- README covering installation, configuration, usage, workflow, security and troubleshooting.
- Workflow and transaction-control SVG diagrams.
- Technical documentation and FAQ.
- Expanded manifest description.

## 17.0.3.3.0

### Added

- Partner Account Approval settings in Accounting settings.
- Related company configuration fields on `res.config.settings`.

## 17.0.3.2.0

### Fixed

- Account History smart button placement.
- Multi-company account-history record rule.

## 17.0.3.1.0

### Added

- Persistent account approval history.
- Reliable rollback to latest approved account.
- Account History smart button.

## Earlier versions

- Added receivable/payable approval controls.
- Added blocking-scope configuration.
- Added invoice, bill, payment and journal-entry posting controls.
- Added chatter audit messages.
- Added cancellation and rejection rollback.
