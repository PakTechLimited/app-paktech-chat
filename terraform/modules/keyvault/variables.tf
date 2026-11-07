variable "name" {
  type        = string
  description = "Globally unique, 3-24 characters."
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "tenant_id" {
  type = string
}

variable "admin_object_id" {
  type        = string
  description = "Object ID of the user or group that administers secrets."
}

variable "purge_protection_enabled" {
  type    = bool
  default = false
}

variable "tags" {
  type    = map(string)
  default = {}
}
