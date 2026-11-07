output "client_id" {
  value       = azurerm_user_assigned_identity.this.client_id
  description = "Goes into the service account annotation azure.workload.identity/client-id."
}

output "principal_id" {
  value = azurerm_user_assigned_identity.this.principal_id
}
