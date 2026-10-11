import logging

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
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
        if settings.SUPPORT_EMAIL:
            service_label = enquiry.get_service_display()
            try:
                email = EmailMessage(
                    f"DocAtDoor service enquiry: {service_label}",
                    f"Enquiry ID: {enquiry.pk}\n"
                    f"Service: {service_label}\n"
                    "Sign in to Django Admin to review the message and manage follow-up.",
                    settings.DEFAULT_FROM_EMAIL,
                    [settings.SUPPORT_EMAIL],
                    reply_to=[enquiry.email],
                )
                sent = email.send(fail_silently=False)
            except Exception:
                logger.exception("Could not send a service enquiry to the configured support inbox")
                sent = 0
            if not sent:
                logger.error("Service enquiry %s is saved for admin follow-up but notification email was not delivered", enquiry.pk)
        messages.success(request, "Your enquiry has been recorded for staff review. Please do not send medical records or urgent-care requests through this form.")
        return render(request, "pages/contact.html", {"form": ContactForm(initial=initial), "submitted": True})
    return render(request, "pages/contact.html", {"form": form, "submitted": None})
def faq(request): return render(request, "pages/faq.html")
def page_not_found(request, exception): return render(request, "errors/404.html", status=404)
def server_error(request): return render(request, "errors/500.html", status=500)
