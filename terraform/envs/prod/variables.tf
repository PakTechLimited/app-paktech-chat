variable "subscription_id" {
  type    = string
  default = "f99345eb-69a8-455e-82d7-25706b78ccaf"
}

variable "location" {
  type    = string
  default = "eastus"
}

variable "project" {
  type    = string
  default = "paktech"
}

variable "environment" {
  type    = string
  default = "prod"
}

variable "admin_object_id" {
  type        = string
  description = "Your Azure AD object ID: az ad signed-in-user show --query id -o tsv"
}

variable "domain_name" {
  type    = string
  default = "paktechlimited.chat"
}

variable "system_vm_size" {
  type    = string
  default = "Standard_D2s_v3"
}

variable "apps_vm_size" {
  type    = string
  default = "Standard_D2s_v3"
}

variable "apps_min_count" {
  type    = number
  default = 1
}

variable "apps_max_count" {
  type    = number
  default = 3
}

variable "monitoring_vm_size" {
  type    = string
  default = "Standard_D2s_v3"
}

variable "kubernetes_version" {
  type    = string
  default = null
}

variable "github_repository" {
  type    = string
  default = "PakTechLimited/app-paktech-chat"
}

variable "github_branches" {
  type    = list(string)
  default = ["develop", "staging", "main"]
}

variable "app_service_accounts" {
  type = list(object({
    namespace = string
    name      = string
  }))
  default = [
    { namespace = "paktech-chat-dev", name = "paktech-chat" },
    { namespace = "paktech-chat-staging", name = "paktech-chat" },
    { namespace = "paktech-chat-prod", name = "paktech-chat" },
  ]
  description = "Kubernetes service accounts that may assume the application identity."
}

variable "admin_ip" {
  type        = string
  description = "Your current public IP, without /32: curl -s https://api.ipify.org"

  validation {
    condition     = can(regex("^[0-9]{1,3}(\\.[0-9]{1,3}){3}$", var.admin_ip))
    error_message = "admin_ip must be a single IPv4 address such as 203.0.113.10 (no /32)."
  }
}

variable "cluster_outbound_ip" {
  type        = string
  description = "Outbound public IP of the AKS load balancer: see terraform.tfvars.example for the commands."

  validation {
    condition     = can(regex("^[0-9]{1,3}(\\.[0-9]{1,3}){3}$", var.cluster_outbound_ip))
    error_message = "cluster_outbound_ip must be a single IPv4 address (no /32)."
  }
}
