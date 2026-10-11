from datetime import datetime, time, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from accounts.models import User
from appointments.models import Appointment, AvailabilitySlot
from django.utils import timezone
from medical_records.models import Consultation
from reviews.models import Review


class Command(BaseCommand):
    help = "Create repeatable local demonstration patients, doctors, and availability."

    def add_arguments(self, parser):
        parser.add_argument("--password", default="DemoCare2026!", help="Password assigned only to newly created demo users.")
        parser.add_argument("--force", action="store_true", help="Allow seeding when DEBUG is false.")

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError("Demo data is disabled when DEBUG=False. Pass --force only for an intentional demo environment.")

        password = options["password"]
        if len(password) < 10:
            raise CommandError("The demo password must contain at least 10 characters.")

        patient, created = User.objects.get_or_create(
            email="patient@demo.example.test",
            defaults={"name": "Aarav Mehta", "role": User.Role.PATIENT, "email_verified": True, "is_verified": True},
        )
        if created:
            patient.set_password(password)
            patient.save(update_fields=["password"])

        doctors = [
            ("doctor1@demo.example.test", "Mira Shah", "General Physician", "MBBS, MD", 12, 650,
             "Fictional demo profile. Focuses on clear primary-care conversations and practical follow-up during home visits."),
            ("doctor2@demo.example.test", "Arjun Rao", "Cardiologist", "MBBS, DM", 15, 900,
             "Fictional demo profile. Uses home visits to understand each patient's concerns and explain next steps clearly."),
            ("doctor3@demo.example.test", "Leena Iyer", "Pediatrician", "MBBS, DCH", 9, 700,
             "Fictional demo profile. Aims to make home-visit conversations comfortable for children and their caregivers."),
        ]
        doctor_accounts = {}
        for email, name, specialty, qualification, experience, fee, bio in doctors:
            doctor, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "name": name,
                    "role": User.Role.DOCTOR,
                    "specialization": specialty,
                    "service_area": "Demo City",
                    "qualification": qualification,
                    "professional_bio": bio,
                    "experience_years": experience,
                    "consultation_fee": fee,
                    "is_available": True,
                    "is_verified": True,
                    "doctor_approval_status": User.DoctorApprovalStatus.APPROVED,
                    "email_verified": True,
                },
            )
            if created:
                doctor.set_password(password)
                doctor.save(update_fields=["password"])
            elif not doctor.service_area:
                doctor.service_area = "Demo City"
                doctor.save(update_fields=["service_area"])
            if not doctor.professional_bio:
                doctor.professional_bio = bio
                doctor.save(update_fields=["professional_bio"])
            doctor_accounts[email] = doctor
            for weekday in range(7):
                AvailabilitySlot.objects.get_or_create(
                    doctor=doctor,
                    weekday=weekday,
                    start_time=time(9, 0),
                    end_time=time(17, 0),
                )

        featured_doctor = doctor_accounts["doctor1@demo.example.test"]
        completed = Appointment.objects.filter(
            patient=patient,
            doctor=featured_doctor,
            symptom_description="Demo visit: routine wellness follow-up",
            status=Appointment.Status.COMPLETED,
        ).first()
        if completed is None:
            past_date = timezone.localdate() - timedelta(days=7)
            completed = Appointment.objects.create(
                patient=patient,
                doctor=featured_doctor,
                symptom_description="Demo visit: routine wellness follow-up",
                address="12 Sample Lane, Demo City",
                scheduled_at=timezone.make_aware(datetime.combine(past_date, time(10, 0))),
                status=Appointment.Status.COMPLETED,
            )
        Consultation.objects.get_or_create(
            appointment=completed,
            defaults={
                "doctor": featured_doctor,
                "summary": "Fictional demonstration note. No real patient was seen and this is not medical advice.",
                "diagnosis": "Sample entry for demonstrating the consultation workflow.",
            },
        )
        Review.objects.get_or_create(
            appointment=completed,
            defaults={
                "patient": patient,
                "doctor": featured_doctor,
                "rating": 5,
                "comment": "Fictional demo feedback for the product walkthrough.",
            },
        )

        upcoming = Appointment.objects.filter(
            patient=patient,
            doctor=featured_doctor,
            symptom_description="Demo visit: upcoming home visit",
            status=Appointment.Status.ACCEPTED,
            scheduled_at__gt=timezone.now(),
        ).first()
        if upcoming is None:
            upcoming_date = timezone.localdate() + timedelta(days=1)
            Appointment.objects.create(
                patient=patient,
                doctor=featured_doctor,
                symptom_description="Demo visit: upcoming home visit",
                address="12 Sample Lane, Demo City",
                scheduled_at=timezone.make_aware(datetime.combine(upcoming_date, time(10, 0))),
                status=Appointment.Status.ACCEPTED,
            )

        self.stdout.write(self.style.SUCCESS("Demo accounts are ready (new accounts use the supplied --password)."))
        self.stdout.write("Patient: patient@demo.example.test")
        self.stdout.write("Doctors: doctor1@demo.example.test, doctor2@demo.example.test, doctor3@demo.example.test")
        self.stdout.write("The completed visit, consultation, review, and upcoming visit are fictional demo records only.")
