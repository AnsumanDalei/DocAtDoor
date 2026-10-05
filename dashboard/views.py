from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from accounts.models import User
from appointments.models import Appointment
from appointments.constants import BOOKING_HORIZON_DAYS
from medical_records.models import MedicalReport, Prescription
from core.models import ServiceEnquiry
from datetime import timedelta

def home(request): return render(request, "home.html")
@login_required
def dashboard(request):
    if request.user.role == User.Role.DOCTOR:
        from appointments.views import doctor_dashboard
        return doctor_dashboard(request)
    if request.user.is_staff:
        return admin_dashboard(request)
    appointments = Appointment.objects.filter(patient=request.user).select_related("doctor")
    today = timezone.localdate()
    upcoming_appointment = appointments.filter(
        status__in=[Appointment.Status.PENDING, Appointment.Status.ACCEPTED],
        scheduled_at__gte=timezone.now(),
    ).order_by("scheduled_at").first()
    return render(request, "patient_dashboard.html", {
        "appointments": appointments.order_by("-updated_at")[:8],
        "upcoming_appointment": upcoming_appointment,
        "recent_reports": MedicalReport.objects.filter(patient=request.user).order_by("-uploaded_at")[:3],
        "recent_prescriptions": Prescription.objects.filter(
            appointment__patient=request.user,
        ).select_related("appointment", "doctor").order_by("-uploaded_at")[:3],
        "recent_notifications": request.user.notifications.order_by("-created_at")[:3],
        "stats": {
            "upcoming": appointments.filter(
                status__in=[Appointment.Status.PENDING, Appointment.Status.ACCEPTED],
                scheduled_at__gte=timezone.now(),
            ).count(),
            "completed": appointments.filter(status="Completed").count(),
            "cancelled": appointments.filter(status="Cancelled").count(),
        },
        "today": today,
        "max_booking_date": today + timedelta(days=BOOKING_HORIZON_DAYS),
        "app_timezone": timezone.get_current_timezone_name(),
    })
@login_required
def admin_dashboard(request):
    if not request.user.is_staff: return redirect("dashboard:home")
    return render(request, "admin_dashboard.html", {
        "doctors": User.objects.filter(role=User.Role.DOCTOR),
        "pending": User.objects.filter(role=User.Role.DOCTOR, is_verified=False),
        "patients": User.objects.filter(role=User.Role.PATIENT).count(),
        "bookings_today": Appointment.objects.filter(created_at__date=timezone.localdate()).count(),
        "recent_appointments": Appointment.objects.select_related("patient", "doctor").order_by("-created_at")[:8],
        "new_enquiries": ServiceEnquiry.objects.filter(status=ServiceEnquiry.Status.NEW).count(),
        "recent_enquiries": ServiceEnquiry.objects.order_by("-created_at")[:5],
    })
