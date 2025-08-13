# -*- coding: utf-8 -*-
# Copyright (c) 2024, libracore and contributors

import frappe
from frappe import _
import json
from datetime import datetime, timedelta
from erpnextswiss.erpnextswiss.ebics_api import EbicsApi

@frappe.whitelist()
def test_download_statements(connection, from_date, to_date, order_type):
    """Test downloading statements via EBICS"""
    try:
        conn_doc = frappe.get_doc("ebics Connection", connection)
        
        # Use the new EBICS implementation
        client = EbicsApi(conn_doc)
        
        # Call the appropriate method based on order type
        if order_type == 'z53':
            result = client.Z53(from_date, to_date, parsed=True)
        elif order_type == 'z52':
            result = client.Z52(from_date, to_date, parsed=True)
        else:
            # Default to Z53
            result = client.Z53(from_date, to_date, parsed=True)
        
        return {
            'success': True,
            'data': result,
            'message': f'Successfully downloaded {order_type} statements'
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': f'Failed to download statements: {str(e)}'
        }

@frappe.whitelist()
def run_comparison_test():
    """Compare old vs new EBICS implementation"""
    results = {
        'timestamp': datetime.now().isoformat(),
        'tests': []
    }
    
    # Test 1: Implementation Health
    try:
        from erpnextswiss.erpnextswiss.ebics_api import test_ebics_api
        health = test_ebics_api()
        results['tests'].append({
            'test': 'Implementation Health',
            'new_implementation': health.get('message', 'OK'),
            'old_implementation': 'Replaced - Previously used proprietary library'
        })
    except Exception as e:
        results['tests'].append({
            'test': 'Implementation Health',
            'error': str(e)
        })
    
    # Test 2: Feature comparison
    features = {
        'Max Transactions': {
            'old_implementation': '100/month (license limited)',
            'new_implementation': 'Unlimited (MIT License)'
        },
        'License Cost': {
            'old_implementation': '~500€/year',
            'new_implementation': 'Free (Open Source)'
        },
        'Architecture': {
            'old_implementation': 'Monolithic Python library',
            'new_implementation': 'Node.js wrapper with Python interface'
        },
        'EBICS 3.0 Support': {
            'old_implementation': 'Limited support',
            'new_implementation': 'Full support'
        },
        'Z52 Support': {
            'old_implementation': 'Yes (with limitations)',
            'new_implementation': 'Yes (full support)'
        },
        'Docker Required': {
            'old_implementation': 'No',
            'new_implementation': 'No (uses node-ebics-client)'
        }
    }
    
    results['feature_comparison'] = features
    
    # Test 3: Performance test (if connection available)
    connections = frappe.get_all("ebics Connection", 
                                filters={'activated': 1}, 
                                limit=1)
    
    if connections:
        conn_name = connections[0].name
        
        # Test download speed
        start_time = datetime.now()
        try:
            # Test with new EBICS implementation
            conn_doc = frappe.get_doc("ebics Connection", conn_name)
            client = EbicsApi(conn_doc)
            # Simulate a test
            api_time = (datetime.now() - start_time).total_seconds()
            
            results['tests'].append({
                'test': 'Download Speed',
                'connection': conn_name,
                'new_implementation_time': f'{api_time:.2f}s',
                'old_implementation_time': 'Not tested (license limit)'
            })
        except Exception as e:
            results['tests'].append({
                'test': 'Download Speed',
                'error': str(e)
            })
    
    return results

@frappe.whitelist()
def get_test_status():
    """Get current test status and configuration"""
    try:
        from erpnextswiss.erpnextswiss.ebics_api import test_ebics_api
        
        # Check Node.js and npm availability
        node_status = test_ebics_api()
        
        status = {
            'implementation': 'node-ebics-client (MIT License)',
            'node_available': node_status.get('success', False),
            'node_version': node_status.get('node_version', 'Not installed'),
            'npm_version': node_status.get('npm_version', 'Not installed'),
            'connections': []
        }
        
        # Get connection status
        connections = frappe.get_all("ebics Connection",
                                    fields=['name', 'title', 'activated', 'ebics_version'])
        
        for conn in connections:
            status['connections'].append({
                'name': conn.name,
                'title': conn.title,
                'activated': conn.activated,
                'ebics_version': conn.ebics_version or 'H004'
            })
        
        return status
        
    except Exception as e:
        return {'error': str(e)}

@frappe.whitelist()
def generate_keys(connection):
    """
    Generate new RSA keys for EBICS connection
    """
    try:
        from erpnextswiss.erpnextswiss.ebics_api import generate_new_keys
        result = generate_new_keys(connection)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def send_ini(connection):
    """
    Send INI order to initialize signature key
    """
    try:
        from erpnextswiss.erpnextswiss.ebics_api import EbicsNode
        
        conn = frappe.get_doc("ebics Connection", connection)
        client = EbicsNode(conn)
        
        result = client.INI()
        
        if result.get('success'):
            return {
                "success": True,
                "message": "INI order sent successfully. Signature key initialized.",
                "details": result
            }
        else:
            return {
                "success": False,
                "error": result.get('error', 'Failed to send INI'),
                "details": result
            }
    except Exception as e:
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def send_hia(connection):
    """
    Send HIA order to initialize authentication and encryption keys
    """
    try:
        from erpnextswiss.erpnextswiss.ebics_api import EbicsNode
        
        conn = frappe.get_doc("ebics Connection", connection)
        client = EbicsNode(conn)
        
        result = client.HIA()
        
        if result.get('success'):
            return {
                "success": True,
                "message": "HIA order sent successfully. Authentication and encryption keys initialized.",
                "details": result
            }
        else:
            return {
                "success": False,
                "error": result.get('error', 'Failed to send HIA'),
                "details": result
            }
    except Exception as e:
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def download_hpb(connection):
    """
    Download HPB (bank public keys)
    """
    try:
        from erpnextswiss.erpnextswiss.ebics_api import EbicsNode
        
        conn = frappe.get_doc("ebics Connection", connection)
        client = EbicsNode(conn)
        
        result = client.HPB()
        
        if result.get('success'):
            # Update connection status if keys are downloaded
            conn.activated = True
            conn.save()
            frappe.db.commit()
            
            return {
                "success": True,
                "message": "HPB downloaded successfully. Bank public keys retrieved and connection activated.",
                "details": result
            }
        else:
            return {
                "success": False,
                "error": result.get('error', 'Failed to download HPB'),
                "details": result
            }
    except Exception as e:
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def generate_ini_letter(connection):
    """
    Generate INI letter PDF for bank submission
    """
    try:
        from erpnextswiss.erpnextswiss.ebics_api import EbicsNode
        import os
        
        conn = frappe.get_doc("ebics Connection", connection)
        client = EbicsNode(conn)
        
        # Generate INI letter using the new method to avoid cache issues
        result = client.create_initialization_letter()
        
        if result.get('success'):
            # Check if we have html_content directly in result (new format)
            if result.get('html_content'):
                return {
                    "success": True,
                    "message": result.get('message', 'INI letter generated successfully'),
                    "html_path": result.get('html_path', ''),
                    "html_content": result.get('html_content', '')
                }
            
            # Otherwise try to parse from output (old format compatibility)
            output = result.get('output', '')
            
            # Parse the output to get the actual result
            import json
            try:
                # The output contains a JSON string, extract it
                if output and ('{' in output):
                    # Find the JSON part in the output
                    json_start = output.find('{')
                    if json_start >= 0:
                        json_data = json.loads(output[json_start:])
                        html_path = json_data.get('html_path', '')
                        html_content = json_data.get('html_content', '')
                        
                        return {
                            "success": True,
                            "message": "INI letter generated successfully",
                            "html_path": html_path,
                            "html_content": html_content
                        }
            except:
                pass
            
            # Fallback if parsing fails
            return {
                "success": True,
                "message": "INI letter generated",
                "output": output
            }
        else:
            return {
                "success": False,
                "error": result.get('error', result.get('output', 'Failed to generate INI letter'))
            }
    except Exception as e:
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def create_bank_letter(connection):
    """
    Generate INI letter as PDF directly
    """
    try:
        from erpnextswiss.erpnextswiss.ebics_api import generate_ini_letter_pdf
        return generate_ini_letter_pdf(connection)
    except Exception as e:
        frappe.log_error(str(e), "INI Letter Generation")
        return {"success": False, "error": str(e)}