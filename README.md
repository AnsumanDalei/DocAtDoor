# DocAtDoor

DocAtDoor is a Django-based home healthcare web application that connects patients with doctors for home visits. Patients can explore approved doctor profiles, request appointments, track visit updates, and access their private medical reports and prescriptions.

## Key Features

### Patient Accounts
- Patient registration with six-digit email OTP verification.
- Login, password reset, profile management, and account settings.
- Optional Google sign-in when configured.
- Patient dashboard for appointments, reports, prescriptions, and notifications.

### Doctor Management
- Patient and doctor registration through shared registration pages.
- Doctor applications remain pending until approved by an administrator.
- Approved doctors can manage appointment requests and weekly availability.
- Doctor dashboards display upcoming visits, pending requests, and completed appointments.

### Doctor Discovery and Appointments
- Public directory of approved doctors.
- Search and filtering by name, specialty, experience, service area, and consultation fee.
- Doctor profiles with qualifications, experience, availability, and reviews.
- Guided home-visit booking, cancellation, and rescheduling.
- Server-side validation of appointment availability.

### Medical Records and Consultations
- Consultation summaries and diagnoses for completed visits.
- Protected prescription uploads and authorized downloads.
- Private patient medical reports and prescription library.
- Notifications, reviews, and administrative management.

### Additional Features
- Responsive Django template-based user interface.
- Django REST API under `/api/`.
- Demo-data seeding command.
- Configurable email delivery and application settings.
- Docker, GitHub Actions, Ansible, Kubernetes, and Terraform configuration documentation.

## Technology Stack

- **Backend:** Python, Django
- **Frontend:** Django Templates, HTML, CSS, JavaScript
- **Database:** MySQL
- **API:** Django REST API
- **Testing:** pytest and Django checks
- **Deployment and DevOps configuration:** Docker, GitHub Actions, Ansible, Kubernetes, Terraform, and AWS EC2 deployment documentation

## Requirements

- Python 3.10 or newer
- MySQL Server
- Git
- Python dependencies listed in `requirements-dev.txt`

## Local Setup

Open a terminal in the project directory.

Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements-dev.txt
```

Create the environment file:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and configure the required secret key, database credentials, allowed hosts, and any email settings. Never commit real credentials.

Create the MySQL database and application user according to your local MySQL configuration. Then run:

```powershell
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver
```

Open `http://127.0.0.1:8000/` in your browser.

The Django development server is intended for local development, not production hosting.

## REST API

The API is available under `/api/`.

It supports the application's account, profile, doctor discovery, availability, appointment, consultation, medical record, prescription, notification, review, and service-enquiry workflows.

Refer to `API.md` for endpoint details, authentication, permissions, and limits.

## Testing and Validation

Run Django's system checks:

```powershell
python manage.py check
```

Check for missing migrations:

```powershell
python manage.py makemigrations --check --dry-run
```

Run the test suite:

```powershell
pytest tests/ -v
```

Review `TEST_REPORT.md` and `CHECKPOINT_12_STATUS.md` for the recorded test results and outstanding verification work.

## Configuration and Deployment

Copy `.env.example` to `.env` and configure the environment before running the application.

The repository contains deployment and infrastructure documentation:

- `DEPLOYMENT.md` — deployment configuration and requirements
- `DOCKER.md` — Docker setup
- `GITHUB_ACTIONS.md` — CI workflow information
- `ANSIBLE.md` — Ansible configuration
- `KUBERNETES.md` — Kubernetes configuration
- `TERRAFORM.md` — Terraform configuration

These files describe configuration and deployment approaches; their presence does not by itself confirm that a production deployment is operational. Verify the relevant setup before deploying.

## Security Notes

- Never commit `.env` files containing real secrets.
- Use a unique production `SECRET_KEY` and strong database credentials.
- Do not commit database exports, real patient records, or private uploads.
- Protect medical records and prescriptions through server-side authorization.
- Configure HTTPS and production security settings before public deployment.

## Project Status

DocAtDoor is a Django web application with a shared Django REST API and MySQL support. Consult the test report and deployment documentation for the current verification status.

## License

No license has been specified for this repository.
