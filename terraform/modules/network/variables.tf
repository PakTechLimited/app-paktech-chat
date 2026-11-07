variable "name" {
  type        = string
  description = "Virtual network name."
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "address_space" {
  type    = string
  default = "10.10.0.0/16"
}

variable "aks_subnet_prefix" {
  type    = string
  default = "10.10.1.0/24"
}

variable "tags" {
  type    = map(string)
  default = {}
}
