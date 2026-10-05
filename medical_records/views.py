from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import FileResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from accounts.models import User
from appointments.models import Appointment
from notifications.models import Notification

from .forms import ConsultationForm, UploadForm
from .models import Consultation, MedicalReport, Prescription


@login_required
def reports(request):
    if request.user.role != User.Role.PATIENT:
        return HttpResponseForbidden()
    return render(request, "reports.html", {"reports": request.user.medical_reports.all(), "form": UploadForm()})


@login_required
def prescriptions(request):
    if request.user.role != User.Role.PATIENT:
        return HttpResponseForbidden()
    items = Prescription.objects.filter(
        appointment__patient=request.user,
    ).select_related("appointment", "doctor").order_by("-uploaded_at")
    return render(request, "prescriptions.html", {"prescriptions": items})


@login_required
@require_POST
def upload_report(request):
    if request.user.role != User.Role.PATIENT:
        return HttpResponseForbidden()
    form = UploadForm(request.POST, request.FILES)
    if form.is_valid():
        uploaded = form.cleaned_data["file"]
        MedicalReport.objects.create(patient=request.user, file=uploaded, original_filename=uploaded.name)
        messages.success(request, "Report uploaded securely.")
    else:
        messages.error(request, " ".join(error for errors in form.errors.values() for error in errors))
    return redirect("records:reports")


@login_required
def download_report(request, pk):
    report = get_object_or_404(MedicalReport, pk=pk)
    related = (
        request.user.role == User.Role.DOCTOR
        and Appointment.objects.filter(
            doctor=request.user,
            patient=report.patient,
            status__in=[Appointment.Status.ACCEPTED, Appointment.Status.COMPLETED],
        ).exists()
    )
    if report.patient_id != request.user.id and not related:
        return HttpResponseForbidden()
    return FileResponse(report.file.open("rb"), as_attachment=True, filename=report.original_filename)


@login_required
@require_POST
def delete_report(request, pk):
    if request.user.role != User.Role.PATIENT:
        return HttpResponseForbidden()
    report = get_object_or_404(MedicalReport, pk=pk, patient=request.user)
    report.file.delete(save=False)
    report.delete()
    messages.success(request, "Report deleted.")
    return redirect("records:reports")


@login_required
@require_POST
def prescription(request, appointment_id):
    if request.user.role != User.Role.DOCTOR:
        return HttpResponseForbidden()
    appointment = get_object_or_404(
        Appointment,
        pk=appointment_id,
        doctor=request.user,
        status=Appointment.Status.COMPLETED,
    )
    form = UploadForm(request.POST, request.FILES)
    notes = request.POST.get("notes", "").strip()
    if len(notes) > 2000:
        messages.error(request, "Prescription notes must be 2,000 characters or fewer.")
    elif form.is_valid():
        uploaded = form.cleaned_data["file"]
        Prescription.objects.update_or_create(
            appointment=appointment,
            defaults={
                "doctor": request.user,
                "file": uploaded,
                "original_filename": uploaded.name,
                "notes": notes,
            },
        )
        Notification.objects.create(
            recipient=appointment.patient,
            appointment=appointment,
            message="Your doctor added or updated a prescription for your completed visit.",
        )
        messages.success(request, "Prescription saved.")
    else:
        messages.error(request, " ".join(error for errors in form.errors.values() for error in errors))
    return redirect("appointments:doctor_dashboard")


@login_required
def download_prescription(request, appointment_id):
    prescription = get_object_or_404(Prescription, appointment_id=appointment_id)
    if request.user.id not in (prescription.appointment.patient_id, prescription.doctor_id):
        return HttpResponseForbidden()
    return FileResponse(prescription.file.open("rb"), as_attachment=True, filename=prescription.original_filename)


@login_required
@require_http_methods(["GET", "POST"])
def consultation(request, appointment_id):
    appointment = get_object_or_404(
        Appointment.objects.select_related("patient", "doctor"),
        pk=appointment_id,
        status=Appointment.Status.COMPLETED,
    )
    record = Consultation.objects.filter(appointment=appointment).first()
    is_assigned_doctor = request.user.role == User.Role.DOCTOR and appointment.doctor_id == request.user.id
    is_patient = request.user.role == User.Role.PATIENT and appointment.patient_id == request.user.id
    if not is_assigned_doctor and not is_patient:
        return HttpResponseForbidden()

    if is_patient:
        if record is None:
            return HttpResponseForbidden()
        return render(request, "consultation.html", {"consultation": record, "read_only": True})

    form = ConsultationForm(request.POST or None, instance=record)
    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)
        record.appointment = appointment
        record.doctor = request.user
        try:
            record.full_clean()
            record.save()
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            Notification.objects.create(
                recipient=appointment.patient,
                appointment=appointment,
                message="Your doctor added or updated the consultation summary for your completed visit.",
            )
            messages.success(request, "Consultation notes saved.")
            return redirect("appointments:doctor_dashboard")
    return render(request, "consultation.html", {"form": form, "appointment": appointment, "read_only": False})
