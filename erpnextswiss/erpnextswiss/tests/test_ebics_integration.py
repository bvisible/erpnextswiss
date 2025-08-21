#!/usr/bin/env python3
"""
Test suite for EBICS integration
Run with: python -m pytest test_ebics_integration.py -v
"""

import json
import subprocess
import os
from datetime import datetime, timedelta
import time

class TestEBICSIntegration:
    """Test EBICS integration functions"""
    
    def __init__(self):
        self.base_path = "/Users/jeremy/GitHub/erpnextswiss"
        self.php_service = f"{self.base_path}/erpnextswiss/erpnextswiss/ebics_service/unified_ebics_service.php"
        self.test_connection = "test"  # Replace with actual test connection name
        self.results = []
    
    def run_ebics_command(self, action, params=None):
        """Execute an EBICS command through the PHP service"""
        request = {
            "action": action,
            "connection": self.test_connection,
            "params": params or {}
        }
        
        # Add authentication
        request["auth"] = {
            "timestamp": str(int(time.time())),
            "site": "prod.local"
        }
        
        # Create HMAC for authentication
        import hashlib
        import hmac
        secret = "test_secret"  # Should match server config
        message = f"{request['auth']['timestamp']}:{request['auth']['site']}"
        request["auth"]["hmac"] = hmac.new(
            secret.encode(), 
            message.encode(), 
            hashlib.sha256
        ).hexdigest()
        
        # Run PHP service
        try:
            result = subprocess.run(
                ["php", self.php_service],
                input=json.dumps(request),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.stdout:
                return json.loads(result.stdout)
            else:
                return {"error": result.stderr}
        except subprocess.TimeoutExpired:
            return {"error": "Command timed out"}
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON response: {e}", "stdout": result.stdout, "stderr": result.stderr}
        except Exception as e:
            return {"error": str(e)}
    
    def test_connection_status(self):
        """Test connection status check"""
        print("\n=== Testing Connection Status ===")
        result = self.run_ebics_command("status")
        self.results.append(("Connection Status", result))
        return result.get("success", False)
    
    def test_haa_order(self):
        """Test HAA (Available order types)"""
        print("\n=== Testing HAA Order ===")
        result = self.run_ebics_command("HAA")
        self.results.append(("HAA Order", result))
        return result.get("success", False)
    
    def test_htd_order(self):
        """Test HTD (Transaction details)"""
        print("\n=== Testing HTD Order ===")
        result = self.run_ebics_command("HTD")
        self.results.append(("HTD Order", result))
        return result.get("success", False)
    
    def test_hkd_order(self):
        """Test HKD (Customer properties)"""
        print("\n=== Testing HKD Order ===")
        result = self.run_ebics_command("HKD")
        self.results.append(("HKD Order", result))
        return result.get("success", False)
    
    def test_z53_download(self):
        """Test Z53 (camt.053 statement download)"""
        print("\n=== Testing Z53 Download ===")
        today = datetime.now()
        week_ago = today - timedelta(days=7)
        
        params = {
            "dateFrom": week_ago.strftime("%Y-%m-%d"),
            "dateTo": today.strftime("%Y-%m-%d")
        }
        
        result = self.run_ebics_command("Z53", params)
        self.results.append(("Z53 Download", result))
        return result.get("success", False)
    
    def test_z54_download(self):
        """Test Z54 (camt.052 intraday statement)"""
        print("\n=== Testing Z54 Download ===")
        today = datetime.now()
        
        params = {
            "dateFrom": today.strftime("%Y-%m-%d"),
            "dateTo": today.strftime("%Y-%m-%d")
        }
        
        result = self.run_ebics_command("Z54", params)
        self.results.append(("Z54 Download", result))
        return result.get("success", False)
    
    def test_ptk_order(self):
        """Test PTK (Transaction status)"""
        print("\n=== Testing PTK Order ===")
        today = datetime.now()
        week_ago = today - timedelta(days=7)
        
        params = {
            "dateFrom": week_ago.strftime("%Y-%m-%d"),
            "dateTo": today.strftime("%Y-%m-%d")
        }
        
        result = self.run_ebics_command("PTK", params)
        self.results.append(("PTK Order", result))
        return result.get("success", False)
    
    def run_all_tests(self):
        """Run all tests and generate report"""
        print("=" * 60)
        print("EBICS Integration Test Suite")
        print("=" * 60)
        
        tests = [
            self.test_connection_status,
            self.test_haa_order,
            self.test_htd_order,
            self.test_hkd_order,
            self.test_z53_download,
            self.test_z54_download,
            self.test_ptk_order
        ]
        
        passed = 0
        failed = 0
        
        for test in tests:
            try:
                if test():
                    print(f"✅ {test.__name__}: PASSED")
                    passed += 1
                else:
                    print(f"❌ {test.__name__}: FAILED")
                    failed += 1
            except Exception as e:
                print(f"❌ {test.__name__}: ERROR - {e}")
                failed += 1
        
        print("\n" + "=" * 60)
        print(f"Test Results: {passed} passed, {failed} failed")
        print("=" * 60)
        
        # Print detailed results
        print("\n=== Detailed Results ===")
        for test_name, result in self.results:
            print(f"\n{test_name}:")
            if isinstance(result, dict):
                if result.get("success"):
                    print("  Status: SUCCESS")
                else:
                    print(f"  Status: FAILED")
                    if "error" in result:
                        print(f"  Error: {result['error']}")
                    if "message" in result:
                        print(f"  Message: {result['message']}")
            else:
                print(f"  Result: {result}")
        
        return passed, failed

def main():
    """Main test runner"""
    tester = TestEBICSIntegration()
    
    # Check if we have a test connection configured
    print("Note: Make sure you have a test EBICS connection configured.")
    print("Update the 'test_connection' variable in this script if needed.\n")
    
    passed, failed = tester.run_all_tests()
    
    # Exit with appropriate code
    exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    main()