targetScope = 'resourceGroup'

@description('Azure region for observability resources')
param location string

@description('Prefix used when constructing resource names')
param namePrefix string

@description('Environment name (e.g., dev, test, prod)')
param envName string

// Names per your pattern: <prefix>-laws-<env>, and a similar pattern for App Insights
var laName   = '${namePrefix}-laws-${envName}'
var appiName = '${namePrefix}-appi-${envName}'

resource laws 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: laName
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
  }
  tags: {
    project: 'hello-azd-bicep'
    env: envName
  }
}

resource appi 'Microsoft.Insights/components@2020-02-02' = {
  name: appiName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: laws.id   // workspace-based App Insights
    Flow_Type: 'Bluefield'         // required by this API version for workspace-based
  }
  tags: {
    project: 'hello-azd-bicep'
    env: envName
  }
}

output laNameOut   string = laws.name
output laIdOut     string = laws.id
output appiNameOut string = appi.name
output appiIdOut   string = appi.id
