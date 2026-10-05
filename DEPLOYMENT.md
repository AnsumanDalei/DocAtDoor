# Deployment and development environments

DocAtDoor is a Django application with Django templates and a shared Django REST Framework API. MySQL is the configured application database. This project has not been deployed to AWS.

## Local native setup

Install Python 3.10+ and MySQL 8.4 LTS. Copy `.env.example` to `.env`; set unique local `SECRET_KEY`, database username/password, database name, host, and port. Create the MySQL database with `utf8mb4`, grant the application user access, and grant the test user/database permissions needed for test database creation and deletion. Install `requirements-dev.txt`, then run `python manage.py migrate`, `python manage.py seed_demo_data`, and `python manage.py runserver`.

The project uses `mysqlclient`. On Debian/Ubuntu, building it from source may require `python3-dev`, `default-libmysqlclient-dev`, `build-essential`, and `pkg-config`. The pinned package provides a CPython 3.12 Windows x86-64 wheel. MySQL must still be installed/running separately.

## Docker Compose learning setup

`docker/` provides a local MySQL 8.4 service and a Django development server. Copy `.env.example` to `.env`, replace placeholder credentials, then run:

```powershell
docker compose --env-file .env -f docker/docker-compose.yml up --build
```

The website/API is available on port 8000. Django `runserver` is a development server. This Compose setup is not suitable for public or production use. Do not expose it to the internet. Docker and Compose were unavailable during the last verification, so this configuration has not been built or run here.

## SQLite data migration procedure

A previous local development version used SQLite. Preserve it by making a private backup of the database and both `media/` and `protected_media/` directories. Temporarily point `DB_ENGINE` and `DB_NAME` to that source for a `dumpdata` export, then configure MySQL, apply migrations, and `loaddata` the fixture. Copy the referenced files to the matching private storage paths, compare table counts and relationships, test authenticated downloads, and only then retire the old copy. Keep the export outside source control and delete it only after a verified backup and approved retention decision. This procedure has not been run on the included database; the repository archive excludes local database and uploaded records.

## Current production limitations

- No production application server is configured. The supplied Dockerfile intentionally runs Django's development server for local learning; it must not be treated as production-ready.
- No Nginx or Gunicorn is part of the target architecture.
- The Docker image/Compose runtime, GitHub Actions workflow, MySQL migrations, and AWS resources have not been runtime-verified in this environment.
- Terraform now prepares an EC2 host with SSH restricted to a caller-supplied IPv4 `/32`, and opens no web port. Ansible only installs Docker and prepares a directory; it does not deploy the app. Both configurations are unvalidated because their tools are unavailable.
- A production operator still needs to select an application server compatible with the project constraints, terminate HTTPS, restrict origin access, configure secure cookies/CSRF, provision MySQL backups, keep medical uploads private, set secrets externally, configure log retention/monitoring, and verify recovery procedures.
- AWS RDS/S3 and any AWS deployment are not completed or claimed. Basic Kubernetes manifests exist but are unvalidated; see `KUBERNETES.md`. No Ansible app deployment is provided.

`SECURE_SSL_REDIRECT=true` should only be used when HTTPS is available end to end or a trusted TLS-terminating load balancer sets `X-Forwarded-Proto`. `SECURE_PROXY_SSL_HEADER_ENABLED=true` must only be enabled when traffic cannot bypass that trusted proxy. HSTS preload is opt-in and needs domain-wide HTTPS review.
