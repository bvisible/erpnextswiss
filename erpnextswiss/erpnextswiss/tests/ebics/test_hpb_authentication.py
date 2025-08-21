#!/usr/bin/env python
"""
EBICS HPB Authentication Test
Specific test to verify HPB fails correctly without bank activation

@author: Claude
@date: 2025-08-20
"""

import frappe
import json
from erpnextswiss.erpnextswiss.ebics_manager import EbicsManager


def test_hpb_authentication():
    """Test that HPB correctly fails without bank activation"""
    
    print("=" * 70)
    print("EBICS HPB AUTHENTICATION TEST")
    print("Verifying HPB fails correctly without bank activation")
    print("=" * 70)
    
    # Test with Credit Suisse Test Platform
    connection_name = "Credit Suisse Test Platform"
    
    try:
        # Create manager
        print(f"\n1. Loading connection: {connection_name}")
        manager = EbicsManager(connection_name)
        print("   ✓ Manager loaded")
        
        # Get connection state
        conn = manager.connection
        print(f"\n2. Connection state:")
        print(f"   - Keys created: {'Yes' if conn.keys_created else 'No'}")
        print(f"   - INI sent: {'Yes' if conn.ini_sent else 'No'}")
        print(f"   - HIA sent: {'Yes' if conn.hia_sent else 'No'}")
        print(f"   - Activated: {'Yes' if conn.activated else 'No'}")
        
        # Test HPB
        print(f"\n3. Testing HPB download...")
        result = manager.download_hpb()
        
        print(f"\n4. Result analysis:")
        
        if result.get('success'):
            print("   ✗ FAILURE: HPB should NOT succeed without activation!")
            print("   This is a critical security issue!")
            return False
            
        else:
            # Check the error code
            code = result.get('code')
            error = result.get('error')
            message = result.get('message')
            
            print(f"   HPB failed (as expected)")
            print(f"   - Error: {error}")
            print(f"   - Code: {code}")
            print(f"   - Message: {message}")
            
            # Verify it's the correct error
            if code in ['091002', '061001', '061002']:
                print("\n   ✓ SUCCESS: HPB correctly returns authentication error!")
                print("   The EBICS workflow is properly enforced.")
                
                if 'details' in result:
                    print(f"\n   Additional details:")
                    for key, value in result['details'].items():
                        print(f"   - {key}: {value}")
                        
                return True
            else:
                print(f"\n   ? WARNING: Unexpected error code: {code}")
                print("   Expected: 091002 (authentication failed)")
                return False
                
    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        print("\n" + "=" * 70)


def run_hpb_test():
    """Run the HPB authentication test"""
    return test_hpb_authentication()


if __name__ == "__main__":
    success = run_hpb_test()
    exit(0 if success else 1)