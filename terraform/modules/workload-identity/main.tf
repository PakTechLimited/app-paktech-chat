# One user-assigned identity for the application. Each Kubernetes service account listed in
# var.service_accounts is federated to it, so pods using that account can request Azure AD tokens.
resource "azurerm_user_assigned_identity" "this" {
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

resource "azurerm_federated_identity_credential" "sa" {
  for_each = { for sa in var.service_accounts : "${sa.namespace}-${sa.name}" => sa }

  name                      = "fic-${each.key}"
  user_assigned_identity_id = azurerm_user_assigned_identity.this.id
  audience                  = ["api://AzureADTokenExchange"]
  issuer                    = var.oidc_issuer_url
  subject                   = "system:serviceaccount:${each.value.namespace}:${each.value.name}"
}

# Read-only access to secrets: the app can fetch them, never change or list the vault.
resource "azurerm_role_assignment" "kv_secrets_user" {
  scope                = var.key_vault_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.this.principal_id
}
