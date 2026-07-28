Stock Scrap Reversal
====================

This Odoo 17 module adds a **Reverse Scrap** button to completed stock scrap
operations.

Behavior
--------

* Creates a new completed stock move from the scrap location back to the
  original source location.
* Links the reversal move to the same ``stock.scrap`` record.
* Links the reversal move to the original move through
  ``origin_returned_move_id``.
* Preserves lot/serial, owner, unit of measure, and package information.
* Prevents the same scrap operation from being reversed more than once.
* Adds reversal details and a smart button to the scrap form.
* Posts the reversal in the scrap chatter.
* Uses the original stock valuation layer cost for FIFO/AVCO returns.
* Reverses the account used by the original scrap valuation entry.

Usage
-----

#. Open **Inventory > Operations > Scrap**.
#. Open a completed scrap operation.
#. Click **Reverse Scrap**.
#. Confirm the warning.
#. Use the **Reversal Move** smart button to inspect the generated stock move.

Only users in the Inventory Administrator group can execute the reversal.
