from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers

from accounts.models import User
from accounts.forms import BLOOD_GROUP_CHOICES, GENDER_CHOICES, normalize_person_name, normalize_phone_number, validate_profile_picture
from appointments.models import Appointment, AvailabilitySlot
from core.models import ServiceEnquiry
from medical_records.models import Consultation, MedicalReport, Prescription
from medical_records.forms import validate_medical_upload
from reviews.models import Review


class PatientRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    name = serializers.CharField(max_length=120)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    age = serializers.IntegerField(min_value=1, max_value=120, required=False, allow_null=True)
    gender = serializers.ChoiceField(choices=GENDER_CHOICES, required=False, allow_blank=True)
    blood_group = serializers.ChoiceField(choices=BLOOD_GROUP_CHOICES, required=False, allow_blank=True)
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False, style={"input_type": "password"})

    def validate_email(self, value):
        value = User.objects.normalize_email(value.strip())
        if User.objects.filter(email__iexact=value).count() >= 2:
            raise serializers.ValidationError("Two accounts already use this email address. Sign in and choose an account, or use another address.")
        return value

    def validate_name(self, value):
        try:
            return normalize_person_name(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc

    def validate_phone(self, value):
        try:
            return normalize_phone_number(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value

    def validate_profile_picture(self, uploaded):
        try:
            return validate_profile_picture(uploaded) if uploaded else uploaded
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(email_verified=False, role=User.Role.PATIENT, **validated_data)
        user.set_password(password)
        code = user.issue_verification_code()
        user._verification_code = code
        user.save()
        return user


class AccountSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "name", "role", "email_verified")
        read_only_fields = fields


class PatientProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "name", "phone", "profile_picture", "age", "gender", "blood_group", "email_verified")
        read_only_fields = ("id", "email", "email_verified")

    def validate_name(self, value):
        try:
            return normalize_person_name(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc

    def validate_phone(self, value):
        try:
            return normalize_phone_number(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc

    def validate_profile_picture(self, uploaded):
        try:
            return validate_profile_picture(uploaded) if uploaded else uploaded
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc

class DoctorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id", "email", "name", "phone", "profile_picture", "specialization",
            "service_area", "qualification", "professional_bio", "experience_years",
            "consultation_fee", "is_available", "email_verified",
        )
        read_only_fields = ("id", "email", "email_verified")

    def validate_name(self, value):
        try:
            return normalize_person_name(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc

    def validate_phone(self, value):
        try:
            return normalize_phone_number(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc

    def validate_profile_picture(self, uploaded):
        try:
            return validate_profile_picture(uploaded) if uploaded else uploaded
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc


class DoctorListSerializer(serializers.ModelSerializer):
    average_rating = serializers.FloatField(read_only=True)
    review_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id", "name", "specialization", "qualification", "experience_years",
            "consultation_fee", "service_area", "professional_bio", "profile_picture",
            "is_available", "average_rating", "review_count",
        )
        read_only_fields = fields


class AvailabilitySlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailabilitySlot
        fields = ("id", "weekday", "start_time", "end_time")
        read_only_fields = ("id",)

    def validate(self, attrs):
        slot = AvailabilitySlot(doctor=self.context["request"].user, **attrs)
        try:
            slot.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages) from exc
        return attrs


class AppointmentReadSerializer(serializers.ModelSerializer):
    doctor_id = serializers.IntegerField(read_only=True, allow_null=True)
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    doctor_name = serializers.CharField(source="doctor.name", read_only=True, allow_null=True)
    doctor_specialization = serializers.CharField(source="doctor.specialization", read_only=True, allow_null=True)

    class Meta:
        model = Appointment
        fields = (
            "id", "doctor_id", "patient_name", "doctor_name", "doctor_specialization", "symptom_description",
            "address", "locality", "city", "contact_phone", "scheduled_at", "status", "created_at",
        )
        read_only_fields = fields


class AppointmentCreateSerializer(serializers.ModelSerializer):
    city = serializers.CharField(max_length=120)
    contact_phone = serializers.CharField(max_length=20)

    class Meta:
        model = Appointment
        fields = ("doctor", "symptom_description", "address", "locality", "city", "contact_phone", "scheduled_at")

    def validate_doctor(self, doctor):
        if doctor.role != User.Role.DOCTOR or not doctor.is_verified or not doctor.is_available:
            raise serializers.ValidationError("Choose a verified doctor who is accepting visits.")
        return doctor

    def validate(self, attrs):
        appointment = Appointment(patient=self.context["request"].user, **attrs)
        try:
            appointment.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages) from exc
        return attrs

    def create(self, validated_data):
        appointment = Appointment.objects.create(patient=self.context["request"].user, **validated_data)
        return appointment


class ConsultationSerializer(serializers.ModelSerializer):
    summary = serializers.CharField(max_length=4000)
    diagnosis = serializers.CharField(max_length=2000, required=False, allow_blank=True)

    class Meta:
        model = Consultation
        fields = ("summary", "diagnosis", "created_at", "updated_at")
        read_only_fields = ("created_at", "updated_at")


class MedicalReportSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = MedicalReport
        fields = ("id", "original_filename", "uploaded_at", "download_url")
        read_only_fields = fields

    def get_download_url(self, obj):
        request = self.context.get("request")
        path = f"/api/records/reports/{obj.pk}/download/"
        return request.build_absolute_uri(path) if request else path


class PrescriptionSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source="doctor.name", read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Prescription
        fields = ("id", "appointment", "doctor_name", "original_filename", "notes", "uploaded_at", "download_url")
        read_only_fields = fields

    def get_download_url(self, obj):
        request = self.context.get("request")
        path = f"/api/records/prescriptions/{obj.pk}/download/"
        return request.build_absolute_uri(path) if request else path


class ProtectedUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, uploaded):
        try:
            return validate_medical_upload(uploaded)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc


class PrescriptionUploadSerializer(ProtectedUploadSerializer):
    notes = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class ReviewSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source="doctor.name", read_only=True)

    class Meta:
        model = Review
        fields = ("id", "doctor_name", "rating", "comment", "created_at")
        read_only_fields = ("id", "doctor_name", "created_at")
        extra_kwargs = {"rating": {"min_value": 1, "max_value": 5}, "comment": {"max_length": 2000}}


class ServiceEnquirySerializer(serializers.ModelSerializer):
    website = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=200)

    class Meta:
        model = ServiceEnquiry
        fields = ("name", "email", "service", "message", "website")

    def validate_website(self, value):
        if value:
            raise serializers.ValidationError("Unable to submit this enquiry.")
        return value

    def create(self, validated_data):
        validated_data.pop("website", None)
        return ServiceEnquiry.objects.create(**validated_data)
