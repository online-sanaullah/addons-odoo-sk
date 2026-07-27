import re
from urllib.parse import urlparse

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


_GOOGLE_DOMAIN_RE = re.compile(
    r"^(?:[a-z0-9-]+\.)*google\.(?:com|[a-z]{2}|co\.[a-z]{2}|com\.[a-z]{2})$"
)
_GOOGLE_SHORT_DOMAIN_RE = re.compile(
    r"^(?:[a-z0-9-]+\.)*(?:g\.page|goo\.gl)$"
)


class PosConfig(models.Model):
    _inherit = "pos.config"

    google_review_qr_enabled = fields.Boolean(
        string="Google Review QR on Receipt",
        help="Print a QR code on this shop's PoS receipts that opens its Google review page.",
    )
    google_review_url = fields.Char(
        string="Google Maps Review Link",
        help=(
            "Paste the HTTPS 'Ask for reviews' link from Google Business Profile, "
            "or a Google Maps link for this shop."
        ),
    )
    google_review_qr_title = fields.Char(
        string="Review QR Heading",
        default="How was your visit?",
        help="Optional heading printed above the Google review QR code.",
    )
    google_review_qr_message = fields.Char(
        string="Review QR Message",
        default="Scan the QR code to review us on Google",
        help="Optional instruction printed with the Google review QR code.",
    )

    def _is_google_review_url(self, value):
        parsed = urlparse(value.strip())
        if (
            parsed.scheme.lower() != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            return False

        hostname = parsed.hostname.lower().rstrip(".")
        return bool(
            _GOOGLE_DOMAIN_RE.fullmatch(hostname)
            or _GOOGLE_SHORT_DOMAIN_RE.fullmatch(hostname)
        )

    @api.constrains("google_review_qr_enabled", "google_review_url")
    def _check_google_review_url(self):
        for config in self:
            review_url = (config.google_review_url or "").strip()
            if config.google_review_qr_enabled and not review_url:
                raise ValidationError(
                    _("Enter a Google Maps review link before enabling the receipt QR code.")
                )
            if review_url and not config._is_google_review_url(review_url):
                raise ValidationError(
                    _(
                        "The review link must be an HTTPS Google URL, such as a "
                        "google.com, g.page, or maps.app.goo.gl link."
                    )
                )
