# Checkpoint 12 — in progress (2026-10-02)

## Current status matrix — refreshed 2026-10-02

| Area | Status | Current evidence | Next action |
|---|---|---|---|
| Django web app | PARTIAL | Existing template design retained; patient and doctor demo sessions reached their dashboard/workspace and read-only records pages. Doctor booking CTA now has a role-specific state. | Finish responsive, error-state, keyboard, accessibility, and remaining role-page browser QA. |
| Database / MySQL 8.4 | IMPLEMENTED; MYSQL NOT VERIFIED | `config/settings.py` defaults to MySQL and reads DB_ENGINE, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT. Migration drift check passes with SQLite override; local MySQL 8.0 rejects the configured user (1045). | Verify fresh migrations and full tests against authorized MySQL 8.4. |
| Authentication | IMPLEMENTED; PARTIALLY BROWSER VERIFIED | Shared patient/doctor login routes to the role-specific dashboard/workspace; OTP/email/password flows exist in source and tests. SMTP delivery is not exercised here. | Inspect admin/staff browser permissions and email delivery with a configured test service. |
| URLs, models, migrations | PRESENT; SQLITE CHECKS PASS | Root/app URL routes, models, and migration history exist; `makemigrations --check --dry-run` reports no changes. | Apply migrations on fresh MySQL 8.4 and exercise them there. |
| REST API | IMPLEMENTED; MYSQL NOT VERIFIED | `/api/` covers account, profile, doctor discovery, availability, appointments, consultations, records, notifications, reviews and enquiries; focused API suite passes 20 tests. | Run API/full suite against MySQL 8.4 and add remaining permission edges. |
| Role isolation | PARTIAL | Patient/doctor browser sessions passed role landing; verified-doctor guards protect patient appointments, records, consultations and notifications; regression cases pass. | Inspect admin/staff browser journeys and cross-role denials in authenticated UI. |
| Git / GitHub | PARTIAL | Supplied working tree has no `.git` metadata; a GitHub Actions workflow exists but no hosted run was observed. | Verify the workflow from an authorized repository checkout. |
| Docker / Compose / CI | PRESENT; NOT VERIFIED | Dockerfile, Compose and MySQL 8.4 CI service exist; Docker/CI have not run in this environment. | Build/run Compose and observe a GitHub Actions run on a suitable host. |
| Nginx / Gunicorn | EXCLUDED FROM CURRENT RUNTIME | Current Docker image starts Django `runserver` for local learning; these are not included in requirements or Compose. Some historical checkpoint text mentions prior setup. | Keep the historical notes superseded and do not describe the dev image as production. |
| Flutter Android / Windows | PARTIAL | Shared Dart source contains patient/doctor flows. Flutter SDK and native targets are unavailable. | Generate platform shells; analyze, test, and build Android and Windows. |
| Kubernetes / Terraform / Ansible / AWS | PRESENT; NOT VERIFIED | Learning manifests and preparation config exist; tools are unavailable and no AWS deployment occurred. | Validate configurations with their tools; keep deployment claims scoped to verified results. |
| Tests and local checks | PASS (SQLite override only) | 115 tests passed in 123.98s; API suite 20 passed; booking suite 20 passed; Django check and migration drift check pass. | Repeat on MySQL 8.4. |

## Implemented and locally verified

- MySQL is the application database default; DRF is installed with token and session authentication, throttling, and role/object permissions.
- API currently covers patient registration/email verification and password flows; profile; verified doctor listing, detail, public availability, and doctor-owned availability management; booking, appointment actions, consultation; protected report/prescription upload/download; notifications; reviews; service enquiries. Registration validates patient age, gender and blood-group values and cannot elevate the submitted role.
- Medical uploads are extension, size, and signature checked. Patient profile pictures have extension, size (5 MB) and decoded-image validation. Development email is suppressed without logging message bodies/recipients or OTP/reset values.
- Docker/Compose were reshaped to Django runserver + MySQL for development only. CI is configured for MySQL; neither Docker nor CI was executable here.
- Flutter shared source now includes API token login, patient registration/email verification with age/gender/blood group/profile picture, secure token storage, doctor discovery, available slots, guided home-visit booking, doctor accept/decline/complete/prescription/consultation actions, patient cancellation/rescheduling/consultation/reviews, and patient report/prescription/notification lists and protected transfers. Native Android/Windows platform targets are not generated or verified; Flutter source has not been analyzed or run.
- API privacy hardening: unverified doctors may retain their own profile and availability setup, but are denied patient appointment lists/details/actions, record downloads, prescription uploads/downloads, consultation access, and notifications. Added regression tests for appointment visibility/rejection and report/prescription/consultation access.
- Verification: focused API suite **20 passed in 43.00s**, booking suite **20 passed in 37.57s**, and latest full suite **115 passed in 123.98s** under an explicit disposable SQLite override. `manage.py check` and migration drift check pass. The local MySQL service still rejects `docatdoor` with no password (1045), so MySQL behavior is not verified. Authenticated patient and doctor browser checks and skip-link keyboard activation passed; broader QA is listed below and in `TEST_REPORT.md`.

## Not verified or incomplete

- MySQL migrations/tests need a real MySQL 8.4 service; GitHub Actions has not run.
- Dockerfile and Compose have not been executed.
- Flutter/Dart SDK was unavailable. No Android or Windows native folders, analyzer run, widget/API client tests, or builds have been produced.
- Flutter source now includes basic file transfer, reschedule/review and consultation flows; these remain unverified without Flutter runtime. Calendar and a broader doctor workspace remain incomplete.
- Basic single-replica MySQL/web Kubernetes manifests now exist, but are unvalidated. Terraform requires a caller-supplied AMI and one-IP SSH `/32`, with no app port; Ansible only prepares Docker. Both are unvalidated and do not deploy the app. AWS has not been deployed.
- Full responsive, accessibility, keyboard/focus, error/empty-state and console QA remains to be completed across role-specific pages. The public directory skip link has been checked with Tab and Enter.

## Environment and data handling

The installed MySQL80 service is running, but the app credentials are unavailable and app/root passwordless connections are rejected; Docker, Flutter, Terraform, Ansible, and kubectl executables are unavailable. Browser smoke used a separate fictional-demo SQLite file `checkpoint12-qa.sqlite3`; it and its temporary server were removed. Test databases created for this continuation are separate from the pre-existing private `db.sqlite3`, which was not inspected or modified and must never be included in a ZIP. This working tree has no Git metadata. Checkpoint 11 remains preserved.

## Next work

1. Continue Django web QA and API authorization edge coverage.
2. Verify MySQL, CI, and Docker/Compose on suitable installed services.
3. Finish the shared Flutter care workflows, generate Android/Windows platform shells, then analyze/test/build both targets.
4. Validate the basic Kubernetes manifests and Terraform/Ansible preparation so they cannot deploy the development server as production.
5. Update docs and package a sanitized checkpoint; continue until all final success criteria are verified or specifically documented as environment-blocked.
