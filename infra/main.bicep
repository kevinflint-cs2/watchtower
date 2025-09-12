targetScope = 'subscription'

@description('Azure region for RG and resources')
param location string

@description('Resource group name to create')
param rgName string

@description('Name prefix used to generate resource names')
param namePrefix string

@description('Environment')
@allowed(['dev','test','prod'])
param environment string

@description('Random string to ensure globally unique resource names')
param rand string

@description('Principal IDs to grant Azure AI Project Manager at the project scope')
param projectManagerPrincipalIds array = []

@description('Principal IDs to grant Azure AI User at the project scope')
param projectUserPrincipalIds array = []

var suffix = toLower('${environment}')
var workspaceName        = toLower('${namePrefix}-laws-${suffix}')
var appInsightsName      = toLower('${namePrefix}-appi-${suffix}')
var diagName             = toLower('${namePrefix}-diag-${suffix}')
var keyVaultName         = toLower('${namePrefix}-kv-${suffix}-${rand}')
var appConfigName        = toLower('${namePrefix}-appconf-${suffix}')
var foundryAccountName   = toLower('${namePrefix}-aifa-${suffix}')
var foundryProjectName   = toLower('${namePrefix}-aifp-${suffix}')

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: rgName
  location: location
  tags: { app: namePrefix, env: environment }
}

module observability './modules/observability.bicep' = {
  name: 'observability'
  scope: resourceGroup(rgName)
  params: {
    location: location
    workspaceName: workspaceName
    appInsightsName: appInsightsName
  }
}

module secretsConfig './modules/secrets-config.bicep' = {
  name: 'secrets-config'
  scope: resourceGroup(rgName)
  params: {
    location: location
    keyVaultName: keyVaultName
    appConfigName: appConfigName
    workspaceId: observability.outputs.workspaceId
  }
}

module aiFoundry './modules/ai-foundry.bicep' = {
  name: 'ai-foundry'
  scope: resourceGroup(rgName)
  params: {
    location: location
    accountName: foundryAccountName
    projectName: foundryProjectName
    accountSku: 'S0'
    workspaceId: observability.outputs.workspaceId
    projectManagerPrincipalIds: projectManagerPrincipalIds
    projectUserPrincipalIds: projectUserPrincipalIds
  }
}

module chat4oMini './modules/aoai-model-chatgpt4o-mini.bicep' = {
  name: 'chatgpt4o-mini-deployment'
  scope: resourceGroup(rgName)
  params: {
    location: location
    accountName: foundryAccountName
    // Optional overrides:
    // deploymentName: 'gpt-4o-mini'
    // modelVersion: '2024-07-18'
    // skuName: 'GlobalStandard'
    // capacity: 2
  }
}

// Subscription Activity Logs -> Log Analytics workspace (SUBSCRIPTION SCOPE)
resource subDiag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: diagName
  // No scope here because file targetScope is already 'subscription'
  properties: {
    workspaceId: observability.outputs.workspaceId
    logs: [
      { categoryGroup: 'AllLogs', enabled: true }
    ]
    metrics: [
      { category: 'AllMetrics', enabled: true }
    ]
  }
}

output resourceGroupId string       = rg.id
output workspaceId string           = observability.outputs.workspaceId
output appInsightsName string       = appInsightsName
output subscriptionDiagName string  = subDiag.name
