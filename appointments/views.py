from datetime import date, datetime, time, timedelta
from django.contrib import messages
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from accounts.models import User
from notifications.models import Notification
from .forms import AppointmentForm, SlotForm
from .constants import BOOKING_HORIZON_DAYS, VISIT_DURATION
from .models import Appointment, AvailabilitySlot
from .scheduling import available_visit_times, booking_date_is_valid

def patient_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if request.user.role != User.Role.PATIENT: messages.error(request, "Patient access is required."); return redirect("dashboard:home_dashboard")
        return view(request, *args, **kwargs)
    return login_required(wrapped)
def doctor_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if request.user.role != User.Role.DOCTOR: messages.error(request, "Doctor access is required."); return redirect("dashboard:home_dashboard")
        return view(request, *args, **kwargs)
    return login_required(wrapped)
def doctors(request):
    q=request.GET.get("q", "").strip()[:120]
    specialization=request.GET.get("specialization", "")
    area=request.GET.get("area", "").strip()[:120]
    min_experience=request.GET.get("min_experience", "").strip()
    max_fee=request.GET.get("max_fee", "").strip()
    result=User.objects.filter(role=User.Role.DOCTOR, is_verified=True)
    if request.GET.get("availability", "available") == "available": result=result.filter(is_available=True)
    if q: result=result.filter(Q(name__icontains=q)|Q(specialization__icontains=q))
    if specialization: result=result.filter(specialization=specialization)
    if area: result=result.filter(service_area__icontains=area)
    try:
        experience_value = int(min_experience)
        if 0 <= experience_value <= 80:
            result = result.filter(experience_years__gte=experience_value)
        else:
            min_experience = ""
    except ValueError:
        min_experience = ""
    try:
        fee_value = int(max_fee)
        if 0 <= fee_value <= 1_000_000:
            result = result.filter(consultation_fee__lte=fee_value)
        else:
            max_fee = ""
    except ValueError:
        max_fee = ""
    result = result.annotate(average_rating=Avg("reviews_received__rating"), review_count=Count("reviews_received"))
    today = timezone.localdate()
    return render(request, "doctors.html", {
        "doctors": result.order_by("-average_rating", "name"),
        "form": AppointmentForm(),
        "specializations": User._meta.get_field("specialization").choices,
        "search_q": q,
        "selected_specialization": specialization,
        "area_filter": area,
        "min_experience_filter": min_experience,
        "max_fee_filter": max_fee,
        "today": today,
        "max_booking_date": today + timedelta(days=BOOKING_HORIZON_DAYS),
        "app_timezone": timezone.get_current_timezone_name(),
    })

def doctor_profile(request, doctor_id):
    doctor = get_object_or_404(
        User.objects.annotate(average_rating=Avg("reviews_received__rating"), review_count=Count("reviews_received")),
        pk=doctor_id, role=User.Role.DOCTOR, is_verified=True,
    )
    reviews = doctor.reviews_received.select_related("patient").order_by("-created_at")[:8]
    slots = doctor.availability_slots.all()
    return render(request, "doctor_profile.html", {
        "doctor": doctor, "reviews": reviews, "slots": slots,
        "app_timezone": timezone.get_current_timezone_name(),
    })

def available_slots(request, doctor_id):
    doctor = get_object_or_404(
        User,
        pk=doctor_id,
        role=User.Role.DOCTOR,
        is_verified=True,
        is_available=True,
    )
    try:
        visit_date = date.fromisoformat(request.GET.get("date", ""))
    except ValueError:
        return JsonResponse({"slots": [], "error": "Choose a valid date."}, status=400)
    if not booking_date_is_valid(visit_date):
        return JsonResponse({"slots": [], "error": "Choose a date within the next 30 days."}, status=400)

    slots = [
        {
            "value": start.strftime("%Y-%m-%dT%H:%M"),
            "label": start.strftime("%I:%M %p").lstrip("0"),
        }
        for start in (timezone.localtime(value) for value in available_visit_times(doctor, visit_date))
    ]
    return JsonResponse({"slots": slots})
@patient_required
@require_POST
def book(request):
    form=AppointmentForm(request.POST)
    if form.is_valid():
        appointment=form.save(commit=False); appointment.patient=request.user
        try:
            with transaction.atomic():
                if appointment.doctor_id:
                    available_doctor = User.objects.select_for_update().filter(
                        pk=appointment.doctor_id,
                        role=User.Role.DOCTOR,
                        is_verified=True,
                        is_available=True,
                    ).first()
                    if available_doctor is None:
                        raise ValidationError({"doctor": "This doctor is no longer accepting visits."})
                appointment.full_clean()
                appointment.save()
                targets=[appointment.doctor] if appointment.doctor else User.objects.filter(role="doctor", is_verified=True, is_available=True)
                Notification.objects.bulk_create([Notification(recipient=doctor, appointment=appointment, message=f"New appointment request from {request.user.name}.") for doctor in targets])
            messages.success(request, "Appointment request submitted.")
        except ValidationError as exc: messages.error(request, "; ".join(exc.messages))
    else: messages.error(request, " ".join(error for errors in form.errors.values() for error in errors))
    return redirect("appointments:doctors")
@patient_required
@require_POST
def cancel(request, pk):
    appointment=get_object_or_404(Appointment, pk=pk, patient=request.user)
    if appointment.status in ("Pending", "Accepted"):
        appointment.status="Cancelled"
        appointment.save()
        if appointment.doctor_id:
            Notification.objects.create(recipient=appointment.doctor, appointment=appointment, message=f"{request.user.name} cancelled a home visit request.")
        messages.success(request, "Appointment cancelled.")
    else: messages.error(request, "This appointment cannot be cancelled.")
    return redirect("dashboard:home_dashboard")
@patient_required
@require_POST
def reschedule(request, pk):
    appointment=get_object_or_404(Appointment, pk=pk, patient=request.user)
    if appointment.status not in ("Pending", "Accepted"): messages.error(request, "This appointment cannot be rescheduled."); return redirect("dashboard:home_dashboard")
    form=AppointmentForm(request.POST, instance=appointment)
    if form.is_valid():
        try:
            updated=form.save()
            if updated.doctor_id:
                Notification.objects.create(recipient=updated.doctor, appointment=updated, message=f"{request.user.name} requested a new visit time.")
            messages.success(request, "Appointment rescheduled.")
        except ValidationError as exc: messages.error(request, "; ".join(exc.messages))
    else: messages.error(request, "Enter a valid future time.")
    return redirect("dashboard:home_dashboard")
@doctor_required
def doctor_dashboard(request):
    now = timezone.now()
    today = timezone.localdate()
    today_start = timezone.make_aware(datetime.combine(today, time.min))
    tomorrow_start = timezone.make_aware(datetime.combine(today + timedelta(days=1), time.min))
    mine = Appointment.objects.filter(doctor=request.user)
    actionable_requests = Appointment.objects.filter(
        Q(doctor=request.user) | Q(doctor__isnull=True),
        status=Appointment.Status.PENDING,
        scheduled_at__gte=now,
    ).select_related("patient", "doctor").order_by("scheduled_at")
    upcoming_visits = mine.filter(
        status=Appointment.Status.ACCEPTED,
        scheduled_at__gte=now,
    ).select_related("patient").order_by("scheduled_at")
    completed_visits = mine.filter(
        status=Appointment.Status.COMPLETED,
    ).select_related("patient").order_by("-scheduled_at")[:6]
    return render(request, "doctor_dashboard.html", {
        "today_count": mine.filter(scheduled_at__gte=today_start, scheduled_at__lt=tomorrow_start).exclude(
            status__in=(Appointment.Status.CANCELLED, Appointment.Status.REJECTED),
        ).count(),
        "pending_count": actionable_requests.count(),
        "upcoming_count": upcoming_visits.count(),
        "completed_count": mine.filter(status=Appointment.Status.COMPLETED).count(),
        "open_requests": actionable_requests,
        "upcoming_visits": upcoming_visits,
        "completed_visits": completed_visits,
        "notifications": request.user.notifications.all()[:10],
        "slots": request.user.availability_slots.all(),
        "slot_form": SlotForm(),
        "app_timezone": timezone.get_current_timezone_name(),
    })
@doctor_required
@require_POST
def accept(request, pk):
    with transaction.atomic():
        appointment=get_object_or_404(
            Appointment.objects.select_for_update().filter(Q(doctor__isnull=True) | Q(doctor=request.user)),
            pk=pk,
            status=Appointment.Status.PENDING,
        )
        appointment.doctor=request.user; appointment.status="Accepted"
        try:
            available_doctor = User.objects.select_for_update().filter(
                pk=request.user.pk,
                role=User.Role.DOCTOR,
                is_verified=True,
                is_available=True,
            ).first()
            if available_doctor is None:
                raise ValidationError({"doctor": "Your profile is not currently accepting visits."})
            appointment.full_clean()
            appointment.save()
            Notification.objects.create(recipient=appointment.patient, appointment=appointment, message=f"Dr. {request.user.name} accepted your home visit request.")
            messages.success(request, "Appointment accepted.")
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
    return redirect("appointments:doctor_dashboard")
@doctor_required
@require_POST
def complete(request, pk):
    appointment=get_object_or_404(Appointment, pk=pk, doctor=request.user)
    if appointment.status == "Accepted":
        appointment.status="Completed"
        appointment.save()
        Notification.objects.create(recipient=appointment.patient, appointment=appointment, message="Your doctor marked the home visit complete. Your care documents are in your dashboard.")
        messages.success(request, "Appointment completed.")
    return redirect("appointments:doctor_dashboard")
@doctor_required
@require_POST
def reject(request, pk):
    appointment=get_object_or_404(Appointment, pk=pk, status="Pending")
    if appointment.doctor_id and appointment.doctor_id != request.user.id:
        messages.error(request, "This request is not assigned to you.")
    else:
        appointment.doctor=request.user; appointment.status="Rejected"; appointment.save()
        Notification.objects.create(recipient=appointment.patient, appointment=appointment, message="Your appointment request was declined.")
        messages.success(request, "Appointment rejected.")
    return redirect("appointments:doctor_dashboard")
@doctor_required
@require_POST
def add_slot(request):
    form=SlotForm(request.POST)
    if form.is_valid(): slot=form.save(commit=False); slot.doctor=request.user; slot.save(); messages.success(request, "Availability slot added.")
    else: messages.error(request, "Please enter a valid availability slot.")
    return redirect("appointments:doctor_dashboard")

@doctor_required
@require_POST
def remove_slot(request, pk):
    slot = get_object_or_404(AvailabilitySlot, pk=pk, doctor=request.user)
    upcoming = Appointment.objects.filter(
        doctor=request.user,
        status__in=[Appointment.Status.PENDING, Appointment.Status.ACCEPTED],
        scheduled_at__gte=timezone.now(),
    )
    for appointment in upcoming:
        local_start = timezone.localtime(appointment.scheduled_at)
        local_end = local_start + VISIT_DURATION
        fits_slot = local_start.date() == local_end.date() and slot.start_time <= local_start.time().replace(tzinfo=None) and slot.end_time >= local_end.time().replace(tzinfo=None)
        if local_start.weekday() == slot.weekday and fits_slot:
            messages.error(request, "This weekly hour is linked to a pending or accepted visit. Reschedule that visit before removing the hour.")
            return redirect("appointments:doctor_dashboard")
    slot.delete()
    messages.success(request, "Weekly availability removed.")
    return redirect("appointments:doctor_dashboard")
