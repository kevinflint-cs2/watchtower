@description('Name of the Foundry account (Microsoft.CognitiveServices/accounts) in this resource group')
param accountName string

@description('Deployment name that will show up in Foundry (also used from code)')
@minLength(1)
param deploymentName string = 'gpt-4o-mini'

@description('Model version to deploy')
param modelVersion string = '2024-07-18'

@description('SKU name (Standard or GlobalStandard depending on region/offer)')
@allowed([
  'Standard'
  'GlobalStandard'
])
param skuName string = 'GlobalStandard'

@description('Capacity units (controls tokens-per-minute)')
@minValue(1)
param capacity int = 1

// Existing Foundry account (kind: AIServices)
resource account 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' existing = {
  name: accountName
}

// Single OpenAI chat deployment for gpt-4o-mini
resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  name: deploymentName
  parent: account
  sku: {
    name: skuName
    capacity: capacity
  }
  properties: {
    model: {
      name: 'gpt-4o-mini'
      version: modelVersion
      format: 'OpenAI'
    }
  }
}

output deployedName string = modelDeployment.name
