#!/usr/bin/env python3
"""
Test EBICS download operations
"""

import json
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def test_download_order(connection_name, order_type, date_from=None, date_to=None):
    """Test a specific download order"""
    try:
        from ebics_manager import EbicsManager
        
        # Use default dates if not provided
        if not date_to:
            date_to = datetime.now().strftime('%Y-%m-%d')
        if not date_from:
            date_from = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        print(f"\n{'='*60}")
        print(f"Testing {order_type} download")
        print(f"Connection: {connection_name}")
        print(f"Date range: {date_from} to {date_to}")
        print(f"{'='*60}")
        
        manager = EbicsManager(connection_name)
        
        params = {
            'dateFrom': date_from,
            'dateTo': date_to
        }
        
        result = manager.execute_order(order_type, **params)
        
        print(f"\nResult:")
        print(json.dumps(result, indent=2))
        
        if result.get('success'):
            print(f"✅ {order_type} download successful")
            if result.get('statements'):
                print(f"   Received {len(result['statements'])} statements")
            elif result.get('data'):
                print(f"   Received data: {len(str(result['data']))} characters")
        else:
            print(f"❌ {order_type} download failed: {result.get('error')}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error testing {order_type}: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}

def test_all_downloads(connection_name):
    """Test all download order types"""
    
    # Order types to test
    order_types = ['Z53', 'Z54', 'HAA', 'HTD', 'PTK', 'HKD']
    
    results = {}
    success_count = 0
    
    print(f"\n{'='*60}")
    print(f"EBICS Download Tests - Starting")
    print(f"{'='*60}")
    
    for order_type in order_types:
        result = test_download_order(connection_name, order_type)
        results[order_type] = result
        if result.get('success'):
            success_count += 1
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Test Summary")
    print(f"{'='*60}")
    print(f"Total tests: {len(order_types)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {len(order_types) - success_count}")
    
    for order_type, result in results.items():
        status = "✅" if result.get('success') else "❌"
        print(f"{status} {order_type}: {result.get('message', result.get('error', 'Unknown'))}")
    
    return results

if __name__ == "__main__":
    # Get connection name from command line or use default
    connection_name = sys.argv[1] if len(sys.argv) > 1 else "Entwicklung CS"
    
    # Test all downloads
    test_all_downloads(connection_name)