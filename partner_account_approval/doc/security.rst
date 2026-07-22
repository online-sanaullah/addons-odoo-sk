Security
========

The account history model is restricted by allowed companies:

``[('company_id', 'in', company_ids)]``

Internal users can read, create and update history records for allowed companies.
Deletion is disabled.
