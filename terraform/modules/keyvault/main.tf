# Authorization uses Azure RBAC, not legacy access policies, so every grant is a visible role assignment.
# Purge protection is OFF on purpose: this lab is torn down after each milestone, and a purge-protected
# vault keeps its name reserved for the whole retention period. Turn it on for a real production vault.
resource "azurerm_key_vault" "this" {
  name                          = var.name
  location                      = var.location
  resource_group_name           = var.resource_group_name
  tenant_id                     = var.tenant_id
  sku_name                      = "standard"
  rbac_authorization_enabled    = true
  soft_delete_retention_days    = 7
  purge_protection_enabled      = var.purge_protection_enabled
  public_network_access_enabled = true
  tags                          = var.tags
}

# Lets the person running Terraform create and read secrets.
resource "azurerm_role_assignment" "admin" {
  scope                = azurerm_key_vault.this.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = var.admin_object_id
}
