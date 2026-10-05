from django.utils import timezone
def site_context(request):
    return {"current_year": timezone.now().year, "unread_notifications": request.user.notifications.filter(is_read=False).count() if request.user.is_authenticated else 0}
