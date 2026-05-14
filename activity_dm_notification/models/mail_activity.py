import logging

from markupsafe import Markup

from odoo import _, api, models

_logger = logging.getLogger(__name__)

# Custom bus notification picked up by our frontend service to force the
# Discuss chat window to open on the recipient's browser.
OPEN_CHAT_BUS_TYPE = 'activity_dm/open_chat'


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    # ------------------------------------------------------------------
    # CRUD overrides – trigger a DM whenever the assignee changes.
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        activities = super().create(vals_list)
        for activity in activities:
            activity._notify_assignee_via_dm()
        return activities

    def write(self, vals):
        if 'user_id' not in vals:
            return super().write(vals)

        previous_user_by_id = {a.id: a.user_id for a in self}
        result = super().write(vals)
        for activity in self:
            if previous_user_by_id.get(activity.id) != activity.user_id:
                activity._notify_assignee_via_dm()
        return result

    # ------------------------------------------------------------------
    # Notification helpers
    # ------------------------------------------------------------------
    def _notify_assignee_via_dm(self):
        """Safe wrapper – never let a failure here block the underlying
        activity create/write."""
        self.ensure_one()
        try:
            self._do_notify_assignee_via_dm()
        except Exception:
            _logger.exception(
                "Failed to send OdooBot DM for activity %s", self.id
            )

    def _do_notify_assignee_via_dm(self):
        if not self.user_id or not self.user_id.active:
            return
        if not self.res_model or not self.res_id:
            return

        odoobot = self.env.ref('base.partner_root', raise_if_not_found=False)
        if not odoobot:
            return

        target_partner = self.user_id.partner_id
        if not target_partner or target_partner == odoobot:
            return

        channel = self._find_odoobot_dm(target_partner, odoobot)
        if not channel:
            _logger.info(
                "No existing OdooBot DM channel for partner %s (user %s); "
                "skipping activity DM notification.",
                target_partner.id, self.user_id.login,
            )
            return

        # Make sure the channel is at least pinned in the user's sidebar.
        # The chat window itself will be force-opened from the frontend
        # via the bus event below.
        self._ensure_dm_pinned(channel, target_partner)

        channel.sudo().message_post(
            body=self._render_dm_body(),
            author_id=odoobot.id,
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
        )

        # Tell the recipient's browser to force-open the Discuss chat
        # window for this channel. Our small frontend service listens
        # for this bus notification.
        self.env['bus.bus']._sendone(
            target_partner,
            OPEN_CHAT_BUS_TYPE,
            {'channel_id': channel.id},
        )

    def _ensure_dm_pinned(self, channel, target_partner):
        """Pin the channel so it appears in the recipient's sidebar."""
        target_member = channel.sudo().channel_member_ids.filtered(
            lambda m: m.partner_id == target_partner
        )
        if not target_member:
            return
        if 'is_pinned' in target_member._fields and not target_member.is_pinned:
            target_member.write({'is_pinned': True})

    def _render_dm_body(self):
        """Build the HTML body posted in the DM.

        Returned as ``markupsafe.Markup`` so ``message_post`` treats the
        tags as HTML rather than escaping them.
        """
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url'
        ) or ''
        record_url = '%s/web#id=%s&model=%s&view_type=form' % (
            base_url, self.res_id, self.res_model,
        )

        record_name = self.res_name or self.res_model or _('related record')
        activity_type = self.activity_type_id.display_name or _('Activity')
        summary = self.summary or activity_type
        deadline = (
            self.date_deadline.strftime('%Y-%m-%d')
            if self.date_deadline else _('not set')
        )

        # The note field is already HTML; mark it safe so it isn't escaped
        # when substituted into the body template.
        note_block = Markup('')
        if self.note and self.note.strip() and self.note.strip() not in ('<p><br></p>', '<p></p>'):
            note_block = Markup('<p><em>%s</em></p>') % _('Note:')
            note_block += Markup(self.note)

        body = Markup(
            '<p>👋 You have a new activity to handle:</p>'
            '<ul>'
            '<li><strong>%(type_label)s:</strong> %(activity_type)s</li>'
            '<li><strong>%(summary_label)s:</strong> %(summary)s</li>'
            '<li><strong>%(due_label)s:</strong> %(deadline)s</li>'
            '<li><strong>%(on_label)s:</strong> '
            '<a href="%(url)s" target="_blank">%(record_name)s</a></li>'
            '</ul>%(note)s'
        ) % {
            'type_label': _('Type'),
            'summary_label': _('Summary'),
            'due_label': _('Due'),
            'on_label': _('On'),
            'activity_type': activity_type,
            'summary': summary,
            'deadline': deadline,
            'url': record_url,
            'record_name': record_name,
            'note': note_block,
        }
        return body

    def _find_odoobot_dm(self, partner, odoobot):
        """Return the existing 1:1 chat between OdooBot and ``partner``.

        Returns an empty recordset if not found – we never create a new
        channel here.
        """
        Channel = self.env['discuss.channel'].sudo()
        candidates = Channel.search([
            ('channel_type', '=', 'chat'),
            ('channel_member_ids.partner_id', '=', partner.id),
        ])
        for channel in candidates:
            partners = channel.channel_member_ids.partner_id
            if len(partners) == 2 and odoobot in partners and partner in partners:
                return channel
        return Channel.browse()
