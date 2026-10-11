# Current continuation — final web verification (2026-10-03)

The old checkpoint sections below are historical; this is the active handoff. The existing web app now has refreshed login/registration/OTP/profile/settings UI, continuous registration-to-OTP session state, explicit POST-only legacy link verification, a two-account email limit with clear account selection, remembered web sessions, opt-in Google OAuth with safe existing-account linking, and canonical `/home/` with `/dashboard/` redirect. Final reruns: full backend **124/124**, API **20/20**, focused account **28/28**, using MySQL and `--reuse-db`; no SQLite override. `accounts.0006_email_account_groups_and_google_identity` is applied to the configured application database; migration drift is clean. Login and registration were visually checked at 360/390/768/1024/1280 CSS px, and the negative-offset decorative element that caused horizontal overflow was corrected.

External live-auth blockers: `MAIL_ENABLED=false`; configured SMTP credentials were not printed, but an SMTP backend handshake ended with `SMTPServerDisconnected`; there is no dedicated OTP test recipient. `GOOGLE_OAUTH_ENABLED=false` and OAuth client settings are absent. No real email or provider request was made; automated tests mock external delivery/provider responses. `manage.py check --database default` has no errors but emits expected `auth.W004` because email is intentionally non-unique and the custom backend handles multiple matches. The project root has no `.git` metadata. Exclude `.env`, private databases, media/uploads, Flutter, caches, and credentials from the requested web ZIP.

Do not proceed into Flutter, Docker/Compose, Kubernetes, Terraform, Ansible, AWS, or other project milestones without a separate instruction. The current task is limited to documenting the live-auth blockers and producing the sanitized final web ZIP.

## Continuation after Checkpoint 12 work (2026-10-02)

- Patient REST registration now validates optional age, gender and blood group; doctored role/specialty POST fields cannot elevate an account. Regression tests verify valid persistence and invalid choices.
- Flutter source now includes demographic and photo registration, API availability lookup, guided home-visit booking, doctor accept/decline/complete/prescription/consultation, patient cancel/reschedule/review/consultation reading, and report/prescription/notification lists with file actions. It has no full doctor calendar/patient workspace.
- Current MySQL milestone: **115/115 backend tests** and **20/20 API tests** pass on MySQL 8.0.46; Django DB-aware check, migrations, and migration-drift check pass. Earlier SQLite-only counts are historical. Flutter source/build remains unverified without the SDK.
- Latest continuation: the full suite now passes **113 tests in 134.08s** under a fresh explicit SQLite override. A focused test covers the patient-only booking message for authenticated doctors; patient and doctor browser sessions reached their correct workspaces, patient records pages rendered, the doctor's own completed-visit notes rendered, and keyboard Tab/Enter activated the skip link. No clinical form was submitted. `manage.py check` and `makemigrations --check --dry-run` pass. See the current status matrix in `CHECKPOINT_12_STATUS.md`.
- Next: continue with Flutter Android/Windows finalization, then Docker/Compose, GitHub Actions, Kubernetes, Terraform, Ansible and remaining browser QA when tools are available. MySQL 8.4 is not a requirement.

# DocAtDoor handoff — checkpoint 10 (historical)



## Project state



This is the supplied Django project, continued from checkpoint 07. The current source includes public doctor profiles with doctor-managed bios and dedicated service/experience/education sections, weekly availability-driven one-hour booking, patient rescheduling/cancellation, doctor appointment actions, consultations and protected prescriptions, hashed email OTP, service enquiries, private report access, demo workflow data, and refreshed core patient/doctor/admin pages. Django checks, migrations, automated tests, and public page smoke checks have run; the larger requested transformation is still incomplete.



## Completed in source



- Kept the original Django apps, database model architecture, SQLite local setup, original migrations, tests, and deployment examples.

- Created a search-led home page, public doctor directory with service-area/minimum-experience/maximum-fee filters and profile pages, shared responsive styles, and service enquiry form with a durable staff-managed admin queue.

- Implemented home-visit city/contact capture, a guided booking review and confirmation step, plus date/time slot lookup from weekly doctor availability, overlapping visit exclusion, a 30-day horizon, server-side schedule validation, rescheduling, and guarded schedule removal.

- Added doctor appointment accept/reject/complete actions and patient/doctor notifications.

- Added consultation summaries/diagnosis for completed appointments, prescription upload, and role-checked report/prescription download.

- Added hashed six-digit email OTP with expiry, attempt limits, resend rate limiting, and legacy link compatibility.

- Added demo account/availability seeding, reminder handling, updated docs, and tests.

- Added a patient-only prescription library and role-specific primary navigation links.
- Added persistent mobile bottom navigation for patients and doctors, with role-specific destinations, current-page states, unread markers, safe-area padding, and mobile browser layout checks.

- Expanded patient dashboard with the next scheduled visit, patient-scoped recent reports/prescriptions/notifications, and clearly marked enquiry shortcuts.

- Expanded the enquiry catalog to elder care and post-hospital recovery while clearly labeling both as enquiry-only.

- Expanded public verified-doctor profiles with a doctor-managed introduction, optional photo/alt text, distinct experience, education, service, availability, and review sections. The bookable-service CTA now filters back to the selected doctor.

- Added admin-managed doctor service areas, patient profile form privacy rules, directory filters, and demo seed defaults.

- Added a `ServiceEnquiry` model and staff-only Django Admin queue with status and staff notes. The public form persists enquiries before attempting optional email notification; notification contains a reference only, and delivery failures do not lose the record. The admin dashboard shows new-enquiry count and latest follow-ups.

- Extended the local-only seed command with a repeatable fictional completed visit, consultation, review, and upcoming accepted visit; added a regression test.



## Incomplete / unverified



- Full test evidence is in `TEST_REPORT.md`: Django check and migration consistency pass; SQLite migrations apply; the 0005 profile-bio migration is applied. The latest full suite passes 93 tests; checkpoint 10 adds retention-command dry-run and deletion coverage. Public responsive checks cover home, directory, and profile at 360px, 768px, and 1366px; the updated profile was also checked at 390px and 1280px.

- The local public homepage and directory were inspected. The updated doctor profile has no horizontal overflow at 390px or 1280px; its browser console had no warnings or errors. Mobile role-specific navigation is covered by rendered-template tests but could not be authenticated browser-tested. Keyboard and broader accessibility QA remain.

- Nursing, physiotherapy, diagnostics, elder care, and recovery are informational/enquiry categories; enquiries are persisted in Django Admin; optional email only alerts staff and does not contain the message body. Enquiries older than the configurable 180-day default can be reviewed and explicitly deleted with `purge_service_enquiries`; the command is not scheduled automatically.

- Booking now has slot selection, details, a review summary, and explicit confirmation. Service selection remains fixed to doctor-at-home within the doctor directory; a broader service-specific workflow is not implemented.

- Patient dashboard and navigation are functional but do not yet provide every requested dedicated section/timeline/mobile navigation treatment; admin workflow remains primarily Django Admin.

- Demo records are fictional and intentionally include no prescription or uploaded file.

- AWS examples have not been deployment tested; no production readiness or deployment is claimed.



## Important implementation files



See `FILE_MAP.md`. Most relevant: `appointments/{models.py,views.py,scheduling.py,forms.py}`, `medical_records/{models.py,views.py,storage.py}`, `accounts/{models.py,views.py}`, templates under `templates/`, and `static/{css/style.css,js/visit-slots.js}`.



## Models



- `accounts.User`: patient/doctor/admin identity, profile, verification and OTP data.

- `appointments.AvailabilitySlot`: weekly doctor hours.

- `appointments.Appointment`: patient, optional doctor, request, schedule, workflow status.

- `medical_records.MedicalReport`, `Prescription`, `Consultation`: private records linked to patient or completed visit.

- `notifications.Notification`, `reviews.Review`: appointment-linked communication and patient feedback.



## Important routes



- `/` home; `/about/`, `/faq/`, `/contact/` public information and enquiries.

- `/appointments/doctors/` directory; `/appointments/doctors/<id>/` verified public profile; `/appointments/doctors/<id>/slots/` slot JSON; `/appointments/book/` patient booking.

- `/appointments/doctor/` doctor workspace; appointment action URLs are defined in `appointments/urls.py`.

- `/accounts/register/`, `/accounts/verify-email/`, `/accounts/login/`, `/accounts/profile/`.

- `/dashboard/`, `/records/reports/`, `/notifications/`, `/django-admin/`, `/health/`.



## Environment and next steps



Use Python 3.10+, install `requirements-dev.txt`, migrate SQLite, seed demo accounts, then run `python manage.py check`, `python manage.py makemigrations --check --dry-run`, and `pytest tests/ -v`. Fix runtime/migration failures first; then run the app and test patient, doctor, admin, privacy and responsive browser flows. Continue actionable items in `REMAINING_TASKS.md`. Do not produce a final-completed ZIP until these checks and remaining product requirements are completed.



The development seed password for newly created `.test` users is `DemoCare2026!`; it has been run locally and is repeatable. Do not use real health information or secrets in demo data.

## Checkpoint 09 update — 2026-10-02

The doctor workspace now presents four appointment summaries and separates pending requests, upcoming confirmed visits, and recent completed care. Pending actions show assigned-to-you requests plus upcoming unassigned requests; another doctor's assigned requests and past pending requests are excluded. The availability form, notifications, visit completion, consultation, and prescription actions remain available. No schema or URL changes were needed.

Regression evidence: full pytest suite **91 passed in 87.98s**; Django system check clean; migration check reports no changes; Python compilation, JavaScript syntax and CSS brace checks pass. Authenticated browser journeys were not performed.

Checkpoint 10 adds a service-enquiry retention command. The 180-day default is configurable; execution is dry-run unless `--execute` is supplied. It deletes every expired enquiry status, so operators must complete required follow-up before expiry. The command is not automatically scheduled. Targeted and full-suite verification for this addition is pending.

Next: continue the exact remaining items in `REMAINING_TASKS.md`, prioritize patient/doctor/admin end-to-end journeys, accessibility and responsive QA, and production-readiness review. Keep service offerings truthful and do not claim AWS deployment.

## Checkpoint 10 update — 2026-10-02

Added configurable service-enquiry retention with a 180-day project default. `python manage.py purge_service_enquiries` reports eligible records only; `--execute` is required to delete. This deletes all expired enquiries irrespective of triage status. The command is not scheduled, and the organization must approve the actual period and ensure follow-up is complete before expiry.

Verification: `tests/test_contact.py` **11 passed**; Django system check clean; migration check reports no changes; full pytest suite **93 passed in 97.27s**.

## Checkpoint 11 update — 2026-10-02

Container scaffolding now collects static assets before Gunicorn starts and places Nginx in front to serve the shared static volume. Django settings can enable HTTPS redirects and trust `X-Forwarded-Proto` only behind a trusted proxy; HSTS preload remains opt-in. CI YAML now runs migration and static collection checks. Production-mode `collectstatic` successfully copied 130 assets and required CSS/JS files were present. A production-like settings check confirms secure cookies, configured redirect, and proxy header. `manage.py check --deploy` reported only the optional HSTS preload advisory.

The container and Nginx configuration have not been built/run because Docker is unavailable. GitHub Actions was not run. This is not a deployment: TLS termination, origin network restrictions, backups, private media operations, database architecture, and staging remain unverified. Full suite **93 passed in 98.09s**; standard Django/migration checks passed.
