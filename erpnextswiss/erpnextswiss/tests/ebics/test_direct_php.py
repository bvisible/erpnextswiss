#!/usr/bin/env python
"""
Direct PHP Service Test
Tests the PHP EBICS service directly without going through Python manager

@author: Claude
@date: 2025-08-20
"""

import subprocess
import json
import hashlib
import hmac
import time
import os
import secrets
import frappe


def test_php_service_direct(action: str = "HPB", params: dict = None):
    """
    Test the PHP EBICS service directly
    
    Args:
        action: EBICS action to test
        params: Parameters for the action
    """
    
    print("=" * 70)
    print("DIRECT PHP SERVICE TEST")
    print(f"Testing action: {action}")
    print("=" * 70)
    
    # Default params for Credit Suisse Test
    if params is None:
        params = {
            "connection_name": "Credit Suisse Test Platform",
            "bank_url": "https://cs-ebics-service-test.credit-suisse.com/ebics/ebics",
            "host_id": "CSCHZZ12",
            "partner_id": "1234",
            "user_id": "USER1",
            "ebics_version": "H005",
            "is_certified": False,
            "password": "test123"
        }
    
    # Path to PHP service
    php_service = os.path.join(
        frappe.utils.get_bench_path(),
        "apps/erpnextswiss/erpnextswiss/erpnextswiss/ebics_service/unified_ebics_service.php"
    )
    
    # Generate security key
    secret_key = secrets.token_hex(32)
    
    # Prepare request
    request = {
        "action": action,
        "params": params,
        "timestamp": int(time.time()),
        "nonce": secrets.token_hex(16)
    }
    
    print(f"\n1. Request preparation:")
    print(f"   - Action: {action}")
    print(f"   - Connection: {params.get('connection_name')}")
    print(f"   - Bank URL: {params.get('bank_url')}")
    
    # Calculate signature
    request_json = json.dumps(request, sort_keys=True, separators=(',', ':'))
    signature = hmac.new(
        secret_key.encode(),
        request_json.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Add signature to request
    request["signature"] = signature
    
    # Prepare environment
    env = os.environ.copy()
    env["EBICS_INTERNAL_SECRET"] = secret_key
    env["FRAPPE_SITE"] = frappe.local.site
    env["FRAPPE_BENCH_PATH"] = frappe.utils.get_bench_path()
    env["FRAPPE_SITE_PATH"] = frappe.utils.get_site_path()
    
    # Send request
    final_request = json.dumps(request, separators=(',', ':'))
    
    print(f"\n2. Sending request to PHP service...")
    print(f"   - PHP script: {php_service}")
    
    # Execute PHP script
    try:
        result = subprocess.run(
            ['php', php_service],
            input=final_request,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env=env
        )
        
        print(f"\n3. Response analysis:")
        print(f"   - Return code: {result.returncode}")
        
        if result.returncode != 0:
            print(f"   ✗ PHP execution failed")
            print(f"   - STDERR: {result.stderr[:500]}")
            print(f"   - STDOUT: {result.stdout[:500]}")
            return False
            
        else:
            # Parse response
            try:
                response = json.loads(result.stdout)
                
                # Extract data from response
                if 'data' in response:
                    data = response['data']
                    
                    print(f"   - Success: {data.get('success')}")
                    
                    if data.get('success'):
                        print(f"   - Message: {data.get('message')}")
                        
                        # Show additional data based on action
                        if action == 'GENERATE_KEYS' and 'keys' in data:
                            print(f"   - Keys generated:")
                            for key_type, key_hash in data['keys'].items():
                                print(f"     • {key_type}: {key_hash[:20]}...")
                                
                        elif action == 'GET_INI_LETTER' and data.get('format'):
                            print(f"   - Format: {data['format']}")
                            print(f"   - Filename: {data.get('filename')}")
                            
                        return True
                        
                    else:
                        print(f"   - Error: {data.get('error')}")
                        print(f"   - Code: {data.get('code')}")
                        print(f"   - Message: {data.get('message')}")
                        
                        # For HPB, failing with 091002 is expected
                        if action == 'HPB' and data.get('code') in ['091002', '061001', '061002']:
                            print(f"\n   ✓ This is expected behavior (not activated)")
                            return True
                        
                        return False
                else:
                    print(f"   ? Unexpected response structure:")
                    print(json.dumps(response, indent=2)[:500])
                    return False
                    
            except json.JSONDecodeError as e:
                print(f"   ✗ Failed to parse JSON response: {e}")
                print(f"   Output: {result.stdout[:500]}")
                return False
                
    except subprocess.TimeoutExpired:
        print(f"   ✗ PHP service timeout")
        return False
    except Exception as e:
        print(f"   ✗ Exception: {e}")
        return False


def run_php_tests():
    """Run a series of PHP service tests"""
    
    print("\nRunning PHP Service Test Suite")
    print("=" * 70)
    
    tests = [
        ("HPB", None),  # Test HPB with default params
        # Add more tests as needed
    ]
    
    passed = 0
    failed = 0
    
    for action, params in tests:
        print(f"\nTest: {action}")
        print("-" * 40)
        
        if test_php_service_direct(action, params):
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 70)
    print("PHP SERVICE TEST SUMMARY")
    print("-" * 40)
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")
    
    return failed == 0


if __name__ == "__main__":
    success = run_php_tests()
    exit(0 if success else 1)