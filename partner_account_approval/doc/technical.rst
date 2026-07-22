Technical Reference
===================

New Model
---------

``res.partner.account.approval.history``

Important Overrides
-------------------

* ``res.partner.create``
* ``res.partner.write``
* ``approval.request.action_approve``
* ``approval.request.action_refuse``
* ``account.move.action_post``
* ``account.payment.action_post``

The module relies on company-dependent partner accounting properties and preserves
multi-company context using ``with_company``.
