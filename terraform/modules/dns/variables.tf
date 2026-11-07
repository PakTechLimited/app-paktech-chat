variable "domain_name" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "ingress_ip" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
