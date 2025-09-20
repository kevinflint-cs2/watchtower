// ./infra/modules/key-vault.bicep
targetScope = 'resourceGroup'

@description('Azure region for the Key Vault')
param location string

@description('Prefix used when constructing resource names')
param namePrefix string

@description('Environment name (e.g., dev, test, prod)')
param envName string

@allowed([
  'standard'
  'premium'
])
@description('Key Vault SKU')
param skuName string = 'standard'

@description('Enable RBAC authorization model (recommended)')
param enableRbacAuthorization bool = true


// @description('Enable purge protection (strongly recommended for prod)')
// param enablePurgeProtection bool = true

@minValue(7)
@maxValue(90)
@description('Soft-delete retention (days)')
param softDeleteRetentionInDays int = 90

@allowed([
  'Enabled'
  'Disabled'
])
@description('Public network access to the vault')
param publicNetworkAccess string = 'Enabled'

@allowed([
  'Allow'
  'Deny'
])
@description('Default firewall action when no rule matches')
param networkDefaultAction string = 'Allow'

@description('Optional IP ranges allowed (CIDR strings). Leave empty for none.')
param allowedIpRanges array = []

// ---------------- RBAC principals ----------------
// Pass objectIds (GUIDs) of users/groups/service principals/managed identities.

@description('Principals that can READ secret values (Key Vault Secrets User)')
param secretReaderPrincipalIds array = []

@description('Principals that can CREATE/UPDATE/DELETE secrets (Key Vault Secrets Officer)')
param secretWriterPrincipalIds array = []

@description('Principals that need full data-plane admin (Key Vault Administrator)')
param adminPrincipalIds array = []

// ---------------- Diagnostics (optional) ----------------

@description('Resource ID of Log Analytics workspace to receive Key Vault logs/metrics')
param logAnalyticsWorkspaceId string = ''

@description('Diagnostic setting name (used to adopt/update if it already exists)')
param diagSettingName string = 'kv-to-la'

// ---------------- Name generation (<= 24 chars constraint) ----------------

var baseName = toLower('${namePrefix}-kv-${envName}')
var suffix = substring(uniqueString(resourceGroup().id), 0, 6)
var kvName = length(baseName) <= 17 ? '${baseName}-${suffix}-01' : '${substring(baseName, 0, 17)}-${suffix}'

// ---------------- Role Definition IDs (built-in) ----------------
var roleId_KeyVaultAdmin        = '00482a5a-887f-4fb3-b363-3b7fe8e74483' // Key Vault Administrator
var roleId_KeyVaultSecretsUser  = '4633458b-17de-408a-b874-0445c86b69e6' // Key Vault Secrets User
var roleId_KeyVaultSecretsOfcr  = 'b86a8fe4-44ce-4948-aee5-eccb2c155cd7' // Key Vault Secrets Officer

// ---------------- Vault ----------------

resource kv 'Microsoft.KeyVault/vaults@2024-11-01' = {
  name: kvName
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: {
      name: skuName
      family: 'A'
    }
    enableRbacAuthorization: enableRbacAuthorization
    // No accessPolicies block when RBAC is enabled
    publicNetworkAccess: publicNetworkAccess
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: networkDefaultAction
      ipRules: [for ip in allowedIpRanges: {
        value: ip
      }]
    }
    softDeleteRetentionInDays: softDeleteRetentionInDays
    //enablePurgeProtection: enablePurgeProtection
  }
  tags: {
    project: 'hello-azd-bicep'
    env: envName
  }
}

// ---------------- RBAC: role assignments at vault scope ----------------

resource raAdmins 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for pid in adminPrincipalIds: {
  name: guid(kv.id, 'kv-admin', pid)
  scope: kv
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleId_KeyVaultAdmin)
    principalId: pid
  }
}]

resource raWriters 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for pid in secretWriterPrincipalIds: {
  name: guid(kv.id, 'kv-secret-writer', pid)
  scope: kv
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleId_KeyVaultSecretsOfcr)
    principalId: pid
  }
}]

resource raReaders 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for pid in secretReaderPrincipalIds: {
  name: guid(kv.id, 'kv-secret-reader', pid)
  scope: kv
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleId_KeyVaultSecretsUser)
    principalId: pid
  }
}]

// ---------------- Diagnostics (optional) ----------------
// Only create if a workspace ID was provided.
resource kvDiag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = if (!empty(logAnalyticsWorkspaceId)) {
  name: diagSettingName
  scope: kv
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    // Category groups recommended by Azure Monitor: allLogs + AllMetrics
    logs: [
      { categoryGroup: 'allLogs', enabled: true }
    ]
    metrics: [
      { category: 'AllMetrics', enabled: true }
    ]
  }
}

output keyVaultName string = kv.name
output keyVaultId   string = kv.id
output keyVaultUri  string = kv.properties.vaultUri
