#!/usr/bin/env python3
"""
Watchtower MITRE ATT&CK Integration
Generates incident data compatible with your Watchtower incident response system.
"""

import json
import os
from datetime import datetime, timedelta
import random

def generate_watchtower_incident(technique_id, technique_name, tactic, severity="MEDIUM", additional_data=None):
    """Generate incident data in format expected by Watchtower"""
    
    incident = {
        "incident_id": f"INC-{int(datetime.now().timestamp())}-{random.randint(1000, 9999)}",
        "timestamp": datetime.now().isoformat(),
        "detection_time": datetime.now().isoformat(),
        "source": "MITRE_SIMULATION",
        "alert_type": "BEHAVIORAL_DETECTION",
        
        # MITRE ATT&CK Information
        "mitre_attack": {
            "technique_id": technique_id,
            "technique_name": technique_name,
            "tactic": tactic,
            "matrix": "Enterprise"
        },
        
        # Risk Assessment
        "risk_assessment": {
            "severity": severity,
            "confidence": "HIGH",
            "impact": calculate_impact(tactic),
            "urgency": calculate_urgency(severity)
        },
        
        # Technical Details
        "technical_details": {
            "host_name": "SIMULATION-HOST-01",
            "user_name": "simulation_user",
            "process_name": "simulation_process.exe",
            "command_line": f"simulation command for {technique_id}",
            "parent_process": "cmd.exe",
            "network_connections": [],
            "file_operations": []
        },
        
        # Response Recommendations
        "response_actions": generate_response_actions(technique_id, tactic),
        
        # Timeline
        "timeline": generate_timeline(technique_id),
        
        # Status
        "status": "OPEN",
        "assigned_to": "watchtower_ai_agent",
        "escalation_required": severity in ["HIGH", "CRITICAL"]
    }
    
    # Add any additional data
    if additional_data:
        incident.update(additional_data)
    
    return incident

def calculate_impact(tactic):
    """Calculate impact based on MITRE tactic"""
    impact_mapping = {
        "Initial Access": "MEDIUM",
        "Execution": "HIGH", 
        "Persistence": "HIGH",
        "Privilege Escalation": "HIGH",
        "Defense Evasion": "MEDIUM",
        "Credential Access": "CRITICAL",
        "Discovery": "LOW",
        "Lateral Movement": "HIGH",
        "Collection": "MEDIUM",
        "Command and Control": "HIGH",
        "Exfiltration": "CRITICAL",
        "Impact": "CRITICAL"
    }
    return impact_mapping.get(tactic, "MEDIUM")

def calculate_urgency(severity):
    """Calculate urgency based on severity"""
    urgency_mapping = {
        "LOW": "P4",
        "MEDIUM": "P3", 
        "HIGH": "P2",
        "CRITICAL": "P1"
    }
    return urgency_mapping.get(severity, "P3")

def generate_response_actions(technique_id, tactic):
    """Generate response actions based on technique"""
    
    base_actions = [
        "Isolate affected system if confirmed malicious",
        "Collect forensic artifacts",
        "Review security logs for related activity",
        "Check for indicators of compromise (IOCs)",
        "Notify security team"
    ]
    
    technique_specific = {
        "T1003": [
            "Force password reset for affected accounts",
            "Review credential stores for compromise",
            "Check for suspicious authentication activity",
            "Scan for credential dumping tools"
        ],
        "T1059": [
            "Analyze PowerShell execution policies", 
            "Review script execution logs",
            "Check for encoded command execution",
            "Validate script sources"
        ],
        "T1012": [
            "Monitor registry access patterns",
            "Check for unauthorized registry modifications",
            "Review system configuration changes",
            "Validate registry key integrity"
        ],
        "T1083": [
            "Monitor file access patterns",
            "Check for data exfiltration attempts",
            "Review file system audit logs",
            "Assess sensitive data exposure"
        ]
    }
    
    actions = base_actions.copy()
    if technique_id in technique_specific:
        actions.extend(technique_specific[technique_id])
    
    return actions

def generate_timeline(technique_id):
    """Generate attack timeline"""
    now = datetime.now()
    
    timeline = [
        {
            "timestamp": (now - timedelta(minutes=30)).isoformat(),
            "event": "Initial suspicious activity detected",
            "source": "Behavioral Detection Engine"
        },
        {
            "timestamp": (now - timedelta(minutes=15)).isoformat(), 
            "event": f"MITRE technique {technique_id} indicators observed",
            "source": "MITRE ATT&CK Detection"
        },
        {
            "timestamp": now.isoformat(),
            "event": "Incident created and assigned to Watchtower AI",
            "source": "Incident Management System"
        }
    ]
    
    return timeline

def create_watchtower_alert_batch():
    """Create a batch of related alerts for testing"""
    
    techniques = [
        ("T1083", "File and Directory Discovery", "Discovery", "LOW"),
        ("T1012", "Query Registry", "Discovery", "MEDIUM"),
        ("T1059", "Command and Scripting Interpreter", "Execution", "HIGH"),
        ("T1003", "OS Credential Dumping", "Credential Access", "CRITICAL")
    ]
    
    alerts = []
    for technique_id, name, tactic, severity in techniques:
        incident = generate_watchtower_incident(technique_id, name, tactic, severity)
        alerts.append(incident)
    
    # Save batch file
    batch_file = f"/tmp/watchtower_alert_batch_{int(datetime.now().timestamp())}.json"
    with open(batch_file, "w") as f:
        json.dump({
            "batch_id": f"BATCH-{int(datetime.now().timestamp())}",
            "timestamp": datetime.now().isoformat(),
            "alert_count": len(alerts),
            "alerts": alerts
        }, f, indent=2)
    
    print(f"📦 Created Watchtower alert batch: {batch_file}")
    return batch_file

if __name__ == "__main__":
    print("🎯 Watchtower MITRE ATT&CK Integration")
    print("=" * 50)
    
    # Create sample incident
    incident = generate_watchtower_incident(
        "T1003", 
        "OS Credential Dumping", 
        "Credential Access", 
        "CRITICAL"
    )
    
    # Save individual incident
    incident_file = f"/tmp/watchtower_incident_{incident['incident_id']}.json"
    with open(incident_file, "w") as f:
        json.dump(incident, f, indent=2)
    
    print(f"📄 Sample incident created: {incident_file}")
    
    # Create alert batch
    batch_file = create_watchtower_alert_batch()
    
    print("\n✅ Watchtower integration files ready!")
    print("🔗 Import these into your Watchtower system for testing")