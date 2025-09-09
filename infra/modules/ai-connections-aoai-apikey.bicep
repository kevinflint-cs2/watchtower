@description('AIServices account (Azure AI Foundry) name')
param aiAccountName string

@description('Project name under the AIServices account')
param aiProjectName string

@description('Azure OpenAI resource name (same RG)')
param aoaiResourceName string

@description('Name for the Project connection')
param connectionName string = 'aoai-apikey'

// Parents in this RG
resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: aiAccountName
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' existing = {
  parent: account
  name: aiProjectName
}

resource aoai 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: aoaiResourceName
}

// Use resource-symbol references (linter-friendly)
var aoaiKeys = aoai.listKeys()
var aoaiRef  = aoai

// Store AOAI key1 in Key Vault (deployer needs KV data-plane rights)
resource aoaiKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: aoaiResourceName
  properties: {
    value: aoaiKeys.key1
  }
}

// Create the Project connection (ApiKey) to AOAI
resource conn 'Microsoft.CognitiveServices/accounts/projects/connections@2025-06-01' = {
  name: connectionName
  parent: project
  properties: {
    category: 'AzureOpenAI'
    authType: 'ApiKey'
    target: aoaiRef.properties.endpoint
    credentials: {
      key: aoaiKeys.key1
    }
  }
}

output connectionId string = conn.id
output keySecretId string = aoaiKeySecret.id
