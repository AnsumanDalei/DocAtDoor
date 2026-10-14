import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django_ratelimit.decorators import ratelimit
from .forms import ContactForm

logger = logging.getLogger(__name__)


def health(request): return JsonResponse({"status": "ok", "time": timezone.now().isoformat()})
def about(request): return render(request, "pages/about.html")


@ratelimit(key="ip", rate="5/h", method="POST", block=True)
def contact(request):
    initial = {"service": request.GET.get("service", "other")}
    form = ContactForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        enquiry = form.save()
        email_delivered = False

        if settings.SUPPORT_EMAIL and settings.RESEND_API_KEY:
            service_label = enquiry.get_service_display()
            try:
                payload = {
                    "from": settings.RESEND_FROM_EMAIL,
                    "to": [settings.SUPPORT_EMAIL],
                    "reply_to": [enquiry.email],
                    "subject": f"DocAtDoor service enquiry: {service_label}",
                    "text": (
                        f"Enquiry ID: {enquiry.pk}\n"
                        f"Service: {service_label}\n"
                        "Sign in to Django Admin to review the message and manage follow-up."
                    ),
                }
                api_request = Request(
                    "https://api.resend.com/emails",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                with urlopen(api_request, timeout=8) as response:
                    email_delivered = 200 <= response.status < 300
            except HTTPError as exc:
                error_detail = exc.read().decode("utf-8", errors="replace")
                logger.error("Resend rejected enquiry %s (HTTP %s): %s", enquiry.pk, exc.code, error_detail[:1000])
            except (URLError, TimeoutError, OSError, ValueError):
                logger.exception(
                    "Could not send service enquiry %s through the Resend API",
                    enquiry.pk,
                )

        if email_delivered:
            messages.success(
                request,
                "Your enquiry was recorded and the notification email was sent. "
                "Please do not send medical records or urgent-care requests through this form.",
            )
        else:
            if not (settings.SUPPORT_EMAIL and settings.RESEND_API_KEY):
                logger.warning("Resend API or support email is not configured; enquiry %s saved without notification", enquiry.pk)
            logger.error(
                "Service enquiry %s is saved for admin follow-up, but notification email was not delivered",
                enquiry.pk,
            )
            messages.warning(
                request,
                "Your enquiry was saved, but we could not send the email notification. "
                "Our team will need to review it. Please do not send medical records or urgent-care requests through this form.",
            )

        return render(
            request,
            "pages/contact.html",
            {
                "form": ContactForm(initial=initial),
                "submitted": True,
                "email_delivered": email_delivered,
            },
        )
    return render(request, "pages/contact.html", {"form": form, "submitted": None})


def faq(request): return render(request, "pages/faq.html")
def page_not_found(request, exception): return render(request, "errors/404.html", status=404)
def server_error(request): return render(request, "errors/500.html", status=500)
