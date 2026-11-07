output "resource_group" {
  value = azurerm_resource_group.main.name
}

output "aks_name" {
  value = module.aks.name
}

output "get_credentials_command" {
  value = "az aks get-credentials --resource-group ${azurerm_resource_group.main.name} --name ${module.aks.name} --overwrite-existing"
}

output "acr_login_server" {
  value = module.acr.login_server
}

output "key_vault_uri" {
  value = module.keyvault.vault_uri
}

output "ingress_public_ip" {
  value = azurerm_public_ip.ingress.ip_address
}

output "dns_name_servers" {
  value       = module.dns.name_servers
  description = "Set these as Custom DNS for paktechlimited.chat at Namecheap."
}

output "app_identity_client_id" {
  value       = module.workload_identity.client_id
  description = "Annotation azure.workload.identity/client-id on the app service account."
}

output "github_oidc_client_id" {
  value       = module.github_oidc.client_id
  description = "Repository variable AZURE_CLIENT_ID for GitHub Actions."
}

output "tenant_id" {
  value = data.azurerm_client_config.current.tenant_id
}

output "subscription_id" {
  value = var.subscription_id
}
