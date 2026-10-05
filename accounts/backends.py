from django.core.mail.backends.base import BaseEmailBackend
from django.contrib.auth.backends import ModelBackend
from accounts.models import User


class EmailAuthenticationBackend(ModelBackend):
    """Authenticate an email/password pair only when it identifies one account."""

    def authenticate(self, request, username=None, password=None, email=None, account_id=None, **kwargs):
        address = (email or username or "").strip()
        if not address or password is None:
            return None
        candidates = User.objects.filter(email__iexact=address)
        if account_id:
            candidates = candidates.filter(pk=account_id)
        matches = [user for user in candidates if user.check_password(password) and self.user_can_authenticate(user)]
        return matches[0] if len(matches) == 1 else None


class RedactedConsoleEmailBackend(BaseEmailBackend):
    """Suppress development email without printing OTPs or personal data."""

    def send_messages(self, email_messages):
        # Missing SMTP configuration must not leak verification codes or
        # contact data to terminal logs. Zero means that nothing was sent.
        return 0
