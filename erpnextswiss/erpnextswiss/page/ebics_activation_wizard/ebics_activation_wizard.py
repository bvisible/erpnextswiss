# -*- coding: utf-8 -*-
# Copyright (c) 2025, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

@frappe.whitelist()
def get_wizard_status(connection_name):
    """Get the current status of the EBICS activation wizard"""
    if not connection_name:
        return {"error": "No connection specified"}
    
    try:
        conn = frappe.get_doc("ebics Connection", connection_name)
        
        # Determine current step based on status
        current_step = 1
        completed_steps = []
        
        # Step 1: Configuration
        if conn.host_id and conn.url and conn.partner_id and conn.user_id and conn.key_password:
            completed_steps.append(1)
            current_step = 2
        
        # Step 2: Keys Generated
        if conn.get("keys_created"):
            completed_steps.append(2)
            current_step = 3
        
        # Step 3: INI Sent
        if conn.ini_sent:
            completed_steps.append(3)
            current_step = 4
        
        # Step 4: HIA Sent
        if conn.hia_sent:
            completed_steps.append(4)
            current_step = 5
        
        # Step 5: INI Letter Created
        if conn.ini_letter_created:
            completed_steps.append(5)
            current_step = 6
        
        # Step 6: HPB Downloaded
        if conn.hpb_downloaded:
            completed_steps.append(6)
            current_step = 7
        
        # Step 7: Activated
        if conn.activated:
            completed_steps.append(7)
            current_step = 7  # Stay on last step
        
        return {
            "success": True,
            "current_step": current_step,
            "completed_steps": completed_steps,
            "connection": {
                "name": conn.name,
                "title": conn.title,
                "host_id": conn.host_id,
                "url": conn.url,
                "partner_id": conn.partner_id,
                "user_id": conn.user_id,
                "ebics_version": conn.ebics_version,
                "bank_config": conn.bank_config,
                "keys_created": conn.get("keys_created", False),
                "ini_sent": conn.ini_sent,
                "hia_sent": conn.hia_sent,
                "ini_letter_created": conn.ini_letter_created,
                "hpb_downloaded": conn.hpb_downloaded,
                "activated": conn.activated
            }
        }
    except Exception as e:
        return {"error": str(e)}

@frappe.whitelist()
def save_wizard_progress(connection_name, step_data):
    """Save progress from the wizard"""
    if not connection_name:
        return {"error": "No connection specified"}
    
    try:
        conn = frappe.get_doc("ebics Connection", connection_name)
        
        # Update fields based on step data
        if isinstance(step_data, str):
            import json
            step_data = json.loads(step_data)
        
        for field, value in step_data.items():
            if hasattr(conn, field):
                setattr(conn, field, value)
        
        conn.save()
        frappe.db.commit()
        
        return {"success": True, "message": _("Progress saved successfully")}
    except Exception as e:
        return {"error": str(e)}

@frappe.whitelist()
def validate_connection_params(host_id, url, partner_id, user_id):
    """Validate EBICS connection parameters"""
    errors = []
    
    if not host_id:
        errors.append(_("Host ID is required"))
    
    if not url:
        errors.append(_("URL is required"))
    elif not (url.startswith("http://") or url.startswith("https://")):
        errors.append(_("URL must start with http:// or https://"))
    
    if not partner_id:
        errors.append(_("Partner ID is required"))
    
    if not user_id:
        errors.append(_("User ID is required"))
    
    if errors:
        return {"success": False, "errors": errors}
    
    return {"success": True, "message": _("All parameters are valid")}

@frappe.whitelist()
def auto_detect_bank(url):
    """Auto-detect bank configuration from URL"""
    if not url:
        return None
    
    url_lower = url.lower()
    
    bank_configs = {
        'raiffeisen': 'Raiffeisen',
        'ubs': 'UBS',
        'credit-suisse': 'Credit Suisse',
        'cs.ch': 'Credit Suisse',
        'postfinance': 'PostFinance',
        'zkb': 'ZKB',
        'bcv': 'BCV',
        'bcge': 'BCGE'
    }
    
    for key, bank in bank_configs.items():
        if key in url_lower:
            return bank
    
    return None

@frappe.whitelist()
def get_help_content(step):
    """Get help content for a specific step"""
    help_content = {
        1: {
            "title": _("Connection Configuration"),
            "content": _("""
                <h5>What you need:</h5>
                <ul>
                    <li><strong>Host ID:</strong> The bank's EBICS host identifier (e.g., RAIFCH22XXX)</li>
                    <li><strong>URL:</strong> The bank's EBICS server URL</li>
                    <li><strong>Partner ID:</strong> Your company's partner identifier</li>
                    <li><strong>User ID:</strong> Your personal EBICS user identifier</li>
                    <li><strong>Key Password:</strong> A strong password to encrypt your keys locally</li>
                </ul>
                <h5>Tips:</h5>
                <ul>
                    <li>These details are provided by your bank when you sign up for EBICS</li>
                    <li>The URL usually ends with /ebics or /ebics-server</li>
                    <li>Choose a strong password - you'll need it for all EBICS operations</li>
                </ul>
            """)
        },
        2: {
            "title": _("Key Generation"),
            "content": _("""
                <h5>About EBICS Keys:</h5>
                <p>Three RSA key pairs will be generated:</p>
                <ul>
                    <li><strong>A006:</strong> Electronic signature key</li>
                    <li><strong>X002:</strong> Authentication key</li>
                    <li><strong>E002:</strong> Encryption key</li>
                </ul>
                <p>These keys are 2048-bit RSA keys and will be encrypted with your password.</p>
                <h5>Security Note:</h5>
                <p>Keys are stored securely in your ERPNext instance. Make sure to backup your keys after generation.</p>
            """)
        },
        3: {
            "title": _("INI Order"),
            "content": _("""
                <h5>What is INI?</h5>
                <p>The INI order transmits your electronic signature public key to the bank.</p>
                <h5>What happens:</h5>
                <ul>
                    <li>Your A006 public key is sent to the bank</li>
                    <li>The bank stores it for signature verification</li>
                    <li>This is the first step of the key exchange</li>
                </ul>
            """)
        },
        4: {
            "title": _("HIA Order"),
            "content": _("""
                <h5>What is HIA?</h5>
                <p>The HIA order transmits your authentication and encryption public keys to the bank.</p>
                <h5>What happens:</h5>
                <ul>
                    <li>Your X002 (auth) and E002 (encryption) public keys are sent</li>
                    <li>The bank stores them for secure communication</li>
                    <li>Completes the key exchange from your side</li>
                </ul>
            """)
        },
        5: {
            "title": _("INI Letter"),
            "content": _("""
                <h5>Manual Verification Step:</h5>
                <p>The INI letter contains the fingerprints (hashes) of your public keys.</p>
                <h5>Required Actions:</h5>
                <ol>
                    <li>Generate and download the PDF letter</li>
                    <li>Print it on company letterhead if required</li>
                    <li>Have it signed by authorized signatories</li>
                    <li>Send to your bank (mail or secure upload)</li>
                    <li>Wait for bank confirmation (1-2 business days)</li>
                </ol>
                <p><strong>Important:</strong> The bank will not activate your account until they receive and verify this letter.</p>
            """)
        },
        6: {
            "title": _("Download Bank Keys"),
            "content": _("""
                <h5>HPB Order:</h5>
                <p>Downloads the bank's public keys for secure communication.</p>
                <h5>Prerequisites:</h5>
                <ul>
                    <li>Bank must have received your INI letter</li>
                    <li>Bank must have verified and activated your keys</li>
                    <li>Usually takes 1-2 business days after sending letter</li>
                </ul>
                <h5>Common Issues:</h5>
                <p>If you get "User not activated" error, the bank hasn't processed your letter yet. Wait and try again later.</p>
            """)
        },
        7: {
            "title": _("Activation"),
            "content": _("""
                <h5>Final Steps:</h5>
                <p>Your connection is ready to be activated!</p>
                <h5>Test Your Connection:</h5>
                <ul>
                    <li>Click "Activate Connection" to enable the connection</li>
                    <li>Use "Test Download" to verify everything works</li>
                    <li>The test will try to download yesterday's statements</li>
                </ul>
                <h5>What's Next:</h5>
                <p>Once activated, you can:</p>
                <ul>
                    <li>Download bank statements automatically</li>
                    <li>Upload payment files</li>
                    <li>Set up automatic synchronization</li>
                </ul>
            """)
        }
    }
    
    step_num = int(step) if isinstance(step, str) else step
    return help_content.get(step_num, {"title": "Help", "content": "No help available for this step"})

@frappe.whitelist()
def get_troubleshooting_guide(error_code=None):
    """Get troubleshooting guide for common EBICS errors"""
    guides = {
        "EBICS_INVALID_USER_OR_USER_STATE": {
            "error": _("Invalid User or User State"),
            "causes": [
                _("User not yet activated by the bank"),
                _("INI letter not yet processed"),
                _("Incorrect User ID or Partner ID")
            ],
            "solutions": [
                _("Wait for bank to process your INI letter (1-2 business days)"),
                _("Contact your bank to verify activation status"),
                _("Double-check your User ID and Partner ID")
            ]
        },
        "EBICS_AUTHENTICATION_FAILED": {
            "error": _("Authentication Failed"),
            "causes": [
                _("Incorrect keys or password"),
                _("Keys not properly initialized"),
                _("Connection parameters incorrect")
            ],
            "solutions": [
                _("Verify your key password is correct"),
                _("Check if keys were generated successfully"),
                _("Confirm Host ID and URL are correct")
            ]
        },
        "EBICS_INVALID_ORDER_TYPE": {
            "error": _("Invalid Order Type"),
            "causes": [
                _("Order type not supported by your bank"),
                _("Wrong EBICS version selected"),
                _("Insufficient permissions for order type")
            ],
            "solutions": [
                _("Check with your bank for supported order types"),
                _("Verify EBICS version (H004 vs H005)"),
                _("Contact bank to enable required order types")
            ]
        },
        "CONNECTION_ERROR": {
            "error": _("Connection Error"),
            "causes": [
                _("Network connectivity issues"),
                _("Firewall blocking EBICS port"),
                _("Incorrect URL")
            ],
            "solutions": [
                _("Check internet connection"),
                _("Verify firewall allows HTTPS connections"),
                _("Confirm URL with your bank")
            ]
        }
    }
    
    if error_code:
        return guides.get(error_code, {
            "error": error_code,
            "causes": [_("Unknown error")],
            "solutions": [_("Contact support or check with your bank")]
        })
    
    return guides

@frappe.whitelist()
def schedule_activation_check(connection_name):
    """Schedule a periodic check for activation readiness"""
    # This could be implemented to periodically check if the bank
    # has processed the INI letter and try to download HPB
    pass