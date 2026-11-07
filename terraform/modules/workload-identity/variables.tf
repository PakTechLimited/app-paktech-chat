variable "name" {
  type = string
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "oidc_issuer_url" {
  type = string
}

variable "key_vault_id" {
  type = string
}

variable "service_accounts" {
  type = list(object({
    namespace = string
    name      = string
  }))
  description = "Kubernetes service accounts allowed to use this identity."
}

variable "tags" {
  type    = map(string)
  default = {}
}
