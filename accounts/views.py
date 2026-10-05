import logging
import hmac
import json
import secrets
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django_ratelimit.decorators import ratelimit

from .forms import ChangePasswordForm, LoginForm, ProfileForm, RegisterForm, VerificationCodeForm
from .models import SocialIdentity, User


logger = logging.getLogger(__name__)


def _mail(user, subject, body):
    return send_mail(subject, body, None, [user.email], fail_silently=False)


@require_http_methods(["GET", "POST"])
def register(request):
    form = RegisterForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                user = form.save()
        except DjangoValidationError as exc:
            if hasattr(exc, "message_dict"):
                for field, errors in exc.message_dict.items():
                    form.add_error(field if field in form.fields else None, errors)
            else:
                form.add_error(None, exc.messages)
            return render(request, "register.html", {"form": form, "google_oauth_enabled": settings.GOOGLE_OAUTH_ENABLED})

        request.session["pending_verification_user_id"] = user.pk
        request.session["pending_registration_user_id"] = user.pk
        try:
            sent = _mail(
                user,
                "Your DocAtDoor verification code",
                f"Your 6-digit DocAtDoor email verification code is {user._verification_code}. "
                "It expires in 10 minutes. If you did not create this account, you can ignore this message.",
            )
        except Exception:
            logger.warning("Could not deliver email verification email for user_id=%s", user.pk)
            sent = 0
        if sent:
            messages.success(request, "Your account is ready for one last check. Enter the 6-digit code sent to your email; you won't need to enter your address again.")
        else:
            messages.warning(request, "Your account details were saved, but email delivery is unavailable on this deployment. Configure email delivery, then request a new code here.")
        return redirect("accounts:verify_otp")
    return render(request, "register.html", {"form": form, "google_oauth_enabled": settings.GOOGLE_OAUTH_ENABLED})


@ratelimit(key="ip", rate="8/m", method="POST", block=True)
def login_view(request):
    pending_choice = request.session.get("pending_login_choice")
    if request.method == "POST" and request.POST.get("account_id"):
        account_id = str(request.POST.get("account_id", ""))
        if pending_choice and pending_choice.get("expires", 0) >= int(time.time()) and account_id in pending_choice.get("ids", []):
            user = User.objects.filter(pk=account_id, is_active=True).first()
            request.session.pop("pending_login_choice", None)
            if user and user.email_verified:
                _complete_login(request, user, remember_me=bool(pending_choice.get("remember")))
                return redirect(_home_for_user(user))
            if user:
                request.session["pending_verification_user_id"] = user.pk
                messages.info(request, "This account still needs email verification. Enter its code to continue.")
                return redirect("accounts:verify_otp")
        request.session.pop("pending_login_choice", None)
        messages.error(request, "That account choice expired. Sign in again to continue.")
        return redirect("accounts:login")

    data = None
    if request.method == "POST":
        data = request.POST.copy()
        # Keep compatibility with existing web clients that submit Django's old
        # AuthenticationForm field name.
        if not data.get("email") and data.get("username"):
            data["email"] = data["username"]
    form = LoginForm(data=data)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        password = form.cleaned_data["password"]
        matches = [
            user for user in User.objects.filter(email__iexact=email).order_by("pk")
            if user.is_active and user.check_password(password)
        ]
        if len(matches) > 1:
            request.session["pending_login_choice"] = {
                "ids": [str(user.pk) for user in matches],
                "expires": int(time.time()) + 300,
                "remember": form.cleaned_data["remember_me"],
            }
            return render(request, "login.html", {
                "form": LoginForm(initial={"email": email, "remember_me": form.cleaned_data["remember_me"]}),
                "account_choices": matches,
                "google_oauth_enabled": settings.GOOGLE_OAUTH_ENABLED,
            })
        request.session.pop("pending_login_choice", None)
        if not matches:
            form.add_error(None, "Email or password is incorrect.")
        else:
            user = matches[0]
            if not user.email_verified:
                request.session["pending_verification_user_id"] = user.pk
                messages.info(request, "Verify the email address for this account before signing in.")
                return redirect("accounts:verify_otp")
            _complete_login(request, user, remember_me=form.cleaned_data["remember_me"])
            next_url = request.POST.get("next") or request.GET.get("next")
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                return redirect(next_url)
            return redirect(_home_for_user(user))
    return render(request, "login.html", {
        "form": form,
        "google_oauth_enabled": settings.GOOGLE_OAUTH_ENABLED,
        "next": request.GET.get("next", ""),
    })


def _home_for_user(user):
    if user.role == User.Role.DOCTOR:
        return reverse("appointments:doctor_dashboard")
    if user.is_staff:
        return reverse("dashboard:admin_dashboard")
    return reverse("dashboard:home_dashboard")


def _complete_login(request, user, remember_me=False):
    request.session.pop("pending_registration_user_id", None)
    request.session.pop("pending_verification_user_id", None)
    request.session.pop("pending_login_choice", None)
    login(request, user, backend="accounts.backends.EmailAuthenticationBackend")
    request.session.set_expiry(settings.SESSION_COOKIE_AGE if remember_me else 0)


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, "You have signed out safely.")
    return redirect("dashboard:home")


@require_http_methods(["GET", "POST"])
def verify(request, token):
    """Require an explicit POST before accepting a legacy verification link."""
    user = get_object_or_404(User, email_verification_token=token)
    if request.method == "GET":
        return render(request, "verify_link.html", {"verification_user": user})
    if not user.email_verification_expires_at or user.email_verification_expires_at < timezone.now():
        messages.error(request, "This verification link has expired. Request a new code to continue.")
        return redirect("accounts:verify_otp")
    user.email_verified = True
    user.email_verification_token = None
    user.email_verification_code_hash = ""
    user.email_verification_expires_at = None
    user.email_verification_attempts = 0
    user.save(update_fields=[
        "email_verified", "email_verification_token", "email_verification_code_hash",
        "email_verification_expires_at", "email_verification_attempts",
    ])
    messages.success(request, "Email verified. You can now sign in.")
    return redirect("accounts:login")


@ratelimit(key="ip", rate="10/h", method="POST", block=True)
@require_http_methods(["GET", "POST"])
def verify_otp(request):
    pending_id = request.session.get("pending_verification_user_id")
    pending_user = User.objects.filter(pk=pending_id, email_verified=False).first() if pending_id else None
    if pending_id and not pending_user:
        request.session.pop("pending_verification_user_id", None)
        request.session.pop("pending_registration_user_id", None)
    form = VerificationCodeForm(request.POST or None, pending_user=pending_user)
    if request.method == "POST" and form.is_valid():
        code = form.cleaned_data["code"]
        email = User.objects.normalize_email(form.cleaned_data["email"].strip())
        with transaction.atomic():
            candidates = User.objects.select_for_update().filter(pk=pending_user.pk) if pending_user else User.objects.select_for_update().filter(email__iexact=email, email_verified=False)
            candidates = list(candidates)
            valid = [
                user for user in candidates
                if user.email_verification_attempts < 5
                and user.email_verification_expires_at
                and user.email_verification_expires_at >= timezone.now()
                and user.check_verification_code(code)
            ]
            verified_user = valid[0] if len(valid) == 1 else None
            if verified_user:
                verified_user.email_verified = True
                verified_user.email_verification_token = None
                verified_user.email_verification_code_hash = ""
                verified_user.email_verification_expires_at = None
                verified_user.email_verification_attempts = 0
                verified_user.save(update_fields=[
                    "email_verified", "email_verification_token", "email_verification_code_hash",
                    "email_verification_expires_at", "email_verification_attempts",
                ])
            else:
                for user in candidates:
                    if user.email_verification_attempts < 5:
                        user.email_verification_attempts += 1
                        user.save(update_fields=["email_verification_attempts"])
        if verified_user:
            registration_id = request.session.get("pending_registration_user_id")
            request.session.pop("pending_verification_user_id", None)
            request.session.pop("pending_registration_user_id", None)
            if str(registration_id) == str(verified_user.pk):
                _complete_login(request, verified_user, remember_me=False)
                messages.success(request, "Email verified. Your account is ready.")
                return redirect(_home_for_user(verified_user))
            messages.success(request, "Email verified. Sign in to continue.")
            return redirect("accounts:login")
        form.add_error(None, "The code is invalid, expired, or unavailable. Check the address or request a new code.")
    return render(request, "verify_email.html", {
        "form": form,
        "pending_user": pending_user,
        "resend_email": pending_user.email if pending_user else "",
        "google_oauth_enabled": settings.GOOGLE_OAUTH_ENABLED,
    })


@ratelimit(key="ip", rate="3/m", method="POST", block=True)
def resend_verification(request):
    if request.method == "POST":
        pending_id = request.session.get("pending_verification_user_id")
        if pending_id:
            targets = list(User.objects.filter(pk=pending_id, email_verified=False))
        else:
            email = request.POST.get("email", "").strip()
            targets = list(User.objects.filter(email__iexact=email, email_verified=False).order_by("pk")[:2])
        sent_count = 0
        for user in targets:
            previous = (
                user.email_verification_token, user.email_verification_code_hash,
                user.email_verification_expires_at, user.email_verification_attempts,
            )
            code = user.issue_verification_code()
            try:
                sent = _mail(
                    user,
                    "Your DocAtDoor verification code",
                    f"Hello {user.name}, your 6-digit DocAtDoor email verification code is {code}. "
                    "It expires in 10 minutes. If you did not create this account, you can ignore this message.",
                )
                if sent:
                    user.save(update_fields=[
                        "email_verification_token", "email_verification_code_hash",
                        "email_verification_expires_at", "email_verification_attempts",
                    ])
                    sent_count += 1
                else:
                    (user.email_verification_token, user.email_verification_code_hash,
                     user.email_verification_expires_at, user.email_verification_attempts) = previous
            except Exception:
                logger.warning("Could not redeliver email verification email for user_id=%s", user.pk)
                (user.email_verification_token, user.email_verification_code_hash,
                 user.email_verification_expires_at, user.email_verification_attempts) = previous
        if pending_id and targets and sent_count == 0:
            messages.error(request, "We couldn't deliver a new code. Email delivery is unavailable; the previous code remains valid if it has not expired.")
        else:
            messages.success(request, "If the address is registered and unverified, a new code has been sent.")
    return redirect("accounts:verify_otp")


GOOGLE_AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"


def _google_redirect_uri(request):
    return settings.GOOGLE_OAUTH_REDIRECT_URI or request.build_absolute_uri(reverse("accounts:google_callback"))


@require_GET
def google_start(request):
    if not settings.GOOGLE_OAUTH_ENABLED:
        messages.error(request, "Google sign-in is not configured on this deployment. Use email and password, or ask the site administrator.")
        return redirect("accounts:settings" if request.user.is_authenticated else "accounts:login")

    intent = request.GET.get("intent", "sign_in")
    if intent not in {"sign_in", "link"}:
        intent = "sign_in"
    if intent == "link" and not request.user.is_authenticated:
        messages.info(request, "Sign in before connecting Google to an existing account.")
        return redirect("accounts:login")

    state = secrets.token_urlsafe(32)
    request.session["google_oauth_state"] = {
        "value": state,
        "intent": intent,
        "user_id": request.user.pk if intent == "link" else None,
        "remember_me": request.GET.get("remember") == "1",
        "expires": int(time.time()) + 600,
    }
    query = urlencode({
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": _google_redirect_uri(request),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    })
    return redirect(f"{GOOGLE_AUTHORIZATION_ENDPOINT}?{query}")


def _google_profile_from_code(code, redirect_uri):
    token_request = Request(
        GOOGLE_TOKEN_ENDPOINT,
        data=urlencode({
            "code": code,
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(token_request, timeout=10) as response:
        token_data = json.loads(response.read().decode("utf-8"))
    access_token = token_data.get("access_token")
    if not access_token:
        raise ValueError("Google did not return an access token")
    profile_request = Request(
        GOOGLE_USERINFO_ENDPOINT,
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
    )
    with urlopen(profile_request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _verified_google_email(profile):
    email = profile.get("email", "")
    verified = profile.get("email_verified") is True or str(profile.get("email_verified", "")).lower() == "true"
    subject = profile.get("sub", "")
    if not email or not verified or not subject:
        raise ValueError("Google identity is missing a verified email or subject")
    try:
        email = User.objects.normalize_email(email.strip())
        from django.core.validators import validate_email
        validate_email(email)
    except Exception as exc:
        raise ValueError("Google identity returned an invalid email") from exc
    return email, str(subject)


def _link_google_identity(user, profile):
    email, subject = _verified_google_email(profile)
    if user.email.casefold() != email.casefold():
        return False, "The Google email must match this DocAtDoor account before it can be connected."
    existing_subject = SocialIdentity.objects.filter(provider=SocialIdentity.Provider.GOOGLE, subject=subject).select_related("user").first()
    if existing_subject:
        if existing_subject.user_id == user.pk:
            return True, "Google is already connected to this account."
        return False, "That Google account is already connected to a different DocAtDoor account."
    existing_user_identity = SocialIdentity.objects.filter(provider=SocialIdentity.Provider.GOOGLE, user=user).first()
    if existing_user_identity:
        return False, "A different Google account is already connected. Sign in with that Google account or use your password."
    try:
        SocialIdentity.objects.create(user=user, provider=SocialIdentity.Provider.GOOGLE, subject=subject)
    except IntegrityError:
        existing_subject = SocialIdentity.objects.filter(provider=SocialIdentity.Provider.GOOGLE, subject=subject).first()
        if existing_subject and existing_subject.user_id == user.pk:
            return True, "Google is connected to this account."
        return False, "That Google account could not be connected. Sign in to the matching DocAtDoor account first."
    return True, "Google is now connected to this account."


def _resolve_google_signin(profile):
    email, subject = _verified_google_email(profile)
    identity = SocialIdentity.objects.filter(
        provider=SocialIdentity.Provider.GOOGLE, subject=subject,
    ).select_related("user").first()
    if identity:
        if identity.user.is_active and identity.user.email_verified:
            return identity.user, "", None
        return None, "This DocAtDoor account is not ready for sign-in. Contact support for help.", None

    matches = list(User.objects.filter(email__iexact=email).order_by("pk")[:3])
    if len(matches) > 1:
        return None, "More than one DocAtDoor account uses this email. Sign in with your password, choose the account, then connect Google in Settings.", None
    if matches:
        user = matches[0]
        if not user.email_verified:
            return None, "An account already uses this email but is not verified. Verify that account before using Google sign-in.", user
        if not user.is_active:
            return None, "This DocAtDoor account is inactive. Contact support for help.", None
        return None, "This email already has a DocAtDoor account. Sign in with your password, then connect Google from Settings.", None

    display_name = " ".join(str(profile.get("name", "")).strip().split())[:120]
    if not display_name:
        display_name = email.split("@", 1)[0][:120] or "DocAtDoor patient"
    try:
        with transaction.atomic():
            user = User(email=email, name=display_name, role=User.Role.PATIENT, is_verified=True, email_verified=True)
            user.set_unusable_password()
            user.save()
            SocialIdentity.objects.create(user=user, provider=SocialIdentity.Provider.GOOGLE, subject=subject)
        return user, "", None
    except IntegrityError:
        identity = SocialIdentity.objects.filter(provider=SocialIdentity.Provider.GOOGLE, subject=subject).select_related("user").first()
        if identity and identity.user.is_active and identity.user.email_verified:
            return identity.user, "", None
        return None, "An account with this email was just created. Sign in again to choose the right account.", None
    except DjangoValidationError:
        return None, "A DocAtDoor account already uses this email limit. Sign in and choose an existing account.", None


@require_GET
def google_callback(request):
    stored = request.session.pop("google_oauth_state", None)
    returned_state = request.GET.get("state", "")
    if not stored or not returned_state or not hmac.compare_digest(stored.get("value", ""), returned_state) or stored.get("expires", 0) < int(time.time()):
        messages.error(request, "Google sign-in could not be verified. Start again to continue safely.")
        return redirect("accounts:login")
    if request.GET.get("error"):
        messages.info(request, "Google sign-in was canceled. Your DocAtDoor account was not changed.")
        return redirect("accounts:settings" if stored.get("intent") == "link" else "accounts:login")
    code = request.GET.get("code", "")
    if not code:
        messages.error(request, "Google did not complete sign-in. Try again or use your password.")
        return redirect("accounts:login")
    try:
        profile = _google_profile_from_code(code, _google_redirect_uri(request))
        _verified_google_email(profile)
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
        messages.error(request, "Google sign-in could not be completed. Try again, or use email and password.")
        return redirect("accounts:settings" if stored.get("intent") == "link" else "accounts:login")

    if stored.get("intent") == "link":
        user = User.objects.filter(pk=stored.get("user_id"), is_active=True).first()
        if not user or not request.user.is_authenticated or request.user.pk != user.pk:
            messages.error(request, "Your sign-in session expired. Sign in again before connecting Google.")
            return redirect("accounts:login")
        linked, detail = _link_google_identity(user, profile)
        (messages.success if linked else messages.error)(request, detail)
        return redirect("accounts:settings")

    try:
        with transaction.atomic():
            user, error, pending_user = _resolve_google_signin(profile)
    except DjangoValidationError:
        user, error, pending_user = None, "No more than two accounts can use this email address. Sign in and choose an existing account.", None
    if error:
        if pending_user:
            request.session["pending_verification_user_id"] = pending_user.pk
            messages.info(request, error)
            return redirect("accounts:verify_otp")
        messages.error(request, error)
        return redirect("accounts:login")
    _complete_login(request, user, remember_me=bool(stored.get("remember_me")))
    messages.success(request, "You are signed in with Google.")
    return redirect(_home_for_user(user))


@ratelimit(key="ip", rate="5/m", method="POST", block=True)
def forgot_password(request):
    if request.method == "POST":
        users = User.objects.filter(email__iexact=request.POST.get("email", "").strip()).order_by("pk")[:2]
        for user in users:
            user.issue_reset_token()
            user.save()
            link = request.build_absolute_uri(reverse("accounts:reset", args=[user.reset_token]))
            try:
                _mail(
                    user,
                    "Reset your DocAtDoor password",
                    f"This link is for the {user.get_role_display().lower()} account named {user.name}. "
                    "If you did not request a password reset, ignore this message.\n\n" + link,
                )
            except Exception:
                logger.warning("Could not deliver password reset email for user_id=%s", user.pk)
        messages.success(request, "If the address is registered, a reset link has been sent.")
        return redirect("accounts:login")
    return render(request, "simple_form.html", {"title": "Reset password", "field": "email", "label": "Email address"})


def reset_password(request, token):
    user = get_object_or_404(User, reset_token=token)
    if not user.reset_token_expiry or user.reset_token_expiry < timezone.now():
        messages.error(request, "This reset link has expired.")
        return redirect("accounts:forgot")
    form = SetPasswordForm(user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        user.reset_token = None
        user.reset_token_expiry = None
        user.save()
        messages.success(request, "Password updated.")
        return redirect("accounts:login")
    return render(request, "form.html", {"form": form, "title": "Choose a new password"})


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("accounts:profile")
    picture_available = False
    if request.user.profile_picture:
        try:
            picture_available = request.user.profile_picture.storage.exists(request.user.profile_picture.name)
        except (OSError, ValueError):
            picture_available = False
    return render(request, "profile.html", {
        "form": form,
        "title": "My profile",
        "profile_picture_available": picture_available,
        "google_connected": request.user.social_identities.filter(provider=SocialIdentity.Provider.GOOGLE).exists(),
        "google_oauth_enabled": settings.GOOGLE_OAUTH_ENABLED,
    })


@login_required
def settings_page(request):
    return render(request, "settings.html", {
        "google_connected": request.user.social_identities.filter(provider=SocialIdentity.Provider.GOOGLE).exists(),
        "google_oauth_enabled": settings.GOOGLE_OAUTH_ENABLED,
    })


@login_required
@require_http_methods(["GET", "POST"])
def change_password(request):
    form = ChangePasswordForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, "Password changed successfully.")
        return redirect("accounts:profile")
    return render(request, "form.html", {"form": form, "title": "Change password"})
