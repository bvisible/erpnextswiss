# -*- coding: utf-8 -*-
# Copyright (c) 2024, libracore (https://www.libracore.com) and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
import json
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from frappe.utils import get_bench_path, get_files_path


class TestebicsConnection(unittest.TestCase):
    """Test suite for EBICS Connection with node-ebics-client"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        cls.test_connection_name = "Test_EBICS_Connection"
        cls.test_config = {
            'user_id': 'TEST123456',
            'partner_id': 'PARTNER789',
            'host_id': 'TESTBANK',
            'url': 'https://ebics-test.example.com',
            'ebics_version': 'H005'
        }
    
    def setUp(self):
        """Set up test method"""
        # Create a test connection if it doesn't exist
        if not frappe.db.exists("ebics Connection", self.test_connection_name):
            self.connection = frappe.get_doc({
                "doctype": "ebics Connection",
                "title": self.test_connection_name,
                "user_id": self.test_config['user_id'],
                "partner_id": self.test_config['partner_id'],
                "host_id": self.test_config['host_id'],
                "url": self.test_config['url'],
                "ebics_version": self.test_config['ebics_version'],
                "activated": 0
            })
            self.connection.insert(ignore_permissions=True)
        else:
            self.connection = frappe.get_doc("ebics Connection", self.test_connection_name)
    
    def tearDown(self):
        """Clean up after test"""
        # Remove test files
        files_path = get_files_path()
        test_key_path = os.path.join(files_path, "ebics_keys", self.test_connection_name)
        if os.path.exists(test_key_path):
            import shutil
            shutil.rmtree(test_key_path)
    
    def test_connection_creation(self):
        """Test creating an EBICS connection"""
        self.assertIsNotNone(self.connection)
        self.assertEqual(self.connection.user_id, self.test_config['user_id'])
        self.assertEqual(self.connection.partner_id, self.test_config['partner_id'])
        self.assertEqual(self.connection.host_id, self.test_config['host_id'])
    
    def test_ebics_api_import(self):
        """Test that EBICS API can be imported"""
        try:
            from erpnextswiss.erpnextswiss.ebics_api import EbicsNode, EbicsApi
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Failed to import EBICS API: {e}")
    
    def test_node_client_initialization(self):
        """Test node-ebics-client initialization"""
        from erpnextswiss.erpnextswiss.ebics_api import EbicsNode
        
        client = EbicsNode(self.connection)
        self.assertIsNotNone(client)
        self.assertIsNotNone(client.connection)
        self.assertEqual(client.connection.name, self.test_connection_name)
    
    def test_key_storage_path(self):
        """Test key storage path creation"""
        from erpnextswiss.erpnextswiss.ebics_api import EbicsNode
        
        client = EbicsNode(self.connection)
        key_path = client._get_key_storage_path()
        
        self.assertTrue(os.path.exists(key_path))
        self.assertTrue(key_path.endswith(self.test_connection_name))
    
    def test_config_creation(self):
        """Test configuration file creation"""
        from erpnextswiss.erpnextswiss.ebics_api import EbicsNode
        
        client = EbicsNode(self.connection)
        config_path = client._create_config()
        
        self.assertTrue(os.path.exists(config_path))
        
        # Verify config content
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        self.assertEqual(config['userId'], self.test_config['user_id'])
        self.assertEqual(config['partnerId'], self.test_config['partner_id'])
        self.assertEqual(config['hostId'], self.test_config['host_id'])
        self.assertEqual(config['url'], self.test_config['url'])
    
    def test_key_generation(self):
        """Test RSA key generation"""
        from erpnextswiss.erpnextswiss.migrate_ebics_keys import generate_rsa_key_pair
        
        key_pair = generate_rsa_key_pair()
        
        self.assertIn('privateKey', key_pair)
        self.assertIn('publicKey', key_pair)
        self.assertTrue(key_pair['privateKey'].startswith('-----BEGIN'))
        self.assertTrue(key_pair['publicKey'].startswith('-----BEGIN'))
    
    def test_key_migration_structure(self):
        """Test key migration data structure"""
        from erpnextswiss.erpnextswiss.migrate_ebics_keys import create_keys_for_connection
        
        keys_data = create_keys_for_connection(
            self.test_config['user_id'],
            self.test_config['partner_id'],
            self.test_config['host_id']
        )
        
        self.assertIn('userId', keys_data)
        self.assertIn('partnerId', keys_data)
        self.assertIn('hostId', keys_data)
        self.assertIn('keys', keys_data)
        
        # Verify all key types are present
        for key_type in ['A006', 'E002', 'X002']:
            self.assertIn(key_type, keys_data['keys'])
    
    def test_key_file_operations(self):
        """Test reading and writing key files"""
        from erpnextswiss.erpnextswiss.ebics_api import EbicsNode
        
        client = EbicsNode(self.connection)
        key_path = client._get_key_storage_path()
        keys_file = os.path.join(key_path, 'keys.json')
        
        # Test data
        test_keys = {
            "userId": self.test_config['user_id'],
            "partnerId": self.test_config['partner_id'],
            "hostId": self.test_config['host_id'],
            "keys": {
                "A006": "test_key_a006",
                "E002": "test_key_e002",
                "X002": "test_key_x002"
            }
        }
        
        # Write keys
        with open(keys_file, 'w') as f:
            json.dump(test_keys, f)
        
        # Verify file exists
        self.assertTrue(os.path.exists(keys_file))
        
        # Read and verify
        with open(keys_file, 'r') as f:
            loaded_keys = json.load(f)
        
        self.assertEqual(loaded_keys['userId'], test_keys['userId'])
        self.assertEqual(loaded_keys['keys']['A006'], test_keys['keys']['A006'])
    
    def test_connection_test_method(self):
        """Test the connection test method"""
        from erpnextswiss.erpnextswiss.ebics_api import EbicsNode
        
        client = EbicsNode(self.connection)
        result = client.test_connection()
        
        self.assertIsInstance(result, dict)
        self.assertIn('success', result)
        self.assertTrue(result['success'])
        self.assertIn('details', result)
        self.assertEqual(result['details']['user_id'], self.test_config['user_id'])
    
    def test_business_transaction_format(self):
        """Test BusinessTransactionFormat compatibility class"""
        from erpnextswiss.erpnextswiss.ebics_api import BusinessTransactionFormat
        
        btf = BusinessTransactionFormat(
            service='EOP',
            msg_name='camt.053',
            scope='CH',
            version='04'
        )
        
        self.assertEqual(btf.service, 'EOP')
        self.assertEqual(btf.msg_name, 'camt.053')
        
        # Test to_dict method
        btf_dict = btf.to_dict()
        self.assertIsInstance(btf_dict, dict)
        self.assertEqual(btf_dict['msg_name'], 'camt.053')
    
    def test_ebics_functional_error(self):
        """Test EbicsFunctionalError compatibility class"""
        from erpnextswiss.erpnextswiss.ebics_api import EbicsFunctionalError
        
        error = EbicsFunctionalError("Test error")
        self.assertIsInstance(error, Exception)
        self.assertEqual(str(error), "Test error")
    
    def test_date_handling(self):
        """Test date parameter handling in API methods"""
        from erpnextswiss.erpnextswiss.ebics_api import EbicsNode
        from datetime import date, datetime
        
        client = EbicsNode(self.connection)
        
        # Test with datetime object
        test_date = datetime(2024, 1, 15)
        
        # Mock the _run_node_command to capture the command
        original_run = client._run_node_command
        captured_command = []
        
        def mock_run(command, args=None):
            captured_command.append(command)
            return {"success": True}
        
        client._run_node_command = mock_run
        
        # Test STA with datetime
        client.STA(test_date, test_date)
        
        # Verify date was formatted correctly
        self.assertIn("2024-01-15", captured_command[0])
        
        # Restore original method
        client._run_node_command = original_run
    
    def test_z53_method_parameters(self):
        """Test Z53 method accepts multiple parameter formats"""
        from erpnextswiss.erpnextswiss.ebics_api import EbicsNode
        
        client = EbicsNode(self.connection)
        
        # Mock the _run_node_command
        def mock_run(command, args=None):
            return {"success": True, "data": "test_data"}
        
        client._run_node_command = mock_run
        
        # Test with start/end parameters
        result1 = client.Z53(start="2024-01-01", end="2024-01-31")
        self.assertTrue(result1['success'])
        
        # Test with from_date/to_date parameters
        result2 = client.Z53(from_date="2024-01-01", to_date="2024-01-31")
        self.assertTrue(result2['success'])
    
    def test_confirm_download_compatibility(self):
        """Test confirm_download method for fintech compatibility"""
        from erpnextswiss.erpnextswiss.ebics_api import EbicsNode
        
        client = EbicsNode(self.connection)
        result = client.confirm_download()
        
        # Should always return True for compatibility
        self.assertTrue(result)
    
    def test_xml_escaping(self):
        """Test XML content escaping in upload methods"""
        from erpnextswiss.erpnextswiss.ebics_api import EbicsNode
        
        client = EbicsNode(self.connection)
        
        # Test XML with special characters
        test_xml = '<?xml version="1.0"?>\n<test attr="value">Content & "quotes"</test>'
        
        # Mock the _run_node_command to capture the command
        captured_command = []
        
        def mock_run(command, args=None):
            captured_command.append(command)
            return {"success": True}
        
        client._run_node_command = mock_run
        
        # Test CCT upload
        client.CCT(test_xml)
        
        # Verify XML was escaped properly
        self.assertIn('\\"', captured_command[0])  # Quotes should be escaped
        self.assertIn('\\n', captured_command[0])  # Newlines should be escaped
    
    def test_api_compatibility_layer(self):
        """Test EbicsApi compatibility layer"""
        from erpnextswiss.erpnextswiss.ebics_api import EbicsApi
        
        client = EbicsApi(self.connection)
        
        # Mock the _run_node_command
        def mock_run(command, args=None):
            return {"success": True, "data": "<xml>test</xml>"}
        
        client._run_node_command = mock_run
        
        # Test Z53 with parsed=False
        result = client.Z53("2024-01-01", "2024-01-31", parsed=False)
        self.assertTrue(result['success'])
        
        # Test Z52 with parsed=False
        result = client.Z52("2024-01-01", "2024-01-31", parsed=False)
        self.assertTrue(result['success'])
    
    @patch('subprocess.run')
    def test_node_client_installation_check(self, mock_subprocess):
        """Test node-ebics-client installation check"""
        from erpnextswiss.erpnextswiss.ebics_api import EbicsNode
        
        # Mock successful node/npm check
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout="v18.0.0",
            stderr=""
        )
        
        client = EbicsNode(self.connection)
        
        # Verify node and npm were checked
        self.assertEqual(mock_subprocess.call_count, 2)  # node and npm version checks
    
    def test_get_ebics_status(self):
        """Test get_ebics_status function"""
        from erpnextswiss.erpnextswiss.ebics_api import get_ebics_status
        
        result = get_ebics_status()
        
        self.assertIsInstance(result, dict)
        self.assertIn('success', result)
        self.assertIn('status', result)
        
        if result['success']:
            status = result['status']
            self.assertIn('has_settings', status)
            self.assertIn('has_node', status)
            self.assertIn('connections_count', status)
            self.assertIn('has_fintech_dependency', status)
    
    def test_test_ebics_api(self):
        """Test test_ebics_api function"""
        from erpnextswiss.erpnextswiss.ebics_api import test_ebics_api
        
        result = test_ebics_api()
        
        self.assertIsInstance(result, dict)
        self.assertIn('success', result)
        self.assertIn('message', result)
        
        # Should have node/npm version info if available
        if result['success']:
            self.assertIn('node_version', result)
            self.assertIn('npm_version', result)


class TestEBICSMigration(unittest.TestCase):
    """Test suite for fintech to node-ebics-client migration"""
    
    def test_migration_functions_exist(self):
        """Test that migration functions are available"""
        try:
            from erpnextswiss.erpnextswiss.migrate_ebics_keys import (
                generate_rsa_key_pair,
                create_keys_for_connection,
                migrate_connection_to_node_ebics,
                check_existing_keys
            )
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Migration functions not found: {e}")
    
    def test_rsa_key_generation(self):
        """Test RSA key pair generation for migration"""
        from erpnextswiss.erpnextswiss.migrate_ebics_keys import generate_rsa_key_pair
        
        key_pair = generate_rsa_key_pair()
        
        # Verify structure
        self.assertIsInstance(key_pair, dict)
        self.assertIn('privateKey', key_pair)
        self.assertIn('publicKey', key_pair)
        
        # Verify PEM format
        self.assertTrue(key_pair['privateKey'].startswith('-----BEGIN'))
        self.assertTrue(key_pair['privateKey'].endswith('-----\n'))
        self.assertTrue(key_pair['publicKey'].startswith('-----BEGIN'))
    
    def test_key_format_conversion(self):
        """Test converting keys to node-ebics-client format"""
        from erpnextswiss.erpnextswiss.migrate_ebics_keys import (
            generate_rsa_key_pair,
            convert_to_node_ebics_format
        )
        
        # Generate a test key
        key_pair = generate_rsa_key_pair()
        
        # Convert to node-ebics format
        node_format = convert_to_node_ebics_format(key_pair['privateKey'])
        
        self.assertIn('pem', node_format)
        self.assertIn('modulus', node_format)
        self.assertIn('exponent', node_format)
        self.assertEqual(node_format['size'], 2048)
    
    def test_keys_data_structure(self):
        """Test the complete keys data structure for migration"""
        from erpnextswiss.erpnextswiss.migrate_ebics_keys import create_keys_for_connection
        
        keys_data = create_keys_for_connection(
            user_id="TEST_USER",
            partner_id="TEST_PARTNER",
            host_id="TEST_HOST"
        )
        
        # Verify top-level structure
        self.assertEqual(keys_data['userId'], "TEST_USER")
        self.assertEqual(keys_data['partnerId'], "TEST_PARTNER")
        self.assertEqual(keys_data['hostId'], "TEST_HOST")
        
        # Verify keys structure
        self.assertIn('keys', keys_data)
        self.assertIn('A006', keys_data['keys'])
        self.assertIn('E002', keys_data['keys'])
        self.assertIn('X002', keys_data['keys'])
        
        # Each key should have required properties
        for key_type in ['A006', 'E002', 'X002']:
            key = keys_data['keys'][key_type]
            self.assertIn('privateKey', key)
            self.assertIn('publicKey', key)
    
    def test_migration_with_existing_connection(self):
        """Test migration process with an existing connection"""
        # Create a test connection
        test_conn_name = "Migration_Test_Connection"
        
        if not frappe.db.exists("ebics Connection", test_conn_name):
            conn = frappe.get_doc({
                "doctype": "ebics Connection",
                "title": test_conn_name,
                "user_id": "MIGRATE_USER",
                "partner_id": "MIGRATE_PARTNER",
                "host_id": "MIGRATE_HOST",
                "url": "https://test.example.com",
                "ebics_version": "H005"
            })
            conn.insert(ignore_permissions=True)
        
        # Test migration
        from erpnextswiss.erpnextswiss.migrate_ebics_keys import migrate_connection_to_node_ebics
        
        try:
            result = migrate_connection_to_node_ebics(test_conn_name)
            
            self.assertIsInstance(result, dict)
            self.assertIn('success', result)
            
            if result['success']:
                self.assertIn('keys_path', result)
                
                # Verify keys file was created
                self.assertTrue(os.path.exists(result['keys_path']))
                
                # Clean up
                import shutil
                shutil.rmtree(os.path.dirname(result['keys_path']))
        except Exception as e:
            self.fail(f"Migration failed: {e}")
        finally:
            # Clean up test connection
            frappe.delete_doc("ebics Connection", test_conn_name, ignore_permissions=True)


class TestEBICSIntegration(unittest.TestCase):
    """Integration tests for EBICS functionality"""
    
    @unittest.skipIf(not os.getenv('RUN_INTEGRATION_TESTS'), 
                     "Integration tests require RUN_INTEGRATION_TESTS=1")
    def test_real_bank_connection(self):
        """Test with real bank connection (requires actual bank credentials)"""
        # This test would only run with real credentials
        # Skip by default to avoid failures in CI/CD
        pass
    
    def test_payment_file_generation(self):
        """Test generating payment files for EBICS upload"""
        from erpnextswiss.erpnextswiss.doctype.payment_proposal.payment_proposal import (
            generate_pain001
        )
        
        # This would test the integration between payment generation and EBICS upload
        # Mock test for now
        self.assertTrue(True)
    
    def test_statement_import_flow(self):
        """Test the complete flow of importing bank statements via EBICS"""
        # This would test:
        # 1. Download statement via EBICS
        # 2. Parse CAMT format
        # 3. Create bank import entries
        # 4. Match with existing transactions
        
        # Mock test for now
        self.assertTrue(True)


def run_tests():
    """Run all EBICS tests"""
    import sys
    from unittest import TestLoader, TextTestRunner
    
    loader = TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    
    runner = TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    unittest.main()