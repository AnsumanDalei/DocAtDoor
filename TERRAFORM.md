# Terraform preparation

`terraform/` contains a small AWS preparation-host example. It creates one EC2 host and a security group that permits SSH only from a caller-supplied IPv4 `/32`; it opens no application port. The AMI ID and existing key-pair name must be supplied for the chosen region. Do not apply without reviewing cost, region, account, network, and SSH source values.

This does not create MySQL/RDS, S3, TLS, production application serving, or a DocAtDoor deployment. `terraform init`, `validate`, `plan`, and `apply` have not been run because Terraform and AWS credentials were unavailable. No resources are claimed as deployed.
