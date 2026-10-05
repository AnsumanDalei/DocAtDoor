from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .models import Notification

@login_required
def inbox(request):
    return render(request, "notifications/inbox.html", {"notifications": request.user.notifications.all()})
@login_required
@require_POST
def mark_all_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect("notifications:inbox")
@login_required
@require_POST
def delete(request, pk):
    get_object_or_404(Notification, pk=pk, recipient=request.user).delete()
    return redirect("notifications:inbox")
