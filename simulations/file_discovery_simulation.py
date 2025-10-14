#!/usr/bin/env python3
"""
MITRE ATT&CK T1083 - File and Directory Discovery Simulation
Simulates file system reconnaissance commonly used by attackers.
"""

import os
import json
import tempfile
from datetime import datetime

def simulate_file_discovery():
    """Simulate T1083 - File and Directory Discovery"""
    print("[SIMULATION] T1083 - File and Directory Discovery")
    print("=" * 50)
    
    # Common reconnaissance commands used by attackers
    discovery_commands = [
        # Directory listing
        "dir C:\\ /s /b",
        "dir C:\\Users /s /b",
        "dir C:\\Program Files /s /b",
        
        # Search for specific file types
        "dir C:\\*.docx /s /b",
        "dir C:\\*.pdf /s /b", 
        "dir C:\\*.xlsx /s /b",
        "dir C:\\*password* /s /b",
        "dir C:\\*config* /s /b",
        "dir C:\\*backup* /s /b",
        
        # Database and sensitive files
        "dir C:\\*.sql /s /b",
        "dir C:\\*.mdb /s /b",
        "dir C:\\*.pst /s /b",
        
        # System files
        "dir C:\\Windows\\System32\\config /b",
        "dir C:\\Windows\\repair /b",
        
        # Network shares
        "net share",
        "net use"
    ]
    
    temp_dir = tempfile.mkdtemp(prefix="mitre_t1083_")
    
    incident_data = {
        "timestamp": datetime.now().isoformat(),
        "technique_id": "T1083",
        "technique_name": "File and Directory Discovery",
        "tactic": "Discovery",
        "severity": "LOW",
        "discovery_commands": discovery_commands,
        "process_name": "cmd.exe",
        "indicators": [
            "Extensive directory enumeration",
            "Search for sensitive file types",
            "System file exploration",
            "Network share enumeration"
        ]
    }
    
    print("[INFO] Simulating systematic file discovery...")
    for i, cmd in enumerate(discovery_commands):
        print(f"[ALERT {i+1:02d}] Discovery command: {cmd}")
    
    # Simulate finding sensitive files
    sensitive_files_found = [
        "C:\\Users\\Admin\\Documents\\passwords.txt",
        "C:\\Backup\\database_backup_2024.sql",
        "C:\\Config\\app_config.xml",
        "C:\\Users\\Finance\\Documents\\financial_data.xlsx"
    ]
    
    print(f"\n[HIGH ALERT] Sensitive files discovered:")
    for file_path in sensitive_files_found:
        print(f"  📄 {file_path}")
    
    incident_data["sensitive_files_found"] = sensitive_files_found
    
    incident_file = os.path.join(temp_dir, "t1083_discovery_incident.json")
    with open(incident_file, "w") as f:
        json.dump(incident_data, f, indent=2)
    
    return incident_file

def simulate_network_share_discovery():
    """Simulate network share discovery"""
    print("\n[SIMULATION] Network Share Discovery")
    print("=" * 50)
    
    network_commands = [
        "net view",
        "net view /domain",
        "net share",
        "dir \\\\server01\\c$ /s /b",
        "dir \\\\dc01\\sysvol /s /b"
    ]
    
    for cmd in network_commands:
        print(f"[ALERT] Network discovery: {cmd}")
    
    return network_commands

if __name__ == "__main__":
    print("📂 MITRE ATT&CK T1083 - File Discovery Simulation\n")
    
    discovery_incident = simulate_file_discovery()
    network_commands = simulate_network_share_discovery()
    
    print(f"\n✅ T1083 simulation complete!")
    print(f"📄 Discovery incident: {discovery_incident}")