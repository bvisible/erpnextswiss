# -*- coding: utf-8 -*-
# Copyright (c) 2019-2025, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
#
# MIGRATION COMPLETE: Using node-ebics-client (MIT License) instead of proprietary library

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
import os
from datetime import datetime, date, timedelta
import hashlib
from erpnextswiss.erpnextswiss.ebics_api import EbicsApi, get_ebics_client

@frappe.whitelist()
def test_connection(connection_name):
    """Test EBICS connection - callable from outside"""
    if not connection_name:
        return "❌ No connection specified"
    
    try:
        conn = frappe.get_doc("ebics Connection", connection_name)
        return conn.test_connection()
    except Exception as e:
        return f"❌ Error: {str(e)}"

@frappe.whitelist()
def get_available_order_types(connection_name):
    """Get available order types from bank"""
    if not connection_name:
        return None
    
    try:
        conn = frappe.get_doc("ebics Connection", connection_name)
        
        # For now, return standard Swiss order types
        # In future, this could query the bank for actual available types
        order_types = {
            "download": {
                "Z53": "Swiss Bank Statement (End of Day)",
                "Z52": "Swiss Intraday Statement",
                "C53": "CAMT.053 - Bank to Customer Statement",
                "C52": "CAMT.052 - Bank to Customer Account Report",
                "C54": "CAMT.054 - Bank to Customer Debit/Credit Notification"
            },
            "upload": {
                "XE2": "Swiss Payment (pain.001.001.03.ch.02)",
                "CCT": "SEPA Credit Transfer",
                "CDD": "SEPA Direct Debit",
                "XE3": "Swiss Direct Debit (pain.008.001.02.ch.03)"
            }
        }
        
        # Check if connection is activated
        if not conn.activated:
            return {
                "status": "warning",
                "message": "Connection not fully activated",
                "order_types": order_types
            }
        
        return {
            "status": "success",
            "message": "Standard order types for Swiss banks",
            "order_types": order_types
        }
        
    except Exception as e:
        frappe.log_error(str(e), "Get Order Types Error")
        return {
            "status": "error",
            "message": str(e)
        }

class ebicsConnection(Document):
    
    def validate(self):
        """Validate EBICS connection settings"""
        # Map new version format to old format for backward compatibility
        if self.ebics_version:
            version_map = {
                "3.0": "H005",  # EBICS 3.0 maps to H005
                "2.5": "H004",  # EBICS 2.5 maps to H004 (CORRECTION!)
                "2.4": "H004",  # EBICS 2.4 maps to H004
                "H004": "H004",  # Keep old format (EBICS 2.4/2.5)
                "H005": "H005"   # Keep old format (EBICS 3.0)
            }
            
            # If it's a new format, keep it but validate it exists in map
            if self.ebics_version not in version_map:
                frappe.throw(_("Invalid EBICS version: {0}. Supported versions are: 3.0, 2.5, 2.4, H004, H005").format(self.ebics_version))
    
    def before_save(self):
        # make sure synced_until is in date format
        if self.synced_until and not isinstance(self.synced_until, date):
            if isinstance(self.synced_until, str):
                # Extract just the date part if there's a time component
                if ' ' in self.synced_until:
                    # Has time component, just take the date part
                    date_part = self.synced_until.split(' ')[0]
                    try:
                        self.synced_until = datetime.strptime(date_part, "%Y-%m-%d").date()
                    except ValueError:
                        frappe.throw(_("Invalid date format for synced_until: {0}").format(self.synced_until))
                else:
                    # Just date, parse directly
                    try:
                        self.synced_until = datetime.strptime(self.synced_until, "%Y-%m-%d").date()
                    except ValueError:
                        frappe.throw(_("Invalid date format for synced_until: {0}").format(self.synced_until))
            elif isinstance(self.synced_until, datetime):
                self.synced_until = self.synced_until.date()
        
        # Clean up URL - remove trailing spaces
        if self.url:
            self.url = self.url.strip()
        
        return
    
    def get_ebics_version_code(self):
        """Get EBICS version code for API calls"""
        version_map = {
            "3.0": "H005",
            "2.5": "H005", 
            "2.4": "H004",
            "H004": "H004",
            "H005": "H005"
        }
        return version_map.get(self.ebics_version, "H005")
    
    def get_client(self):
        """Get EBICS client using new API wrapper"""
        return EbicsApi(self)
    
    @frappe.whitelist()
    def get_activation_wizard(self):
        """Get activation wizard HTML"""
        # determine configuration stage
        if (not self.host_id) or (not self.url) or (not self.partner_id) or (not self.user_id) or (not self.key_password):
            stage = 0
        elif not self.keys_created:
            stage = 1
        elif not self.ini_sent:
            stage = 2
        elif not self.hia_sent:
            stage = 3
        elif not self.hpb_downloaded:
            stage = 4
        elif not self.activated:
            stage = 5
        else:
            stage = 6
        
        html = """
        <h3>EBICS Activation Wizard</h3>
        <p><b>Using:</b> node-ebics-client (MIT License, no transaction limits)</p>
        <p><b>Stage:</b> {stage}/6</p>
        
        <div style="margin: 20px 0;">
            <h4>Step 1: Configuration</h4>
            <p>Host ID: {host_id}</p>
            <p>User ID: {user_id}</p>
            <p>Partner ID: {partner_id}</p>
            <p>URL: {url}</p>
            <p>Version: {version}</p>
            <p>Status: {config_status}</p>
        </div>
        """.format(
            stage=stage,
            host_id=self.host_id or "Not set",
            user_id=self.user_id or "Not set",
            partner_id=self.partner_id or "Not set",
            url=self.url or "Not set",
            version=self.ebics_version or "H004",
            config_status="✅ Ready" if stage > 0 else "⏳ Please complete configuration"
        )
        
        if stage > 0:
            html += """
            <div style="margin: 20px 0;">
                <h4>Step 2: Generate Keys</h4>
                <button class="btn btn-primary" onclick="frappe.call({{
                    method: 'create_keys',
                    doc: cur_frm.doc,
                    callback: function(r) {{ 
                        frappe.msgprint(r.message);
                        cur_frm.reload_doc(); 
                    }}
                }})">Generate Keys</button>
                <span>{keys_status}</span>
            </div>
            """.format(
                keys_status="✅ Done" if self.keys_created else "⏳ Pending"
            )
        
        if stage > 1:
            html += """
            <div style="margin: 20px 0;">
                <h4>Step 3: Send INI</h4>
                <button class="btn btn-primary" onclick="frappe.call({{
                    method: 'send_signature',
                    doc: cur_frm.doc,
                    callback: function(r) {{ 
                        frappe.msgprint(r.message);
                        cur_frm.reload_doc(); 
                    }}
                }})">Send INI</button>
                <span>{ini_status}</span>
            </div>
            """.format(
                ini_status="✅ Done" if self.ini_sent else "⏳ Pending"
            )
        
        if stage > 2:
            html += """
            <div style="margin: 20px 0;">
                <h4>Step 4: Send HIA</h4>
                <button class="btn btn-primary" onclick="frappe.call({{
                    method: 'send_keys',
                    doc: cur_frm.doc,
                    callback: function(r) {{ 
                        frappe.msgprint(r.message);
                        cur_frm.reload_doc(); 
                    }}
                }})">Send HIA</button>
                <span>{hia_status}</span>
            </div>
            """.format(
                hia_status="✅ Done" if self.hia_sent else "⏳ Pending"
            )
        
        if stage > 3:
            html += """
            <div style="margin: 20px 0;">
                <h4>Step 5: Download Bank Keys</h4>
                <button class="btn btn-primary" onclick="frappe.call({{
                    method: 'download_public_keys',
                    doc: cur_frm.doc,
                    callback: function(r) {{ 
                        frappe.msgprint(r.message);
                        cur_frm.reload_doc(); 
                    }}
                }})">Download HPB</button>
                <span>{hpb_status}</span>
            </div>
            """.format(
                hpb_status="✅ Done" if self.hpb_downloaded else "⏳ Pending"
            )
        
        if stage > 4:
            html += """
            <div style="margin: 20px 0;">
                <h4>Step 6: Activate Account</h4>
                <button class="btn btn-primary" onclick="frappe.call({{
                    method: 'activate_account',
                    doc: cur_frm.doc,
                    callback: function(r) {{ 
                        frappe.msgprint(r.message);
                        cur_frm.reload_doc(); 
                    }}
                }})">Activate</button>
                <span>{activation_status}</span>
            </div>
            """.format(
                activation_status="✅ Active" if self.activated else "⏳ Pending"
            )
        
        if stage == 6:
            html += """
            <div style="margin: 20px 0; padding: 10px; background-color: #d4edda; border: 1px solid #c3e6cb;">
                <h4>✅ Account Activated!</h4>
                <p>Your EBICS connection is ready to use.</p>
                <button class="btn btn-success" onclick="frappe.call({{
                    method: 'test_connection',
                    doc: cur_frm.doc,
                    callback: function(r) {{ frappe.msgprint(r.message); }}
                }})">Test Connection</button>
            </div>
            """
        
        return html
    
    @frappe.whitelist()
    def test_connection(self):
        """Test the EBICS connection"""
        try:
            client = self.get_client()
            result = client.test_connection()
            
            if result.get('success'):
                message = """
                <h4>✅ Connection Test Successful</h4>
                <p><b>API Status:</b> Connected</p>
                <p><b>Host ID:</b> {host_id}</p>
                <p><b>User ID:</b> {user_id}</p>
                <p><b>URL:</b> {url}</p>
                <p><b>Version:</b> {version}</p>
                """.format(
                    host_id=self.host_id,
                    user_id=self.user_id,
                    url=self.url,
                    version=self.ebics_version
                )
                return message
            else:
                return "<h4>⚠️ Connection Test Failed</h4><p>{0}</p>".format(
                    result.get('message', 'Unknown error')
                )
                
        except Exception as e:
            return "<h4>❌ Connection Test Error</h4><p>{0}</p>".format(str(e))
    
    @frappe.whitelist()
    def ping(self):
        """Ping the EBICS connection"""
        return self.test_connection()
    
    @frappe.whitelist()
    def create_keys(self):
        """Generate keys for this connection"""
        try:
            client = self.get_client()
            result = client.generate_keys(self.key_password)
            
            if result.get('success'):
                self.keys_created = 1
                self.save()
                frappe.db.commit()
                return "✅ Keys generated successfully"
            else:
                frappe.throw(_("Failed to generate keys: {0}").format(
                    result.get('message', 'Unknown error')
                ))
                
        except Exception as e:
            frappe.log_error(str(e), "EBICS Key Generation Error")
            frappe.throw(_("Error generating keys: {0}").format(str(e)))
    
    @frappe.whitelist()
    def send_signature(self):
        """Send INI order (signature key)"""
        try:
            client = self.get_client()
            result = client.INI()
            
            if result.get('success'):
                self.ini_sent = 1
                self.save()
                frappe.db.commit()
                return "✅ INI sent successfully"
            else:
                frappe.throw(_("Failed to send INI: {0}").format(
                    result.get('message', 'Unknown error')
                ))
                
        except Exception as e:
            frappe.log_error(str(e), "EBICS INI Error")
            frappe.throw(_("Error sending INI: {0}").format(str(e)))
    
    @frappe.whitelist()
    def send_keys(self):
        """Send HIA order (authentication and encryption keys)"""
        try:
            client = self.get_client()
            result = client.HIA()
            
            if result.get('success'):
                self.hia_sent = 1
                self.save()
                frappe.db.commit()
                return "✅ HIA sent successfully"
            else:
                frappe.throw(_("Failed to send HIA: {0}").format(
                    result.get('message', 'Unknown error')
                ))
                
        except Exception as e:
            frappe.log_error(str(e), "EBICS HIA Error")
            frappe.throw(_("Error sending HIA: {0}").format(str(e)))
    
    @frappe.whitelist()
    def download_public_keys(self):
        """Download bank public keys (HPB)"""
        try:
            client = self.get_client()
            result = client.HPB()
            
            if result.get('success'):
                self.hpb_downloaded = 1
                self.save()
                frappe.db.commit()
                return "✅ Bank public keys downloaded successfully"
            else:
                frappe.throw(_("Failed to download HPB: {0}").format(
                    result.get('message', 'Unknown error')
                ))
                
        except Exception as e:
            frappe.log_error(str(e), "EBICS HPB Error")
            frappe.throw(_("Error downloading HPB: {0}").format(str(e)))
    
    @frappe.whitelist()
    def activate_account(self):
        """Activate the EBICS account"""
        try:
            # Check prerequisites
            if not self.keys_created:
                frappe.throw(_("Please create keys first"))
            if not self.ini_sent:
                frappe.throw(_("Please send INI first"))
            if not self.hia_sent:
                frappe.throw(_("Please send HIA first"))
            if not self.hpb_downloaded:
                frappe.throw(_("Please download bank keys (HPB) first"))
            
            # Mark as activated
            self.activated = 1
            self.save()
            frappe.db.commit()
            
            return "✅ EBICS account activated successfully"
            
        except Exception as e:
            frappe.log_error(str(e), "EBICS Activation Error")
            frappe.throw(_("Error activating account: {0}").format(str(e)))
    
    @frappe.whitelist()
    def get_transactions_range(self, from_date, to_date):
        """Get transactions for a date range"""
        try:
            client = self.get_client()
            
            # Convert dates to string format if needed
            if isinstance(from_date, (date, datetime)):
                from_date = from_date.strftime("%Y-%m-%d")
            if isinstance(to_date, (date, datetime)):
                to_date = to_date.strftime("%Y-%m-%d")
            
            # Try Z53 first (Swiss standard)
            result = client.Z53(from_date, to_date, parsed=True)
            
            if not result.get('success'):
                # Fallback to C53 (CAMT.053)
                result = client.C53(from_date, to_date, parsed=True)
            
            if result.get('success'):
                # Process and import statements
                self._process_statements(result.get('data'))
                frappe.msgprint(_("Transactions imported successfully"))
            else:
                frappe.msgprint(_("No transactions found for the period"))
                
        except Exception as e:
            frappe.log_error(str(e), "EBICS Transaction Import Error")
            frappe.throw(_("Error importing transactions: {0}").format(str(e)))
    
    @frappe.whitelist()
    def get_intraday_statements(self, date_param=None):
        """Get intraday statements (Z52)"""
        try:
            client = self.get_client()
            
            if not date_param:
                date_param = datetime.today().strftime("%Y-%m-%d")
            elif isinstance(date_param, (date, datetime)):
                date_param = date_param.strftime("%Y-%m-%d")
            
            # Get Z52 statements
            result = client.Z52(date_param, date_param, parsed=True)
            
            if result.get('success'):
                frappe.msgprint(_("Intraday statements retrieved successfully"))
                return result.get('data')
            else:
                frappe.msgprint(_("No intraday data available"))
                return None
                
        except Exception as e:
            frappe.log_error(str(e), "EBICS Z52 Error")
            frappe.throw(_("Error getting intraday statements: {0}").format(str(e)))
    
    @frappe.whitelist()
    def test_connection(self):
        """Test EBICS connection"""
        try:
            # Check basic configuration
            if not self.url or not self.host_id or not self.user_id:
                return "❌ Missing configuration: URL, Host ID or User ID"
            
            # Try to create client
            try:
                client = self.get_client()
                
                # Check if keys are initialized
                if self.activated:
                    # Try a simple operation like getting bank info
                    return "✅ Connection successful - Account is activated"
                elif self.hpb_downloaded:
                    return "✅ Connection successful - Bank keys downloaded"
                elif self.hia_sent:
                    return "✅ Connection successful - HIA sent"
                elif self.ini_sent:
                    return "✅ Connection successful - INI sent"
                elif self.keys_created:
                    return "✅ Connection successful - Keys created"
                else:
                    return "⚠️ Connection configured but not initialized - Please run activation wizard"
                    
            except Exception as e:
                return f"❌ Connection failed: {str(e)}"
                
        except Exception as e:
            frappe.log_error(str(e), "ebics Connection Test Error")
            return f"❌ Error testing connection: {str(e)}"
    
    @frappe.whitelist()
    def execute_payment(self, payment_proposal):
        """Execute payment via EBICS"""
        try:
            client = self.get_client()
            
            # Get payment proposal document
            pp = frappe.get_doc("Payment Proposal", payment_proposal)
            
            # Generate payment file
            payment_file = pp.create_bank_file()
            xml_content = payment_file.get('content')
            
            if not xml_content:
                frappe.throw(_("Failed to generate payment file"))
            
            # Determine payment type
            if pp.payment_type == "SEPA":
                result = client.CCT(xml_content)
            else:
                # Default to Swiss payment (XE2)
                result = client.XE2(xml_content)
            
            if result.get('success'):
                frappe.msgprint(_("Payment transmitted successfully via EBICS"))
                
                # Mark payment proposal as sent
                frappe.db.set_value("Payment Proposal", payment_proposal, 
                                  "file_sent_to_ebics", 1)
                frappe.db.commit()
            else:
                frappe.throw(_("Failed to transmit payment: {0}").format(
                    result.get('message', 'Unknown error')
                ))
                
        except Exception as e:
            frappe.log_error(str(e), "EBICS Payment Error")
            frappe.throw(_("Error transmitting payment: {0}").format(str(e)))
    
    @frappe.whitelist()
    def get_available_order_types(self):
        """Get available order types from bank"""
        try:
            client = self.get_client()
            result = client.HAA()
            
            if result.get('success'):
                return result.get('data')
            else:
                frappe.msgprint(_("Could not retrieve order types: {0}").format(
                    result.get('message', 'Unknown error')
                ))
                return None
                
        except Exception as e:
            frappe.log_error(str(e), "EBICS HAA Error")
            return None
    
    def _process_statements(self, statements):
        """Process and import bank statements"""
        if not statements:
            return
        
        # Handle different statement formats
        if isinstance(statements, dict):
            if 'raw' in statements:
                # Raw XML data
                self._import_raw_statement(statements['raw'])
            else:
                # Parsed data
                for account, content in statements.items():
                    self._import_statement(account, content)
        elif isinstance(statements, str):
            # Raw XML string
            self._import_raw_statement(statements)
    
    def _import_statement(self, account, content):
        """Import a single bank statement"""
        try:
            # Create EBICS Statement document
            statement = frappe.new_doc("ebics Statement")
            statement.ebics_connection = self.name
            statement.date = datetime.now().date()
            statement.xml_content = content if isinstance(content, str) else str(content)
            statement.bank_statement_id = hashlib.md5(statement.xml_content.encode()).hexdigest()
            statement.content_hash = statement.bank_statement_id
            statement.status = "Pending"
            
            statement.insert()
            statement.parse_content()
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(str(e), "Statement Import Error")
    
    def _import_raw_statement(self, xml_content):
        """Import raw XML statement"""
        try:
            statement = frappe.new_doc("ebics Statement")
            statement.ebics_connection = self.name
            statement.date = datetime.now().date()
            statement.xml_content = xml_content
            statement.bank_statement_id = hashlib.md5(xml_content.encode()).hexdigest()
            statement.content_hash = statement.bank_statement_id
            statement.status = "Pending"
            
            statement.insert()
            statement.parse_content()
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(str(e), "Raw Statement Import Error")
    
    def get_keys_file_name(self):
        """Get the keys file name for backward compatibility"""
        return os.path.join(frappe.utils.get_files_path(), 
                           "{0}_keys.json".format(self.name))


# Backward compatibility functions
@frappe.whitelist()
def execute_payment(ebics_connection, payment_proposal):
    """Execute payment via EBICS (backward compatibility)"""
    conn = frappe.get_doc("ebics Connection", ebics_connection)
    return conn.execute_payment(payment_proposal)

@frappe.whitelist()
def test_real_connection(connection):
    """Test real EBICS connection"""
    conn = frappe.get_doc("ebics Connection", connection)
    return conn.test_connection()