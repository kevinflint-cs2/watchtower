# MITRE ATT&CK Simulation Framework for Watchtower

This simulation framework provides safe, local simulations of common MITRE ATT&CK techniques to test your Watchtower incident response system.

## 🎯 Available Simulations

| Technique ID | Name | Tactic | Description |
|-------------|------|---------|-------------|
| **T1003** | OS Credential Dumping | Credential Access | Simulates Mimikatz-like credential extraction |
| **T1059** | Command and Scripting Interpreter | Execution | PowerShell and command-line abuse simulation |
| **T1012** | Query Registry | Discovery | Registry reconnaissance and persistence |
| **T1083** | File and Directory Discovery | Discovery | File system enumeration and sensitive data discovery |

## 🚀 Quick Start

### Run Individual Simulations

```bash
# List available simulations
python3 simulations/run_mitre_simulation.py --list

# Run specific technique simulation
python3 simulations/run_mitre_simulation.py --simulation credential_dump
python3 simulations/run_mitre_simulation.py --simulation command_execution
python3 simulations/run_mitre_simulation.py --simulation registry_query
python3 simulations/run_mitre_simulation.py --simulation file_discovery
```

### Run Complete Attack Chain

```bash
# Simulate realistic multi-stage attack
python3 simulations/run_mitre_simulation.py --attack-chain
```

### Generate Watchtower Incidents

```bash
# Create incident data for Watchtower
python3 simulations/watchtower_integration.py
```

## 📋 Simulation Details

### T1003 - OS Credential Dumping
- **Risk Level**: 🔴 Critical
- **Simulates**: Mimikatz credential extraction, LSASS memory access, registry credential theft
- **Artifacts Created**: Fake memory dumps, registry exports, process injection traces
- **Detection Points**: Suspicious process names, memory access patterns, file creation

### T1059 - Command and Scripting Interpreter  
- **Risk Level**: 🟡 High
- **Simulates**: PowerShell abuse, encoded commands, living-off-the-land techniques
- **Artifacts Created**: Suspicious command logs, encoded PowerShell execution
- **Detection Points**: Hidden execution, bypass attempts, web download patterns

### T1012 - Query Registry
- **Risk Level**: 🟡 Medium  
- **Simulates**: System reconnaissance, security software detection, persistence setup
- **Artifacts Created**: Registry query logs, system information exports
- **Detection Points**: Bulk registry access, sensitive key enumeration

### T1083 - File and Directory Discovery
- **Risk Level**: 🟢 Low-Medium
- **Simulates**: File system reconnaissance, sensitive data discovery
- **Artifacts Created**: Directory enumeration logs, file search patterns
- **Detection Points**: Systematic file access, sensitive file targeting

## 🛡️ Integration with Watchtower

### Incident Data Format

The simulations generate JSON incident data compatible with Watchtower:

```json
{
  "incident_id": "INC-1729123456-7890",
  "timestamp": "2025-10-14T10:30:00",
  "mitre_attack": {
    "technique_id": "T1003",
    "technique_name": "OS Credential Dumping",
    "tactic": "Credential Access"
  },
  "risk_assessment": {
    "severity": "CRITICAL",
    "confidence": "HIGH",
    "impact": "CRITICAL"
  },
  "response_actions": [
    "Force password reset for affected accounts",
    "Review credential stores for compromise"
  ]
}
```

### AI Agent Testing

Use these simulations to test your Watchtower AI agents:

1. **Triage Agent**: Test incident classification and prioritization
2. **Enrichment Agent**: Test evidence gathering and correlation
3. **Response Agent**: Test containment action recommendations

## 🔬 Testing Scenarios

### Basic Detection Testing
```bash
# Test individual technique detection
python3 simulations/credential_dump_simulation.py
```

### Advanced Attack Chain Testing
```bash  
# Test multi-stage attack handling
python3 simulations/run_mitre_simulation.py --attack-chain
```

### Batch Incident Testing
```bash
# Generate multiple related incidents
python3 simulations/watchtower_integration.py
```

## 🚨 Safety Notes

- ✅ All simulations are **SAFE** - no actual malware or system compromise
- ✅ Only creates **fake artifacts** and **log entries**
- ✅ No network traffic to external malicious sites
- ✅ No actual credential extraction or system modification
- ✅ Temporary files are created in `/tmp/` directories

## 📊 Expected Outputs

Each simulation generates:

1. **Console Output**: Real-time simulation alerts and status
2. **JSON Incident Files**: Structured incident data for Watchtower
3. **Artifact Files**: Fake malware artifacts and traces
4. **Timeline Data**: Attack progression timestamps

## 🎭 Customization

### Adding New Techniques

1. Create new simulation script in `/simulations/`
2. Follow existing pattern for incident generation
3. Add to `run_mitre_simulation.py` registry
4. Update README with technique details

### Modifying Severity Levels

Edit `watchtower_integration.py` to adjust:
- Risk calculations
- Response actions  
- Escalation triggers
- Timeline generation

## 🔍 Monitoring Integration

These simulations work with:
- **SIEM Systems**: Import JSON logs
- **EDR Tools**: Monitor file/process activity  
- **Watchtower AI**: Test agent responses
- **SOC Playbooks**: Validate response procedures

## 📈 Metrics and Analysis

Track your incident response effectiveness:
- Detection time (simulated vs actual)
- False positive rates
- Response action accuracy
- Escalation appropriateness

---

**Happy Testing! 🛡️**

Use these simulations to strengthen your Watchtower incident response capabilities and validate your security detection mechanisms.