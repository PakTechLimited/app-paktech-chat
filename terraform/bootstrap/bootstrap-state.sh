#!/usr/bin/env bash
# One-time (idempotent) creation of the Terraform remote-state storage.
# Run once per subscription, with `az login` done. Safe to re-run.
set -euo pipefail

# Git Bash on Windows rewrites arguments that start with "/" (such as /subscriptions/...) into Windows paths.
# Turn that off, otherwise the role assignment below fails.
export MSYS_NO_PATHCONV=1

SUBSCRIPTION_ID="${SUBSCRIPTION_ID:-f99345eb-69a8-455e-82d7-25706b78ccaf}"
LOCATION="${LOCATION:-eastus}"
STATE_RG="${STATE_RG:-rg-paktech-tfstate}"
STATE_SA="${STATE_SA:-paktechtfstateprod}"
STATE_CONTAINER="${STATE_CONTAINER:-tfstate}"

az account set --subscription "$SUBSCRIPTION_ID"

az group create --name "$STATE_RG" --location "$LOCATION" --output none

if ! az storage account show --name "$STATE_SA" --resource-group "$STATE_RG" >/dev/null 2>&1; then
  az storage account create \
    --name "$STATE_SA" --resource-group "$STATE_RG" --location "$LOCATION" \
    --sku Standard_LRS --kind StorageV2 \
    --min-tls-version TLS1_2 --allow-blob-public-access false \
    --output none
fi

# Versioning + soft delete let you recover an overwritten or deleted state file.
az storage account blob-service-properties update \
  --account-name "$STATE_SA" --resource-group "$STATE_RG" \
  --enable-versioning true \
  --enable-delete-retention true --delete-retention-days 14 \
  --output none

# The container is created with Azure AD auth, so no storage account key is ever used.
ME="$(az ad signed-in-user show --query id -o tsv)"
SA_ID="$(az storage account show --name "$STATE_SA" --resource-group "$STATE_RG" --query id -o tsv)"
az role assignment create --assignee-object-id "$ME" --assignee-principal-type User \
  --role "Storage Blob Data Contributor" --scope "$SA_ID" --output none || echo "Role assignment not created (it may already exist); check it if the next step returns 403."
sleep 20   # role assignments take a moment to propagate

az storage container create --name "$STATE_CONTAINER" --account-name "$STATE_SA" --auth-mode login --output none

echo "State backend ready: $STATE_SA/$STATE_CONTAINER in $STATE_RG"
