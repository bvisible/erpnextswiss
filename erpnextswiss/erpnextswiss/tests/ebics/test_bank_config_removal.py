#!/usr/bin/env python3
"""
Test script to verify bank_config removal and ebics_version usage
"""

import sys
import os
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../..'))

def test_no_bank_config_references():
    """Test that bank_config has been removed from all files"""
    print("Testing for bank_config references...")
    
    base_path = os.path.join(os.path.dirname(__file__), '../..')
    files_to_check = [
        'doctype/ebics_connection/ebics_connection.json',
        'doctype/ebics_connection/ebics_connection.py',
        'doctype/ebics_connection/ebics_connection.js',
        'page/ebics_activation_wizard/ebics_activation_wizard.py',
        'page/ebics_activation_wizard/ebics_activation_wizard.js',
        'ebics.py'
    ]
    
    errors = []
    
    for file_path in files_to_check:
        full_path = os.path.join(base_path, file_path)
        if os.path.exists(full_path):
            with open(full_path, 'r') as f:
                content = f.read()
                
                # Check for bank_config references (excluding comments)
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    # Skip comment lines
                    if line.strip().startswith('#') or line.strip().startswith('//'):
                        continue
                    if 'bank_config' in line.lower() and 'removed' not in line.lower():
                        errors.append(f"{file_path}:{i} - Found bank_config reference: {line.strip()}")
        else:
            print(f"  Warning: File not found: {file_path}")
    
    if errors:
        print("  ❌ Found bank_config references:")
        for error in errors:
            print(f"    {error}")
        return False
    else:
        print("  ✅ No bank_config references found")
        return True

def test_ebics_version_field():
    """Test that ebics_version field exists and is configured correctly"""
    print("\nTesting ebics_version field configuration...")
    
    json_path = os.path.join(os.path.dirname(__file__), '../../doctype/ebics_connection/ebics_connection.json')
    
    if not os.path.exists(json_path):
        print(f"  ❌ File not found: {json_path}")
        return False
    
    with open(json_path, 'r') as f:
        doctype_def = json.load(f)
    
    # Check if ebics_version field exists
    fields = doctype_def.get('fields', [])
    ebics_version_field = None
    
    for field in fields:
        if field.get('fieldname') == 'ebics_version':
            ebics_version_field = field
            break
    
    if not ebics_version_field:
        print("  ❌ ebics_version field not found in DocType definition")
        return False
    
    # Verify field configuration
    expected_config = {
        'fieldname': 'ebics_version',
        'fieldtype': 'Select',
        'label': 'Version',
        'default': 'H005',
        'options': 'H005\nH004\n3.0\n2.5\n2.4'
    }
    
    issues = []
    for key, expected_value in expected_config.items():
        actual_value = ebics_version_field.get(key)
        if actual_value != expected_value:
            issues.append(f"    {key}: expected '{expected_value}', got '{actual_value}'")
    
    if issues:
        print("  ❌ ebics_version field configuration issues:")
        for issue in issues:
            print(issue)
        return False
    else:
        print("  ✅ ebics_version field correctly configured")
        return True

def test_ebics_py_defaults():
    """Test that ebics.py uses correct H005 defaults"""
    print("\nTesting ebics.py H005 defaults...")
    
    ebics_py_path = os.path.join(os.path.dirname(__file__), '../../ebics.py')
    
    if not os.path.exists(ebics_py_path):
        print(f"  ❌ File not found: {ebics_py_path}")
        return False
    
    with open(ebics_py_path, 'r') as f:
        content = f.read()
    
    # Check for correct H005 defaults
    expected_defaults = [
        "service='EOP'",
        "msg_name='camt.053'",
        "scope='CH'",
        "version='04'",
        "container='ZIP'"
    ]
    
    missing = []
    for default in expected_defaults:
        if default not in content:
            missing.append(default)
    
    if missing:
        print("  ❌ Missing H005 defaults:")
        for item in missing:
            print(f"    {item}")
        return False
    else:
        print("  ✅ H005 defaults correctly set")
        return True

def test_connection_logging():
    """Test that connection names are properly logged"""
    print("\nTesting connection name logging...")
    
    manager_path = os.path.join(os.path.dirname(__file__), '../../ebics_manager.py')
    
    if not os.path.exists(manager_path):
        print(f"  ❌ File not found: {manager_path}")
        return False
    
    with open(manager_path, 'r') as f:
        content = f.read()
    
    # Check for proper connection name handling in _log_operation
    checks = [
        "connection_name = self.connection_name",
        "'connection': connection_name"
    ]
    
    missing = []
    for check in checks:
        if check not in content:
            missing.append(check)
    
    if missing:
        print("  ❌ Missing connection logging code:")
        for item in missing:
            print(f"    {item}")
        return False
    else:
        print("  ✅ Connection logging properly implemented")
        return True

def main():
    """Run all tests"""
    print("=" * 60)
    print("EBICS Bank Config Removal Test Suite")
    print("=" * 60)
    
    tests = [
        test_no_bank_config_references,
        test_ebics_version_field,
        test_ebics_py_defaults,
        test_connection_logging
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ❌ Test failed with exception: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)