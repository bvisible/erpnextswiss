#!/usr/bin/env python3
"""
Direct test of EBICS workflow through PHP service
This test directly calls the PHP service to verify it's working
"""

import json
import subprocess
import os
import hashlib
import hmac
import time
import secrets

def test_php_service_direct():
    """Test PHP service directly"""
    print("=" * 60)
    print("DIRECT PHP SERVICE TEST")
    print("=" * 60)
    
    php_service = "/Users/jeremy/GitHub/erpnextswiss/erpnextswiss/erpnextswiss/ebics_service/unified_ebics_service.php"
    
    # Generate a test secret key
    secret_key = secrets.token_hex(32)
    
    # Test connection data (example bank)
    test_connection = {
        "connection_name": "TEST_BANK",
        "bank_url": "https://example-bank.com/ebics",
        "host_id": "TESTHOST",
        "partner_id": "TEST001",
        "user_id": "TEST001",
        "ebics_version": "H005",
        "is_certified": False,
        "password": "test_password"
    }
    
    # Test 1: Generate Keys
    print("\n1. Testing GENERATE_KEYS...")
    request = {
        "action": "GENERATE_KEYS",
        "params": test_connection,
        "timestamp": int(time.time()),
        "nonce": secrets.token_hex(16)
    }
    
    # Add signature
    request_json = json.dumps(request, sort_keys=True, separators=(',', ':'))
    signature = hmac.new(
        secret_key.encode(),
        request_json.encode(),
        hashlib.sha256
    ).hexdigest()
    request["signature"] = signature
    
    # Set environment
    env = os.environ.copy()
    env["EBICS_INTERNAL_SECRET"] = secret_key
    env["FRAPPE_SITE"] = "test.local"
    env["FRAPPE_BENCH_PATH"] = "/Users/jeremy/GitHub/erpnextswiss"
    
    try:
        result = subprocess.run(
            ['php', php_service],
            input=json.dumps(request),
            capture_output=True,
            text=True,
            timeout=30,
            env=env
        )
        
        if result.returncode != 0:
            print(f"  ❌ PHP error: {result.stderr}")
        else:
            try:
                response = json.loads(result.stdout)
                if response.get('data', {}).get('success'):
                    print("  ✅ Keys generated successfully")
                else:
                    print(f"  ⚠️  Response: {response.get('data', {}).get('message', 'Unknown')}")
            except json.JSONDecodeError:
                print(f"  ❌ Invalid JSON response: {result.stdout[:200]}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # Test 2: Send INI (will fail without keys, but tests the flow)
    print("\n2. Testing INI...")
    request = {
        "action": "INI",
        "params": test_connection,
        "timestamp": int(time.time()),
        "nonce": secrets.token_hex(16)
    }
    
    request_json = json.dumps(request, sort_keys=True, separators=(',', ':'))
    signature = hmac.new(
        secret_key.encode(),
        request_json.encode(),
        hashlib.sha256
    ).hexdigest()
    request["signature"] = signature
    
    try:
        result = subprocess.run(
            ['php', php_service],
            input=json.dumps(request),
            capture_output=True,
            text=True,
            timeout=30,
            env=env
        )
        
        if result.returncode != 0:
            print(f"  ❌ PHP error: {result.stderr}")
        else:
            try:
                response = json.loads(result.stdout)
                data = response.get('data', {})
                if data.get('code') == '091002':
                    print("  ✅ Got expected 091002 error (bank not activated)")
                    print(f"     Message: {data.get('message', '')}")
                elif data.get('success'):
                    print("  ✅ INI sent successfully")
                else:
                    print(f"  ⚠️  Response: {data.get('message', 'Unknown')}")
            except json.JSONDecodeError:
                print(f"  ❌ Invalid JSON response: {result.stdout[:200]}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("IMPORTANT NOTES:")
    print("=" * 60)
    print("1. Error 091002 is EXPECTED and CORRECT")
    print("   - It means the bank hasn't activated the account")
    print("   - This happens BEFORE the bank processes the INI letter")
    print("2. The connection name issue has been fixed in the code")
    print("3. Make sure all files are uploaded to the server")
    print("4. Clear cache and restart the server after upload")

if __name__ == "__main__":
    test_php_service_direct()