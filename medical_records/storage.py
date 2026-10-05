"""Storage for files that must only ever be reachable through an
authenticated view, never a public URL.

Files saved here (medical reports, prescriptions) live under
settings.PROTECTED_MEDIA_ROOT, which is a completely separate directory
from MEDIA_ROOT and is never mounted at any URL in config/urls.py. The
only way to read them back is through medical_records.views.download_report
/ download_prescription, which each perform their own permission check
before streaming the file.
"""
from django.conf import settings
from django.core.files.storage import FileSystemStorage

protected_storage = FileSystemStorage(location=settings.PROTECTED_MEDIA_ROOT)
