targetScope = 'resourceGroup'

@description('Azure region for resources')
param location string

@description('Prefix for names')
param namePrefix string

@allowed([
  'Standard_LRS'
  'Standard_GRS'
  'Standard_RAGRS'
  'Standard_ZRS'
])
@description('Storage SKU')
param accountSku string

@description('Environment name (e.g., dev, test, prod)')
param envName string

@description('Principal IDs to grant Azure AI Project Manager at the project scope')
param projectManagerPrincipalIds array = []

@description('Principal IDs to grant Azure AI User at the project scope')
param projectUserPrincipalIds array = []

var storageAccountName = '${namePrefix}st${envName}${uniqueString(resourceGroup().id)}'
var laName   = '${namePrefix}-laws-${envName}'
var appiName = '${namePrefix}-appi-${envName}'
// ---------------- KV Name generation (<= 24 chars constraint) ----------------
var baseName = toLower('${namePrefix}-kv-${envName}')
var suffix = substring(uniqueString(resourceGroup().id), 0, 6)
var keyVaultName = length(baseName) <= 17 ? '${baseName}-${suffix}-01' : '${substring(baseName, 0, 17)}-${suffix}'
var foundryAccountName   = toLower('${namePrefix}-aifa-${envName}')
var foundryProjectName   = toLower('${namePrefix}-aifp-${envName}')
var modelName4oMini      = toLower('${namePrefix}-gpt40-mini')

// Can update tags later as necessary
var tags = {
  project: namePrefix
  env: envName
}

// Existing storage module
module storage './modules/storage-account.bicep' = {
  name: 'storageAccountModule'
  params: {
    location:   location
    storageAccountName: storageAccountName
    accountSku: accountSku
    logAnalyticsWorkspaceId: observability.outputs.laIdOut
    tags: tags
  }
}

// NEW: Observability module (LA + App Insights)
module observability './modules/observability.bicep' = {
  name: 'observabilityModule'
  params: {
    location:   location
    tags: tags
    laName: laName
    appiName: appiName
  }
}

module keyvault './modules/key-vault.bicep' = {
  name: 'keyvault'
  params: {
    location: location
    keyVaultName: keyVaultName
    skuName: 'standard'
    tags: tags
    // Wire diagnostics to your LA workspace
    logAnalyticsWorkspaceId: observability.outputs.laIdOut

    // Example principal IDs (objectIds) for RBAC:
    // - Logic App (Standard) / Function App system-assigned identity principalId
    // - Service principal used by your SOAR automations
    secretWriterPrincipalIds: [
      // '<objectId-of-ci/seeding-identity-that-adds-secrets>'
    ]
    secretReaderPrincipalIds: [
      // '<objectId-of-app/logicapp/func-that-reads-secrets>'
    ]
    adminPrincipalIds: [
      // '<objectId-of-break-glass-admin-group>'
    ]
  }
}

module aiFoundry './modules/ai-foundry-project.bicep' = {
  name: 'ai-foundry'
  params: {
    location: location
    tags: tags
    accountName: foundryAccountName
    projectName: foundryProjectName
    accountSku: 'S0'
    diagSettingName: 'aifoundry-account-to-la'
    workspaceId: observability.outputs.laIdOut
    projectManagerPrincipalIds: projectManagerPrincipalIds
    projectUserPrincipalIds: projectUserPrincipalIds
  }
}

module chat4oMini './modules/aoai-model-chatgpt4o-mini.bicep' = {
  name: 'chatgpt4o-mini-deployment'
  params: {
    accountName: foundryAccountName
    deploymentName: modelName4oMini
    tags: tags
    // Optional overrides:
    // deploymentName: 'gpt-4o-mini'
    // modelVersion: '2024-07-18'
    // skuName: 'GlobalStandard'
    // capacity: 2
  }
  dependsOn: [ aiFoundry ]
}

output storage_account      string = storage.outputs.name
output la_name              string = observability.outputs.laNameOut
output appi_name           string = observability.outputs.appiNameOut
output appi_conn_str_id     string = observability.outputs.appiConnStr
output keyvault_name        string = keyvault.outputs.keyVaultName
output aifoundry_account    string = aiFoundry.outputs.accountName
output aifoundry_project    string = aiFoundry.outputs.projectName
output aifountry_project_endpoint string = aiFoundry.outputs.projectEndpoints['AI Foundry API']
output model_chatgpt4o_mini string = chat4oMini.outputs.deployedName

