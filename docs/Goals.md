**docs/goals.md**
```md
# Goals & Non-Goals

## Primary Goal
Create an Agentic AI environment to repeatably build and test new features. 

## Goals
- [x] Deploy ChatGPT 4o Mini LLM in Azure Foundry Project
- [x] Create an AI Agent to interact with LLM model
- [ ] Add file to AI Agent to give additional contextual data for grounding
- [ ] Deploy a Logic App as Code to query AbuseIPDB, then connect to AI Agent
- [ ] Deploy a Function App as Code to query VT, then connect to AI Agent
- [ ] Build Function App as Code to push data into Log Analytics
- [ ] Deploy a Logic App as Code to query LAWs custom data, then connect to AI Agent

## Non-Goals
- None yet

## Roadmap (high level)
- Now: Create an AI Agent to interact with LLM model
- Next: Add file to AI Agent to give additional contextual data for grounding
- Later: Deploy a Logic App as Code to query AbuseIPDB, then connect to AI Agent

---

# 🔹 1. Advanced Agent Orchestration

* **Tool integration**: Attach tools like Azure Search, Cosmos DB, or custom APIs, and show agents reasoning over enterprise data.
* **Role specialization**: Build a multi-agent system where one agent handles data retrieval, another summarizes, another validates.
* **Agent collaboration patterns**: Implement supervisor-worker or debate patterns, and compare outcomes.

---

# 🔹 2. Enterprise Integration

* **Event-driven workflows**: Trigger agents from Service Bus/Event Grid when new data arrives.
* **SOAR/SIEM tie-in**: For your blue-team/SOC world — integrate an agent with Sentinel queries (`AzureDeveloperCliCredential` + KQL).
* **Power Automate / Logic Apps**: Connect an AI agent into business workflows for approvals, routing, ticketing.

---

# 🔹 3. Governance & Security

* **RBAC & Managed Identity**: Show how to run agents with *least privilege* using managed identities instead of secrets.
* **Data boundaries**: Configure prompt shields / content filters to demonstrate responsible AI use.
* **Auditability**: Log every interaction to Log Analytics for later forensic review.

---

# 🔹 4. Observability & Monitoring

* **Telemetry**: Pipe agent events to Application Insights. Build KQL dashboards showing latency, token usage, error rates.
* **Performance tuning**: Compare agent response quality across models (e.g., GPT-4o vs GPT-4o-mini) and optimize.
* **Feedback loops**: Store user ratings and fine-tune workflows based on reinforcement.

---

# 🔹 5. DevOps & Automation

* **Infra as Code**: Expand your Bicep + `azd` setup to auto-provision multiple Foundry accounts/projects/agents.
* **Testing harness**: Write automated smoke tests for agents (prompt → expected response).
* **Release strategy**: Demonstrate semantic-release style versioning for agent configs and infra.

---

# 🔹 6. Customization & Extensibility

* **Custom tools**: Build Python tool plugins (e.g., database query executor, ticket system connector).
* **Memory / state**: Show long-running context or external memory integration (Redis, Cosmos).
* **Evaluation**: Use Azure Prompt Flow to benchmark agents across test datasets.

---

# 🔹 7. Showcase Scenarios

* **Security Copilot-like agent**: A multi-agent system that takes IOCs, hunts in Sentinel, summarizes findings, and drafts a report.
* **Data analysis agent**: One agent ingests CSVs from Blob, another cleans/normalizes, another generates insights with charts.
* **Knowledge-base Q\&A**: Hook an agent to Azure Cognitive Search and expose it as an internal chatbot.

---

