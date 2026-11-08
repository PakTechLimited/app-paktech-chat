resource "azurerm_dns_zone" "this" {
  name                = var.domain_name
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

# Apex record points at the ingress public IP.
resource "azurerm_dns_a_record" "apex" {
  name                = "@"
  zone_name           = azurerm_dns_zone.this.name
  resource_group_name = var.resource_group_name
  ttl                 = 300
  records             = [var.ingress_ip]
}

resource "azurerm_dns_cname_record" "www" {
  name                = "www"
  zone_name           = azurerm_dns_zone.this.name
  resource_group_name = var.resource_group_name
  ttl                 = 300
  record              = var.domain_name
}

# One A record per extra environment hostname (dev, staging). All hostnames share the one ingress IP;
# the Gateway routes by Host header.
resource "azurerm_dns_a_record" "env" {
  for_each            = toset(var.env_subdomains)
  name                = each.value
  zone_name           = azurerm_dns_zone.this.name
  resource_group_name = var.resource_group_name
  ttl                 = 300
  records             = [var.ingress_ip]
}
