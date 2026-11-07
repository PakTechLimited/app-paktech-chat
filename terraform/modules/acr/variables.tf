variable "name" {
  type        = string
  description = "Globally unique, 5-50 lowercase alphanumerics."
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "sku" {
  type    = string
  default = "Basic"
}

variable "tags" {
  type    = map(string)
  default = {}
}
