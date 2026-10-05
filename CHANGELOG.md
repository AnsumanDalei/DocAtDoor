# Checkpoint 12 — in progress (2026-10-02)

- Added server-side API patient registration validation for age, gender and blood group; doctor role/specialty data remains ignored. Added tests for supported values and invalid choices.
- Extended Flutter registration inputs with optional age, gender and blood group.
- Extended the Flutter client from read-only appointments to slot lookup, guided doctor home-visit booking, and doctor accept/decline/complete plus patient cancellation actions.
- Added patient tabs for report, prescription and notification lists plus doctor consultation summary/diagnosis entry.
- Persisted the signed-in account ID in secure storage so doctor-specific actions survive app restart; admin login receives an explicit secure-web-console message.
- Added cross-platform file selection, patient profile-photo/report upload, private record/prescription download, doctor prescription upload, patient rescheduling, consultation reading, reviews, and notification read actions to Flutter source.
- Added profile image file extension and 5 MB size validation to website/API registration and profile editing; API regression coverage verifies real PNG acceptance and unsupported extension rejection.
- Ran the updated full backend suite: 112 passed in 166.48s and API suite: 18 passed in 33.80s with explicit SQLite overrides. Flutter remains unbuilt because the SDK is absent.

- Configured MySQL as the application DB default and added DRF token/session authentication, throttling and role/object-scoped API workflows for accounts, profiles, doctors, availability, appointments, consultations, protected records, prescriptions, notifications, reviews, enquiries and password management.
- Added file extension/size/signature validation and a redacted default development email backend.
- Replaced the prior Nginx/Gunicorn Docker path with a Django development server + MySQL Compose setup; this is local learning infrastructure only. Historical Checkpoint 11 notes below are superseded.
- Added early shared Flutter source for authentication, patient registration/email verification, secure token storage, doctor discovery and role-aware appointment lists; native platform generation/builds remain outstanding.
- Verified 110 backend tests (temporary explicit SQLite override), Django system check, migration drift check, and authenticated fictional demo patient browser smoke. MySQL, Docker, Flutter and CI are unverified in this environment.

# Changelog (historical entries follow)



## 2026-10-02 — checkpoint 01



- Reworked the existing home page into a search-led, responsive healthcare-at-home introduction with service categories, an honest three-step doctor-visit journey, privacy information, and a clear account CTA.

- Made the verified-doctor directory publicly browsable. Booking remains patient-only and requires sign-in.

- Displayed real review averages/counts in the doctor directory instead of the existing default rating field.

- Added a service enquiry form for nursing, physiotherapy, diagnostics, and other requests. It emails only a configured `SUPPORT_EMAIL`, asks visitors not to submit sensitive health information, and does not claim success when the inbox is unset.

- Replaced hardcoded example support contact details in the contact page with the form.

- Added `seed_demo_data`, an idempotent local command for fictional `.test` patient/doctor accounts and doctor availability. It does not generate appointments or health records and is disabled in non-debug settings unless explicitly forced.

- Added contact and public-directory test cases.

- Restricted report uploads/deletion to patients and report downloads by doctors to active (accepted/completed) appointments; added regression cases for those boundaries.

- Aligned shared navigation, forms, directory cards, dashboard surfaces, and sign-in styling to a multicolor DocAtDoor visual system; added keyboard focus treatment, skip navigation, responsive layouts, and reduced-motion support.

- Configured `.env` loading and made production startup reject the repository's known placeholder secret keys.

- Rewrote the local setup documentation to use existing migrations and SQLite, and to describe the actual application scope.

- Replaced the deployment guide's unverified claims with a clear inventory of existing examples and the production setup still required.



This is a checkpoint: the requested end-to-end product transformation is not complete. See `REMAINING_TASKS.md` and `TEST_REPORT.md`.



## 2026-10-02 — continued work after checkpoint 01



- Added 60-minute appointment slots generated from weekly doctor hours, filtered out overlapping pending/accepted visits, and added a date horizon plus server-side schedule validation.

- Added a read-only date/availability endpoint and shared browser code for booking and rescheduling.

- Added doctor schedule removal with an active-appointment guard, doctor-side appointment acceptance ownership checks, and patient notifications for accepted/completed visits and prescription/consultation updates.

- Added completed-visit consultation summary/diagnosis with patient and assigned-doctor authorization, plus patient-facing read-only view and doctor dashboard links.

- Added the consultation model and portable protected-storage migration. The migration was authored manually and has not been run.

- Replaced email-link-only registration with a 6-digit code, 10-minute expiry, hashed-at-rest storage, five-attempt limit, IP rate limiting, and resend workflow; retained the legacy token route for previously issued integrations.

- Ensured a Django-created superuser has a verified email so the admin can sign in without patient OTP.

- Improved patient records, doctor workspace, notifications, admin overview, public FAQ/about, and patient feedback layouts.

- Made service-enquiry delivery failures explicit and corrected reminder delivery to mark a reminder sent only after the mail backend accepts it.

- Added scheduling, consultation, OTP, privacy, and admin regression tests. Tests and migrations remain unexecuted due to missing Django/Pytest packages and denied PyPI access.

- Added public verified-doctor profile pages with qualifications, experience, fee, weekly hours, and real patient review data; linked profiles from directory cards.

- Updated handoff and test report to checkpoint 02 and recorded current static-check results.

- Installed development dependencies in a workspace-local environment; fixed the service-enquiry `EmailMessage` reply-to issue found by tests.

- Added fictional walkthrough appointments, consultation, and review to the idempotent local demo seeder, with a regression test.

- Applied all SQLite migrations and verified the complete suite: 78 passed. Inspected home, directory, and profile in the local browser.

- Updated test report and handoff to checkpoint 03 with remaining authenticated, responsive, accessibility, and deployment QA clearly marked.



- Added a patient-only prescriptions list and patient/doctor-focused shared navigation links with regression coverage for cross-patient privacy.

- Added elder care and post-hospital recovery as enquiry-only service categories, with homepage cards and coverage.

- Added city, locality, and contact-phone fields to home-visit requests, including migration, booking validation, rescheduling preservation, and patient/doctor display.

- Added a branded SVG favicon and declared it in the shared page head.

- Added a guided booking progress/review/confirm step that shows doctor, time, fee, visit reason, address, and contact before submission.

- Expanded the patient dashboard with a next-visit panel, scoped report/prescription/notification previews, care enquiry shortcuts, and accurate future-visit counts.

- Added regression coverage for the booking review UI and patient dashboard privacy/date filtering; full suite now passes 81 tests.

- Updated checkpoint 04 handoff, remaining-task list, and test report with current dashboard and guided booking evidence.



- Added admin-managed doctor service areas and directory filters for service area, minimum experience, and maximum fee; public profile pages show the service area. Demo doctors are assigned Demo City without overwriting existing nonempty areas. Added service-area migration and filter/form/profile regression tests.

- Django system check and migration consistency pass; all SQLite migrations applied. Full suite after this change: 84 passed in 143.19s.


## 2026-10-02 — checkpoint 06

- Added durable service enquiry storage, staff-only Admin queue, triage status and notes.
- Enquiry submissions now persist even with email unconfigured or unavailable; optional email carries only the queue ID and service type.
- Added an admin-dashboard enquiry count and recent follow-up list.
- Added tests for queue persistence, failed notification delivery, honeypot behavior, staff-only access, and dashboard follow-up visibility.
- Django system check, migration consistency, source compilation, and full suite pass; **89 tests passed in 146.23s**.

## 2026-10-02 — checkpoint 07

- Replaced stacked patient/doctor mobile links with a fixed, role-specific bottom navigation, safe-area spacing, focus treatment, active-location indicators, and unread markers.
- Added role-specific navigation regression coverage and mobile layout/console browser observations.
- Recorded the required public product research and how it informed original UX choices in `DESIGN_RESEARCH.md`.
- Full suite passes: **89 passed in 121.25s**. Django checks, migration check, Python compilation, JavaScript syntax check, and CSS brace count pass.

## 2026-10-02 — checkpoint 08

- Added a doctor-managed public profile introduction with patient-field privacy boundaries and an applied schema migration.
- Reorganized doctor profiles into About, Experience, Education, Services, Availability, and Reviews; only the implemented doctor home-visit service is shown.
- Displayed uploaded doctor profile photos with descriptive alt text, with initials as the no-photo fallback.
- Updated the booking CTA to return to the selected available doctor; unavailable profiles link to other doctors.
- Added fictional demo introductions and tests for form role boundaries, public content escaping, profile sections, CTA, and seed data.
- Desktop and mobile profile browser checks pass at 1280px and 390px. Full suite: **90 passed in 118.27s**.

## 2026-10-02 — checkpoint 09

- Reworked the doctor workspace to show daily visit count, requests needing a response, confirmed upcoming visits, and completed visit history.
- Split the schedule into pending requests, upcoming confirmed visits, and recent completed care, with actionable visit details and clear empty states.
- Scoped pending requests to upcoming visits assigned to the signed-in doctor or unassigned legacy requests; dashboard metrics and history are scoped to that doctor.
- Added regression coverage for dashboard counts, request ownership, stale requests, and upcoming confirmed visits.
- Django checks, migration consistency, compileall, JavaScript syntax, CSS brace balance, and the full suite pass: **91 passed in 87.98s**.

## 2026-10-02 — checkpoint 10

- Added `SERVICE_ENQUIRY_RETENTION_DAYS` with a configurable 180-day default and `.env.example` documentation.
- Added `purge_service_enquiries`; it reports eligible records by default and only deletes when `--execute` is supplied.
- Documented the retention behavior and operator responsibilities in README and deployment notes; the command is not automatically scheduled.
- Added tests proving dry-run preservation and confirmed deletion of expired records while preserving recent enquiries.
- Focused contact tests: **11 passed**. Django check and migration check pass. Full suite: **93 passed in 97.27s**.

## 2026-10-02 — checkpoint 11

- Added production-mode Docker static collection and an Nginx reverse-proxy/static-file configuration with a shared collected-static volume.
- Added explicit `SECURE_SSL_REDIRECT`, trusted `X-Forwarded-Proto`, and opt-in HSTS preload settings; HTTP preview remains available when redirect is disabled.
- Expanded CI checks to include migration consistency and `collectstatic`.
- Production-mode static collection copied 130 files, including CSS and booking JavaScript. Django configuration confirms redirect/proxy/cookie flags when enabled; `check --deploy` reports only the intentional HSTS preload advisory.
- Docker/Compose and GitHub Actions were not available to run. Full suite: **93 passed in 98.09s**; Django and migration checks pass.
# Continued Checkpoint 12 — 2026-10-02

- Fixed the doctor directory's authenticated non-patient state: doctors and staff see “Patient account required” instead of a misleading sign-in action. Added a regression test.
- Ran the refreshed full suite: **113 passed in 134.08s** under an explicit disposable SQLite override. `manage.py check` and `makemigrations --check --dry-run` pass. MySQL 8.4 remains unverified because the local MySQL 8.0 service rejects the configured user.
- Performed read-only browser checks with fictional patient and doctor accounts. Checked patient dashboard, reports, prescriptions, notifications and profile, doctor dashboard and consultation form, role-specific directory controls, and keyboard skip-link activation. Responsive, admin, full accessibility and console-log checks remain open.

