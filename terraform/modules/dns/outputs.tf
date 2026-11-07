output "name_servers" {
  value       = azurerm_dns_zone.this.name_servers
  description = "Enter these as Custom DNS at your registrar."
}
