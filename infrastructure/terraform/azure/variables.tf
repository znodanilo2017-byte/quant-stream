variable "resource_group_name" {
  description = "Azure resource group for the QuantStream VM."
  type        = string
  default     = "quant-stream-rg"
}

variable "location" {
  description = "Azure region for deployment."
  type        = string
  default     = "Norway East"
}

variable "vm_size" {
  description = "VM size for the Docker Compose host."
  type        = string
  default     = "Standard_D2as_v4"
}

variable "admin_username" {
  description = "Admin username for the Linux VM."
  type        = string
  default     = "azureuser"
}

variable "ssh_public_key_path" {
  description = "Path to the SSH public key used for VM access."
  type        = string
  default     = "~/.ssh/id_rsa_azure.pub"
}

variable "allowed_cidr" {
  description = "CIDR block allowed to access SSH and Grafana. Replace the demo-friendly default before exposing the VM publicly."
  type        = string
  default     = "0.0.0.0/0"
}
