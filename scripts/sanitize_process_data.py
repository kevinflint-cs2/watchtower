#!/usr/bin/env python3
"""
Data Sanitization Script for Process Reconnaissance CSV
Replaces sensitive information with realistic fake data while preserving data structure.
"""

import csv
import hashlib
import random
import uuid
from datetime import datetime, timedelta

class DataSanitizer:
    def __init__(self):
        # Consistent mapping for repeated values
        self.name_mapping = {}
        self.domain_mapping = {}
        self.device_mapping = {}
        self.tenant_mapping = {}
        self.email_mapping = {}
        self.sid_mapping = {}
        self.object_id_mapping = {}
        self.device_id_mapping = {}
        
        # Fake data pools
        self.fake_names = [
            "jsmith", "mwilson", "achang", "rbrown", "sjohnson", "ldavis", 
            "kgarcia", "tmiller", "hwang", "jlee", "cmartin", "awhite",
            "dtaylor", "lthomas", "bclark", "nrodriguez", "plewis", "jwalker"
        ]
        
        self.fake_domains = [
            "contoso.com", "fabrikam.com", "northwind.com", "adventure-works.com",
            "litware.com", "woodgrove.com", "tailspin.com", "proseware.com"
        ]
        
        self.fake_companies = [
            "Contoso Electronics", "Fabrikam Manufacturing", "Northwind Traders",
            "Adventure Works Cycles", "Litware Insurance", "Woodgrove Bank"
        ]

    def generate_fake_tenant_id(self, original):
        """Generate consistent fake tenant ID"""
        if original not in self.tenant_mapping:
            self.tenant_mapping[original] = str(uuid.uuid4())
        return self.tenant_mapping[original]

    def generate_fake_name(self, original):
        """Generate consistent fake username"""
        if original not in self.name_mapping:
            # Use hash for consistency but pick from fake names
            hash_val = int(hashlib.md5(original.encode()).hexdigest()[:8], 16)
            self.name_mapping[original] = self.fake_names[hash_val % len(self.fake_names)]
        return self.name_mapping[original]

    def generate_fake_domain(self, original):
        """Generate consistent fake domain"""
        if original not in self.domain_mapping:
            hash_val = int(hashlib.md5(original.encode()).hexdigest()[:8], 16)
            self.domain_mapping[original] = self.fake_domains[hash_val % len(self.fake_domains)]
        return self.domain_mapping[original]

    def generate_fake_email(self, original):
        """Generate consistent fake email"""
        if original not in self.email_mapping:
            if '@' in original:
                username_part = original.split('@')[0]
                fake_username = self.generate_fake_name(username_part)
                fake_domain = self.generate_fake_domain(original.split('@')[1])
                self.email_mapping[original] = f"{fake_username}@{fake_domain}"
            else:
                self.email_mapping[original] = original
        return self.email_mapping[original]

    def generate_fake_device_name(self, original):
        """Generate consistent fake device name"""
        if original not in self.device_mapping:
            hash_val = int(hashlib.md5(original.encode()).hexdigest()[:8], 16)
            prefix = ["WKS", "LAP", "SRV", "DEV"][hash_val % 4]
            suffix = f"{hash_val % 1000:03d}"
            fake_domain = self.generate_fake_domain("example.com")
            self.device_mapping[original] = f"{prefix}-{suffix}.{fake_domain}"
        return self.device_mapping[original]

    def generate_fake_sid(self, original):
        """Generate consistent fake SID"""
        if original not in self.sid_mapping:
            if original.startswith("S-1-5-21-"):
                # Keep SID structure but randomize numbers
                hash_val = int(hashlib.md5(original.encode()).hexdigest()[:16], 16)
                domain_id1 = (hash_val % 4000000000) + 1000000000
                domain_id2 = ((hash_val >> 32) % 4000000000) + 1000000000  
                domain_id3 = ((hash_val >> 64) % 4000000000) + 1000000000
                rid = (hash_val % 900000) + 100000
                self.sid_mapping[original] = f"S-1-5-21-{domain_id1}-{domain_id2}-{domain_id3}-{rid}"
            else:
                self.sid_mapping[original] = original
        return self.sid_mapping[original]

    def generate_fake_object_id(self, original):
        """Generate consistent fake object ID (GUID)"""
        if original not in self.object_id_mapping:
            # Generate deterministic but fake GUID
            hash_val = hashlib.md5(original.encode()).hexdigest()
            fake_guid = f"{hash_val[:8]}-{hash_val[8:12]}-{hash_val[12:16]}-{hash_val[16:20]}-{hash_val[20:32]}"
            self.object_id_mapping[original] = fake_guid
        return self.object_id_mapping[original]

    def generate_fake_device_id(self, original):
        """Generate consistent fake device ID"""
        if original not in self.device_id_mapping:
            # Generate deterministic but fake device ID
            hash_val = hashlib.md5(original.encode()).hexdigest()
            self.device_id_mapping[original] = hash_val
        return self.device_id_mapping[original]

    def sanitize_file_path(self, path):
        """Sanitize file paths while preserving structure"""
        if not path or path in ["", "na"]:
            return path
            
        # Replace usernames in paths
        for original_name, fake_name in self.name_mapping.items():
            path = path.replace(original_name, fake_name)
            
        # Replace domain names in paths  
        for original_domain, fake_domain in self.domain_mapping.items():
            path = path.replace(original_domain, fake_domain)
            
        return path

    def sanitize_command_line(self, command):
        """Sanitize command lines while preserving structure"""
        if not command or command in ["", "na"]:
            return command
            
        # Replace usernames and domains in command lines
        for original_name, fake_name in self.name_mapping.items():
            command = command.replace(original_name, fake_name)
            
        for original_domain, fake_domain in self.domain_mapping.items():
            command = command.replace(original_domain, fake_domain)
            
        return command

    def sanitize_row(self, row):
        """Sanitize a single CSV row"""
        sanitized = row.copy()
        
        # Tenant ID
        if row.get('TenantId'):
            sanitized['TenantId'] = self.generate_fake_tenant_id(row['TenantId'])
            
        # Account information
        if row.get('AccountName') and row['AccountName'] != 'na':
            sanitized['AccountName'] = self.generate_fake_name(row['AccountName'])
            
        if row.get('AccountUpn') and row['AccountUpn'] != 'na':
            sanitized['AccountUpn'] = self.generate_fake_email(row['AccountUpn'])
            
        if row.get('AccountObjectId'):
            sanitized['AccountObjectId'] = self.generate_fake_object_id(row['AccountObjectId'])
            
        if row.get('AccountSid'):
            sanitized['AccountSid'] = self.generate_fake_sid(row['AccountSid'])
            
        # Device information
        if row.get('DeviceName'):
            sanitized['DeviceName'] = self.generate_fake_device_name(row['DeviceName'])
            
        if row.get('DeviceId'):
            sanitized['DeviceId'] = self.generate_fake_device_id(row['DeviceId'])
            
        # Initiating process account info
        if row.get('InitiatingProcessAccountName') and row['InitiatingProcessAccountName'] != 'na':
            sanitized['InitiatingProcessAccountName'] = self.generate_fake_name(row['InitiatingProcessAccountName'])
            
        if row.get('InitiatingProcessAccountUpn') and row['InitiatingProcessAccountUpn'] != 'na':
            sanitized['InitiatingProcessAccountUpn'] = self.generate_fake_email(row['InitiatingProcessAccountUpn'])
            
        if row.get('InitiatingProcessAccountObjectId'):
            sanitized['InitiatingProcessAccountObjectId'] = self.generate_fake_object_id(row['InitiatingProcessAccountObjectId'])
            
        if row.get('InitiatingProcessAccountSid'):
            sanitized['InitiatingProcessAccountSid'] = self.generate_fake_sid(row['InitiatingProcessAccountSid'])
            
        # File paths
        for path_field in ['FolderPath', 'InitiatingProcessFolderPath']:
            if row.get(path_field):
                sanitized[path_field] = self.sanitize_file_path(row[path_field])
                
        # Command lines
        for cmd_field in ['InitiatingProcessCommandLine', 'ProcessCommandLine']:
            if row.get(cmd_field):
                sanitized[cmd_field] = self.sanitize_command_line(row[cmd_field])
                
        return sanitized

def sanitize_csv_file(input_file, output_file):
    """Sanitize the entire CSV file"""
    sanitizer = DataSanitizer()
    
    print(f"🔄 Reading {input_file}...")
    
    with open(input_file, 'r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames
        
        sanitized_rows = []
        total_rows = 0
        
        for row in reader:
            total_rows += 1
            sanitized_row = sanitizer.sanitize_row(row)
            sanitized_rows.append(sanitized_row)
            
            # Progress indicator
            if total_rows % 100 == 0:
                print(f"  Processed {total_rows} rows...")
    
    print(f"✅ Processed {total_rows} total rows")
    print(f"🔄 Writing sanitized data to {output_file}...")
    
    with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sanitized_rows)
    
    print(f"✅ Sanitization complete!")
    print(f"📊 Summary:")
    print(f"  - Sanitized {len(sanitizer.name_mapping)} unique usernames")
    print(f"  - Sanitized {len(sanitizer.domain_mapping)} unique domains") 
    print(f"  - Sanitized {len(sanitizer.email_mapping)} unique email addresses")
    print(f"  - Sanitized {len(sanitizer.device_mapping)} unique device names")
    print(f"  - Sanitized {len(sanitizer.tenant_mapping)} unique tenant IDs")

if __name__ == "__main__":
    input_file = "src/data/processes_recon/processes.csv"
    output_file = "src/data/processes_recon/processes_sanitized.csv"
    
    sanitize_csv_file(input_file, output_file)
    
    print(f"\n📁 Original file: {input_file}")
    print(f"📁 Sanitized file: {output_file}")
    print(f"\n⚠️  Remember to use the sanitized file for any analysis or sharing!")