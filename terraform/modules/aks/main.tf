resource "azurerm_kubernetes_cluster" "this" {
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name
  dns_prefix          = var.name
  kubernetes_version  = var.kubernetes_version
  sku_tier            = "Free"

  # Workload Identity: pods get Azure AD tokens through a federated service account,
  # so no client secrets are stored anywhere in the cluster.
  oidc_issuer_enabled       = true
  workload_identity_enabled = true

  default_node_pool {
    name                         = "system"
    vm_size                      = var.system_vm_size
    vnet_subnet_id               = var.subnet_id
    node_count                   = 1
    os_disk_size_gb              = 64
    temporary_name_for_rotation  = "systmp"
    only_critical_addons_enabled = true # taints the pool CriticalAddonsOnly: only CoreDNS, metrics-server, CSI drivers etc.

    upgrade_settings {
      max_surge = "10%"
    }
  }

  identity {
    type = "SystemAssigned"
  }

  # Azure CNI Overlay keeps pod IPs out of the VNet; Cilium provides NetworkPolicy enforcement,
  # which Phase 3 needs for default-deny policies.
  network_profile {
    network_plugin      = "azure"
    network_plugin_mode = "overlay"
    network_data_plane  = "cilium"
    network_policy      = "cilium"
    load_balancer_sku   = "standard"
    pod_cidr            = "192.168.0.0/16"
    service_cidr        = "172.16.0.0/16"
    dns_service_ip      = "172.16.0.10"
  }

  # Secrets Store CSI driver with the Azure Key Vault provider: mounts Key Vault secrets as files / env.
  key_vault_secrets_provider {
    secret_rotation_enabled  = true
    secret_rotation_interval = "2m"
  }

  tags = var.tags
}

# Pool 2: the chat workload (backend, frontend, Redis, PostgreSQL). Autoscaled.
resource "azurerm_kubernetes_cluster_node_pool" "apps" {
  name                  = "apps"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.this.id
  vm_size               = var.apps_vm_size
  mode                  = "User"
  vnet_subnet_id        = var.subnet_id
  auto_scaling_enabled  = true
  min_count             = var.apps_min_count
  max_count             = var.apps_max_count
  os_disk_size_gb       = 64
  node_labels           = { workload = "apps" }
  tags                  = var.tags

  upgrade_settings {
    max_surge = "10%"
  }
}

# Pool 3: observability and runtime security (Prometheus, Grafana, AlertManager, Falco, Trivy Operator).
# Tainted so application pods never land here; Phase 5 and 6 Helm values add the matching toleration and nodeSelector.
resource "azurerm_kubernetes_cluster_node_pool" "monitoring" {
  name                  = "monitoring"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.this.id
  vm_size               = var.monitoring_vm_size
  mode                  = "User"
  vnet_subnet_id        = var.subnet_id
  node_count            = 1
  os_disk_size_gb       = 64
  node_labels           = { workload = "monitoring" }
  node_taints           = ["workload=monitoring:NoSchedule"]
  tags                  = var.tags

  upgrade_settings {
    max_surge = "10%"
  }
}

# Nodes pull images from ACR with their managed identity, no image pull secrets.
resource "azurerm_role_assignment" "acr_pull" {
  scope                            = var.acr_id
  role_definition_name             = "AcrPull"
  principal_id                     = azurerm_kubernetes_cluster.this.kubelet_identity[0].object_id
  skip_service_principal_aad_check = true
}

# Lets the cluster identity attach the pre-created ingress public IP (which lives in our resource group).
resource "azurerm_role_assignment" "network_contributor" {
  scope                = var.resource_group_id
  role_definition_name = "Network Contributor"
  principal_id         = azurerm_kubernetes_cluster.this.identity[0].principal_id
}
