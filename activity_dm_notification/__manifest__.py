{
    'name': 'Activity DM Notification',
    'version': '17.0.1.1.0',
    'summary': 'OdooBot sends a direct chat message when an activity is assigned',
    'description': """
Activity DM Notification
========================

When an activity is assigned to a user (either when created or when
reassigned), OdooBot posts a message in the user's existing OdooBot
direct-message channel. The message contains:

* the activity type and summary
* the deadline
* a clickable link to the concerned record

The recipient's Discuss chat window is force-opened on their browser
so they cannot miss the notification.

No new chat channels are ever created — the module only uses the
default OdooBot DM that every Odoo user already has.
""",
    'author': 'Sanaullah Khan',
    'category': 'Productivity/Discuss',
    'depends': ['mail', 'bus'],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
    'assets': {
        'web.assets_backend': [
            'activity_dm_notification/static/src/services/open_chat_service.js',
        ],
    },
}
