@description('Azure region for the resources')
param location string

@description('Key Vault name (must be globally unique, 3–24 chars, letters/numbers/hyphens)')
param keyVaultName string

@description('App Configuration store name (must be globally unique, lowercase letters/numbers/hyphens)')
param appConfigName string

@description('Target Log Analytics workspace resource ID for diagnostics')
param workspaceId string

// ---------------- Key Vault ----------------
resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  tags: {}
  properties: {
    tenantId: subscription().tenantId
    sku: {
      name: 'standard'
      family: 'A'
    }
    // Soft-delete is always on for new vaults; keep purge protection enabled for compliance
    // enablePurgeProtection: true // Remove for compliance requirements
    softDeleteRetentionInDays: 90
    publicNetworkAccess: 'Enabled'
    accessPolicies: []
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow'
    }
  }
}

// KV → Log Analytics diagnostics
resource kvDiag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'kv-to-laws'
  scope: kv
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

// ---------------- App Configuration ----------------
resource appc 'Microsoft.AppConfiguration/configurationStores@2023-03-01' = {
  name: appConfigName
  location: location
  sku: {
    name: 'Standard'
  }
  tags: {}
}

// App Configuration → Log Analytics diagnostics
resource appcDiag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'appconfig-to-la'
  scope: appc
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

output keyVaultId string = kv.id
output appConfigId string = appc.id
