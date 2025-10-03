# Infrastructure Documentation

## Overview

The Watchtower repository uses Azure Developer CLI (azd) with Bicep templates to provision and manage Azure infrastructure for an AI-powered incident response system. The infrastructure includes Azure AI Services (OpenAI), Azure AI Foundry projects, Container Apps, Application Insights, Log Analytics, Storage Accounts, and optionally Azure AI Search services.

The deployment follows a modular approach with lifecycle hooks defined in [`azure.yaml`](azure.yaml) that orchestrate validation, provisioning, and post-deployment configuration through PowerShell and Bash scripts in the [`scripts/`](scripts/) directory.

## Provisioning Flow (from `azure.yaml`)

### Hook-by-Hook Execution Map

The provisioning workflow executes in this order [`azure.yaml` L11-43]:

#### 1. Pre-Up Hook (`preup`)
- **POSIX**: [`./scripts/validate_env_vars.sh`](scripts/validate_env_vars.sh) [`azure.yaml` L13-17]
- **Windows**: [`./scripts/validate_env_vars.ps1`](scripts/validate_env_vars.ps1) [`azure.yaml` L18-22]
- **Purpose**: Validates `AZURE_EXISTING_AIPROJECT_RESOURCE_ID` environment variable format if provided

#### 2. AZD Provision (implicit)
- Executes `azd provision` using [`infra/main.bicep`](infra/main.bicep) with parameters from [`infra/main.parameters.json`](infra/main.parameters.json)

#### 3. Post-Provision Hook (`postprovision`)
- **POSIX**: [`./scripts/write_env.sh`](scripts/write_env.sh) [`azure.yaml` L29-33]
- **Windows**: [`./scripts/write_env.ps1`](scripts/write_env.ps1) [`azure.yaml` L24-28]
- **Purpose**: Extracts azd environment values and writes them to `src/.env` file

#### 4. Post-Deploy Hook (`postdeploy`)
- **POSIX**: [`./scripts/postdeploy.sh`](scripts/postdeploy.sh) [`azure.yaml` L39-43]
- **Windows**: [`./scripts/postdeploy.ps1`](scripts/postdeploy.ps1) [`azure.yaml` L34-38]
- **Purpose**: Displays optional credential setup message

### Script Call Graph

```
azure.yaml
├── preup
│   ├── validate_env_vars.sh (POSIX)
│   └── validate_env_vars.ps1 (Windows)
├── [azd provision] → infra/main.bicep + infra/main.parameters.json
├── postprovision
│   ├── write_env.sh (POSIX)
│   └── write_env.ps1 (Windows)
└── postdeploy
    ├── postdeploy.sh (POSIX)
    └── postdeploy.ps1 (Windows)
```

## Parameters & Environment Variables

### Azure.yaml Pipeline Variables [`azure.yaml` L55-89]

| Variable | Purpose | Used By |
|----------|---------|---------|
| `AZURE_RESOURCE_GROUP` | Resource group name | Bicep templates, scripts |
| `AZURE_AIHUB_NAME` | AI Hub resource name | Bicep parameters |
| `AZURE_AIPROJECT_NAME` | AI Project resource name | Bicep parameters |
| `AZURE_AISERVICES_NAME` | AI Services resource name | Bicep parameters |
| `AZURE_SEARCH_SERVICE_NAME` | Search service resource name | Bicep parameters |
| `AZURE_APPLICATION_INSIGHTS_NAME` | App Insights resource name | Bicep parameters |
| `AZURE_CONTAINER_REGISTRY_NAME` | Container registry resource name | Bicep parameters |
| `AZURE_KEYVAULT_NAME` | Key Vault resource name | Bicep parameters |
| `AZURE_STORAGE_ACCOUNT_NAME` | Storage account resource name | Bicep parameters |
| `AZURE_LOG_ANALYTICS_WORKSPACE_NAME` | Log Analytics workspace name | Bicep parameters |
| `USE_CONTAINER_REGISTRY` | Enable/disable container registry | Bicep parameters |
| `USE_APPLICATION_INSIGHTS` | Enable/disable App Insights | Bicep parameters |
| `USE_AZURE_AI_SEARCH_SERVICE` | Enable/disable AI Search | Bicep parameters |

### Core Infrastructure Parameters [`infra/main.parameters.json`]

| Parameter | Source Env Var | Default | Type | Used By |
|-----------|----------------|---------|------|---------|
| `environmentName` | `AZURE_ENV_NAME` | - | string | Resource naming [`main.parameters.json` L4-6] |
| `location` | `AZURE_LOCATION` | - | string | All resources [`main.parameters.json` L7-9] |
| `principalId` | `AZURE_PRINCIPAL_ID` | - | string | RBAC assignments [`main.parameters.json` L10-12] |
| `useSearchService` | `USE_AZURE_AI_SEARCH_SERVICE` | `false` | bool | Search service conditional deployment [`main.parameters.json` L47-49] |
| `useApplicationInsights` | `USE_APPLICATION_INSIGHTS` | `true` | bool | App Insights conditional deployment [`main.parameters.json` L44-46] |

### AI Model Configuration Parameters [`infra/main.parameters.json` L50-92]

| Parameter | Source Env Var | Default | Type | Notes |
|-----------|----------------|---------|------|-------|
| `agentName` | `AZURE_AI_AGENT_NAME` | `agent-template-assistant` | string | Agent display name |
| `agentModelName` | `AZURE_AI_AGENT_MODEL_NAME` | `gpt-4o-mini` | string | Chat model name |
| `agentModelVersion` | `AZURE_AI_AGENT_MODEL_VERSION` | `2024-07-18` | string | Model version |
| `agentDeploymentSku` | `AZURE_AI_AGENT_DEPLOYMENT_SKU` | `GlobalStandard` | string | Deployment tier |
| `agentDeploymentCapacity` | `AZURE_AI_AGENT_DEPLOYMENT_CAPACITY` | `80` | int | Model capacity (TPM) |
| `embedModelName` | `AZURE_AI_EMBED_MODEL_NAME` | `text-embedding-3-small` | string | Embedding model name |
| `embedDeploymentCapacity` | `AZURE_AI_EMBED_DEPLOYMENT_CAPACITY` | `50` | int | Embedding capacity |
| `embeddingDeploymentDimensions` | `AZURE_AI_EMBED_DIMENSIONS` | `100` | string | Embedding dimensions |

### Environment Variable Resolution Path

Example flow for `useSearchService` parameter:
1. **Source**: `USE_AZURE_AI_SEARCH_SERVICE` environment variable [`main.parameters.json` L47-49]
2. **Template**: Parameter passed to `main.bicep` as `useSearchService` [`main.bicep` L103]
3. **Resource**: Conditionally deploys search service module [`main.bicep` L114-118]
4. **Output**: Generates search endpoint output if deployed [`main.bicep` L210-211]

### Scripts Environment Variable Usage

#### `validate_env_vars.sh` [`scripts/validate_env_vars.sh`]
- **Reads**: `AZURE_EXISTING_AIPROJECT_RESOURCE_ID`
- **Validates**: Resource ID format against regex pattern
- **Action**: Exits with error code if invalid format

#### `write_env.sh` [`scripts/write_env.sh`]
- **Reads**: All azd environment values via `azd env get-value`
- **Writes**: 14 environment variables to `src/.env` file
- **Key Variables**: Project endpoint, agent deployment, search configuration

## AI Search Creation Flow

### Conditional Deployment Logic

Azure AI Search is deployed conditionally based on the `useSearchService` parameter [`main.bicep` L103]:

```bicep
param useSearchService bool = false
```

### Resource Creation Order [`infra/core/host/ai-environment.bicep` L116-129]

1. **Cognitive Services Deployment** - Creates AI Services account with project [`ai-environment.bicep` L79-88]
2. **Search Service Deployment** - Conditionally deploys if `searchServiceName` is not empty [`ai-environment.bicep` L116-129]
   - **Dependencies**: `dependsOn: [cognitiveServices]`
   - **Module**: [`core/search/search-services.bicep`](infra/core/search/search-services.bicep)

### Search Service Configuration [`infra/core/search/search-services.bicep`]

| Property | Value | Source |
|----------|-------|--------|
| **SKU** | `basic` | Hard-coded [`search-services.bicep` L49-51] |
| **Semantic Search** | `free` | Passed from ai-environment [`ai-environment.bicep` L123] |
| **Auth Options** | `aadOrApiKey` with bearer challenge | [`ai-environment.bicep` L124] |
| **Identity** | System-assigned managed identity | [`search-services.bicep` L38-40] |

### Post-Provision Configuration

#### RBAC Assignment [`search-services.bicep` L65-73]
- **Role**: Cognitive Services User (`a97b65f3-24c7-4388-baec-2e87135dc908`)
- **Principal**: Search service managed identity
- **Scope**: Resource group level

#### AI Project Connection [`search-services.bicep` L81-96]
- **Connection Name**: `searchConnection`
- **Category**: `CognitiveSearch`
- **Auth Type**: `ApiKey`
- **Target**: Search service endpoint
- **Credentials**: Primary admin key from `search.listAdminKeys()`

### Dependencies

The search service requires:
- **AI Services Account**: Must exist before search deployment [`ai-environment.bicep` L117]
- **AI Project**: Search connection created within project context [`search-services.bicep` L75-96]
- **Managed Identity**: For RBAC assignments [`search-services.bicep` L65-73]

### Network Configuration
- **Public Access**: Enabled by default [`search-services.bicep` L29]
- **Network Rules**: Empty IP rules, no bypass [`search-services.bicep` L22-25]
- **Private Endpoints**: > TODO: Not found in repo

## Add a New Resource (Using Current Workflow)

### Step-by-Step Recipe

#### 1. Add Environment Variable to Pipeline [`azure.yaml`]
Add the new variable to the pipeline variables section:
```yaml
pipeline:
  variables:
    - AZURE_NEW_RESOURCE_NAME  # Add your variable here
```

#### 2. Add Parameter to main.parameters.json [`infra/main.parameters.json`]
Add parameter mapping with default value:
```json
{
  "parameters": {
    "newResourceName": {
      "value": "${AZURE_NEW_RESOURCE_NAME=default-name}"
    }
  }
}
```

#### 3. Add Parameter to main.bicep [`infra/main.bicep`]
Add parameter declaration and pass to module:
```bicep
@description('The new resource name. If omitted will be generated')
param newResourceName string = ''

// In resource deployment section
module newResource 'core/category/new-resource.bicep' = {
  name: 'newResource'
  scope: rg
  params: {
    location: location
    tags: tags
    name: !empty(newResourceName) ? newResourceName : '${abbrs.categoryNewResource}${resourceToken}'
  }
}
```

#### 4. Create Bicep Module [`infra/core/category/new-resource.bicep`]
Follow existing patterns from [`core/storage/storage-account.bicep`] or [`core/ai/cognitiveservices.bicep`]:
```bicep
metadata description = 'Creates a new Azure resource.'
param name string
param location string = resourceGroup().location
param tags object = {}

resource newResource 'Microsoft.Provider/resourceType@2024-01-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    // Resource-specific properties
  }
}

output id string = newResource.id
output name string = newResource.name
```

#### 5. Add Outputs to main.bicep [`infra/main.bicep`]
Add outputs for consumption by scripts:
```bicep
output AZURE_NEW_RESOURCE_NAME string = newResource.outputs.name
output AZURE_NEW_RESOURCE_ENDPOINT string = newResource.outputs.endpoint
```

#### 6. Update write_env Scripts [`scripts/write_env.sh` and `scripts/write_env.ps1`]
Add environment variable extraction:
```bash
echo "AZURE_NEW_RESOURCE_NAME=$(azd env get-value AZURE_NEW_RESOURCE_NAME 2>/dev/null)" >> $ENV_FILE_PATH
echo "AZURE_NEW_RESOURCE_ENDPOINT=$(azd env get-value AZURE_NEW_RESOURCE_ENDPOINT 2>/dev/null)" >> $ENV_FILE_PATH
```

#### 7. Local Validation and Deployment
```bash
# Validate Bicep syntax
az bicep build --file infra/main.bicep

# Deploy with azd
azd up
```

### Minimal Example: Adding Azure Key Vault

#### 1. Pipeline Variable [`azure.yaml`]
```yaml
pipeline:
  variables:
    - AZURE_KEYVAULT_NAME
```

#### 2. Parameter [`infra/main.parameters.json`]
```json
"keyVaultName": {
  "value": "${AZURE_KEYVAULT_NAME}"
}
```

#### 3. Main Template [`infra/main.bicep`]
```bicep
@description('The Key Vault resource name. If omitted will be generated')
param keyVaultName string = ''

module keyVault 'core/security/keyvault.bicep' = {
  name: 'keyVault'
  scope: rg
  params: {
    name: !empty(keyVaultName) ? keyVaultName : '${abbrs.keyVaultVaults}${resourceToken}'
    location: location
    tags: tags
    principalId: principalId
  }
}

output AZURE_KEYVAULT_NAME string = keyVault.outputs.name
output AZURE_KEYVAULT_ENDPOINT string = keyVault.outputs.endpoint
```

## Appendix

### File Map

| File | Description |
|------|-------------|
| [`azure.yaml`](azure.yaml) | AZD configuration with lifecycle hooks and pipeline variables |
| [`infra/main.bicep`](infra/main.bicep) | Primary Bicep template for subscription-level deployment |
| [`infra/main.parameters.json`](infra/main.parameters.json) | Parameter mappings from environment variables to Bicep |
| [`infra/abbreviations.json`](infra/abbreviations.json) | Azure resource naming abbreviations |
| [`infra/core/host/ai-environment.bicep`](infra/core/host/ai-environment.bicep) | AI Services, storage, monitoring deployment |
| [`infra/core/host/container-apps.bicep`](infra/core/host/container-apps.bicep) | Container Apps environment and registry |
| [`infra/core/search/search-services.bicep`](infra/core/search/search-services.bicep) | Azure AI Search service deployment |
| [`infra/core/ai/cognitiveservices.bicep`](infra/core/ai/cognitiveservices.bicep) | AI Services account and model deployments |
| [`infra/core/security/role.bicep`](infra/core/security/role.bicep) | RBAC role assignments |
| [`scripts/validate_env_vars.sh`](scripts/validate_env_vars.sh) | Environment variable validation (POSIX) |
| [`scripts/write_env.sh`](scripts/write_env.sh) | Extract azd values to .env file (POSIX) |
| [`scripts/postdeploy.sh`](scripts/postdeploy.sh) | Post-deployment message (POSIX) |

### Common Commands

| Command | Purpose | Context |
|---------|---------|---------|
| `azd up` | Full provision and deploy | Initial deployment |
| `azd provision` | Infrastructure only | Update infrastructure |
| `azd deploy` | Application only | Code changes |
| `azd env get-values` | List all environment variables | Debug configuration |
| `az bicep build --file infra/main.bicep` | Validate Bicep syntax | Local development |