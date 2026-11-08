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

variable "env_subdomains" {
  description = "Host names (relative to the zone) that point at the ingress IP, one per non-prod environment."
  type        = list(string)
  default     = ["dev", "staging"]
}
