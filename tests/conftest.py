import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _clear_ratelimit_cache():
    """login/resend-verification/forgot-password are rate-limited per IP via
    django-ratelimit, which stores its counters in Django's cache. The test
    client always uses the same IP, so without this the counters would carry
    over between tests and cause unrelated tests to fail with 403s once a
    limit is hit."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def _isolate_protected_media(tmp_path, monkeypatch):
    """Tests that upload a MedicalReport/Prescription write through the real
    medical_records.storage.protected_storage singleton. Without this, those
    uploads land in the actual project's protected_media/ folder and get
    shipped in the final ZIP. Point the singleton at a throwaway per-test
    directory instead — production storage.py is untouched."""
    from medical_records import storage as storage_module
    monkeypatch.setattr(storage_module.protected_storage, "_location", str(tmp_path))
    storage_module.protected_storage.__dict__.pop("base_location", None)
    storage_module.protected_storage.__dict__.pop("location", None)
    yield
    storage_module.protected_storage.__dict__.pop("base_location", None)
    storage_module.protected_storage.__dict__.pop("location", None)


@pytest.fixture
def patient(db):
    from accounts.models import User
    return User.objects.create_user(
        email="patient@example.com", password="TestPass123", name="Pat Patient",
        role=User.Role.PATIENT, is_verified=True, email_verified=True,
    )


@pytest.fixture
def other_patient(db):
    from accounts.models import User
    return User.objects.create_user(
        email="other-patient@example.com", password="TestPass123", name="Other Patient",
        role=User.Role.PATIENT, is_verified=True, email_verified=True,
    )


@pytest.fixture
def doctor(db):
    from datetime import time
    from accounts.models import User
    from appointments.models import AvailabilitySlot
    doctor = User.objects.create_user(
        email="doctor@example.com", password="TestPass123", name="Dr. Doctor",
        role=User.Role.DOCTOR, is_verified=True, email_verified=True, is_available=True,
        specialization="Cardiologist",
    )
    AvailabilitySlot.objects.bulk_create([
        AvailabilitySlot(doctor=doctor, weekday=weekday, start_time=time(0, 0), end_time=time(23, 59))
        for weekday in range(7)
    ])
    return doctor


@pytest.fixture
def other_doctor(db):
    from datetime import time
    from accounts.models import User
    from appointments.models import AvailabilitySlot
    doctor = User.objects.create_user(
        email="other-doctor@example.com", password="TestPass123", name="Dr. Other",
        role=User.Role.DOCTOR, is_verified=True, email_verified=True, is_available=True,
        specialization="Dermatologist",
    )
    AvailabilitySlot.objects.bulk_create([
        AvailabilitySlot(doctor=doctor, weekday=weekday, start_time=time(0, 0), end_time=time(23, 59))
        for weekday in range(7)
    ])
    return doctor
