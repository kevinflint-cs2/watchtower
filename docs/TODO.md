# TODOs
- [x] Handle different environments (dev and prod maybe preprod)
- [x] ./infra/main.bicep: LLM is created before Azure AI Foundry
- [x] Add needed az providers for cognitive services and machine learning services
- [x] Add poe sequence task of pushing code to github
- [x] Add tool to scan for secrets in github code
- [ ] ./infra/modules/key-vault.bicep:Purge protection is causing issues during testing, removing for now, later need to disable in dev and enable in prod
- [ ] In general I would like to see what I can do to improve securing my resources