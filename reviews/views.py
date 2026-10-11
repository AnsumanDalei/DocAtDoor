from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from appointments.models import Appointment
from .forms import ReviewForm
from .models import Review

@login_required
@require_http_methods(["GET", "POST"])
def create_or_update(request, appointment_id):
    appointment = get_object_or_404(Appointment, pk=appointment_id, patient=request.user, status="Completed")
    if not appointment.doctor_id: return redirect("dashboard:home_dashboard")
    review = Review.objects.filter(appointment=appointment).first()
    form = ReviewForm(request.POST or None, instance=review)
    if request.method == "POST" and form.is_valid():
        review = form.save(commit=False); review.appointment=appointment; review.patient=request.user; review.doctor=appointment.doctor; review.save()
        appointment.doctor.rating = appointment.doctor.reviews_received.aggregate(value=Avg("rating"))["value"] or 4.5
        appointment.doctor.save(update_fields=["rating"])
        messages.success(request, "Thank you for your review.")
        return redirect("dashboard:home_dashboard")
    return render(request, "form.html", {"form": form, "title": "Rate your doctor"})
@login_required
def doctor_reviews(request):
    if (
        request.user.role != "doctor"
        or request.user.doctor_approval_status != "approved"
    ):
        return redirect("accounts:doctor_application_status" if request.user.role == "doctor" else "dashboard:home_dashboard")
    return render(request, "reviews/doctor_reviews.html", {"reviews": request.user.reviews_received.select_related("patient")})
