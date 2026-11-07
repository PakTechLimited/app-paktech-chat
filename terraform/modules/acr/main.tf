# Basic SKU is enough for this project (about $5/month) and supports managed-identity pulls.
# Admin user stays disabled: nothing authenticates with a shared password.
resource "azurerm_container_registry" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = var.sku
  admin_enabled       = false
  tags                = var.tags
}
