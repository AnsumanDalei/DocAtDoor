# GitHub Actions

`.github/workflows/ci.yml` configures a pull-request/push workflow with MySQL 8.4. It installs Python dependencies and Linux MySQL client headers, checks Django and model migrations, applies migrations, collects static files, compiles Python modules, runs tests, and builds the development Docker image.

The workflow is configured but has not run in GitHub from this environment. Do not describe CI as passing until a GitHub run completes successfully. The workflow's MySQL root password is a test-only service credential; never reuse it outside the ephemeral CI service. The Docker stage builds only a development image.
