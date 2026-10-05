# Basic Kubernetes learning manifests

`k8s/mysql.yaml` and `k8s/web.yaml` define a single-replica MySQL StatefulSet, persistent claims, and a Django web Deployment behind internal ClusterIP services. No Ingress or external load balancer is defined. The manifests are for local learning only: the app image runs Django's development server. Do not use it for production or expose it publicly.

The namespace expects a pre-created `docatdoor-secrets` Secret with keys `mysql-root-password`, `db-password`, and `secret-key`. Keep that Secret outside source control; use your cluster's approved secret-management process. Never place real values in these YAML files.

Build the development image using `docker build -t docatdoor:dev -f docker/Dockerfile .`, make it available to the chosen local cluster, then apply the secret and manifests. Start with `kubectl apply -f k8s/mysql.yaml`, wait for MySQL, then apply `kubectl apply -f k8s/web.yaml`. Use `kubectl port-forward service/docatdoor-web 8000:8000` to reach it locally. Remove the test namespace/data only after reviewing Kubernetes PVC retention behavior.

No kubectl or cluster was available during Checkpoint 12; YAML parsing, scheduling, persistence, probes, and app startup are unverified. PVCs are not backups. Medical uploads still require private access controls, encrypted storage, tested backup/restore, retention policy, and a suitable object-storage strategy before real data is used. The Django development image/automatic migration command is not production ready.
