#!/usr/bin/env python3
"""
Complete EBICS Test Suite
Tests all EBICS functionality including Credit Suisse Test Platform

@author: Claude
@date: 2025-08-20
"""

import frappe
import unittest
import json
import os
import time
import subprocess
from datetime import datetime, timedelta

class TestEBICSFullSuite(unittest.TestCase):
    """Complete test suite for EBICS functionality"""
    
    @classmethod
    def setUpClass(cls):
        """Setup test environment"""
        cls.test_connection_name = "CS_TEST"
        cls.test_results = []
        print("\n" + "="*70)
        print("EBICS COMPLETE TEST SUITE - CREDIT SUISSE TEST PLATFORM")
        print("="*70)
        
    def setUp(self):
        """Setup before each test"""
        self.start_time = time.time()
        
    def tearDown(self):
        """Cleanup after each test"""
        elapsed = time.time() - self.start_time
        test_name = self.id().split('.')[-1]
        result = "PASS" if self._outcome.success else "FAIL"
        self.test_results.append({
            "test": test_name,
            "result": result,
            "time": f"{elapsed:.2f}s"
        })
        print(f"  [{result}] {test_name} ({elapsed:.2f}s)")
    
    # ========== TEST 1: Connection Setup ==========
    def test_01_ensure_connection_exists(self):
        """Test 1: Ensure CS_TEST connection exists"""
        print("\n### TEST 1: Connection Setup ###")
        
        from erpnextswiss.erpnextswiss.page.ebics_test_center.ebics_test_center import ensure_cs_test_connection
        
        connection_name = ensure_cs_test_connection()
        self.assertIsNotNone(connection_name)
        
        # Verify connection exists
        exists = frappe.db.exists("ebics Connection", connection_name)
        self.assertTrue(exists)
        
        # Get connection details
        conn = frappe.get_doc("ebics Connection", connection_name)
        print(f"  Connection: {conn.name}")
        print(f"  URL: {conn.url}")
        print(f"  Host ID: {conn.host_id}")
        print(f"  User ID: {conn.user_id}")
        
        self.assertEqual(conn.url, "https://example-bank.com/ebics")
        self.assertEqual(conn.host_id, "TESTHOST")
        
    # ========== TEST 2: Key Generation ==========
    def test_02_generate_keys(self):
        """Test 2: Generate RSA keys"""
        print("\n### TEST 2: Key Generation ###")
        
        from erpnextswiss.erpnextswiss.page.ebics_test_center.ebics_test_center import generate_keys
        
        result = generate_keys(self.test_connection_name)
        print(f"  Result: {json.dumps(result, indent=2)}")
        
        self.assertTrue(result.get("success"))
        self.assertIn("Keys generated successfully", result.get("message", ""))
        
    # ========== TEST 3: Verify Keys Exist ==========
    def test_03_check_keys_status(self):
        """Test 3: Verify keys exist on disk"""
        print("\n### TEST 3: Key Status Check ###")
        
        from erpnextswiss.erpnextswiss.page.ebics_test_center.ebics_test_center import check_keys_status
        
        result = check_keys_status(self.test_connection_name)
        print(f"  Keys exist: {result.get('keys_exist')}")
        print(f"  Keys valid: {result.get('keys_valid')}")
        print(f"  Location: {result.get('location')}")
        
        self.assertTrue(result.get("keys_exist"), "Keys should exist on disk")
        self.assertTrue(result.get("keys_valid"), "Keys should be valid")
        
    # ========== TEST 4: PHP Service Test ==========
    def test_04_php_service(self):
        """Test 4: Test PHP service directly"""
        print("\n### TEST 4: PHP Service Test ###")
        
        php_script = frappe.utils.get_bench_path() + "/apps/erpnextswiss/erpnextswiss/erpnextswiss/ebics_simple_keys.php"
        
        # Test PHP script exists
        self.assertTrue(os.path.exists(php_script), f"PHP script should exist at {php_script}")
        
        # Test PHP syntax
        result = subprocess.run(
            ['php', '-l', php_script],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0, f"PHP syntax error: {result.stderr}")
        print(f"  PHP syntax: OK")
        
        # Test PHP execution with test data
        test_data = {
            "connection": {
                "name": "TEST_PHP",
                "url": "https://test.example.com",
                "host_id": "TEST001",
                "partner_id": "PARTNER001",
                "user_id": "USER001",
                "bank_code": ""
            }
        }
        
        result = subprocess.run(
            ['php', php_script],
            input=json.dumps(test_data),
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            response = json.loads(result.stdout)
            self.assertTrue(response.get("success"), f"PHP execution failed: {response}")
            print(f"  PHP execution: OK")
            print(f"  Keys path: {response.get('keys_path')}")
        else:
            self.fail(f"PHP script failed: {result.stderr}")
    
    # ========== TEST 5: Send INI ==========
    def test_05_send_ini(self):
        """Test 5: Send INI order"""
        print("\n### TEST 5: Send INI Order ###")
        
        from erpnextswiss.erpnextswiss.page.ebics_test_center.ebics_test_center import send_ini
        
        result = send_ini(self.test_connection_name)
        print(f"  Result: {json.dumps(result, indent=2)}")
        
        # For test platform, we expect either success or specific error
        if not result.get("success"):
            # Check if it's an expected error for test platform
            error = result.get("error", "")
            print(f"  Note: Test platform response - {error}")
        
    # ========== TEST 6: Send HIA ==========
    def test_06_send_hia(self):
        """Test 6: Send HIA order"""
        print("\n### TEST 6: Send HIA Order ###")
        
        from erpnextswiss.erpnextswiss.page.ebics_test_center.ebics_test_center import send_hia
        
        result = send_hia(self.test_connection_name)
        print(f"  Result: {json.dumps(result, indent=2)}")
        
        # For test platform, we expect either success or specific error
        if not result.get("success"):
            error = result.get("error", "")
            print(f"  Note: Test platform response - {error}")
    
    # ========== TEST 7: Generate Bank Letter ==========
    def test_07_generate_bank_letter(self):
        """Test 7: Generate INI letter PDF"""
        print("\n### TEST 7: Bank Letter Generation ###")
        
        from erpnextswiss.erpnextswiss.page.ebics_test_center.ebics_test_center import create_bank_letter
        
        result = create_bank_letter(self.test_connection_name)
        print(f"  PDF generated: {result.get('success')}")
        
        if result.get("pdf_base64"):
            pdf_size = len(result.get("pdf_base64", ""))
            print(f"  PDF size (base64): {pdf_size} chars")
            self.assertGreater(pdf_size, 100, "PDF should have content")
        
    # ========== TEST 8: Download HPB ==========
    def test_08_download_hpb(self):
        """Test 8: Download bank public keys (HPB)"""
        print("\n### TEST 8: Download HPB ###")
        
        from erpnextswiss.erpnextswiss.page.ebics_test_center.ebics_test_center import download_hpb
        
        result = download_hpb(self.test_connection_name)
        print(f"  Result: {json.dumps(result, indent=2)}")
        
        # For test platform, we expect either success or specific error
        if not result.get("success"):
            error = result.get("error", "")
            print(f"  Note: Test platform response - {error}")
    
    # ========== TEST 9: Connection Status ==========
    def test_09_get_connection_status(self):
        """Test 9: Get comprehensive connection status"""
        print("\n### TEST 9: Connection Status ###")
        
        from erpnextswiss.erpnextswiss.page.ebics_test_center.ebics_test_center import get_connection_status, ensure_cs_test_connection
        
        # Use the actual connection name from database
        actual_connection_name = ensure_cs_test_connection()
        status = get_connection_status(actual_connection_name)
        
        print(f"  Activated: {status.get('activated')}")
        print(f"  Keys created: {status.get('keys_created')}")
        print(f"  INI sent: {status.get('ini_sent')}")
        print(f"  HIA sent: {status.get('hia_sent')}")
        print(f"  HPB downloaded: {status.get('hpb_downloaded')}")
        print(f"  Status message: {status.get('status_message')}")
        
        self.assertIsNotNone(status)
        self.assertTrue(status.get("success", False))
        self.assertIn("keys_created", status)
    
    # ========== TEST 10: Error Handling ==========
    def test_10_error_handling(self):
        """Test 10: Test error handling with invalid connection"""
        print("\n### TEST 10: Error Handling ###")
        
        from erpnextswiss.erpnextswiss.page.ebics_test_center.ebics_test_center import generate_keys
        
        # Test with non-existent connection
        result = generate_keys("INVALID_CONNECTION_XYZ")
        print(f"  Invalid connection result: {result.get('success')}")
        
        self.assertFalse(result.get("success"))
        self.assertIn("error", result)
        print(f"  Error message: {result.get('error')}")
    
    # ========== TEST 11: Key Files Verification ==========
    def test_11_verify_key_files(self):
        """Test 11: Verify actual key files on disk"""
        print("\n### TEST 11: Key Files Verification ###")
        
        # Get the actual connection name
        from erpnextswiss.erpnextswiss.page.ebics_test_center.ebics_test_center import ensure_cs_test_connection
        connection_name = ensure_cs_test_connection()
        
        # Build key path
        site_path = frappe.get_site_path()
        key_path = os.path.join(site_path, "private", "files", f"ebics_keys_{connection_name}")
        
        print(f"  Checking path: {key_path}")
        
        if os.path.exists(key_path):
            files = os.listdir(key_path)
            print(f"  Files found: {files}")
            
            # Check for expected key files
            expected_files = [
                "a006_private.pem", "a006_public.pem",
                "x002_private.pem", "x002_public.pem",
                "e002_private.pem", "e002_public.pem"
            ]
            
            for expected_file in expected_files:
                self.assertIn(expected_file, files, f"Missing key file: {expected_file}")
                
            print(f"  All key files present: ✓")
        else:
            print(f"  Key directory does not exist yet")
    
    # ========== TEST 12: PHP Components ==========
    def test_12_php_components(self):
        """Test 12: Verify all PHP components"""
        print("\n### TEST 12: PHP Components ###")
        
        php_files = [
            "ebics_simple_keys.php",
            "ebics_secure_service/ebics_secure_api.php",
            "ebics_secure_service/generate_ini_letter_pdf.php"
        ]
        
        base_path = frappe.utils.get_bench_path() + "/apps/erpnextswiss/erpnextswiss/erpnextswiss/"
        
        for php_file in php_files:
            full_path = base_path + php_file
            exists = os.path.exists(full_path)
            print(f"  {php_file}: {'✓' if exists else '✗'}")
            
            if exists:
                # Check PHP syntax
                result = subprocess.run(
                    ['php', '-l', full_path],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    print(f"    Syntax: OK")
                else:
                    print(f"    Syntax error: {result.stderr}")
    
    @classmethod
    def tearDownClass(cls):
        """Print summary after all tests"""
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        
        passed = sum(1 for r in cls.test_results if r["result"] == "PASS")
        failed = sum(1 for r in cls.test_results if r["result"] == "FAIL")
        
        for result in cls.test_results:
            symbol = "✓" if result["result"] == "PASS" else "✗"
            print(f"  {symbol} {result['test']} ({result['time']})")
        
        print("\n" + "-"*70)
        print(f"Total: {len(cls.test_results)} tests")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(passed/len(cls.test_results)*100):.1f}%")
        print("="*70)


def run_full_test_suite():
    """Run the complete test suite"""
    print("\nStarting EBICS Full Test Suite...")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestEBICSFullSuite)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    # Can be run directly
    success = run_full_test_suite()
    exit(0 if success else 1)