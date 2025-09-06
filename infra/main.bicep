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

@description('Principal IDs to grant Azure AI Project Manager at the project scope')
param projectManagerPrincipalIds array = []

@description('Principal IDs to grant Azure AI User at the project scope')
param projectUserPrincipalIds array = []

var suffix = toLower('${environment}-${replace(location, ' ', '')}')
var workspaceName   = '${namePrefix}-la-${suffix}'       // e.g., watchtower-la-dev-eastus
var appInsightsName = '${namePrefix}-appi-${suffix}'     // e.g., watchtower-appi-dev-eastus
var diagName        = '${namePrefix}-diag-${suffix}'
var keyVaultName    = toLower('${namePrefix}-kv-${suffix}')
var appConfigName   = toLower('${namePrefix}-appcs-${suffix}') // common app config prefix
var foundryAccountName = toLower('${namePrefix}-aif-${suffix}')
var foundryProjectName = toLower('${namePrefix}-proj-${suffix}')


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

// Subscription Activity Logs -> Log Analytics workspace (SUBSCRIPTION SCOPE)
resource subDiag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: diagName
  scope: subscription()
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

output resourceGroupId string     = rg.id
output workspaceId string         = observability.outputs.workspaceId
output appInsightsName string     = appInsightsName
output subscriptionDiagName string = subDiag.name
