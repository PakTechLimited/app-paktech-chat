variable "display_name" {
  type = string
}

variable "subjects" {
  type        = list(string)
  description = "Allowed GitHub token subjects, e.g. repo:ORG/REPO:ref:refs/heads/main."
}

variable "acr_id" {
  type = string
}

variable "aks_id" {
  type = string
}
