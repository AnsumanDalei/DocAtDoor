# Docker and Compose

The root `docker/` files are intentionally for local learning. The Docker image installs `mysqlclient`, runs migrations, and starts Django's development server. Compose provides MySQL 8.4 and Django on localhost port 8000. Set placeholders in a private `.env` before starting; do not commit it. Protected medical uploads and MySQL data use named volumes.

```powershell
docker compose --env-file .env -f docker/docker-compose.yml up --build
```

The web process is `runserver`, not a production server. The Compose file is not safe to expose publicly. Build/run status: not verified in the current environment because Docker is unavailable. Kubernetes learning setup is documented separately in `KUBERNETES.md` and uses the same development image.
