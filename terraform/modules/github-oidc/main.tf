# GitHub Actions authenticates with a short-lived OIDC token, so the pipeline stores no Azure secret.
# Azure trusts tokens only when their "sub" claim matches one of the federated credentials below.
resource "azuread_application" "ci" {
  display_name = var.display_name
}

resource "azuread_service_principal" "ci" {
  client_id = azuread_application.ci.client_id
}

resource "azuread_application_federated_identity_credential" "subject" {
  for_each = { for s in var.subjects : replace(replace(s, ":", "-"), "/", "-") => s }

  application_id = azuread_application.ci.id
  display_name   = each.key
  description    = "GitHub Actions: ${each.value}"
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = each.value
}

# Least privilege for CI: push images, and fetch cluster credentials. Nothing else.
resource "azurerm_role_assignment" "acr_push" {
  scope                = var.acr_id
  role_definition_name = "AcrPush"
  principal_id         = azuread_service_principal.ci.object_id
}

resource "azurerm_role_assignment" "aks_cluster_user" {
  scope                = var.aks_id
  role_definition_name = "Azure Kubernetes Service Cluster User Role"
  principal_id         = azuread_service_principal.ci.object_id
}

# az acr build (ACR Tasks) needs more than push/pull: it must read the registry
# and schedule a cloud build run. Scoped to this one registry only.
resource "azurerm_role_assignment" "acr_reader" {
  scope                = var.acr_id
  role_definition_name = "Reader"
  principal_id         = azuread_service_principal.ci.object_id
}

resource "azurerm_role_assignment" "acr_tasks" {
  scope                = var.acr_id
  role_definition_name = "Container Registry Tasks Contributor"
  principal_id         = azuread_service_principal.ci.object_id
}
