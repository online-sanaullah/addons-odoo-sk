# -*- coding: utf-8 -*-
from odoo import Command, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _apply_pricelist_commands(self, current_ids, commands, preserve_on_empty=False):
        """Return the ids represented by an x2many command list.

        The Point of Sale settings view normally sends link commands or a single
        SET command.  When relation values have been filtered at UI level, the
        web client may instead send an empty list.  Treat that empty list as no
        change so saving unrelated POS settings cannot remove pricelists.
        """
        if not commands:
            return set(current_ids) if preserve_on_empty else set()

        valid_commands = [
            command for command in commands
            if isinstance(command, (list, tuple)) and command
        ]

        # The settings view uses LINK commands as a complete selection, not as
        # incremental additions. Mirror Odoo's own preprocessing semantics.
        if valid_commands and all(command[0] == Command.LINK for command in valid_commands):
            return {command[1] for command in valid_commands if len(command) > 1}

        result_ids = set(current_ids)
        for command in valid_commands:
            operation = command[0]
            if operation == Command.CREATE:
                # A newly-created pricelist has no id yet and is not expected in
                # this settings field. Leave creation handling to the ORM.
                continue
            if operation == Command.UPDATE:
                continue
            if operation in (Command.DELETE, Command.UNLINK):
                if len(command) > 1:
                    result_ids.discard(command[1])
            elif operation == Command.LINK:
                if len(command) > 1:
                    result_ids.add(command[1])
            elif operation == Command.CLEAR:
                result_ids.clear()
            elif operation == Command.SET:
                result_ids = set(command[2] if len(command) > 2 else [])

        return result_ids

    def _normalize_available_pricelists_from_settings(self, vals):
        """Protect POS settings writes from UI-filtered pricelist values.

        Pricelist access in this addon is intentionally view/search based. The
        POS settings page may therefore load only the pricelists visible to the
        current user. Saving the page must not unlink existing hidden pricelists,
        and an empty command list must not reach the Odoo POS write implementation
        because it assumes a SET command while a session is open.
        """
        if (
            not self.env.context.get('from_settings_view')
            or 'available_pricelist_ids' not in vals
        ):
            return vals

        self.ensure_one()
        vals = dict(vals)

        current_ids = set(self.available_pricelist_ids.ids)
        commands = vals.get('available_pricelist_ids') or []
        has_open_session = bool(self.session_ids.filtered(lambda session: session.state != 'closed'))
        requested_ids = self._apply_pricelist_commands(
            current_ids,
            commands,
            # Odoo forbids removing available pricelists while a session is open.
            # Preserve the current set when the web client sends a malformed empty
            # command list, rather than letting core index commands[0].
            preserve_on_empty=has_open_session,
        )

        accessible_ids = self.env['product.pricelist']._get_accessible_pricelist_ids(
            user=self.env.user,
            admin_bypass=True,
        )

        # False means unrestricted/bypassed. Otherwise preserve current records
        # hidden by the pricelist UI filter while applying changes to visible ones.
        if accessible_ids is not False:
            hidden_existing_ids = current_ids - set(accessible_ids)
            requested_ids |= hidden_existing_ids

        vals['available_pricelist_ids'] = [Command.set(sorted(requested_ids))]
        return vals

    def write(self, vals):
        vals = self._normalize_available_pricelists_from_settings(vals)
        return super().write(vals)
