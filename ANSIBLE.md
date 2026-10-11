# Ansible preparation

`ansible/playbook.yml` installs the Ubuntu `docker.io` package, enables Docker, and creates a restricted root-owned working directory. It intentionally does not copy secrets, pull an app image, map a port, or start the Django development server. This is preparation only; it is not an application deployment.

Edit `ansible/inventory.ini` to use a host and SSH key controlled by the operator. Keep private key files out of the project. `ansible-playbook --syntax-check` and any host run remain unverified because Ansible was unavailable. The playbook requires SSH access to a restricted host; the Terraform example rejects broad SSH source ranges.
