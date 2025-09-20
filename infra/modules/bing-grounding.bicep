@description('Name of the Bing Grounding account resource')
param name string

@description('Azure region for the resource (e.g., eastus)')
param location string

@description('SKU tier (e.g., S0)')
param sku string = 'S0'

@description('Optional tags map')
param tags object = {}

@description('Bing Grounding account')
resource bing 'Microsoft.Bing/accounts@2025-05-01-preview' = {
  name: name
  location: location
  kind: 'Bing.Grounding'
  tags: tags
  sku: {
    name: sku
  }
}

@description('Resource ID of the Bing Grounding account')
output bingAccountId string = bing.id
