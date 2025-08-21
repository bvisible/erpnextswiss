#!/usr/bin/env python3
"""
Test to verify that ini_letter_created field is properly updated
"""

import frappe
from frappe import _
from erpnextswiss.erpnextswiss.ebics_manager import EbicsManager

def test_ini_letter_field_update():
    """Test that generating INI letter updates the field"""
    
    print("=" * 60)
    print("TESTING INI LETTER FIELD UPDATE")
    print("=" * 60)
    
    # Get the connection
    connection_name = "TEST_PHP"  # or whatever connection you're testing
    
    try:
        # Initialize manager
        manager = EbicsManager(connection_name)
        
        # Check initial state
        print(f"\nBefore generating INI letter:")
        print(f"  ini_letter_created: {manager.connection.ini_letter_created}")
        
        # Generate INI letter
        print(f"\nGenerating INI letter...")
        result = manager.get_ini_letter()
        
        # Check if successful
        if result.get('success'):
            print(f"  ✅ INI letter generated successfully")
            
            # Reload connection to check if field was updated
            manager.load_connection(connection_name)
            print(f"\nAfter generating INI letter:")
            print(f"  ini_letter_created: {manager.connection.ini_letter_created}")
            
            if manager.connection.ini_letter_created:
                print(f"\n✅ SUCCESS: Field was properly updated!")
            else:
                print(f"\n❌ ERROR: Field was NOT updated despite successful generation")
        else:
            print(f"  ❌ Failed to generate INI letter: {result.get('error')}")
            print(f"  Code: {result.get('code')}")
            print(f"  Message: {result.get('message')}")
            
    except Exception as e:
        print(f"\n❌ Error during test: {str(e)}")

if __name__ == "__main__":
    # Initialize Frappe for the site
    import sys
    if len(sys.argv) > 1:
        site = sys.argv[1]
    else:
        site = "dmis.neoffice.me"
    
    frappe.init(site=site)
    frappe.connect()
    
    test_ini_letter_field_update()
    
    frappe.destroy()