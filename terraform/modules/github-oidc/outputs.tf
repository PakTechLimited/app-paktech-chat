output "client_id" {
  value       = azuread_application.ci.client_id
  description = "Store as the AZURE_CLIENT_ID repository variable (not a secret)."
}
