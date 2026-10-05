import logging
from datetime import date

from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.contrib.auth.password_validation import validate_password
from django.conf import settings
from django.core.mail import EmailMessage
from rest_framework import generics, permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from django.http import FileResponse
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.models import User
from appointments.models import Appointment, AvailabilitySlot
from appointments.constants import VISIT_DURATION
from appointments.scheduling import available_visit_times, booking_date_is_valid
from core.models import ServiceEnquiry
from medical_records.models import Consultation, MedicalReport, Prescription
from notifications.models import Notification
from reviews.models import Review

from .permissions import IsDoctor, IsPatient, IsPatientOrVerifiedDoctor, IsVerifiedDoctor
from .serializers import (
    AccountSummarySerializer,
    AppointmentCreateSerializer,
    AppointmentReadSerializer,
    AvailabilitySlotSerializer,
    ConsultationSerializer,
    DoctorProfileSerializer,
    DoctorListSerializer,
    MedicalReportSerializer,
    PatientProfileSerializer,
    PatientRegistrationSerializer,
    PrescriptionSerializer,
    PrescriptionUploadSerializer,
    ProtectedUploadSerializer,
    ReviewSerializer,
    ServiceEnquirySerializer,
)

logger = logging.getLogger(__name__)


def _send_verification_code(user, code):
    try:
        return bool(send_mail(
            "Your DocAtDoor verification code",
            f"Your 6-digit verification code is {code}. It expires in 10 minutes.",
            None,
            [user.email],
            fail_silently=False,
        ))
    except Exception:
        logger.warning("Verification email delivery failed for user_id=%s", user.pk)
        return False


def _send_account_email(user, subject, body):
    try:
        return bool(send_mail(subject, body, None, [user.email], fail_silently=False))
    except Exception:
        logger.warning("Account email delivery failed for user_id=%s", user.pk)
        return False


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    def post(self, request):
        serializer = PatientRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        sent = _send_verification_code(user, user._verification_code)
        return Response(
            {
                "account": AccountSummarySerializer(user).data,
                "verification_email_sent": sent,
                "detail": "Account created. Verify the email address before signing in.",
            },
            status=status.HTTP_201_CREATED,
        )


class TokenLoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        email = str(request.data.get("email", "")).strip()
        password = request.data.get("password", "")
        account_id = request.data.get("account_id")
        candidates = User.objects.filter(email__iexact=email, is_active=True).order_by("pk")
        if account_id:
            candidates = candidates.filter(pk=account_id)
        matches = [user for user in candidates if user.check_password(password)]
        if not matches:
            return Response({"detail": "Email or password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)
        if len(matches) > 1:
            return Response({
                "detail": "More than one account matches these credentials. Choose the account you want to use and submit account_id with the same credentials.",
                "accounts": [{"id": user.pk, "name": user.name, "role": user.role} for user in matches],
            }, status=status.HTTP_409_CONFLICT)
        user = matches[0]
        if not user.email_verified:
            return Response({"detail": "Verify your email before signing in."}, status=status.HTTP_403_FORBIDDEN)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "account": AccountSummarySerializer(user).data})


class LogoutView(APIView):
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class VerificationStatusView(APIView):
    def get(self, request):
        return Response({"email_verified": request.user.email_verified})


class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "verify_email"

    def post(self, request):
        email = str(request.data.get("email", "")).strip()
        code = str(request.data.get("code", ""))
        account_id = request.data.get("account_id")
        with transaction.atomic():
            candidates = User.objects.select_for_update().filter(email__iexact=email, email_verified=False)
            if account_id:
                candidates = candidates.filter(pk=account_id)
            candidates = list(candidates.order_by("pk")[:2])
            valid_users = [
                user for user in candidates
                if user.email_verification_attempts < 5
                and user.email_verification_expires_at
                and user.email_verification_expires_at >= timezone.now()
                and user.check_verification_code(code)
            ]
            user = valid_users[0] if len(valid_users) == 1 else None
            if user:
                user.email_verified = True
                user.email_verification_token = None
                user.email_verification_code_hash = ""
                user.email_verification_expires_at = None
                user.email_verification_attempts = 0
                user.save(update_fields=(
                    "email_verified", "email_verification_token", "email_verification_code_hash",
                    "email_verification_expires_at", "email_verification_attempts",
                ))
            elif len(valid_users) > 1:
                return Response({"detail": "The code matches more than one account. Submit account_id to identify the intended account."}, status=status.HTTP_409_CONFLICT)
            else:
                for candidate in candidates:
                    if candidate.email_verification_attempts < 5:
                        candidate.email_verification_attempts += 1
                        candidate.save(update_fields=("email_verification_attempts",))
        if not user:
            return Response({"detail": "The code is invalid, expired, or unavailable."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "Email verified. You can now sign in."})


class ResendVerificationView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "resend_otp"

    def post(self, request):
        email = str(request.data.get("email", "")).strip()
        users = User.objects.filter(email__iexact=email, email_verified=False).order_by("pk")[:2]
        for user in users:
            previous = (
                user.email_verification_token, user.email_verification_code_hash,
                user.email_verification_expires_at, user.email_verification_attempts,
            )
            code = user.issue_verification_code()
            if _send_verification_code(user, code):
                user.save(update_fields=(
                    "email_verification_token", "email_verification_code_hash",
                    "email_verification_expires_at", "email_verification_attempts",
                ))
            else:
                (user.email_verification_token, user.email_verification_code_hash,
                 user.email_verification_expires_at, user.email_verification_attempts) = previous
        return Response({"detail": "If the address is registered and unverified, a code has been sent."})


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    def post(self, request):
        email = str(request.data.get("email", "")).strip()
        users = User.objects.filter(email__iexact=email, is_active=True).order_by("pk")[:2]
        for user in users:
            user.issue_reset_token()
            user.save(update_fields=("reset_token", "reset_token_expiry"))
            reset_url = request.build_absolute_uri(reverse("accounts:reset", args=(user.reset_token,)))
            _send_account_email(user, "Reset your DocAtDoor password", f"This link is for the {user.get_role_display().lower()} account named {user.name}. If you did not request a reset, ignore this email.\n\n{reset_url}")
        return Response({"detail": "If the address is registered, a reset link has been sent."})


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset_confirm"

    def post(self, request):
        token = str(request.data.get("token", ""))
        password = request.data.get("password", "")
        user = User.objects.filter(reset_token=token, is_active=True).first()
        if not user or not user.reset_token_expiry or user.reset_token_expiry < timezone.now():
            return Response({"token": ["This reset link is invalid or expired."]}, status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_password(password, user=user)
        except ValidationError as exc:
            return Response({"password": exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(password)
        user.reset_token = None
        user.reset_token_expiry = None
        user.save(update_fields=("password", "reset_token", "reset_token_expiry"))
        Token.objects.filter(user=user).delete()
        return Response({"detail": "Password updated. Sign in with the new password."})


class ChangePasswordView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "change_password"

    def post(self, request):
        current_password = request.data.get("current_password", "")
        new_password = request.data.get("new_password", "")
        if not check_password(current_password, request.user.password):
            return Response({"current_password": ["The current password is incorrect."]}, status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_password(new_password, user=request.user)
        except ValidationError as exc:
            return Response({"new_password": exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        request.user.set_password(new_password)
        request.user.save(update_fields=("password",))
        Token.objects.filter(user=request.user).delete()
        return Response({"detail": "Password updated. Sign in again with the new password."})


class ProfileView(generics.RetrieveUpdateAPIView):
    def get_serializer_class(self):
        if self.request.user.role == User.Role.PATIENT:
            return PatientProfileSerializer
        if self.request.user.role == User.Role.DOCTOR:
            return DoctorProfileSerializer
        return PatientProfileSerializer

    def get_object(self):
        if self.request.user.role not in (User.Role.PATIENT, User.Role.DOCTOR):
            self.permission_denied(self.request, message="Patient or doctor access is required.")
        return self.request.user


class DoctorAvailabilityManagementView(APIView):
    permission_classes = [IsDoctor]

    def get(self, request):
        slots = request.user.availability_slots.all()
        return Response(AvailabilitySlotSerializer(slots, many=True).data)

    def post(self, request):
        serializer = AvailabilitySlotSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        slot = serializer.save(doctor=request.user)
        return Response(AvailabilitySlotSerializer(slot).data, status=status.HTTP_201_CREATED)


class DoctorAvailabilitySlotDetailView(APIView):
    permission_classes = [IsDoctor]

    def delete(self, request, pk):
        slot = get_object_or_404(AvailabilitySlot, pk=pk, doctor=request.user)
        upcoming = Appointment.objects.filter(
            doctor=request.user,
            status__in=(Appointment.Status.PENDING, Appointment.Status.ACCEPTED),
            scheduled_at__gte=timezone.now(),
        )
        for appointment in upcoming:
            start = timezone.localtime(appointment.scheduled_at)
            end = start + VISIT_DURATION
            if start.date() == end.date() and start.weekday() == slot.weekday and slot.start_time <= start.time().replace(tzinfo=None) and slot.end_time >= end.time().replace(tzinfo=None):
                return Response({"detail": "This availability is linked to a pending or confirmed visit."}, status=status.HTTP_409_CONFLICT)
        slot.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DoctorListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = DoctorListSerializer

    def get_queryset(self):
        queryset = User.objects.filter(role=User.Role.DOCTOR, is_verified=True)
        if self.request.query_params.get("available", "true").lower() == "true":
            queryset = queryset.filter(is_available=True)
        query = self.request.query_params.get("q", "").strip()[:120]
        area = self.request.query_params.get("area", "").strip()[:120]
        specialization = self.request.query_params.get("specialization", "").strip()[:120]
        if query:
            queryset = queryset.filter(Q(name__icontains=query) | Q(specialization__icontains=query))
        if area:
            queryset = queryset.filter(service_area__icontains=area)
        if specialization:
            queryset = queryset.filter(specialization__iexact=specialization)
        try:
            minimum_experience = int(self.request.query_params.get("min_experience", ""))
            if 0 <= minimum_experience <= 80:
                queryset = queryset.filter(experience_years__gte=minimum_experience)
        except ValueError:
            pass
        try:
            maximum_fee = int(self.request.query_params.get("max_fee", ""))
            if 0 <= maximum_fee <= 1_000_000:
                queryset = queryset.filter(consultation_fee__lte=maximum_fee)
        except ValueError:
            pass
        return queryset.annotate(
            average_rating=Avg("reviews_received__rating"),
            review_count=Count("reviews_received"),
        ).order_by("-average_rating", "name")


class DoctorDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = DoctorListSerializer
    queryset = User.objects.filter(role=User.Role.DOCTOR, is_verified=True).annotate(
        average_rating=Avg("reviews_received__rating"),
        review_count=Count("reviews_received"),
    )


class DoctorAvailabilityView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, doctor_id):
        doctor = get_object_or_404(User, pk=doctor_id, role=User.Role.DOCTOR, is_verified=True, is_available=True)
        try:
            visit_date = date.fromisoformat(request.query_params.get("date", ""))
        except ValueError:
            return Response({"date": ["Choose a valid date."]}, status=status.HTTP_400_BAD_REQUEST)
        if not booking_date_is_valid(visit_date):
            return Response({"date": ["Choose a date within the booking window."]}, status=status.HTTP_400_BAD_REQUEST)
        slots = [
            {"starts_at": start.isoformat(), "label": timezone.localtime(start).strftime("%I:%M %p").lstrip("0")}
            for start in available_visit_times(doctor, visit_date)
        ]
        return Response({"date": visit_date.isoformat(), "timezone": timezone.get_current_timezone_name(), "slots": slots})


class AppointmentListCreateView(APIView):
    permission_classes = [IsPatient]

    def get(self, request):
        queryset = Appointment.objects.filter(patient=request.user).select_related("doctor").order_by("-scheduled_at")
        return Response(AppointmentReadSerializer(queryset, many=True).data)

    def post(self, request):
        serializer = AppointmentCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            requested_doctor = serializer.validated_data.get("doctor")
            doctor = None
            if requested_doctor is not None:
                doctor = User.objects.select_for_update().filter(
                    pk=requested_doctor.pk,
                    role=User.Role.DOCTOR,
                    is_verified=True,
                    is_available=True,
                ).first()
            if requested_doctor is not None and doctor is None:
                return Response({"doctor": ["This doctor is no longer accepting visits."]}, status=status.HTTP_400_BAD_REQUEST)
            appointment = Appointment(patient=request.user, **serializer.validated_data)
            try:
                appointment.full_clean()
            except ValidationError as exc:
                errors = exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages}
                return Response(errors, status=status.HTTP_400_BAD_REQUEST)
            appointment.save()
            recipients = [doctor] if doctor else User.objects.filter(role=User.Role.DOCTOR, is_verified=True, is_available=True)
            Notification.objects.bulk_create([
                Notification(recipient=recipient, appointment=appointment, message=f"New appointment request from {request.user.name}.")
                for recipient in recipients
            ])
        return Response(AppointmentReadSerializer(appointment).data, status=status.HTTP_201_CREATED)


class AppointmentDetailView(APIView):
    permission_classes = [IsPatientOrVerifiedDoctor]

    def get_appointment(self, request, pk):
        if request.user.role == User.Role.PATIENT:
            query = Appointment.objects.filter(patient=request.user)
        elif request.user.role == User.Role.DOCTOR:
            query = Appointment.objects.filter(
                Q(doctor=request.user)
                | Q(doctor__isnull=True, status=Appointment.Status.PENDING, scheduled_at__gte=timezone.now())
            )
        else:
            self.permission_denied(request, message="This account cannot access patient appointment details.")
        return get_object_or_404(query.select_related("patient", "doctor"), pk=pk)

    def get(self, request, pk):
        appointment = self.get_appointment(request, pk)
        return Response(AppointmentReadSerializer(appointment).data)


class DoctorAppointmentListView(generics.ListAPIView):
    permission_classes = [IsVerifiedDoctor]
    serializer_class = AppointmentReadSerializer

    def get_queryset(self):
        return Appointment.objects.filter(
            Q(doctor=self.request.user)
            | Q(doctor__isnull=True, status=Appointment.Status.PENDING, scheduled_at__gte=timezone.now())
        ).select_related("patient", "doctor").order_by("scheduled_at")


class AppointmentActionView(APIView):
    permission_classes = [IsVerifiedDoctor]
    action = ""

    def post(self, request, pk):
        with transaction.atomic():
            appointment = get_object_or_404(
                Appointment.objects.select_for_update().filter(Q(doctor__isnull=True) | Q(doctor=request.user)),
                pk=pk,
            )
            if self.action in ("accept", "reject"):
                if appointment.status != Appointment.Status.PENDING:
                    return Response({"detail": "Only pending visits can be accepted or declined."}, status=status.HTTP_409_CONFLICT)
                if self.action == "accept":
                    available_doctor = User.objects.select_for_update().filter(
                        pk=request.user.pk, role=User.Role.DOCTOR, is_verified=True, is_available=True,
                    ).first()
                    if available_doctor is None:
                        return Response({"detail": "Your profile is not currently accepting visits."}, status=status.HTTP_409_CONFLICT)
                    if appointment.doctor_id is None:
                        appointment.doctor = request.user
                appointment.status = Appointment.Status.ACCEPTED if self.action == "accept" else Appointment.Status.REJECTED
                if self.action == "accept":
                    try:
                        appointment.full_clean()
                    except ValidationError as exc:
                        errors = exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages}
                        return Response(errors, status=status.HTTP_409_CONFLICT)
            elif self.action == "complete":
                if appointment.doctor_id != request.user.pk or appointment.status != Appointment.Status.ACCEPTED:
                    return Response({"detail": "Only your confirmed visits can be completed."}, status=status.HTTP_409_CONFLICT)
                appointment.status = Appointment.Status.COMPLETED
            else:
                return Response({"detail": "Unsupported action."}, status=status.HTTP_404_NOT_FOUND)
            appointment.save(update_fields=("doctor", "status", "updated_at"))
            status_message = {"accept": "accepted", "reject": "declined", "complete": "completed"}[self.action]
            Notification.objects.create(
                recipient=appointment.patient,
                appointment=appointment,
                message=f"Your visit request was {status_message} by Dr. {request.user.name}.",
            )
        return Response(AppointmentReadSerializer(appointment).data)


class PatientAppointmentActionView(APIView):
    permission_classes = [IsPatient]
    action = ""

    def post(self, request, pk):
        appointment = get_object_or_404(Appointment, pk=pk, patient=request.user)
        if appointment.status not in (Appointment.Status.PENDING, Appointment.Status.ACCEPTED):
            return Response({"detail": "This visit can no longer be changed."}, status=status.HTTP_409_CONFLICT)
        if appointment.scheduled_at <= timezone.now():
            return Response({"detail": "A visit can no longer be changed after its start time."}, status=status.HTTP_409_CONFLICT)
        if self.action == "cancel":
            appointment.status = Appointment.Status.CANCELLED
        elif self.action == "reschedule":
            requested_time = request.data.get("scheduled_at")
            new_time = parse_datetime(str(requested_time or ""))
            if new_time is None:
                return Response({"scheduled_at": ["Provide an ISO 8601 date and time."]}, status=status.HTTP_400_BAD_REQUEST)
            appointment.scheduled_at = new_time
            try:
                appointment.full_clean()
            except Exception as exc:
                from django.core.exceptions import ValidationError
                if isinstance(exc, ValidationError):
                    return Response({"scheduled_at": exc.message_dict if hasattr(exc, "message_dict") else exc.messages}, status=status.HTTP_400_BAD_REQUEST)
                raise
        appointment.save(update_fields=("status", "scheduled_at", "updated_at"))
        if appointment.doctor_id:
            Notification.objects.create(
                recipient=appointment.doctor,
                appointment=appointment,
                message=f"A patient {self.action}ed a home visit request.",
            )
        return Response(AppointmentReadSerializer(appointment).data)


class ReportListCreateView(APIView):
    permission_classes = [IsPatient]

    def get(self, request):
        reports = MedicalReport.objects.filter(patient=request.user)
        return Response(MedicalReportSerializer(reports, many=True, context={"request": request}).data)

    def post(self, request):
        serializer = ProtectedUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uploaded = serializer.validated_data["file"]
        report = MedicalReport.objects.create(
            patient=request.user,
            file=uploaded,
            original_filename=uploaded.name,
        )
        return Response(
            MedicalReportSerializer(report, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ReportDetailView(APIView):
    permission_classes = [IsPatient]

    def delete(self, request, pk):
        report = get_object_or_404(MedicalReport, pk=pk, patient=request.user)
        report.file.delete(save=False)
        report.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReportDownloadView(APIView):
    permission_classes = [IsPatientOrVerifiedDoctor]

    def get(self, request, pk):
        report = get_object_or_404(MedicalReport.objects.select_related("patient"), pk=pk)
        own_record = request.user.role == User.Role.PATIENT and report.patient_id == request.user.pk
        related_doctor = (
            request.user.role == User.Role.DOCTOR
            and Appointment.objects.filter(
                doctor=request.user,
                patient_id=report.patient_id,
                status__in=(Appointment.Status.ACCEPTED, Appointment.Status.COMPLETED),
            ).exists()
        )
        if not own_record and not related_doctor:
            return Response({"detail": "Record not found."}, status=status.HTTP_404_NOT_FOUND)
        return FileResponse(report.file.open("rb"), as_attachment=True, filename=report.original_filename)


class PrescriptionListView(APIView):
    permission_classes = [IsPatient]

    def get(self, request):
        prescriptions = Prescription.objects.filter(
            appointment__patient=request.user,
        ).select_related("appointment", "doctor")
        return Response(PrescriptionSerializer(prescriptions, many=True, context={"request": request}).data)


class PrescriptionDownloadView(APIView):
    permission_classes = [IsPatientOrVerifiedDoctor]

    def get(self, request, pk):
        prescription = get_object_or_404(
            Prescription.objects.select_related("appointment", "doctor"),
            pk=pk,
        )
        is_patient = request.user.role == User.Role.PATIENT and prescription.appointment.patient_id == request.user.pk
        is_doctor = (
            request.user.role == User.Role.DOCTOR
            and request.user.is_verified
            and prescription.doctor_id == request.user.pk
        )
        if not is_patient and not is_doctor:
            return Response({"detail": "Prescription not found."}, status=status.HTTP_404_NOT_FOUND)
        return FileResponse(prescription.file.open("rb"), as_attachment=True, filename=prescription.original_filename)


class PrescriptionUploadView(APIView):
    permission_classes = [IsVerifiedDoctor]

    def post(self, request, appointment_id):
        appointment = get_object_or_404(
            Appointment,
            pk=appointment_id,
            doctor=request.user,
            status=Appointment.Status.COMPLETED,
        )
        serializer = PrescriptionUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uploaded = serializer.validated_data["file"]
        prescription = Prescription.objects.filter(appointment=appointment).first()
        previous_file = prescription.file if prescription else None
        if prescription is None:
            prescription = Prescription(appointment=appointment, doctor=request.user)
        prescription.doctor = request.user
        prescription.file = uploaded
        prescription.original_filename = uploaded.name
        prescription.notes = serializer.validated_data.get("notes", "")
        prescription.full_clean(exclude=("file",))
        prescription.save()
        if previous_file and previous_file.name != prescription.file.name:
            previous_file.delete(save=False)
        Notification.objects.create(
            recipient=appointment.patient,
            appointment=appointment,
            message="Your doctor added or updated a prescription for your completed visit.",
        )
        return Response(
            PrescriptionSerializer(prescription, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ConsultationDetailView(APIView):
    permission_classes = [IsPatientOrVerifiedDoctor]

    def get_accessible_appointment(self, request, appointment_id):
        appointment = get_object_or_404(
            Appointment.objects.select_related("patient", "doctor"),
            pk=appointment_id,
            status=Appointment.Status.COMPLETED,
        )
        allowed = (
            request.user.role == User.Role.PATIENT and appointment.patient_id == request.user.pk
        ) or (
            request.user.role == User.Role.DOCTOR and appointment.doctor_id == request.user.pk
        )
        if not allowed:
            return None
        return appointment

    def get(self, request, appointment_id):
        appointment = self.get_accessible_appointment(request, appointment_id)
        if appointment is None:
            return Response({"detail": "Consultation not found."}, status=status.HTTP_404_NOT_FOUND)
        consultation = get_object_or_404(Consultation, appointment=appointment)
        return Response(ConsultationSerializer(consultation).data)

    def post(self, request, appointment_id):
        if request.user.role != User.Role.DOCTOR:
            return Response({"detail": "Doctor access is required."}, status=status.HTTP_403_FORBIDDEN)
        appointment = get_object_or_404(
            Appointment,
            pk=appointment_id,
            doctor=request.user,
            status=Appointment.Status.COMPLETED,
        )
        existing = Consultation.objects.filter(appointment=appointment).first()
        serializer = ConsultationSerializer(existing, data=request.data)
        serializer.is_valid(raise_exception=True)
        consultation = existing or Consultation(appointment=appointment, doctor=request.user)
        for field, value in serializer.validated_data.items():
            setattr(consultation, field, value)
        try:
            consultation.full_clean()
        except ValidationError as exc:
            errors = exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages}
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)
        consultation.save()
        Notification.objects.create(
            recipient=appointment.patient,
            appointment=appointment,
            message="Your doctor added or updated the consultation summary for your completed visit.",
        )
        return Response(ConsultationSerializer(consultation).data)


class NotificationListView(APIView):
    permission_classes = [IsPatientOrVerifiedDoctor]

    def get(self, request):
        notifications = request.user.notifications.select_related("appointment").all()
        return Response([
            {
                "id": item.pk,
                "appointment_id": item.appointment_id,
                "message": item.message,
                "is_read": item.is_read,
                "created_at": item.created_at,
            }
            for item in notifications
        ])


class NotificationDetailView(APIView):
    permission_classes = [IsPatientOrVerifiedDoctor]

    def patch(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notification.is_read = True
        notification.save(update_fields=("is_read",))
        return Response({"id": notification.pk, "is_read": notification.is_read})

    def delete(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notification.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class NotificationReadAllView(APIView):
    permission_classes = [IsPatientOrVerifiedDoctor]

    def post(self, request):
        request.user.notifications.filter(is_read=False).update(is_read=True)
        return Response(status=status.HTTP_204_NO_CONTENT)


class DoctorReviewListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ReviewSerializer

    def get_queryset(self):
        return Review.objects.filter(
            doctor_id=self.kwargs["doctor_id"],
            doctor__role=User.Role.DOCTOR,
            doctor__is_verified=True,
        ).select_related("doctor").order_by("-created_at")


class PatientReviewView(APIView):
    permission_classes = [IsPatient]

    def post(self, request, appointment_id):
        appointment = get_object_or_404(
            Appointment.objects.select_related("doctor"),
            pk=appointment_id,
            patient=request.user,
            status=Appointment.Status.COMPLETED,
        )
        if appointment.doctor_id is None:
            return Response({"detail": "This visit has no assigned doctor to review."}, status=status.HTTP_409_CONFLICT)
        review = Review.objects.filter(appointment=appointment).first()
        is_new = review is None
        serializer = ReviewSerializer(review, data=request.data)
        serializer.is_valid(raise_exception=True)
        review = serializer.save(appointment=appointment, patient=request.user, doctor=appointment.doctor)
        rating = appointment.doctor.reviews_received.aggregate(value=Avg("rating"))["value"] or 4.5
        User.objects.filter(pk=appointment.doctor_id).update(rating=rating)
        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED if is_new else status.HTTP_200_OK)


class ServiceEnquiryCreateView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "service_enquiry"

    def post(self, request):
        serializer = ServiceEnquirySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        enquiry = serializer.save()
        if settings.SUPPORT_EMAIL:
            try:
                email = EmailMessage(
                    f"DocAtDoor service enquiry: {enquiry.get_service_display()}",
                    f"Enquiry ID: {enquiry.pk}\nService: {enquiry.get_service_display()}\nSign in to Django Admin to review the message.",
                    settings.DEFAULT_FROM_EMAIL,
                    [settings.SUPPORT_EMAIL],
                    reply_to=[enquiry.email],
                )
                if not email.send(fail_silently=False):
                    logger.error("Service enquiry %s was saved but staff notification was not delivered", enquiry.pk)
            except Exception:
                logger.warning("Service enquiry %s was saved but staff notification failed", enquiry.pk)
        return Response(
            {"detail": "Your enquiry has been recorded for staff review. Do not send medical records or urgent-care requests through this form."},
            status=status.HTTP_201_CREATED,
        )
