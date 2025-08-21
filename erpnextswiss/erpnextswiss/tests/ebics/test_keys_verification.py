#!/usr/bin/env python3
"""
Test to verify EBICS keys consistency
"""

import os
import json
import hashlib
from datetime import datetime

def check_keyring_files():
    """Check if keyring files exist and their status"""
    print("=" * 60)
    print("EBICS KEYS VERIFICATION")
    print("=" * 60)
    
    # Base path for EBICS keys
    base_paths = [
        "/Users/jeremy/GitHub/erpnextswiss/erpnextswiss/erpnextswiss/ebics_keys",
        "/Users/jeremy/GitHub/erpnextswiss/sites/site1.local/private/files/ebics_keys",
        "~/frappe-bench/sites/dmis.neoffice.me/private/files/ebics_keys"
    ]
    
    for base_path in base_paths:
        expanded_path = os.path.expanduser(base_path)
        if os.path.exists(expanded_path):
            print(f"\n📁 Found keys directory: {expanded_path}")
            
            # List all subdirectories (connections)
            for conn_dir in os.listdir(expanded_path):
                conn_path = os.path.join(expanded_path, conn_dir)
                if os.path.isdir(conn_path):
                    print(f"\n  Connection: {conn_dir}")
                    
                    # Check for keyring.json
                    keyring_path = os.path.join(conn_path, "keyring.json")
                    if os.path.exists(keyring_path):
                        stat = os.stat(keyring_path)
                        modified = datetime.fromtimestamp(stat.st_mtime)
                        size = stat.st_size
                        
                        print(f"    ✅ keyring.json found")
                        print(f"       Size: {size} bytes")
                        print(f"       Modified: {modified}")
                        
                        # Try to read and analyze
                        try:
                            with open(keyring_path, 'r') as f:
                                content = f.read()
                                if content:
                                    # Check if it's encrypted or plain JSON
                                    if content.startswith('{'):
                                        data = json.loads(content)
                                        print(f"       Format: Plain JSON")
                                        if 'keys' in data:
                                            print(f"       Keys found in data")
                                    else:
                                        print(f"       Format: Encrypted")
                                        print(f"       First 50 chars: {content[:50]}")
                                else:
                                    print(f"       ⚠️  File is empty!")
                        except Exception as e:
                            print(f"       ❌ Error reading: {e}")
                    else:
                        print(f"    ❌ No keyring.json found")
                    
                    # Check for other key files
                    for file in os.listdir(conn_path):
                        if file != "keyring.json" and not file.startswith('.'):
                            file_path = os.path.join(conn_path, file)
                            if os.path.isfile(file_path):
                                size = os.path.getsize(file_path)
                                print(f"    📄 {file} ({size} bytes)")

def check_error_codes():
    """Explain EBICS error codes"""
    print("\n" + "=" * 60)
    print("EBICS ERROR CODES EXPLANATION")
    print("=" * 60)
    
    errors = {
        "091002": "User not activated - Bank hasn't processed INI letter yet",
        "061001": "Authentication failed - Keys don't match what bank has",
        "061002": "Authentication failed - Invalid signature",
        "091010": "Bank keys already exist - HPB was already done",
        "091116": "Order data not found - No data available for download"
    }
    
    for code, meaning in errors.items():
        print(f"\n{code}: {meaning}")
    
    print("\n" + "=" * 60)
    print("YOUR CURRENT ERROR: 061001")
    print("=" * 60)
    print("""
This means the bank has your user activated BUT:
1. The keys being used don't match what was sent in INI/HIA
2. Possible causes:
   - Keys were regenerated after sending INI/HIA
   - Wrong keyring is being loaded
   - Keys weren't properly saved after generation
   
SOLUTION:
1. Check if keys were regenerated (look at timestamps)
2. If keys were regenerated, you need to:
   - Send new INI/HIA to bank
   - Get new INI letter
   - Have bank re-activate with new keys
3. OR reset connection and start fresh
""")

def suggest_fix():
    """Suggest how to fix the issue"""
    print("\n" + "=" * 60)
    print("RECOMMENDED ACTIONS")
    print("=" * 60)
    print("""
1. First, fix the "(No connection)" issue:
   - Make sure you're selecting a connection in the Control Panel
   - The connection name should appear in logs

2. For error 061001, you have two options:

   Option A: Reset and start fresh
   - Reset the EBICS connection
   - Generate new keys
   - Send new INI/HIA
   - Generate new INI letter
   - Send to bank for re-activation

   Option B: Check if existing keys match
   - Verify keyring.json hasn't been modified after activation
   - Ensure the correct keyring is being loaded
   - Check that keys weren't regenerated
""")

if __name__ == "__main__":
    check_keyring_files()
    check_error_codes()
    suggest_fix()