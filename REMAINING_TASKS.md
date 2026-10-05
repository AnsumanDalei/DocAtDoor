# Live priority update — final web auth verification (2026-10-03)

The entries below contain older checkpoint notes. Use this current priority list wherever they conflict:

1. Core web UX/auth and MySQL regression work is complete. Final reruns pass: account/auth 28/28, full backend 124/124, API 20/20; migration drift is clean and Django has no errors.
2. Exact SMTP blocker: environment host, port, username and password are present, but `MAIL_ENABLED=false`; a credential-only handshake ended with `SMTPServerDisconnected`. No controlled `SMTP_TEST_RECIPIENT` or `OTP_TEST_EMAIL` is configured. Do not claim live OTP delivery until the relay accepts authenticated SMTP and a controlled inbox is available.
3. Exact Google OAuth blocker: OAuth is disabled; client ID, client secret and redirect URI are not configured. Do not claim live provider verification.
4. `auth.W004` remains an expected Django warning because email is intentionally non-unique to permit two accounts; the custom backend handles ambiguity and tests cover account choice.
5. Browser checks covered login/registration at 360, 390, 768, 1024 and 1280 CSS px. Flutter, Docker/Compose, GitHub Actions hosted execution, Kubernetes, Terraform, Ansible and AWS are separate unverified deliverables and remain out of scope here.

The Django system check reports `auth.W004` because email is intentionally non-unique for the two-account rule. The custom backend handles ambiguity and the tests cover selection. The worktree has no Git metadata. Do not inspect or package local database files, `.env`, or medical uploads.

## Current continuation tasks

### Task: Finish and verify shared Flutter workflows

**STATUS:** PARTIAL — patient profile-photo/demographic registration, doctor discovery, availability lookup, guided booking, cancel/reschedule/review, appointment actions, patient record/prescription/notification lists with upload/download actions and consultation viewing, and doctor consultation/prescription flows exist in Dart source. No Flutter analyzer/build run is possible here.

**PRIORITY:** High

**FILES TO EDIT:** `flutter_app/lib/api_client.dart`, `flutter_app/lib/main.dart`, `flutter_app/pubspec.yaml`, `FLUTTER.md`, `README.md`.

**WHAT TO CHANGE:** Review/analyze the new source; fix any errors; expand the doctor schedule and assigned-patient workspace, add widget/API client tests, and improve downloaded file access on device. Generate native `android/` and `windows/` shells and run `flutter analyze`, `flutter test`, Android build, and Windows build. Complete authenticated client journeys against MySQL-backed Django.

**WHY:** Flutter Android and Windows are required clients over the shared REST API, but source-only screens are not proof of functioning apps.

**EXPECTED RESULT:** Patient and doctor flows work on each native target, use backend role enforcement, and have recorded analyze/test/build outcomes.

**HOW TO TEST:** With Flutter 3.24+, Android SDK and Windows desktop toolchain: `flutter pub get`, `flutter analyze`, `flutter test`, `flutter build apk`, and `flutter build windows`; then run authenticated client flows against Django + MySQL.

**DEPENDENCIES:** Flutter/Dart SDK; Android SDK/JDK for Android; Visual Studio C++ desktop workload for Windows; usable MySQL 8.4 and configured email for OTP.

**KNOWN PROBLEMS:** These tools and native target folders are absent in this environment. The shared client has not been analyzed or run; native file behavior, permission errors, expiry/network conditions and device UI remain unverified. Full calendar and doctor patient workflow are incomplete.

### Task: Verify app against MySQL — COMPLETE (2026-10-03)

**STATUS:** COMPLETE — local MySQL 8.0.46 verification passed. The application does not require MySQL 8.4 or another specific minor version.

**PRIORITY:** Complete

**FILES CHANGED:** `appointments/views.py` and `tests/test_core.py` only; no migration was needed. Verification records are in `TEST_REPORT.md` and this file.

**WHAT CHANGED:** Replaced the MySQL named-timezone `__date` lookup in the doctor dashboard with timezone-aware local-day bounds; corrected the test fixture to construct its “today” visit on the local date. Intended dashboard behavior is preserved.

**WHY:** SQLite-only verification cannot establish required MySQL compatibility.

**RESULT:** MySQL migrations and migration-drift check pass; full suite 115/115 and API suite 20/20 pass. Details are recorded in `TEST_REPORT.md`.

**HOW TO TEST:** Configure a dedicated MySQL app database and test database; run Django checks/migrations and the test suites using `--reuse-db`, without a SQLite override.

**DEPENDENCIES:** Authorized access to a MySQL server and its dedicated application/test databases; no minor-version pin.

**KNOWN PROBLEMS:** None for this milestone. Broader finalization work remains listed above.

# Remaining tasks (historical entries follow)



Checkpoint 10 includes public doctor profile pages, a search-led homepage, public doctor search with service-area/experience/fee filters, appointment-slot selection/validation, patient rescheduling, doctor appointment actions, consultations, email OTP, service enquiries, and private-record authorization improvements. It is not the completed transformation requested in the product brief. Continue from this exact tree; do not rebuild the project.



## Task: Run Django checks, existing tests, and new tests



**STATUS:** Completed — Django check and migration consistency pass; SQLite migrations applied; all 93 tests pass, including service-enquiry retention, doctor profile, service-area/filter, persistent service enquiry queue, and admin dashboard follow-up cases.



**PRIORITY:** Blocker for release



**FILES TO EDIT:** Fix any failures in the source files named by the test output; update `TEST_REPORT.md` after actual checks. Include both new migration files and verify dynamic private storage path migration.



**WHAT TO CHANGE:** Install `requirements-dev.txt` in a local virtual environment, run `python manage.py check`, `python manage.py makemigrations --check --dry-run`, and `pytest tests/ -v`. Resolve failures without dropping the existing security and permissions tests.



**WHY:** The checkpoint changes add a management command, public doctor directory, contact form/email, and `.env` loading that cannot be validated with static compilation alone.



**EXPECTED RESULT:** All checks pass and the report includes actual outputs. If a failure is environmental, document the exact failure instead of marking it passed.



**HOW TO TEST:** Use the commands above with project dependencies installed.



**DEPENDENCIES:** Python 3.10+, internet or cached wheels for `requirements-dev.txt`.



**KNOWN PROBLEMS:** Pytest needs a workspace `--basetemp` because sandbox permissions deny access to the user-wide temp folder.



## Task: Verify and harden doctor visit scheduling with availability



**STATUS:** Availability scheduling and a guided booking review/confirmation step are implemented; relevant automated tests pass. Authenticated browser interaction and timezone-boundary checks remain.



**PRIORITY:** High



**FILES TO EDIT:** `appointments/constants.py`, `appointments/scheduling.py`, `appointments/models.py`, `appointments/forms.py`, `appointments/views.py`, `appointments/urls.py`, `templates/doctors.html`, `templates/patient_dashboard.html`, `templates/doctor_dashboard.html`, `static/js/visit-slots.js`, `tests/conftest.py`, `tests/test_booking.py`, `tests/test_scheduling.py`, `tests/permissions_tests.py`.



**WHAT TO CHANGE:** Run the new schedule tests and Django checks; verify local timezone date boundaries and app behavior near midnight; confirm doctor row locking and SQLite behavior; decide whether to prevent removing/reducing availability for visits beyond the next booking horizon. Current code offers hourly one-hour visits within a doctor's weekly schedule for the next 30 local calendar days, excludes pending/accepted overlapping appointments, validates selections server-side, and blocks removing a slot used by an active upcoming visit.



**WHY:** Scheduling is wired and Django/database validation passed, but specific timezone-boundary and real browser interaction checks remain.



**EXPECTED RESULT:** Existing/new tests pass; patient date/time selection, rescheduling, acceptance conflict handling, and doctor schedule editing work without time-zone or database errors.



**HOW TO TEST:** Add tests for outside-hours requests, duplicate requests, unavailable doctors, simultaneous/competing acceptance, and patient/doctor notifications; then exercise them through the browser.



**DEPENDENCIES:** Use the installed development dependencies and a migrated SQLite database.



**KNOWN PROBLEMS:** Availability remains weekly recurring hours rather than dated exceptions; doctor's schedule changes do not automatically notify affected patients. SQLite does not enforce `select_for_update` row locks like a server database.



## Task: Add doctor profile pages and complete doctor consultation workflow



**STATUS:** Public profile sections, photo fallback/alt behavior, doctor-only bio editing, and selected-doctor CTA implemented; migration applied; tests pass. Public profile browser view checked at desktop and mobile widths. Authenticated doctor editing and uploaded-photo browser flow remain untested.



**PRIORITY:** High



**FILES TO EDIT:** `appointments/urls.py`, `appointments/views.py`, `templates/doctors.html`, new doctor-detail template, `medical_records/models.py`, `medical_records/forms.py`, `medical_records/views.py`, `medical_records/migrations/0003_consultation_and_protected_storage.py`, `medical_records/admin.py`, `templates/consultation.html`, `templates/doctor_dashboard.html`, `templates/patient_dashboard.html`, `tests/permissions_tests.py`.



**WHAT TO CHANGE:** Review and refine the public profile at `/appointments/doctors/<id>/`; it shows a doctor-managed introduction, verified status, listed qualification, experience, fee, one genuinely supported home-visit service, weekly hours, service area, and real review data. Run the new consultation migration and permission tests, verify patient-only read access and assigned-doctor write access, and ensure the fixed private-media storage path is portable on Windows and Linux.



**WHY:** Profile and permission workflows now have targeted test evidence, but full browser journeys and deployment portability remain unverified.



**EXPECTED RESULT:** Patients can inspect doctor profiles and only see their own records; the assigned doctor can author completed-visit notes and prescriptions.



**HOW TO TEST:** Cover cross-patient and wrong-doctor access with permission tests, then run the patient and doctor journeys in a browser.



**DEPENDENCIES:** Existing account, appointment, and medical-record models.



**KNOWN PROBLEMS:** No consultation notes are linked from uncompleted visits; browser write/read flows and Windows/Linux protected-file behavior still need manual validation.



## Task: Verify the email OTP flow and account migration



**STATUS:** OTP account tests passed in the full suite; migration applied. SMTP delivery and resend rate-limit browser flow are not externally verified.



**PRIORITY:** Medium



**FILES TO EDIT:** `accounts/models.py`, `accounts/forms.py`, `accounts/views.py`, `accounts/urls.py`, `accounts/migrations/0003_email_verification_code.py`, `templates/verify_email.html`, `templates/login.html`, `tests/test_accounts.py`.



**WHAT TO CHANGE:** Run the code-verification tests and migration checks. Verify actual SMTP delivery, console-development behavior, expiration, resend throttling, hashed code storage, and that a valid OTP cannot be reused.



**WHY:** The brief requires email OTP and the source now implements it, but no runtime proof exists yet.



**EXPECTED RESULT:** OTP registration and verification pass tests and work with configured email; existing link-based verification remains for old links.



**HOW TO TEST:** Valid, invalid, expired, already-used, rate-limited, and resend cases.



**DEPENDENCIES:** Configured email delivery for live testing; console backend remains suitable for local development.



**KNOWN PROBLEMS:** SMTP delivery is not configured or tested. In development the console backend prints verification codes.



## Task: Add service catalog and decide service-request fulfillment



**STATUS:** Partially complete — non-doctor categories remain enquiry-only; requests persist in a staff-only queue with triage status and notes. A configurable 180-day default retention cutoff and dry-run/explicit-delete management command are implemented. Service areas and actual offered services still need business confirmation; organization approval and scheduled operation of the retention command remain.



**PRIORITY:** Medium



**FILES TO EDIT:** `core/forms.py`, `core/views.py`, `templates/home.html`, `templates/pages/contact.html`, `config/settings.py`, `tests/test_contact.py`, `README.md`.



**WHAT TO CHANGE:** Decide what service categories DocAtDoor actually offers and in which cities; replace placeholder copy only with verified business information. Service enquiries have durable staff handling, IP rate limiting and a honeypot. Keep submitted fields non-clinical, confirm actual categories/areas with the business, obtain approval for `SERVICE_ENQUIRY_RETENTION_DAYS`, and configure a reviewed periodic run of `python manage.py purge_service_enquiries --execute`.



**WHY:** Nursing, physiotherapy, and diagnostic requests have no operational workflow or real support contact supplied in the ZIP.



**EXPECTED RESULT:** Visitors can request only services the organization can actually follow up on, and staff can track submitted requests if required.



**HOW TO TEST:** Validate configured/unconfigured email paths, spam throttling, form accessibility, and staff response workflow.



**DEPENDENCIES:** Real support inbox/service-area decisions for production operation.



**KNOWN PROBLEMS:** Submitted contact details and message are stored in the application database. The cleanup command is not scheduled; backups may retain deleted copies, and organization-specific retention approval is still required. Optional email carries no message body. Do not include medical records or sensitive clinical details.



## Task: Improve responsive/accessibility and product polish across every page



**STATUS:** Partial — shared styling covers public, booking, patient dashboard, and key workflows; additional secondary-page visual/accessibility review is still needed.



**PRIORITY:** High



**FILES TO EDIT:** `templates/base.html`, `templates/login.html`, `templates/form.html`, `templates/patient_dashboard.html`, `templates/doctor_dashboard.html`, `templates/admin_dashboard.html`, `templates/reports.html`, `templates/notifications/inbox.html`, `templates/reviews/doctor_reviews.html`, `templates/pages/about.html`, `templates/pages/faq.html`, `templates/errors/404.html`, `templates/errors/500.html`, `static/css/style.css`.



**WHAT TO CHANGE:** Apply one visual system to every workflow, add empty/loading/success/error states and mobile table alternatives, improve keyboard navigation and field help, check contrast and labels, and remove broken/dead interaction affordances.



**WHY:** The requested quality bar covers the whole product, while checkpoint visual work focused on public entry, discovery, and contact.



**EXPECTED RESULT:** Every patient, doctor, and admin page feels consistent and remains usable on narrow screens and with keyboard navigation.



**HOW TO TEST:** Browser viewport checks at phone/tablet/desktop widths, keyboard-only navigation, screen-reader landmarks, contrast inspection, and page screenshots.



**DEPENDENCIES:** Running Django application and browser automation.



**KNOWN PROBLEMS:** Original `docs/screenshots/` are stale and were not refreshed.



## Task: Add genuine demo workflow data and test accounts documentation



**STATUS:** Completed — fictional patient/doctor, availability, upcoming and completed visits, sample consultation and review are seeded repeatably; automated idempotence test passes.



**PRIORITY:** Medium



**FILES TO EDIT:** `appointments/management/commands/seed_demo_data.py`, optionally add management commands for demo appointments/records, `README.md`, `HANDOFF.md`, related tests.



**WHAT TO CHANGE:** Decide whether to create fictional completed visits and records for a local walkthrough; use only `.test` accounts and explicit local-development guardrails. Include demo login instructions in README only after a running seed command is verified.



**WHY:** The project brief requests a complete patient, doctor, and admin demo journey.



**EXPECTED RESULT:** A reproducible local data set supports end-to-end workflow demonstration without real patient data.



**HOW TO TEST:** Run seed twice; verify idempotence and account roles; execute patient/doctor/admin walkthrough.



**DEPENDENCIES:** Django runtime and successful migration state.



**KNOWN PROBLEMS:** No prescription or uploaded file is included. Existing account passwords are not reset.



## Task: Review and finish deployment readiness without claiming deployment



**STATUS:** Partial — added production-mode static collection, Nginx HTTP preview path, configurable HTTPS redirect and trusted-proxy settings, plus CI checks for migrations and static collection. Container orchestration has not been built or deployed; TLS, secure database/media/backup architecture, CI execution, and target-environment validation remain.



**PRIORITY:** Medium



**FILES TO EDIT:** `config/settings.py`, `.env.example`, `DEPLOYMENT.md`, `docker/`, `.github/workflows/ci.yml`, `jenkins/`, `ansible/`, `terraform/`, `README.md`.



**WHAT TO CHANGE:** Validate the Docker/Nginx static-asset path with a container build and staging run. Review cloud scaffolding for HTTPS, allowed hosts, secret handling, private media storage, backup/restore, logging, and database choices. Keep local development on SQLite and do not claim AWS deployment.



**WHY:** Existing CI and infra snippets are not proof of an operable, secure AWS deployment.



**EXPECTED RESULT:** Reproducible deployment docs and a safe sample configuration with remaining manual secrets/infrastructure clearly called out.



**HOW TO TEST:** Run CI build/test; inspect deployment configuration; only report cloud validation after access and an actual deployment.



**DEPENDENCIES:** Cloud account/credentials and environment-specific infrastructure approvals.



**KNOWN PROBLEMS:** No Docker binary, AWS credentials, or deployment environment were supplied; image build, HTTPS runtime, database/media scalability, backups, and deployment security are not verified. `check --deploy` continues to report the opt-in HSTS preload warning unless explicitly enabled.



## Task: Perform browser QA and create final release archive



**STATUS:** Public home, directory, and verified profile checked at phone/tablet/desktop widths with no horizontal overflow; directory console is clean. Authenticated browser journeys and authenticated mobile-nav inspection remain.



**PRIORITY:** Blocker for final release



**FILES TO EDIT:** Fix discovered issues across the project; update `TEST_REPORT.md`; rebuild archive under `outputs/`.



**WHAT TO CHANGE:** Start Django, test the full requested patient/doctor/admin flows and negative access cases, inspect phone/tablet/desktop layouts, correct issues, remove caches/databases/secrets, update documentation, and package one clean final ZIP.



**WHY:** The requested final quality bar requires real application, browser, permissions, and visual checks.



**EXPECTED RESULT:** Verified application and a clean `DocAtDoor_Final_Completed.zip`. Until those checks and all product work above are done, provide a checkpoint archive only.



**HOW TO TEST:** Browser journeys in `TEST_REPORT.md`, Django check/migrations/tests, and archive inventory/security inspection.



**DEPENDENCIES:** Django dependencies, a browser session, and any support/service decisions needed for real operations.



**KNOWN PROBLEMS:** Patient/doctor/admin browser journeys and mobile, keyboard, accessibility, and browser-console checks are outstanding.

## Checkpoint 09 progress note

Doctor daily scheduling dashboard is implemented and regression-tested in `appointments/views.py`, `templates/doctor_dashboard.html`, `static/css/style.css`, and `tests/test_core.py`. Summary metrics distinguish today's visits, actionable upcoming requests, confirmed upcoming visits, and completed history. Pending request visibility is limited to this doctor and unassigned legacy requests. No migration was required.

The remaining tasks below are still open unless explicitly marked complete above. Authenticated end-to-end browser journeys, keyboard/accessibility review, broader phone/tablet QA, approval and scheduled operation of the configurable retention policy, and deployment configuration review remain priorities before a final release.

## Checkpoint 10 progress note

Service-enquiry expiry is now configurable via `SERVICE_ENQUIRY_RETENTION_DAYS` (default 180 days). `python manage.py purge_service_enquiries` is a dry run; pass `--execute` to delete every enquiry older than the chosen cutoff. No scheduled job was installed. Organization approval of the period, periodic operation, and handling of follow-ups before expiry remain open.

## Checkpoint 11 progress note

The Docker image now migrates, runs `collectstatic`, then starts Gunicorn; Compose places Nginx in front and serves the shared collected-static volume. Django can trust `X-Forwarded-Proto` only when explicitly enabled. Production-mode `collectstatic` copied 130 assets and the CSS/JS files were present. Docker/Compose binaries are unavailable here, so image build, Nginx runtime, HTTPS, and staging remain unverified.

HTTPS redirect is configurable for deployments behind a trusted TLS proxy. HSTS preload remains opt-in and needs full-domain HTTPS review. CI now includes migration consistency and `collectstatic` checks; this workflow was edited but not run on GitHub in this environment.

## Checkpoint 11 progress note

Container scaffolding now collects static files and uses Nginx for static delivery/reverse proxy. HTTPS redirect and proxy awareness are explicit environment settings, and CI includes migration and static collection checks. `collectstatic` succeeded with 130 assets; production settings and Django checks were inspected. Docker/Compose, GitHub Actions, and HTTPS staging were not run; HSTS preload remains intentionally off. Continue deployment validation only in an environment that can build and run the actual container and TLS proxy.
