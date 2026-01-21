provider "aws" {
  region = "eu-central-1" # Frankfurt (Good for Ukraine)
}

# 1. Security Group (The Firewall)
resource "aws_security_group" "drone_sg" {
  name        = "drone-command-center-sg"
  description = "Allow SSH and Streamlit"

  # SSH Access (Change 0.0.0.0/0 to your IP for safety if you want)
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Streamlit Dashboard Access
  ingress {
    from_port   = 8501
    to_port     = 8501
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Outbound Internet Access (for downloading Docker/Pip packages)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# 2. Key Pair (To login)
# We assume you have a public key at ~/.ssh/id_rsa.pub
# If not, run: ssh-keygen -t rsa -b 4096
resource "aws_key_pair" "deployer" {
  key_name   = "drone-key"
  public_key = file("~/.ssh/id_rsa.pub") 
}

# 3. The Server (EC2)
resource "aws_instance" "app_server" {
  ami           = "ami-0faab6bdbac9486fb" # Ubuntu 22.04 in eu-central-1
  instance_type = "c7i-flex.large"             # 4GB RAM (Necessary for Redpanda)
  key_name      = aws_key_pair.deployer.key_name
  vpc_security_group_ids = [aws_security_group.drone_sg.id]

  # Storage (20GB is safer for DB logs)
  root_block_device {
    volume_size = 20
  }

  # 4. The "Magic" Setup Script
  # This runs ONCE when the server starts.
  user_data = <<-EOF
              #!/bin/bash
              apt-get update
              apt-get install -y docker.io docker-compose git
              systemctl start docker
              systemctl enable docker
              usermod -aG docker ubuntu
              EOF

  tags = {
    Name = "Drone-Command-Center"
  }
}

# Output the IP so you know where to connect
output "public_ip" {
  value = aws_instance.app_server.public_ip
}