// ./infra/modules/storage-account.bicep
targetScope = 'resourceGroup'

@description('Azure region for the storage account')
param location string

@description('Prefix for the storage account name')
param namePrefix string

@allowed([
  'Standard_LRS'
  'Standard_GRS'
  'Standard_RAGRS'
  'Standard_ZRS'
])
@description('Storage SKU')
param accountSku string

@description('Resource ID of the Log Analytics Workspace (from observability.bicep outputs)')
param logAnalyticsWorkspaceId string

// Stable, unique SA name from the RG id to avoid collisions
var storageAccountName = '${namePrefix}st${uniqueString(resourceGroup().id)}'

resource sa 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: { name: accountSku }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
  tags: {
    project: 'hello-azd-bicep'
    env: 'dev'
  }
}

// ----- Existing service handles (required for per-service diagnostic settings)
resource blobSvc 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' existing = {
  parent: sa
  name: 'default'
}

resource fileSvc 'Microsoft.Storage/storageAccounts/fileServices@2023-01-01' existing = {
  parent: sa
  name: 'default'
}

resource queueSvc 'Microsoft.Storage/storageAccounts/queueServices@2023-01-01' existing = {
  parent: sa
  name: 'default'
}

resource tableSvc 'Microsoft.Storage/storageAccounts/tableServices@2023-01-01' existing = {
  parent: sa
  name: 'default'
}

// ----- Diagnostic settings: send ALL logs + metrics to Log Analytics
// Categories for Storage services are StorageRead, StorageWrite, StorageDelete.
// Metrics category is AllMetrics.

// Blob
resource diagBlob 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'send-blob-to-la'
  scope: blobSvc
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      { category: 'StorageRead',  enabled: true }
      { category: 'StorageWrite', enabled: true }
      { category: 'StorageDelete', enabled: true }
    ]
    metrics: [
      { category: 'AllMetrics', enabled: true }
    ]
  }
}

// File
resource diagFile 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'send-file-to-la'
  scope: fileSvc
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      { category: 'StorageRead',  enabled: true }
      { category: 'StorageWrite', enabled: true }
      { category: 'StorageDelete', enabled: true }
    ]
    metrics: [
      { category: 'AllMetrics', enabled: true }
    ]
  }
}

// Queue
resource diagQueue 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'send-queue-to-la'
  scope: queueSvc
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      { category: 'StorageRead',  enabled: true }
      { category: 'StorageWrite', enabled: true }
      { category: 'StorageDelete', enabled: true }
    ]
    metrics: [
      { category: 'AllMetrics', enabled: true }
    ]
  }
}

// Table
resource diagTable 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'send-table-to-la'
  scope: tableSvc
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      { category: 'StorageRead',  enabled: true }
      { category: 'StorageWrite', enabled: true }
      { category: 'StorageDelete', enabled: true }
    ]
    metrics: [
      { category: 'AllMetrics', enabled: true }
    ]
  }
}

output name string = sa.name
output location string = sa.location
output sku string = accountSku
