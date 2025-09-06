@description('Azure region for the resources')
param location string

@description('Log Analytics workspace name')
param workspaceName string

@description('Application Insights component name (workspace-based)')
param appInsightsName string

// Log Analytics Workspace (props nested under properties)
resource la 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: workspaceName
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
  }
}

// Workspace-based Application Insights
resource appi 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: la.id
  }
}

output workspaceId string = la.id
output appInsightsName string = appi.name
