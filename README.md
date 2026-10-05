# DocAtDoor



DocAtDoor is a Django home healthcare application. Patients can explore verified doctor profiles, request a doctor home visit, track appointment updates, and access their private reports and prescriptions. Doctors manage appointment requests and availability; administrators manage accounts and doctor verification in Django Admin.



The project remains a single Django application using Django templates and a shared Django REST API. MySQL is the configured application database. Shared Flutter client source in `flutter_app/` consumes that API for sign-in, patient registration/email verification, doctor discovery, slot-based home-visit booking, appointment actions, patient reports/prescriptions/notifications, and consultation/review flows. Native Android/Windows platform builds have not been generated or verified on this machine. The current self-service booking workflow is for doctor home visits. Nursing, physiotherapy, diagnostics, elder care, and post-hospital recovery are enquiry links only; their dedicated booking workflows are not implemented.



## Included workflows



- Patient account creation with a continuous 6-digit email OTP flow, password reset, profile and settings pages, remembered sessions, optional Google sign-in/linking, and explicit account selection when two accounts share an email.

- Public doctor directory with name/specialty search, service-area, minimum-experience, and maximum-fee filters, plus verified profiles with optional doctor photo and introduction, listed qualification, experience, service area, fee, bookable service, weekly hours, and real review data where available.

- Patient home-visit requests use a guided date/time, details, and review flow; capture street address, city, and contact number (locality is optional); and support cancellation and availability-based rescheduling. Visits are 60 minutes, offered hourly within the doctor's weekly hours; occupied times are excluded and the server validates each request.

- Doctor workspace summaries for today, response-needed requests, upcoming confirmed visits, and completed history; accept/reject/complete actions, weekly availability entries, consultation summaries and diagnosis for completed visits, and protected prescription uploads.

- Private medical report and prescription uploads, a patient prescription library, and authorized downloads.

- Patient dashboard previews for the next visit, reports, prescriptions, and notifications; patient and doctor notifications, reviews, admin management, and a health endpoint.

- Responsive template UI, local demo-data command, and deployment configuration examples.

- `/api/` REST endpoints for patient registration and email OTP verification, token login/logout, patient/doctor profile, verified doctor discovery and availability management, patient/doctor appointments, booking, cancellation, rescheduling, doctor appointment actions, consultations, protected medical records, prescriptions, notifications, reviews, service enquiries, and password management. See `API.md` for the endpoint contract and limits.



Email is suppressed by default so verification codes and personal data are not written to terminal logs. Configure SMTP environment variables and set `MAIL_ENABLED=true` to deliver verification and reset emails. Local self-registration requires email delivery; seeded demo accounts can be used without it. Medical data and real credentials must not be placed in demo data or committed to the repository.



Google sign-in is optional. Configure `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, and the registered `GOOGLE_OAUTH_REDIRECT_URI` in the local environment to enable it. The redirect URI must point to `/accounts/google/callback/`. Existing password accounts are not silently linked; sign in and explicitly connect Google from Settings. The current local environment has no Google OAuth client configured, so live provider sign-in has not been exercised.

## Local setup (MySQL)

Requires Python 3.10 or newer and a basic MySQL Server installation. Local MySQL 8.0.46 has been verified; the application does not require a specific MySQL minor release. Install and start MySQL, then create a database and development user. The app defaults to MySQL; it does not silently fall back to SQLite.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
# Edit .env; replace all placeholder passwords/secrets.
mysql -u root -p
# In the MySQL prompt:
# CREATE DATABASE docatdoor CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
# CREATE USER 'docatdoor'@'localhost' IDENTIFIED BY 'your-local-password';
# GRANT ALL PRIVILEGES ON docatdoor.* TO 'docatdoor'@'localhost';
# GRANT CREATE, DROP ON *.* TO 'docatdoor'@'localhost';
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver
```

`runserver` is for development only. The app uses MySQL and `mysqlclient`; Linux builds need MySQL client development headers (see `DEPLOYMENT.md`).

## Docker Compose development setup

Copy `.env.example` to `.env`, replace placeholder secrets, then run `docker compose --env-file .env -f docker/docker-compose.yml up --build`. Compose starts MySQL 8.4 and Django's development server on port `8000`. This is a local learning setup, not a production deployment or production app server. Do not expose it publicly.

## Migrating existing SQLite data to MySQL

Back up the source database and both upload directories first. For an existing SQLite installation, temporarily select it while exporting a fixture, then switch back to MySQL and load the fixture after migrations:

```powershell
$env:DB_ENGINE = "django.db.backends.sqlite3"
$env:DB_NAME = "db.sqlite3"
python manage.py dumpdata accounts appointments medical_records notifications reviews core auth.Group --natural-foreign --natural-primary --indent 2 --output sqlite-export.json
Remove-Item Env:DB_ENGINE
Remove-Item Env:DB_NAME
python manage.py migrate
python manage.py loaddata sqlite-export.json
```

Keep the export outside source control, transfer `media/` and `protected_media/` to private storage, compare record counts and relationships, then securely remove temporary exports when authorized. This procedure is documented but has not been run against the included local database. MySQL test runs require permission to create/drop a test database.

## REST API and Flutter client

API base path: `/api/`. Email/password token auth is available for Flutter clients, with session auth also supported for same-origin use. Registration can create patient accounts only. Appointment and profile access is enforced server-side. See `API.md` for endpoints and permissions.

Install Flutter 3.24 or newer on a development machine. From this folder, generate the standard native project shells once, then fetch packages and run the shared app:

```powershell
cd flutter_app
flutter create --platforms=android,windows .
flutter pub get
# Android emulator talking to Django on the host:
flutter run -d <android-device> --dart-define=API_BASE_URL=http://10.0.2.2:8000/api
# Windows desktop talking to Django on the same computer:
flutter run -d windows --dart-define=API_BASE_URL=http://127.0.0.1:8000/api
```

The app saves its API token using platform secure storage. Android emulator networking uses `10.0.2.2` for the host; Windows uses loopback. For a physical device, use the development computer's reachable LAN address and configure Django `ALLOWED_HOSTS` accordingly. The source is not yet validated by `flutter analyze`, widget tests, or Android/Windows builds because Flutter SDK/platform tooling is unavailable in the current environment. File picking uses `file_picker`; private downloads are written to the app documents directory with `path_provider`. Calendar and broader doctor workspace screens remain incomplete.

## Checks and tests



```powershell

python manage.py check

python manage.py makemigrations --check --dry-run

pytest tests/ -v

```

Checkpoint 12's latest full suite passed **113 tests in 134.08s** with a disposable SQLite test override. This is regression evidence only; MySQL 8.4 migrations and tests remain unverified. See `TEST_REPORT.md` and `CHECKPOINT_12_STATUS.md` for the current matrix and environment limits.



`python manage.py check --deploy` reports production security settings that require real deployment configuration; it is not a deployment test.



## Configuration and deployment

Copy `.env.example` to `.env`. Set a unique `SECRET_KEY`, correct `ALLOWED_HOSTS`, and MySQL credentials. Never commit populated environment files, database exports, or uploaded records. `.github/workflows/ci.yml` configures a MySQL service for the automated test job; the workflow has not been run in GitHub for this checkpoint.

See `FLUTTER.md`, `DOCKER.md`, `GITHUB_ACTIONS.md`, `KUBERNETES.md`, `TERRAFORM.md`, `ANSIBLE.md`, and `DEPLOYMENT.md` for setup and validation status. The Docker/Kubernetes image uses Django's development server and is not production-ready. AWS has not been deployed. No Nginx or Gunicorn is part of the intended runtime.
