#!/usr/bin/env python3
"""
Test complete EBICS workflow from initialization to activation
"""

import json
import sys
import os
import time
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def test_workflow_step(manager, action, description, **params):
    """Execute and report a workflow step"""
    print(f"\n{'='*60}")
    print(f"Step: {description}")
    print(f"Action: {action}")
    print(f"{'='*60}")
    
    try:
        result = manager.execute_order(action, **params)
        
        if result.get('success') or result.get('workflow_success'):
            print(f"✅ {description} successful")
            if result.get('awaiting_activation'):
                print("   ⏳ Awaiting bank activation")
            if result.get('message'):
                print(f"   {result['message']}")
        else:
            print(f"❌ {description} failed")
            if result.get('error'):
                print(f"   Error: {result['error']}")
            if result.get('code'):
                print(f"   Code: {result['code']}")
        
        return result
    except Exception as e:
        print(f"❌ Exception in {description}: {str(e)}")
        return {'success': False, 'error': str(e)}

def test_complete_workflow(connection_name):
    """Test the complete EBICS workflow"""
    try:
        from ebics_manager import EbicsManager
        
        print(f"\n{'='*60}")
        print(f"EBICS Complete Workflow Test")
        print(f"Connection: {connection_name}")
        print(f"{'='*60}")
        
        manager = EbicsManager(connection_name)
        
        # Load current connection state
        connection = manager.connection
        
        print(f"\nCurrent Connection State:")
        print(f"  Keys Created: {connection.keys_created}")
        print(f"  INI Sent: {connection.ini_sent}")
        print(f"  HIA Sent: {connection.hia_sent}")
        print(f"  INI Letter Created: {connection.ini_letter_created}")
        print(f"  Bank Activated: {connection.bank_activation_confirmed}")
        print(f"  HPB Downloaded: {connection.hpb_downloaded}")
        print(f"  Activated: {connection.activated}")
        
        results = {}
        
        # Step 1: Generate Keys (if not already done)
        if not connection.keys_created:
            results['generate_keys'] = test_workflow_step(
                manager, 'GENERATE_KEYS', 'Generate Keys'
            )
            time.sleep(2)  # Small delay between steps
        else:
            print("\n✅ Keys already generated - skipping")
        
        # Step 2: Send INI (if not already done)
        if connection.keys_created and not connection.ini_sent:
            results['send_ini'] = test_workflow_step(
                manager, 'INI', 'Send INI'
            )
            time.sleep(2)
        else:
            print("\n✅ INI already sent - skipping")
        
        # Step 3: Send HIA (if not already done)
        if connection.keys_created and not connection.hia_sent:
            results['send_hia'] = test_workflow_step(
                manager, 'HIA', 'Send HIA'
            )
            time.sleep(2)
        else:
            print("\n✅ HIA already sent - skipping")
        
        # Step 4: Generate INI Letter (if not already done)
        if connection.ini_sent and connection.hia_sent and not connection.ini_letter_created:
            results['generate_letter'] = test_workflow_step(
                manager, 'GET_INI_LETTER', 'Generate INI Letter'
            )
        else:
            print("\n✅ INI Letter already created - skipping")
        
        # Step 5: Check for bank activation
        if connection.ini_letter_created and not connection.bank_activation_confirmed:
            print(f"\n{'='*60}")
            print("⏳ Waiting for bank activation...")
            print("   Please submit the INI letter to your bank")
            print("   and wait for their confirmation")
            print(f"{'='*60}")
        
        # Step 6: Download HPB (if bank activated)
        if connection.bank_activation_confirmed and not connection.hpb_downloaded:
            results['download_hpb'] = test_workflow_step(
                manager, 'HPB', 'Download HPB'
            )
        elif connection.hpb_downloaded:
            print("\n✅ HPB already downloaded - skipping")
        
        # Step 7: Test a download if fully activated
        if connection.activated:
            print(f"\n{'='*60}")
            print("Testing download capability with Z53")
            print(f"{'='*60}")
            
            results['test_z53'] = test_workflow_step(
                manager, 'Z53', 'Test Z53 Download',
                dateFrom='2024-01-01',
                dateTo=datetime.now().strftime('%Y-%m-%d')
            )
        
        # Summary
        print(f"\n{'='*60}")
        print(f"Workflow Test Summary")
        print(f"{'='*60}")
        
        # Reload connection to get updated state
        manager.load_connection(connection_name)
        connection = manager.connection
        
        print(f"\nFinal Connection State:")
        print(f"  Keys Created: {connection.keys_created} {'✅' if connection.keys_created else '❌'}")
        print(f"  INI Sent: {connection.ini_sent} {'✅' if connection.ini_sent else '❌'}")
        print(f"  HIA Sent: {connection.hia_sent} {'✅' if connection.hia_sent else '❌'}")
        print(f"  INI Letter Created: {connection.ini_letter_created} {'✅' if connection.ini_letter_created else '❌'}")
        print(f"  Bank Activated: {connection.bank_activation_confirmed} {'✅' if connection.bank_activation_confirmed else '⏳'}")
        print(f"  HPB Downloaded: {connection.hpb_downloaded} {'✅' if connection.hpb_downloaded else '❌'}")
        print(f"  Fully Activated: {connection.activated} {'✅' if connection.activated else '❌'}")
        
        if not connection.activated:
            if not connection.bank_activation_confirmed:
                print("\n⏳ Next step: Submit INI letter to bank and wait for activation")
            elif not connection.hpb_downloaded:
                print("\n⏳ Next step: Download HPB after bank activation")
        else:
            print("\n✅ Connection is fully activated and ready for use!")
        
        return results
        
    except Exception as e:
        print(f"❌ Error in workflow test: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}

if __name__ == "__main__":
    # Get connection name from command line or use default
    connection_name = sys.argv[1] if len(sys.argv) > 1 else "Entwicklung CS"
    
    # Test complete workflow
    test_complete_workflow(connection_name)