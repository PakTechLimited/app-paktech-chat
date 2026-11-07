provider "azurerm" {
  subscription_id = var.subscription_id
  features {
    key_vault {
      # Re-creating the vault after a teardown must not fail on a soft-deleted copy.
      recover_soft_deleted_key_vaults = true
    }
  }
}

provider "azuread" {}
