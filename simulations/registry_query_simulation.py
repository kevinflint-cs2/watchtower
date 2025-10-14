#!/usr/bin/env python3
"""
MITRE ATT&CK T1012 - Query Registry Simulation
Simulates suspicious registry queries commonly used for reconnaissance and persistence.
"""

import os
import json
import subprocess
import tempfile
from datetime import datetime

def simulate_registry_reconnaissance():
    """Simulate T1012 - Registry reconnaissance"""
    print("[SIMULATION] T1012 - Query Registry")
    print("=" * 50)
    
    # Common registry keys queried by attackers
    suspicious_registry_queries = [
        # System information gathering
        "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion",
        "HKLM\\SYSTEM\\CurrentControlSet\\Services",
        "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall",
        
        # Security software detection
        "HKLM\\SOFTWARE\\Microsoft\\Windows Defender",
        "HKLM\\SOFTWARE\\McAfee",
        "HKLM\\SOFTWARE\\Symantec",
        
        # User information
        "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\UserAssist",
        "HKLM\\SAM\\SAM\\Domains\\Account\\Users",
        
        # Network configuration
        "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters",
        "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\NetworkList",
        
        # Startup programs
        "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run",
        "HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run"
    ]
    
    temp_dir = tempfile.mkdtemp(prefix="mitre_t1012_")
    
    incident_data = {
        "timestamp": datetime.now().isoformat(),
        "technique_id": "T1012",
        "technique_name": "Query Registry",
        "tactic": "Discovery",
        "severity": "MEDIUM",
        "registry_queries": suspicious_registry_queries,
        "process_name": "reg.exe",
        "parent_process": "cmd.exe",
        "command_patterns": []
    }
    
    # Simulate registry query commands
    commands = []
    for reg_key in suspicious_registry_queries:
        cmd = f'reg query "{reg_key}"'
        commands.append(cmd)
        print(f"[ALERT] Suspicious registry query: {cmd}")
    
    incident_data["command_patterns"] = commands
    
    # Create fake registry export
    fake_export = os.path.join(temp_dir, "system_recon.reg")
    with open(fake_export, "w") as f:
        f.write("Windows Registry Editor Version 5.00\n\n")
        f.write("[HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion]\n")
        f.write('"ProductName"="Microsoft Windows 10 Pro"\n')
        f.write('"BuildLab"="19041.vb_release.191206-1406"\n')
    
    print(f"[ALERT] Registry data exported to: {fake_export}")
    
    incident_file = os.path.join(temp_dir, "t1012_registry_incident.json")
    with open(incident_file, "w") as f:
        json.dump(incident_data, f, indent=2)
    
    return incident_file

def simulate_persistence_registry_modification():
    """Simulate registry modification for persistence"""
    print("\n[SIMULATION] Registry Persistence Attempt")
    print("=" * 50)
    
    persistence_keys = [
        "HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run",
        "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run",
        "HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\RunOnce"
    ]
    
    for key in persistence_keys:
        print(f'[ALERT] Persistence attempt: reg add "{key}" /v "FakeBackdoor" /d "C:\\temp\\backdoor.exe"')
    
    return persistence_keys

if __name__ == "__main__":
    print("🔍 MITRE ATT&CK T1012 - Registry Query Simulation\n")
    
    registry_incident = simulate_registry_reconnaissance()
    persistence_keys = simulate_persistence_registry_modification()
    
    print(f"\n✅ T1012 simulation complete!")
    print(f"📄 Registry incident: {registry_incident}")