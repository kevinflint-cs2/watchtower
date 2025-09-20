@description('Azure region')
param location string

@description('AI Foundry account (Cognitive Services) name')
param accountName string

@description('AI Foundry project name')
param projectName string

@description('SKU for the Foundry account')
@allowed(['S0'])
param accountSku string = 'S0'

@description('Workspace resourceId for diagnostics (Log Analytics)')
param workspaceId string

// In ./infra/modules/ai-foundry-project.bicep
@description('Name of the diagnostic setting to create/update on the AI Foundry account')
param diagSettingName string

@description('Principal IDs to grant Azure AI Project Manager at the project scope')
param projectManagerPrincipalIds array = []

@description('Principal IDs to grant Azure AI User at the project scope')
param projectUserPrincipalIds array = []

// ----- Account (kind=AIServices) -----
resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: accountName
  location: location
  kind: 'AIServices'
  sku: { name: accountSku }
  identity: { type: 'SystemAssigned' }
  properties: {
    allowProjectManagement: true
    publicNetworkAccess: 'Enabled'
    customSubDomainName: projectName
  }
}

// Account diagnostics -> Log Analytics
resource acctDiag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: diagSettingName
  scope: account
  properties: {
    workspaceId: workspaceId
    logs: [
      { categoryGroup: 'AllLogs', enabled: true }
    ]
    metrics: [
      { category: 'AllMetrics', enabled: true }
    ]
  }
}


// ----- Project (child of account) -----
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  name: projectName
  parent: account
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    displayName: projectName
    description: 'Project for ${accountName}'
  }
  tags: { managedBy: 'bicep' }
}


// ----- RBAC at project scope (optional) -----
var roleIdProjectManager = 'eadc314b-1a2d-4efa-be10-5d325db5065e' // Azure AI Project Manager
var roleIdAiUser         = '53ca6127-db72-4b80-b1b0-d745d6d5456d' // Azure AI User

resource raManagers 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for pid in projectManagerPrincipalIds: {
  name: guid(project.id, roleIdProjectManager, pid)
  scope: project
  properties: {
    principalId: pid
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIdProjectManager)
    principalType: 'ServicePrincipal' // change to 'User' if needed
  }
}]

resource raUsers 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for pid in projectUserPrincipalIds: {
  name: guid(project.id, roleIdAiUser, pid)
  scope: project
  properties: {
    principalId: pid
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIdAiUser)
    principalType: 'ServicePrincipal'
  }
}]

output accountId string = account.id
output projectId string = project.id
