"""
EBICS Secure Caller - Communication sécurisée avec le service PHP
Jamais exposé directement au web - uniquement via Frappe

@author: Claude
@date: 2025-08-20
@version: 1.1
"""

import subprocess
import json
import hashlib
import hmac
import time
import os
import secrets
from typing import Dict, Any, Optional
import frappe
from frappe import _
from frappe.utils import get_site_path, cstr


class EbicsSecureCaller:
    """
    Secure caller for EBICS PHP service
    Executes PHP scripts via subprocess with HMAC authentication
    """
    
    def __init__(self):
        """Initialize the secure caller"""
        # Use the simpler PHP script without vendor dependencies
        self.php_script = os.path.join(
            frappe.utils.get_bench_path(),
            "apps/erpnextswiss/erpnextswiss/erpnextswiss/ebics_secure_service/ebics_simple_secure_api.php"
        )
        # Generate a secure key for HMAC
        self.secret_key = secrets.token_hex(32)
        
    def _generate_signature(self, data: str) -> str:
        """Generate HMAC signature for the request"""
        return hmac.new(
            self.secret_key.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def call_ebics_service(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call the EBICS PHP service securely
        
        Args:
            action: The action to perform (generate_keys, send_ini, etc.)
            params: Parameters for the action
            
        Returns:
            Response from the PHP service
        """
        try:
            # Prepare the request
            request = {
                "action": action,
                "params": params,
                "timestamp": int(time.time()),
                "nonce": secrets.token_hex(16)
            }
            
            # Calculate signature on the request data (without signature field)
            request_json = json.dumps(request, sort_keys=True, separators=(',', ':'))
            signature = self._generate_signature(request_json)
            
            # Add signature to request
            request["signature"] = signature
            
            # Prepare environment with secret key
            env = os.environ.copy()
            env["EBICS_INTERNAL_SECRET"] = self.secret_key  # Match PHP expected variable name
            env["FRAPPE_SITE"] = frappe.local.site
            env["FRAPPE_BENCH_PATH"] = frappe.utils.get_bench_path()
            env["FRAPPE_SITE_PATH"] = frappe.utils.get_site_path()
            
            # Send the complete request with signature
            final_request = json.dumps(request, separators=(',', ':'))
            
            # Execute PHP script via subprocess
            result = subprocess.run(
                ['php', self.php_script],
                input=final_request,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
                env=env
            )
            
            if result.returncode != 0:
                frappe.log_error(
                    f"PHP Error - Return code: {result.returncode}\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}\nCommand: {self.php_script}",
                    "EBICS Secure Service Error"
                )
                return {
                    "success": False,
                    "error": f"PHP execution failed: {result.stderr or result.stdout}"
                }
            
            # Parse response
            try:
                # Log the raw output for debugging
                if action == "GET_INI_LETTER":
                    frappe.log_error(
                        f"PHP Response for INI Letter:\nSTDOUT: {result.stdout[:500]}",
                        "EBICS INI Letter Debug"
                    )
                
                response = json.loads(result.stdout)
                return response
            except json.JSONDecodeError as e:
                frappe.log_error(
                    f"Invalid JSON response: {result.stdout}",
                    "EBICS JSON Error"
                )
                return {
                    "success": False,
                    "error": f"Invalid response from PHP service: {str(e)}"
                }
                
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "PHP service timeout"
            }
        except Exception as e:
            frappe.log_error(
                f"Secure caller error: {str(e)}",
                "EBICS Secure Caller Error"
            )
            return {
                "success": False,
                "error": str(e)
            }
    
    def generate_keys(self, connection_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate EBICS keys for a connection"""
        return self.call_ebics_service('GENERATE_KEYS', {
            'connection': connection_data
        })
    
    def send_ini(self, connection_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send INI order"""
        return self.call_ebics_service('INI', {
            'connection': connection_data
        })
    
    def send_hia(self, connection_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send HIA order"""
        return self.call_ebics_service('HIA', {
            'connection': connection_data
        })
    
    def download_hpb(self, connection_data: Dict[str, Any]) -> Dict[str, Any]:
        """Download HPB (bank public keys)"""
        # Pass connection parameters directly for HPB
        return self.call_ebics_service('HPB', connection_data)
    
    def generate_ini_letter(self, connection_data: Dict[str, Any], keys: Optional[Dict] = None) -> Dict[str, Any]:
        """Generate INI letter PDF"""
        params = {
            'connection': connection_data
        }
        if keys:
            params['keys'] = keys
        return self.call_ebics_service('GET_INI_LETTER', params)