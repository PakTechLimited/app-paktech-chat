variable "name" {
  type = string
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "resource_group_id" {
  type = string
}

variable "subnet_id" {
  type = string
}

variable "acr_id" {
  type = string
}

variable "kubernetes_version" {
  type        = string
  default     = null
  description = "Null uses the AKS default for the region."
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

variable "tags" {
  type    = map(string)
  default = {}
}

variable "api_authorized_ip_ranges" {
  type        = list(string)
  description = "CIDR ranges allowed to call the Kubernetes API server: admin IP(s) and the cluster outbound IP."

  validation {
    condition     = length(var.api_authorized_ip_ranges) > 0 && alltrue([for c in var.api_authorized_ip_ranges : can(cidrhost(c, 0))])
    error_message = "Provide at least one valid CIDR range, for example 203.0.113.10/32."
  }
}
