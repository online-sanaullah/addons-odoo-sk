# Stock State Last Updated By

Technical module folder name: stock_state_last_updated_by

This version avoids concrete model multiple inheritance. It extends the real models with normal string `_inherit` only:
- `_inherit = "stock.picking"`
- `_inherit = "stock.move"`
- `_inherit = "stock.move.line"`

All fields are non-stored computed fields.

For stock move lines the resolution order is:
1. stock.move.line state tracking
2. parent stock.move state tracking
3. parent stock.picking state tracking
4. inventory adjustment line: stock.move.line create_uid/create_date
5. normal fallback: stock.move.line write_uid/write_date
6. parent stock.move write_uid/write_date

The user field is a res.users Many2one and uses the many2one_avatar_user widget.
