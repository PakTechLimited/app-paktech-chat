# Remote state in Blob Storage (created by terraform/bootstrap/bootstrap-state.sh).
# use_azuread_auth: access is by your Azure AD login, so no storage account key is needed.
terraform {
  backend "azurerm" {
    resource_group_name  = "rg-paktech-tfstate"
    storage_account_name = "paktechtfstateprod"
    container_name       = "tfstate"
    key                  = "paktech-chat-prod.tfstate"
    use_azuread_auth     = true
  }
}
