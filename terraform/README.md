# PakTech Chat: Azure infrastructure (Terraform)

Provisions everything Phase 3 (GitOps) needs, in one resource group `rg-paktech-prod` (East US).

| Resource | Name | Notes |
|---|---|---|
| AKS | `aks-paktech-prod` | Azure CNI Overlay + Cilium (NetworkPolicy), three node pools (`system` 1 node tainted CriticalAddonsOnly, `apps` autoscaled 1 to 3, `monitoring` 1 node tainted `workload=monitoring:NoSchedule`), OIDC issuer + Workload Identity, Key Vault Secrets Store CSI driver |
| ACR | `paktechacr` | Basic SKU, admin user off; AKS pulls with its managed identity (AcrPull) |
| Key Vault | `kv-paktech-prod` | Azure RBAC authorization, soft delete 7 days, purge protection off (lab teardown) |
| App identity | `id-paktech-chat-prod` | User-assigned identity federated to the app's Kubernetes service accounts; reads secrets only |
| Public IP | `pip-ingress-paktech-prod` | Static, outside the cluster so DNS survives rebuilds |
| DNS | `paktechlimited.chat` | Azure DNS zone, apex A record to the ingress IP, `www` CNAME |
| CI identity | `sp-github-paktech-cicd` | Azure AD app with GitHub OIDC federation (no stored secrets); AcrPush on ACR, Cluster User on AKS |
| Network | `vnet-paktech-prod` | 10.10.0.0/16, AKS subnet 10.10.1.0/24 |

State lives in `rg-paktech-tfstate` / `paktechtfstateprod` / container `tfstate` (versioned, soft delete, Azure AD auth).

## Layout

```
terraform/
  bootstrap/bootstrap-state.sh     one-time creation of the state storage
  envs/prod/                       the only environment: wires the modules together
  modules/{network,acr,aks,keyvault,workload-identity,dns,github-oidc}
```

## Who needs which permission

- `Owner` (or Contributor + User Access Administrator) on the subscription: Terraform creates role assignments.
- Permission to register applications in Azure AD (for example the Application Developer role): the `github-oidc` module creates an app registration.

## Run it

```bash
az login
az account set --subscription f99345eb-69a8-455e-82d7-25706b78ccaf

# 1. State storage (skip if paktechtfstateprod already exists; the script is idempotent anyway)
bash terraform/bootstrap/bootstrap-state.sh

# 2. Your object ID goes into a git-ignored tfvars file
cd terraform/envs/prod
cp terraform.tfvars.example terraform.tfvars
az ad signed-in-user show --query id -o tsv     # paste into terraform.tfvars

# 3. Plan, read it, apply
terraform init
terraform fmt -check -recursive ../..
terraform validate
terraform plan -out tfplan
terraform apply tfplan

# 4. Connect and verify
$(terraform output -raw get_credentials_command)
kubectl get nodes
kubectl get pods -n kube-system | grep -E "secrets-store|azure-wi|cilium"
az acr show --name paktechacr --query loginServer -o tsv
```

Commit the generated `.terraform.lock.hcl` (it pins provider versions). Never commit `terraform.tfvars` or state.

## Point the domain at Azure (Namecheap)

1. `terraform output dns_name_servers` prints four Azure name servers.
2. Namecheap: Domain List > Manage > Nameservers > Custom DNS, enter the four values, save.
3. Propagation can take from minutes to a few hours. Check with `nslookup -type=NS paktechlimited.chat`.

The apex record already points at the static ingress IP. Nothing answers on it until Phase 3 installs the ingress controller with that IP.

## GitHub Actions variables (Phase 4)

Set these as repository **variables** (they are identifiers, not secrets): `AZURE_CLIENT_ID` = `terraform output github_oidc_client_id`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`. The workflow then logs in with `azure/login` and `permissions: id-token: write`.

## Approximate cost (check the Azure pricing page for current numbers)

The cluster dominates: each `Standard_D2s_v3` node runs roughly $2 to $3 per day and the minimum is three nodes (one per pool), so about $6 to $9 per day for compute, plus about $0.50 per day for the static IP and load balancer, ACR Basic about $0.17 per day, DNS and Key Vault pennies. The `apps` pool can scale to 3 nodes, so the ceiling is five nodes. Stop compute between sessions with `az aks stop -g rg-paktech-prod -n aks-paktech-prod` (start with `az aks start`), or tear down completely:

```bash
terraform destroy      # keeps rg-paktech-tfstate; the next apply recreates everything
```

The Key Vault is soft-deleted on destroy; the provider is configured to recover it on the next apply.

## Design decisions (why)

- **Modules + one `envs/prod`**: reusable pieces, a visible structure, one state file. A second environment later is a new folder, not a rewrite.
- **Remote state with Azure AD auth**: no storage keys to leak; versioning lets you recover a bad state.
- **Workload Identity over secrets in the cluster**: a pod proves who it is with a Kubernetes-issued token that Azure AD trusts through federation; there is no password to rotate or steal.
- **Key Vault with RBAC, read-only for the app**: the app gets `Key Vault Secrets User`, so a compromised pod can read its own secrets but not change or enumerate the vault.
- **GitHub OIDC federation**: the pipeline holds no Azure credential. Azure accepts only tokens whose subject matches the allowed branches, pull requests and the `prod` environment.
- **Three node pools**: `system` runs only cluster add-ons so an app or Prometheus memory spike cannot starve CoreDNS; `apps` is the autoscaled chat workload; `monitoring` is tainted so Prometheus, Grafana and Falco (Phases 5 and 6) are isolated from production pods and need an explicit toleration plus `nodeSelector: workload=monitoring`. This matches the architecture diagram.
- **Cilium + overlay**: NetworkPolicy enforcement is required for Phase 3 default-deny policies, and overlay avoids burning VNet IPs on pods.
- **Static ingress IP outside AKS**: the DNS record survives a cluster teardown.
- **PostgreSQL and Redis run in-cluster** (decided for cost and easy teardown); managed Azure services are the production-grade alternative.

## Known hardening backlog (deliberately left out of the first pass)

- Private cluster, API server authorized IP ranges, and Azure AD RBAC for the Kubernetes API (local admin accounts are still enabled).
- Key Vault private endpoint and network ACLs; purge protection on.
- Defender for Containers.
- Checkov and tfsec in CI (Phase 4) will flag the items above, which is the expected starting point.

## Validation status

`tofu fmt` passes. The module code was written against azurerm 4.x and azuread 3.x but has **not** been run through `terraform validate` or `plan` against Azure, so expect to fix small attribute-name differences on the first `validate`.
