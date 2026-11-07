data "azurerm_client_config" "current" {}

locals {
  suffix = "${var.project}-${var.environment}"
  tags = {
    project     = "paktech-chat"
    environment = var.environment
    managed_by  = "terraform"
  }
  github_subjects = concat(
    [for b in var.github_branches : "repo:${var.github_repository}:ref:refs/heads/${b}"],
    ["repo:${var.github_repository}:pull_request", "repo:${var.github_repository}:environment:${var.environment}"],
  )
}

resource "azurerm_resource_group" "main" {
  name     = "rg-${local.suffix}"
  location = var.location
  tags     = local.tags
}

module "network" {
  source              = "../../modules/network"
  name                = "vnet-${local.suffix}"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.tags
}

module "acr" {
  source              = "../../modules/acr"
  name                = "${var.project}acr"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.tags
}

module "keyvault" {
  source              = "../../modules/keyvault"
  name                = "kv-${local.suffix}"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  admin_object_id     = var.admin_object_id
  tags                = local.tags
}

# Static public IP for the ingress controller, kept outside the cluster so DNS survives cluster rebuilds.
resource "azurerm_public_ip" "ingress" {
  name                = "pip-ingress-${local.suffix}"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = local.tags
}

module "aks" {
  source              = "../../modules/aks"
  name                = "aks-${local.suffix}"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  resource_group_id   = azurerm_resource_group.main.id
  subnet_id           = module.network.aks_subnet_id
  acr_id              = module.acr.id
  kubernetes_version  = var.kubernetes_version
  system_vm_size      = var.system_vm_size
  apps_vm_size        = var.apps_vm_size
  apps_min_count      = var.apps_min_count
  apps_max_count      = var.apps_max_count
  monitoring_vm_size  = var.monitoring_vm_size
  tags                = local.tags
}

module "workload_identity" {
  source              = "../../modules/workload-identity"
  name                = "id-paktech-chat-${var.environment}"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  oidc_issuer_url     = module.aks.oidc_issuer_url
  key_vault_id        = module.keyvault.id
  service_accounts    = var.app_service_accounts
  tags                = local.tags
}

module "dns" {
  source              = "../../modules/dns"
  domain_name         = var.domain_name
  resource_group_name = azurerm_resource_group.main.name
  ingress_ip          = azurerm_public_ip.ingress.ip_address
  tags                = local.tags
}

module "github_oidc" {
  source       = "../../modules/github-oidc"
  display_name = "sp-github-paktech-cicd"
  subjects     = local.github_subjects
  acr_id       = module.acr.id
  aks_id       = module.aks.id
}
