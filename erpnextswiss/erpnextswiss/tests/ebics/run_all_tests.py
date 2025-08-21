#!/usr/bin/env python3
"""
Run all EBICS tests
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def run_all_tests(connection_name="Entwicklung CS"):
    """Run all EBICS tests"""
    
    print("="*70)
    print("EBICS COMPLETE TEST SUITE")
    print("="*70)
    print(f"Testing connection: {connection_name}")
    print()
    
    # Import test modules
    from test_ebics_downloads import test_all_downloads
    from test_ebics_uploads import test_all_uploads
    from test_ebics_workflow import test_complete_workflow
    
    results = {}
    
    # Test 1: Workflow
    print("\n" + "="*70)
    print("TEST 1: EBICS WORKFLOW")
    print("="*70)
    results['workflow'] = test_complete_workflow(connection_name)
    
    # Test 2: Downloads
    print("\n" + "="*70)
    print("TEST 2: EBICS DOWNLOADS")
    print("="*70)
    results['downloads'] = test_all_downloads(connection_name)
    
    # Test 3: Uploads
    print("\n" + "="*70)
    print("TEST 3: EBICS UPLOADS")
    print("="*70)
    results['uploads'] = test_all_uploads(connection_name)
    
    # Final Summary
    print("\n" + "="*70)
    print("FINAL TEST SUMMARY")
    print("="*70)
    
    for test_name, test_results in results.items():
        print(f"\n{test_name.upper()}:")
        if isinstance(test_results, dict):
            if 'error' in test_results:
                print(f"  ❌ Error: {test_results['error']}")
            else:
                for key, result in test_results.items():
                    if isinstance(result, dict):
                        status = "✅" if result.get('success') else "❌"
                        print(f"  {status} {key}")
        else:
            print(f"  Results: {test_results}")
    
    return results

if __name__ == "__main__":
    # Get connection name from command line or use default
    connection_name = sys.argv[1] if len(sys.argv) > 1 else "Entwicklung CS"
    
    # Run all tests
    run_all_tests(connection_name)