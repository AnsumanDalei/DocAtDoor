# DocAtDoor verification report

## Final web verification and live-auth blockers — 2026-10-03

| Check | Result | Evidence / limit |
|---|---|---|
| Full backend suite | PASS — 124 tests | `python -m pytest -p no:cacheprovider -q --reuse-db`; 124 passed in 208.94s against the dedicated MySQL test database. No SQLite override. |
| Account UX/auth suite | PASS — 28 tests | `python -m pytest tests/test_accounts.py -q --reuse-db`; covers registration/OTP continuity, explicit POST verification, email ambiguity, remembered sessions, Google conflict behavior, profile/settings and `/home/`. |
| REST API suite | PASS — 20 tests | `python -m pytest -p no:cacheprovider -q tests/test_api.py --reuse-db`; 20 passed in 48.81s against MySQL. |
| Django database-aware check | PASS WITH WARNING | `manage.py check --database default --verbosity 1`; no errors. Django reports expected `auth.W004` because the two-account-per-email rule makes email non-unique; the configured backend resolves ambiguity and tests cover it. |
| MySQL schema | PASS | `manage.py migrate --noinput` applied `accounts.0006_email_account_groups_and_google_identity`; `makemigrations --check --dry-run` reports no changes. |
| Responsive browser layout | PASS | Login and registration reviewed at 360, 390, 768, 1024, and 1280 CSS px. Registration initially had horizontal overflow from an off-card decorative pseudo-element; moving it inside the card yields document width equal to the viewport content width at all five breakpoints. |
| SMTP configuration/transport | BLOCKED | SMTP host, port, username and password are configured through environment settings, but `MAIL_ENABLED` resolves false. A credential-only SMTP backend handshake failed with `SMTPServerDisconnected`. No dedicated `SMTP_TEST_RECIPIENT` or `OTP_TEST_EMAIL` is configured; no email was sent. |
| Real registration/OTP email journey | BLOCKED | Requires an accepting SMTP relay, `MAIL_ENABLED=true`, and a controlled test recipient so the delivered OTP can be retrieved. Automated OTP flow remains covered by tests. |
| Live Google OAuth | BLOCKED BY CONFIGURATION | `GOOGLE_OAUTH_ENABLED` resolves false; client ID, client secret and redirect URI are absent. No live provider request was made. State validation, verified-email, new-patient, and account-conflict logic is implemented; the success callback is mocked in tests. |

The current source has no `.git` metadata. These test counts supersede older historical counts below. No SQLite verification was used for this milestone. No SMTP/OAuth credentials or OTP values were printed.

## MySQL compatibility fix and verification — 2026-10-03

All database-backed verification below used MySQL with `DB_NAME=docatdoor_db`; Django tests used the dedicated `test_docatdoor_db` with `--reuse-db`. No SQLite override was used.

| Check | Result | Evidence |
|---|---|---|
| Django database-aware system check | PASS | `manage.py check --database default --verbosity 1`; no issues. |
| MySQL migrations | PASS | `manage.py migrate --noinput`; no migrations remained to apply. The schema had been migrated in the preceding MySQL run. |
| Migration drift | PASS | `manage.py makemigrations --check --dry-run`; no changes detected. |
| Focused regression | PASS — 1 test | `tests/test_core.py::test_doctor_dashboard_schedule_metrics_and_requests_are_scoped`; 1 passed in 3.29s against MySQL. |
| Full backend suite | PASS — 115 tests | `pytest -p no:cacheprovider -q tests/ --reuse-db ...`; 115 passed in 138.14s against MySQL. |
| REST API suite | PASS — 20 tests | `pytest -p no:cacheprovider -q tests/test_api.py --reuse-db ...`; 20 passed in 38.29s against MySQL. |

### Root cause and fix

The dashboard used `scheduled_at__date=today`. Django compiled this for MySQL as `DATE(CONVERT_TZ(scheduled_at, UTC, Asia/Kolkata))`; the local MySQL instance has no named timezone data, so `CONVERT_TZ(..., 'Asia/Kolkata')` returns `NULL` and the query counts no visits. The test fixture also used `timezone.now().replace(hour=10)`, which can stay on the previous UTC date when the local date has advanced. The dashboard now filters a timezone-aware local-midnight-to-local-midnight range, preserving local-day behavior without MySQL timezone tables, and the fixture now constructs its 10:00 visit on `timezone.localdate()`.

The MySQL server used for this verification is 8.0.46; no specific MySQL minor version is an application requirement.

## Historical Checkpoint 12 verification — 2026-10-02

## Finalization audit — 2026-10-02

| Check | Result | Evidence / limit |
|---|---|---|
| Current API suite | PASS — 20 tests in 35.93s | Ran with `DB_ENGINE=django.db.backends.sqlite3`, `DB_NAME=:memory:`, `pytest -p no:cacheprovider -q tests/test_api.py --basetemp=<system-temp> --tb=short`. Existing project database was not used. |
| Django system check | PASS | `manage.py check --verbosity 1`; default engine is MySQL, and this check does not connect to the database. |
| MySQL application connection | BLOCKED | `manage.py check --database default --verbosity 2` fails with error 1045: `docatdoor` denied using no password. No `.env` or DB environment variables are present. MySQL80 service is running; MySQL 8.4 integration is not verified. |
| Migration drift | PASS (SQLite override only) | `DB_ENGINE=django.db.backends.sqlite3`, `DB_NAME=:memory:`, `manage.py makemigrations --check --dry-run`: no changes detected. This is not MySQL migration verification. |
| Flutter Android / Windows | BLOCKED | Flutter CLI unavailable; `flutter_app/android` and `flutter_app/windows` are absent. No analysis, platform builds, or runtime QA. |
| Docker / Compose | BLOCKED | Docker CLI unavailable; Compose runtime/config validation not performed. |
| GitHub Actions | CONFIGURATION PRESENT; HOSTED RUN UNVERIFIED | Workflow reviewed; no `.git` metadata, GitHub CLI, or actionlint available. |
| Kubernetes | MANIFESTS PRESENT; VALIDATION BLOCKED | kubectl/YAML parser unavailable; manifests inspected only. `/health/` exists in Django URLs for the configured probes. |
| Terraform / Ansible | VALIDATION BLOCKED | Terraform and ansible-playbook are unavailable; source reviewed only. No AWS deployment occurred. |
| Web/browser QA | PARTIAL; CURRENT RUNTIME QA BLOCKED | No local app listener on port 8000. No server was started during this audit. Earlier browser smoke is recorded below. |

The latest recorded full backend run remains **115 passed in 123.98s** on a disposable SQLite override; it was not rerun in this finalization audit. The current focused API suite was run and passed as recorded above.

| Area | Result | Evidence / limit |
|---|---|---|
| Backend regression suite | PASS — 115 tests in 123.98s | `pytest tests/ -q --basetemp=.pytest-tmp-full-next2` with explicit disposable SQLite override; does not prove MySQL behavior. |
| API regression suite | PASS — 20 tests in 35.93s (current audit) | `DB_ENGINE=django.db.backends.sqlite3`, `DB_NAME=:memory:`, then `pytest -p no:cacheprovider -q tests/test_api.py --basetemp=<system-temp> --tb=short`; includes current API tests and does not touch the project database. |
| Booking regression suite | PASS — 20 tests in 37.57s | `pytest tests/test_booking.py -q --basetemp=.pytest-tmp-booking-qa`; fixtures now use a fixed 10:00 in-hours slot. |
| Directory role-label regression | PASS — 1 test in 2.01s | Authenticated doctor sees `Patient account required`, not a sign-in link; patient booking controls remain available in browser. |
| API test collection | PASS — 20 tests collected (current audit) | `pytest -p no:cacheprovider --collect-only -q tests/test_api.py`; confirms current file contains 20 tests. The 18-test run below is historical and superseded by the current 20-test pass above. |
| Django system check | PASS | Default app settings use MySQL; check did not require a database connection. |
| Migration drift check | PASS | `makemigrations --check --dry-run` under explicit SQLite override; no model changes detected. |
| Authenticated browser smoke | PASS (partial) | Separate fictional-demo SQLite database; patient login/dashboard, reports, prescriptions, notifications, profile, and doctor-booking controls; doctor login/workspace, own consultation view, and role-specific directory state. Keyboard Tab/Enter activated skip link. No appointment or clinical record was submitted or changed. Responsive, broad accessibility, admin, and console QA remain incomplete. |
| MySQL integration / GitHub Actions | NOT VERIFIED | MySQL80 service exists but app credentials are unavailable (1045); workflow has not run remotely. |
| Docker/Compose | NOT VERIFIED | Docker unavailable. |
| Flutter | SOURCE UPDATED; NOT VERIFIED | Flutter/Dart unavailable; no native platform targets, analyzer/test run or builds. File-picker and app-documents download flows require runtime validation. |
| Kubernetes / Terraform / Ansible | NOT VERIFIED | Tools unavailable; basic manifests/configuration exist but have not been validated. |

No AWS deployment occurred. Existing private `db.sqlite3` was not inspected or changed. Checkpoint 12 is in progress.

The browser smoke used `checkpoint12-browser-qa.sqlite3`, a separate fictional seed DB, and a local Django development server. The temporary server and QA database are removed after verification. The browser tree showed no errors in the pages inspected, but browser console logs were not independently collected in this run.

The first full run after adding the verified-doctor API guards had three failures in existing booking tests because their helper selected the current local wall-clock time (around 23:00), outside seeded doctor availability. The helper in `tests/test_booking.py` now fixes the test slot at 10:00; the booking suite and full suite then passed. No product scheduling rule was relaxed.

# Test report — checkpoint 08 (historical)

## Checkpoint 12 continuation update — 2026-10-02

| Check | Result | Evidence |
|---|---|---|
| `manage.py check` | PASS | “System check identified no issues (0 silenced).” Default MySQL settings; this check did not open a DB connection. |
| API suite (historical) | PASS (SQLite override) | An earlier snapshot collected and passed **18 tests in 33.80s**. Superseded: current audit collected and passed **20 tests in 35.93s** using in-memory SQLite. |
| Patient registration details/profile photo | PASS (SQLite override) | Registration cases: **3 passed**. Invalid choices reject; patient details persist without role elevation; valid PNG accepted and unsupported extension rejected. |
| API suite under default MySQL config | BLOCKED BY LOCAL CREDENTIALS | Test DB setup failed with MySQL error 1045: `docatdoor`@`localhost` denied with no password. No test tables were created; default MySQL behavior remains unverified. |
| Flutter care/file flows | SOURCE IMPLEMENTED; NOT RUNTIME VERIFIED | Flutter/Dart SDK and native platform folders are unavailable; no analyze/test/build or live API client run. |
| Full suite after this update | PASS (SQLite override) | `pytest tests/ -q --reuse-db --tb=short --basetemp=.pytest-tmp57`: **112 passed in 166.48s**. |



Only checks actually run are marked PASS. The test run was against Django 5.2.17 on Python 3.12.14, Windows, and SQLite.



| Check | Result | Evidence |

|---|---|---|

| Python syntax compilation | PASS | Python compile checks completed for project source/test modules; the full test run imported and executed the application modules. |

| JavaScript syntax | PASS | `node --check static/js/visit-slots.js` completed. |

| CSS brace balance | PASS | Fresh count: 564 opening and 564 closing braces. |

| `manage.py check` | PASS | “System check identified no issues (0 silenced).” |

| `makemigrations --check --dry-run` | PASS | “No changes detected.” |

| SQLite migration application | PASS | `manage.py migrate --noinput` applied all migrations, including OTP, consultation/protected storage, appointment location/contact, doctor service-area, doctor profile biography, and service enquiry fields. |

| Doctor profile content and CTA | PASS | Doctor-only editable introduction, About/Experience/Education/Services/Availability/Reviews sections, selected-doctor return link, and escaped public bio are covered by booking/profile tests. |

| Guided booking review test | PASS | Patient directory render exposes progress, review, doctor summary, and confirm controls. |

| Patient dashboard previews | PASS | Document/notification isolation test and upcoming-visit date filter pass. |

| Full pytest suite | PASS | `pytest tests/ -q --basetemp=.pytest-tmp33 --reuse-db`: **90 passed in 118.27s**. |

| Patient prescription list permission | PASS | Included in the final full run; own records appear, cross-patient content is hidden, doctors receive 403. |

| New service category cards | PASS | Homepage smoke test shows elder care and recovery as enquiry only; corresponding service form categories are choices. |

| Contact email tests | PASS | Included in the final full run; earlier targeted run also passed 4/4 after replacing unsupported `send_mail(reply_to=...)` with `EmailMessage`. |

| Demo seed idempotence | PASS | `tests/test_demo_seed.py` invokes the command twice and confirms exactly one completed and one upcoming appointment, consultation, and review. |

| Homepage render after adding the branded favicon link | PASS | `test_home_and_health`: 1 passed after the final shared-head edit. |

| Patient dashboard render after showing location/contact details | PASS | `test_patient_dashboard_renders`: 1 passed after the appointment model and template updates. |

| Local migration + demo seed | PASS | All migrations applied to local SQLite; seed ran twice without errors. The local database is excluded from ZIP. |

| Service enquiry queue | PASS | `tests/test_contact.py`: 9 passed, including persisted record without support email, failed notification preservation, honeypot rejection, anonymous denial, and staff access. `test_core.py`: 10 passed including admin dashboard follow-up visibility. |
| Directory filter tests | PASS | Targeted booking suite: 18 passed, including combined area/experience/fee, invalid numeric filters, and profile/form service-area checks. |

| Public browser smoke check | PASS (checkpoint 04 and updated profile in checkpoint 08) | Local app at `127.0.0.1:8017`: homepage, doctor directory, and verified doctor profile rendered. Profile displayed schedule and fictional demo feedback. |

| Patient/doctor/admin authenticated browser flows | NOT RUN | No browser credentials entered. Authorization/workflow coverage is through tests. |

| Public responsive browser QA | PASS (partial) | Home, directory, and verified profile at 360px, 768px, and 1366px had no horizontal overflow (checkpoint 07). Updated doctor profile at 390px and 1280px also has no overflow; profile console has no warnings/errors. Zero image elements missing alt on the three public pages during viewport checks. |
| Authenticated mobile nav browser QA | NOT RUN | Navigation markup is role-specific and covered by tests; authenticated browser sessions were not used. |
| Keyboard and broader accessibility QA | NOT RUN | Not performed. |

| AWS deployment | NOT RUN | No deployment attempted. |



## Environment notes



Development requirements were installed in workspace-local `.venv` from cached wheels. Pytest's user-wide temporary directory is blocked by sandbox permissions, so tests must use a workspace `--basetemp`. The release archive excludes `.venv`, database files, pytest temp files, caches, and bytecode.

## Checkpoint 09 — 2026-10-02

| Check | Result | Evidence |
|---|---|---|
| Doctor schedule summary and request scoping | PASS | Regression test verifies today's, pending, upcoming, and completed counts; only own or unassigned upcoming pending requests are included. |
| Django system check | PASS | `manage.py check`: no issues (0 silenced). |
| Migration consistency | PASS | `manage.py makemigrations --check --dry-run`: no changes detected. |
| Full pytest suite | PASS | `pytest -q --reuse-db --basetemp=.pytest-tmp35`: **91 passed in 87.98s**. |
| Python source compilation | PASS | `compileall` completed for project apps and config. |
| JavaScript syntax | PASS | `node --check static/js/visit-slots.js`. |
| CSS brace balance | PASS | 581 opening and 581 closing braces. |
| Authenticated doctor browser journey | NOT RUN | Authenticated UI sessions were not used; workflow rendering and access are covered by automated tests. |

## Checkpoint 10 — 2026-10-02

| Check | Result | Evidence |
|---|---|---|
| Enquiry retention dry run | PASS | Test confirms expired records are reported and retained without `--execute`. |
| Enquiry retention deletion | PASS | Test confirms `--execute` deletes an expired enquiry and preserves a recent one. |
| Focused contact suite | PASS | `pytest tests/test_contact.py -q --reuse-db --basetemp=.pytest-tmp36`: **11 passed in 2.98s**. |
| Django system check | PASS | `manage.py check`: no issues (0 silenced). |
| Migration consistency | PASS | `manage.py makemigrations --check --dry-run`: no changes detected. |
| Full pytest suite | PASS | `pytest -q --reuse-db --basetemp=.pytest-tmp37`: **93 passed in 97.27s**. |
| Production retention operation | NOT RUN | No scheduled job configured; organization approval of the 180-day default and periodic execution is still required. |

## Checkpoint 11 — 2026-10-02

| Check | Result | Evidence |
|---|---|---|
| Production-mode static collection | PASS | With `DEBUG=false`, a temporary secret, and workspace `STATIC_ROOT`, `collectstatic` copied 130 assets; `css/style.css` and `js/visit-slots.js` were present. |
| Production proxy/security settings | PASS | With temporary environment values, Django loaded HTTPS redirect, trusted `X-Forwarded-Proto`, and secure session/CSRF cookies. No secret was written to project files. |
| `manage.py check --deploy` | PASS WITH ADVISORY | One warning remains: `security.W021` for opt-in HSTS preload. It is intentionally not enabled before domain-wide HTTPS and organization review. |
| Standard Django system check | PASS | `manage.py check`: no issues (0 silenced). |
| Migration consistency | PASS | `manage.py makemigrations --check --dry-run`: no changes detected. |
| Full pytest suite | PASS | `pytest -q --reuse-db --basetemp=.pytest-tmp40`: **93 passed in 98.09s**. |
| Docker image / Compose runtime | NOT RUN | Docker and Docker Compose binaries are unavailable in this environment. |
| GitHub Actions workflow | NOT RUN | Workflow file updated but not run on GitHub. |
| AWS deployment / HTTPS staging | NOT RUN | No cloud environment or credentials were supplied. |
