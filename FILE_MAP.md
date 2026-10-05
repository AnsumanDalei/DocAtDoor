# Checkpoint 12 additions/current notes (2026-10-02)

- `templates/doctors.html` — patient booking, signed-out login, and authenticated non-patient states for the doctor directory; the latest continuation adds a clear patient-account requirement for doctors/staff.
- `tests/test_booking.py` — regression coverage for directory filters, booking, schedule validation, and the authenticated-doctor booking affordance.
- `config/settings.py` — MySQL default with environment-driven connection settings; SQLite is used only by explicit local test/QA overrides, not as the final database.
- `api/serializers.py` — patient registration serializer validates age, gender and blood group for REST clients; `tests/test_api.py` verifies invalid choices are rejected and doctor role elevation is prevented.
- `flutter_app/lib/api_client.dart`, `flutter_app/lib/main.dart` — shared API client plus patient registration/profile photo, doctor discovery, slot-based booking/actions, report/prescription upload/download, patient reschedule/review/consultation/notification actions and doctor consultation/prescription workflow. Flutter source has not been analyzed or built.
- `flutter_app/pubspec.yaml` — shared Flutter dependencies. `file_picker` handles Android/Windows photo and medical-document selection; `path_provider` saves protected downloads in app documents.

- `api/` — DRF serializers, permissions and endpoints for account, profile, directory, availability, appointment, consultation, records, notification, review, enquiry and password workflows.
- `flutter_app/lib/` — shared Flutter API client and early authentication/discovery/appointment-list UI for Android/Windows. Native targets are not generated or verified.
- `API.md` — current API path and access contract.
- `CHECKPOINT_12_STATUS.md` — current progress and verification gaps.
- `k8s/`, `KUBERNETES.md` — basic MySQL/web manifests and learning instructions; not cluster-validated.
- `docker/`, `.github/workflows/ci.yml` — MySQL/Django development Compose and MySQL CI configuration; both unexecuted here.

Old Checkpoint 11 Nginx/Gunicorn Docker notes below are historical and superseded. Kubernetes manifests exist but are unvalidated. This working tree has no Git metadata.

# File map (historical notes follow)



This map names files present in the supplied project and identifies the important implementation points and checkpoint changes.



## Project and configuration



- `manage.py` — Django command entry point.

- `config/settings.py` — apps, middleware, SQLite, email, local `.env` loading, and security settings. Changed in checkpoint 01.

- `config/urls.py` — root URL routing and development media configuration.

- `requirements.txt`, `requirements-dev.txt` — application and test dependencies.

- `.env.example`, `.gitignore` — environment template and local-data exclusions. `.env.example` changed in checkpoint 01.

- `README.md` — local setup, workflows, and current scope. Changed in checkpoint 01.
- `DESIGN_RESEARCH.md` — dated product/UI reference notes and original design decisions.

- `DEPLOYMENT.md` — deployment notes; infrastructure has not been deployed.

- `CHANGELOG.md`, `FILE_MAP.md`, `REMAINING_TASKS.md`, `TEST_REPORT.md`, `HANDOFF.md`, `CONTINUATION_PROMPT.txt` — checkpoint documentation.



## User accounts



- `accounts/migrations/0004_user_service_area.py` — doctor service-area field.



- `accounts/models.py` — custom email user, patient/doctor/admin roles, doctor profile fields including the public introduction, hashed email OTP and reset tokens.

- `accounts/forms.py` — patient registration, OTP verification, role-aware profile editing, password change.

- `accounts/views.py`, `accounts/urls.py` — registration, login, OTP and legacy email-link verification, password reset, profile, logout.

- `accounts/admin.py`, `accounts/migrations/` — admin and schema history, including `0003_email_verification_code.py`, `0004_user_service_area.py`, and `0005_user_professional_bio.py`.



## Visits and doctor availability



- `appointments/models.py` — home-visit appointments, weekly availability entries, and schedule/overlap validation.

- `appointments/constants.py`, `appointments/scheduling.py` — one-hour visit duration, booking horizon, and available-time calculation.

- `appointments/forms.py` — appointment and availability forms.

- `appointments/views.py`, `appointments/urls.py` — public doctor directory with service area, experience, and fee filters and profile, available-slot endpoint, patient booking/cancel/reschedule, doctor schedule/requests, and status notifications.

- `appointments/management/commands/seed_demo_data.py` — idempotent local `.test` accounts (including demo service area), availability, and fictional completed/upcoming appointment walkthrough data.

- `appointments/management/commands/send_appointment_reminders.py` — reminder command.

- `appointments/migrations/` — appointment schema history, including optional locality and required-on-new-booking city/contact fields.



## Records, notifications, reviews, dashboards



- `medical_records/models.py`, `medical_records/storage.py`, `medical_records/forms.py`, `medical_records/views.py`, `medical_records/urls.py` — private reports/prescriptions, consultation summaries, and authorized read/write/download flow.

- `medical_records/migrations/0003_consultation_and_protected_storage.py` — consultation schema and environment-based storage correction; manually authored and not migration-tested.

- `notifications/models.py`, `notifications/views.py`, `notifications/urls.py` — user notifications and inbox actions.

- `reviews/models.py`, `reviews/forms.py`, `reviews/views.py`, `reviews/urls.py` — patient reviews.

- `dashboard/views.py`, `dashboard/urls.py`, `dashboard/context_processors.py` — patient, doctor, and admin dashboard routing, patient-scoped previews, admin appointment/enquiry summaries, and shared context.

- `core/views.py`, `core/urls.py`, `core/forms.py` — public pages, health endpoint, and rate-limited service enquiry capture with optional email notification.



- `core/models.py`, `core/admin.py`, `core/migrations/0001_initial.py` — durable service enquiry queue and staff follow-up fields.

## Templates and styles



- `templates/base.html` — shared navigation, role-aware mobile bottom navigation, messages, footer, metadata, CSS, and JS links.

- `templates/home.html` — search-led homepage.

- `templates/doctors.html` — public doctor search, available-time selection, and patient visit request cards.

- `templates/doctor_profile.html` — public verified doctor profile, doctor introduction/photo, experience, education, supported service, availability, fees, and reviews.

- `templates/consultation.html` — doctor authoring and patient read-only completed-visit consultation view.

- `templates/prescriptions.html` — patient-only prescription library with authorized downloads.

- `templates/verify_email.html` — OTP entry page.

- `templates/pages/contact.html` — support enquiry form.

- `templates/pages/about.html`, `templates/pages/faq.html` — public information pages.

- `templates/form.html`, `templates/simple_form.html`, `templates/login.html` — account forms and sign-in.

- `templates/patient_dashboard.html`, `templates/doctor_dashboard.html`, `templates/admin_dashboard.html` — patient, doctor, and admin workflows.

- `templates/reports.html`, `templates/notifications/inbox.html`, `templates/reviews/doctor_reviews.html` — records, notifications, review pages.

- `templates/errors/404.html`, `templates/errors/500.html` — error pages.

- `static/css/style.css` — shared responsive design system, cards, forms, dashboards, and mobile layouts.

- `static/favicon.svg` — DocAtDoor's compact browser tab icon.

- `static/js/visit-slots.js` — fetches available times, advances the booking review flow, and supports rescheduling.



## Tests and deployment scaffolding



- `tests/conftest.py`, `tests/test_accounts.py`, `tests/test_booking.py`, `tests/permissions_tests.py`, `tests/test_core.py`, `tests/test_notifications.py`, `tests/test_reviews.py` — existing test coverage.

- `tests/test_contact.py` — public-directory and contact workflow cases.

- `tests/test_scheduling.py` — slot filtering, horizon, availability validation, and slot-removal protection.

- `tests/test_demo_seed.py` — repeatability and workflow-content check for local fictional demo data.

- `.github/workflows/ci.yml`, `docker/Dockerfile`, `docker/docker-compose.yml`, `jenkins/Jenkinsfile`, `ansible/`, `terraform/` — existing CI and deployment scaffolding; not deployed or fully reviewed in this checkpoint.

- `docs/screenshots/` — screenshots supplied inside the original ZIP; not refreshed for the new UI.

## Checkpoint 09 additions

- `appointments/views.py` — doctor dashboard builds per-doctor summary metrics and date-filtered pending/upcoming/completed querysets; no appointment permissions or state transitions were changed.
- `templates/doctor_dashboard.html` — renders the four summary tiles and separate actionable schedule/history sections.
- `static/css/style.css` — semantic dashboard summary colors, spacing, and narrow-screen layout.
- `tests/test_core.py` — regression coverage for metrics and doctor-specific request visibility.

## Checkpoint 10 additions

- `config/settings.py` — reads `SERVICE_ENQUIRY_RETENTION_DAYS` (default 180).
- `.env.example` — shows the retention value and safe review/execute commands.
- `core/management/commands/purge_service_enquiries.py` — reports expired enquiries by default and deletes only with `--execute`.
- `tests/test_contact.py` — checks dry-run preservation and explicit deletion cutoff.
- `README.md`, `DEPLOYMENT.md`, `HANDOFF.md`, `REMAINING_TASKS.md`, `TEST_REPORT.md` — describe the policy, evidence, and unscheduled operational step.

## Checkpoint 11 additions

- `config/settings.py` — supports environment-configured static root, optional HTTPS redirects, trusted proxy scheme recognition, and opt-in HSTS preload.
- `docker/Dockerfile` — collects static assets before running Gunicorn and prepares the static volume path.
- `docker/docker-compose.yml` — runs Django behind Nginx and shares collected static assets.
- `docker/nginx.conf` — serves `/static/` and forwards dynamic requests to Django; it does not terminate TLS.
- `.github/workflows/ci.yml` — adds migration drift and `collectstatic` checks.
- `.env.example`, `DEPLOYMENT.md`, `README.md` — describe the HTTP preview and trusted TLS proxy requirements.
