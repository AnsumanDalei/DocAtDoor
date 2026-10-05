output "server_public_ip" {
  description = "Preparation host IP for restricted SSH; no application port is open."
  value       = aws_instance.docatdoor_server.public_ip
}

output "server_id" {
  description = "EC2 instance ID"
  value       = aws_instance.docatdoor_server.id
}

output "security_group_id" {
  description = "Security group ID attached to the instance"
  value       = aws_security_group.docatdoor_sg.id
}
