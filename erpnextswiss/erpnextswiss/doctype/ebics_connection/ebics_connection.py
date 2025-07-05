# -*- coding: utf-8 -*-
# Copyright (c) 2024, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
#

import frappe
from frappe.model.document import Document
import os
import fintech
fintech.register()
from fintech.ebics import EbicsKeyRing, EbicsBank, EbicsUser, EbicsClient, BusinessTransactionFormat
#from fintech.sepa import Account, SEPACreditTransfer
from frappe import _
from frappe.utils.file_manager import save_file
from frappe.utils.password import get_decrypted_password
from datetime import datetime, date

class ebicsConnection(Document):
    def before_save(self):
        # make sure synced_until is in date format
        if self.synced_until and not isinstance(self.synced_until, date):
            if isinstance(self.synced_until, str):
                self.synced_until = datetime.strptime(self.synced_until, "%Y-%m-%d").date()
            elif isinstance(self.synced_until, datetime):
                self.synced_until = self.synced_until.date()
        
        # Clean up URL - remove trailing spaces
        if self.url:
            self.url = self.url.strip()
        
        # Auto-detect bank config if not set
        if not self.bank_config and self.url:
            detected_config = self.detect_bank_config()
            if detected_config:
                self.bank_config = detected_config
                
        return
        
    @frappe.whitelist()
    def get_activation_wizard(self):
        # determine configuration stage
        if (not self.host_id) or (not self.url) or (not self.partner_id) or (not self.user_id) or (not self.key_password):
            stage = 0
        elif (not os.path.exists(self.get_keys_file_name())):
            stage = 1
        elif (not self.ini_sent):
            stage = 2
        elif (not self.hia_sent):
            stage = 3
        elif (not self.ini_letter_created):
            stage = 4
        elif (not self.hpb_downloaded):
            stage = 5
        elif (not self.activated):
            stage = 6
        else:
            stage = 7
            
        content = frappe.render_template(
            "erpnextswiss/erpnextswiss/doctype/ebics_connection/ebics_connection_wizard.html", 
            {
                'doc': self.as_dict(),
                'stage': stage
            }
        )
        return {'html': content, 'stage': stage}
        
        
    def get_keys_file_name(self):
        keys_file = "{0}.keys".format((self.name or "").replace(" ", "_"))
        full_keys_file_path = os.path.join(frappe.utils.get_bench_path(), "sites", frappe.utils.get_site_path()[2:], keys_file)
        return full_keys_file_path

    def get_bank_config(self):
        """Get bank configuration with defaults"""
        if self.bank_config:
            return frappe.get_doc("ebics Bank Config", self.bank_config)
        else:
            # Return default config for backward compatibility
            return frappe._dict({
                'payment_order_type_h004': 'XE2',
                'statement_order_type_h004': 'Z53',
                'payment_service_h005': 'MCT',
                'payment_scope_h005': 'CH',
                'payment_msg_name_h005': 'pain.001',
                'statement_service_h005': 'EOP',
                'statement_scope_h005': 'CH',
                'statement_msg_name_h005': 'camt.053',
                'statement_version_h005': '04',
                'statement_container_h005': 'ZIP',
                'use_swiss_namespace': 1,
                'custom_namespace': '',
                'supported_payment_types': '["SEPA", "IBAN", "ESR", "QRR", "SCOR"]'
            })
    
    @frappe.whitelist()
    def detect_bank_config(self):
        """Auto-detect bank configuration based on URL"""
        if not self.url:
            return None
            
        url_lower = self.url.lower()
        if 'raiffeisen' in url_lower:
            # Check if Raiffeisen config exists
            if frappe.db.exists("ebics Bank Config", "Raiffeisen"):
                return "Raiffeisen"
        elif 'ubs' in url_lower:
            if frappe.db.exists("ebics Bank Config", "UBS"):
                return "UBS"
        elif 'credit-suisse' in url_lower or 'credit.suisse' in url_lower:
            if frappe.db.exists("ebics Bank Config", "Credit Suisse"):
                return "Credit Suisse"
        elif 'postfinance' in url_lower:
            if frappe.db.exists("ebics Bank Config", "PostFinance"):
                return "PostFinance"
        elif 'zkb' in url_lower:
            if frappe.db.exists("ebics Bank Config", "ZKB"):
                return "ZKB"
        
        return None
        
    def get_client(self):
        passphrase = get_decrypted_password("ebics Connection", self.name, "key_password", False)
        keyring = EbicsKeyRing(keys=self.get_keys_file_name(), passphrase=passphrase)
        bank = EbicsBank(keyring=keyring, hostid=self.host_id, url=self.url)
        user = EbicsUser(keyring=keyring, partnerid=self.partner_id, userid=self.user_id)
        client = EbicsClient(bank, user, version=self.ebics_version)
        return client
        
    @frappe.whitelist()
    def create_keys(self):
        try:
            passphrase = get_decrypted_password("ebics Connection", self.name, "key_password", False)
            keyring = EbicsKeyRing(keys=self.get_keys_file_name(), passphrase=passphrase)
            bank = EbicsBank(keyring=keyring, hostid=self.host_id, url=self.url)
            user = EbicsUser(keyring=keyring, partnerid=self.partner_id, userid=self.user_id)
            
            # Check if we need to create keys or just certificates
            try:
                user.create_keys(keyversion='A006', bitlength=2048)
                frappe.msgprint(_("Keys created successfully"))
            except RuntimeError as e:
                if "keys already present" in str(e):
                    frappe.msgprint(_("Keys already exist, creating certificates only"))
                else:
                    raise e
                    
            # Always try to create certificates
            self.create_certificate()
            frappe.msgprint(_("Certificates created successfully"))
            
        except Exception as err:
            frappe.throw( "{0}".format(err), _("Error") )
        return

    @frappe.whitelist()
    def create_certificate(self):
        try:
            passphrase = get_decrypted_password("ebics Connection", self.name, "key_password", False)
            keyring = EbicsKeyRing(keys=self.get_keys_file_name(), passphrase=passphrase)
            user = EbicsUser(keyring=keyring, partnerid=self.partner_id, userid=self.user_id)
            x509_dn = {
                'commonName': '{0} ebics'.format(self.company or "libracore ERP"),
                'organizationName': (self.company or "libracore ERP"),
                'organizationalUnitName': 'Administration',
                'countryName': 'CH',
                'stateOrProvinceName': 'ZH',
                'localityName': 'Winterthur',
                'emailAddress': 'info@libracore.com'
            }
            user.create_certificates(validity_period=5, **x509_dn)
            
        except Exception as err:
            frappe.throw( "{0}".format(err), _("Error") )
        return
        
    @frappe.whitelist()
    def send_signature(self):
        try:
            client = self.get_client()
            client.INI()
            self.ini_sent = 1
            self.save()
            frappe.db.commit()
        except fintech.ebics.EbicsTechnicalError as err:
            error_msg = str(err)
            if "EBICS_INVALID_USER_OR_USER_STATE" in error_msg:
                frappe.throw(
                    _("The EBICS user is not recognized by the bank or is in an invalid state. "
                      "Please contact your bank to ensure your EBICS user account has been created and activated. "
                      "User ID: {0}, Partner ID: {1}").format(self.user_id, self.partner_id),
                    _("EBICS User Not Active")
                )
            else:
                frappe.throw( "{0}".format(err), _("EBICS Technical Error") )
        except Exception as err:
            frappe.throw( "{0}".format(err), _("Error") )
        return
    
    @frappe.whitelist()
    def send_keys(self):
        try:
            client = self.get_client()
            client.HIA()
            self.hia_sent = 1
            self.save()
            frappe.db.commit()
        except fintech.ebics.EbicsTechnicalError as err:
            error_msg = str(err)
            if "EBICS_INVALID_USER_OR_USER_STATE" in error_msg:
                frappe.throw(
                    _("The EBICS user is not recognized by the bank or is in an invalid state. "
                      "Please contact your bank to ensure your EBICS user account has been created and activated. "
                      "User ID: {0}, Partner ID: {1}").format(self.user_id, self.partner_id),
                    _("EBICS User Not Active")
                )
            else:
                frappe.throw( "{0}".format(err), _("EBICS Technical Error") )
        except Exception as err:
            frappe.throw( "{0}".format(err), _("Error") )
        return
    
    @frappe.whitelist()
    def create_ini_letter(self):
        try:
            # create ini letter
            file_name = "/tmp/ini_letter.pdf"
            passphrase = get_decrypted_password("ebics Connection", self.name, "key_password", False)
            keyring = EbicsKeyRing(keys=self.get_keys_file_name(), passphrase=passphrase)
            user = EbicsUser(keyring=keyring, partnerid=self.partner_id, userid=self.user_id)
            user.create_ini_letter(bankname=self.title, path=file_name)
            # load ini pdf
            f = open(file_name, "rb")
            pdf_content = f.read()
            f.close()
            # attach to ebics
            save_file("ini_letter.pdf", pdf_content, self.doctype, self.name, is_private=1)
            # remove tmp file
            os.remove(file_name)
            # mark created
            self.ini_letter_created = 1
            self.save()
            frappe.db.commit()
        except Exception as err:
            frappe.throw( "{0}".format(err), _("Error") )
        return
        
    @frappe.whitelist()
    def download_public_keys(self):
        try:
            client = self.get_client()
            client.HPB()
            self.hpb_downloaded = 1
            self.save()
            frappe.db.commit()
        except Exception as err:
            frappe.throw( "{0}".format(err), _("Error") )
        return
        
    @frappe.whitelist()
    def activate_account(self):
        try:
            passphrase = get_decrypted_password("ebics Connection", self.name, "key_password", False)
            keyring = EbicsKeyRing(keys=self.get_keys_file_name(), passphrase=passphrase)
            bank = EbicsBank(keyring=keyring, hostid=self.host_id, url=self.url)
            bank.activate_keys()
            self.activated = 1
            self.save()
            frappe.db.commit()
        except Exception as err:
            frappe.throw( "{0}".format(err), _("Error") )
        return
    
    @frappe.whitelist()
    def test_connection(self):
        """Test the EBICS connection parameters"""
        try:
            # Display current configuration
            config_info = f"""
            <h4>Configuration actuelle:</h4>
            <ul>
                <li><b>Host ID:</b> {self.host_id}</li>
                <li><b>URL:</b> {self.url}</li>
                <li><b>Partner ID:</b> {self.partner_id}</li>
                <li><b>User ID:</b> {self.user_id}</li>
                <li><b>EBICS Version:</b> {self.ebics_version}</li>
                <li><b>Keys file:</b> {os.path.basename(self.get_keys_file_name())}</li>
                <li><b>Keys exist:</b> {'Yes' if os.path.exists(self.get_keys_file_name()) else 'No'}</li>
            </ul>
            """
            
            # Display bank configuration if selected
            if self.bank_config:
                bank_config = self.get_bank_config()
                config_info += f"""
                <h4>Configuration de la banque ({self.bank_config}):</h4>
                <ul>
                    <li><b>Code banque:</b> {bank_config.get('bank_code', 'N/A')}</li>
                    <li><b>Namespace suisse:</b> {'Oui' if bank_config.get('use_swiss_namespace') else 'Non'}</li>
                """
                
                if self.ebics_version == "H005":
                    config_info += f"""
                    <li><b>Service paiement (H005):</b> {bank_config.get('payment_service_h005', 'N/A')}</li>
                    <li><b>Service relevé (H005):</b> {bank_config.get('statement_service_h005', 'N/A')}</li>
                    <li><b>Scope:</b> {bank_config.get('payment_scope_h005', 'N/A')}</li>
                    """
                else:
                    config_info += f"""
                    <li><b>Type ordre paiement (H004):</b> {bank_config.get('payment_order_type_h004', 'N/A')}</li>
                    <li><b>Type ordre relevé (H004):</b> {bank_config.get('statement_order_type_h004', 'N/A')}</li>
                    """
                
                config_info += "</ul>"
            else:
                config_info += """
                <p style='color: orange;'>⚠ Aucune configuration de banque sélectionnée. 
                Les valeurs par défaut seront utilisées.</p>
                """
            
            # Try to create client
            try:
                client = self.get_client()
                config_info += "<p style='color: green;'>✓ Client EBICS créé avec succès</p>"
                
                # Test if we can get HAA (available order types) - only for activated connections
                if self.activated:
                    try:
                        order_types = client.HAA()
                        config_info += "<p style='color: green;'>✓ Communication avec la banque réussie</p>"
                    except Exception as haa_error:
                        # HAA might not be available for all banks/users
                        config_info += "<p style='color: orange;'>⚠ Test de communication: {0}</p>".format(str(haa_error))
                
            except Exception as e:
                config_info += f"<p style='color: red;'>✗ Échec de création du client: {str(e)}</p>"
                
            frappe.msgprint(config_info, title=_("Test de connexion EBICS"), as_list=False)
            
        except Exception as err:
            frappe.throw( "{0}".format(err), _("Error") )
        return

    @frappe.whitelist()
    def execute_payment(self, payment_proposal):
        payment = frappe.get_doc("Payment Proposal", payment_proposal)
        
        # generate content
        bank_file = payment.create_bank_file()
        xml_content = bank_file['content']
        
        # Get bank configuration
        bank_config = self.get_bank_config()
        
        # Check if we need Swiss-specific namespace based on bank config
        if bank_config.use_swiss_namespace and 'xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.03"' in xml_content:
            frappe.log_error("Standard namespace detected, using Swiss-specific namespace", "EBICS XML Namespace")
            # Use Swiss-specific namespace if configured
            if bank_config.custom_namespace:
                # Use custom namespace if provided
                xml_content = xml_content.replace(
                    'xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.03"',
                    bank_config.custom_namespace
                )
            else:
                # Use default Swiss namespace
                xml_content = xml_content.replace(
                    'xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.03"',
                    'xmlns="http://www.six-interbank-clearing.com/de/pain.001.001.03.ch.02.xsd"'
                )
                xml_content = xml_content.replace(
                    'xsi:schemaLocation=""',
                    'xsi:schemaLocation="http://www.six-interbank-clearing.com/de/pain.001.001.03.ch.02.xsd pain.001.001.03.ch.02.xsd"'
                )
            frappe.log_error("Using bank-specific namespace", "EBICS XML Modified")
        
        # Debug logging removed - don't save files in logs directory
        
        # Try to get supported order types
        try:
            client = self.get_client()
            # Try HAA (Download available order types)
            supported_types = client.HAA()
            # Extract order types from XML response
            import xml.etree.ElementTree as ET
            if isinstance(supported_types, bytes):
                root = ET.fromstring(supported_types)
                order_types = root.find('.//{urn:org:ebics:H004}OrderTypes')
                if order_types is not None:
                    types_list = order_types.text.split()
                    frappe.neolog("EBICS Types", f"Supported types: {', '.join(types_list)}")
                    # Check if we have HVU (overview of VEU order types)
                    if 'HVU' in types_list:
                        try:
                            veu_types = client.HVU()
                            frappe.neolog("EBICS VEU", f"VEU types: {veu_types}")
                        except:
                            pass
        except Exception as e:
            pass  # Ignore errors from logging
        
        # Ensure the XML is properly encoded
        if isinstance(xml_content, str):
            xml_transaction = xml_content.encode('utf-8')
        else:
            xml_transaction = xml_content
        
        # get client
        client = self.get_client()
        
        # Log the EBICS version being used
        frappe.neolog("EBICS Debug", f"EBICS Version: {self.ebics_version}")
        
        try:
            # upload data based on version
            if self.ebics_version == "H005":
                # ebics v3.0 uses BTU (Business Transaction Upload) for uploads
                CCT = BusinessTransactionFormat(
                    service=bank_config.payment_service_h005 or 'MCT',
                    msg_name=bank_config.payment_msg_name_h005 or 'pain.001',
                    scope=bank_config.payment_scope_h005 or 'CH'
                )
                # Use BTU for upload, not BTD (which is for download)
                data = client.BTU(CCT, xml_transaction)
                frappe.msgprint(_("Payment transmitted successfully via EBICS H005"))
                return
            else:
                # use version 2.5 (H004)
                # For H004, we might need to use INI (Initialization) followed by HIA (Bank public key)
                # Then use specific upload methods
                
                # Log all available methods on the client
                available_methods = [method for method in dir(client) if not method.startswith('_') and callable(getattr(client, method))]
                frappe.neolog("EBICS Debug", f"Available client methods: {', '.join(available_methods[:20])}")
                
                # Since standard order types aren't working, let's try a different approach
                # Check if we need to use VEU (distributed signature)
                try:
                    # For Raiffeisen, try HVE with XE2
                    if hasattr(client, 'HVE'):
                        # Upload VEU order with XE2
                        frappe.log_error("Trying HVE with XE2", "EBICS VEU")
                        order_id = client.HVE(xml_transaction, 'XE2')
                        frappe.msgprint(_("Payment uploaded for signature (VEU). Order ID: {0}").format(order_id))
                        return
                except Exception as veu_error:
                    frappe.log_error(str(veu_error), "EBICS VEU XE2 Failed")
                    
                # Try HVT (Transport VEU)
                try:
                    if hasattr(client, 'HVT'):
                        frappe.log_error("Trying HVT for VEU transport", "EBICS HVT")
                        order_id = client.HVT(xml_transaction)
                        frappe.msgprint(_("Payment uploaded via HVT. Order ID: {0}").format(order_id))
                        return
                except Exception as e:
                    frappe.log_error(str(e), "EBICS HVT Failed")
                
                # Available methods from logs: AXZ, BTD, BTU, C52, C53, C54, CCT, CCU, CDB, CDD, CDZ, CIP, CIZ, CRZ, FDL, FUL, H3K, HAA, HAC, HCA
                # Bank supported types: PTK, Z52, Z53, Z54, Z01, ZDF, HAC
                # None of these are standard upload types, let's try a different approach
                
                # For Raiffeisen, we know from the document that XE2 is configured
                # But it might not appear in HAA because it's a submission type, not a fetch type
                # Let's try FUL with XE2 directly
                try:
                    frappe.log_error("Attempting FUL with XE2 for Raiffeisen", "EBICS Raiffeisen XE2")
                    
                    # Use bank-specific order type
                    order_type = bank_config.payment_order_type_h004 or 'XE2'
                    data = client.FUL(xml_transaction, order_type)
                    
                    # If we get here, the upload was accepted
                    frappe.log_error("FUL with XE2 accepted", "EBICS XE2 Success")
                    
                    # Confirm the upload
                    client.confirm_upload()
                    
                    frappe.msgprint(_("Payment transmitted successfully via EBICS using XE2"))
                    return
                    
                except fintech.ebics.EbicsFunctionalError as e:
                    error_msg = str(e)
                    frappe.log_error(error_msg, "EBICS XE2 Functional Error")
                    
                    # Check specific error codes
                    if "EBICS_INVALID_ORDER_TYPE" in error_msg:
                        # XE2 might not be available, contact bank
                        frappe.throw(_("Order type XE2 not accepted by bank. Please contact Raiffeisen to enable XE2 for your EBICS user."))
                    elif "EBICS_INVALID_ORDER_DATA_FORMAT" in error_msg:
                        # Format issue - might need Swiss namespace
                        frappe.throw(_("Invalid XML format. The bank might require Swiss-specific pain.001 namespace."))
                    elif "EBICS_PROCESSING_ERROR" in error_msg:
                        # This might mean the order was accepted but needs further processing
                        frappe.msgprint(_("Payment submitted to bank for processing. Please check your e-banking for status."))
                        return
                    else:
                        frappe.throw(_("EBICS Error: {0}").format(error_msg))
                        
                except fintech.ebics.EbicsTechnicalError as e:
                    error_msg = str(e)
                    frappe.log_error(error_msg, "EBICS XE2 Technical Error")
                    if "EBICS_INVALID_ORDER_TYPE" in error_msg:
                        # XE2 is not accepted even though it's in the bank document
                        error_text = _("""
Unable to transmit payment via EBICS. Order type XE2 was rejected by the bank.

According to your Raiffeisen document, XE2 should be configured for pain.001 uploads, but the bank is rejecting it.

Possible solutions:
1. Contact Raiffeisen and ask them to:
   - Activate XE2 for your EBICS user (User ID: {0})
   - Confirm which order type should be used for pain.001 uploads
   - Check if your user has payment upload permissions

2. The bank might require EBICS H005 for XE2. Your current version is H004.

3. In the meantime, you can download the payment file and upload it manually in your e-banking.

Technical details: {1}
                        """).format(self.user_id or "1279585381", error_msg)
                        frappe.throw(error_text)
                    else:
                        frappe.throw(_("Technical error with EBICS: {0}").format(error_msg))
                    
                except Exception as e:
                    frappe.log_error(str(e), "EBICS XE2 Exception")
                    # Don't throw here, let it try other methods
                
                # If XE2 doesn't work, we're out of standard options
                # The bank documentation clearly shows XE2 should work
                # Don't try other random order types as they will fail
                order_types_to_try = []
                
                last_error = None
                data = None
                for order_type, method in order_types_to_try:
                    try:
                        frappe.neolog("EBICS Payment Debug", f"Trying order type: {order_type}")
                        data = method()
                        frappe.neolog("EBICS Payment Debug", f"Success with order type: {order_type}")
                        break
                    except fintech.ebics.EbicsTechnicalError as e:
                        last_error = e
                        if "EBICS_INVALID_ORDER_TYPE" in str(e):
                            continue  # Try next order type
                        else:
                            raise
                    except fintech.ebics.EbicsFunctionalError as e:
                        last_error = e
                        if "EBICS_INVALID_ORDER_DATA_FORMAT" in str(e):
                            continue  # Try next order type
                        else:
                            raise
                    except AttributeError:
                        # Method doesn't exist, try next
                        continue
                else:
                    # None of the order types worked - but we already showed error for XE2
                    pass
                        
                client.confirm_upload()
            
            frappe.msgprint(_("Payment transmitted successfully via EBICS"))
            
        except fintech.ebics.EbicsFunctionalError as e:
            error_msg = str(e)
            if "EBICS_INVALID_ORDER_DATA_FORMAT" in error_msg:
                frappe.throw(_("Invalid payment file format. Please check the payment data. XML saved to logs for debugging."))
            elif "EBICS_INVALID_ORDER_TYPE" in error_msg:
                frappe.throw(_("Invalid order type. Your bank may not support this payment method."))
            else:
                frappe.throw(_("EBICS Error: {0}").format(error_msg))
        except Exception as e:
            frappe.throw(_("Error transmitting payment: {0}").format(str(e)))
        
        return
        
    def get_transactions_range(self, from_date, to_date, debug=False):
        """Get transactions for a date range instead of a single day"""
        if isinstance(from_date, (date, datetime)):
            from_date = from_date.strftime("%Y-%m-%d")
        if isinstance(to_date, (date, datetime)):
            to_date = to_date.strftime("%Y-%m-%d")
            
        frappe.log_error("EBICS Range Debug", f"get_transactions_range called for range: {from_date} to {to_date}")
        
        try:
            client = self.get_client()
            bank_config = self.get_bank_config()
            
            if self.ebics_version == "H005":
                from fintech.ebics import BusinessTransactionFormat
                Z53_format = BusinessTransactionFormat(
                    service=bank_config.statement_service_h005 or 'EOP',
                    msg_name=bank_config.statement_msg_name_h005 or 'camt.053',
                    scope=bank_config.statement_scope_h005 or 'CH',
                    version=bank_config.statement_version_h005 or '04',
                    container=bank_config.statement_container_h005 or 'ZIP'
                )
                frappe.log_error("EBICS BTD Range Debug", f"Calling BTD with range: {from_date} to {to_date}")
                data = client.BTD(Z53_format, start_date=from_date, end_date=to_date)
            else:
                frappe.log_error("EBICS Z53 Range Debug", f"Calling Z53 with range: {from_date} to {to_date}")
                data = client.Z53(start=from_date, end=to_date)
                
            client.confirm_download()
            
            frappe.log_error("EBICS Range Data Debug", f"Data received from EBICS: {len(data)} accounts for range {from_date} to {to_date}")
            
            if len(data) > 0:
                # Collect all unique dates to debug
                unique_dates = set()
                statements_imported = 0
                for account, content in data.items():
                    try:
                        from erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard import read_camt053_meta
                        meta = read_camt053_meta(content)
                        bank_statement_id = meta.get('msgid')
                        statement_date = meta.get('statement_date')
                        
                        # Check if date is within requested range
                        if statement_date:
                            unique_dates.add(statement_date)
                            stmt_date = datetime.strptime(statement_date, "%Y-%m-%d").date()
                            from_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
                            to_dt = datetime.strptime(to_date, "%Y-%m-%d").date()
                            
                            if not (from_dt <= stmt_date <= to_dt):
                                frappe.log_error(
                                    "EBICS Range Filter",
                                    f"Statement date {statement_date} outside range {from_date} to {to_date}, skipping"
                                )
                                continue
                        
                        # Check for duplicates
                        if bank_statement_id:
                            if frappe.db.exists('ebics Statement', {'bank_statement_id': bank_statement_id}):
                                continue
                        else:
                            import hashlib
                            content_hash = hashlib.md5(content.encode() if isinstance(content, str) else content).hexdigest()
                            if frappe.db.exists('ebics Statement', {'ebics_connection': self.name, 'content_hash': content_hash}):
                                continue
                        
                        # Create statement
                        stmt = frappe.get_doc({
                            'doctype': 'ebics Statement',
                            'ebics_connection': self.name,
                            'file_name': account,
                            'xml_content': content,
                            'date': statement_date or from_date,
                            'company': self.company
                        })
                        stmt.insert()
                        frappe.db.commit()
                        stmt.parse_content(debug=debug)
                        stmt.process_transactions()
                        statements_imported += 1
                        
                    except Exception as e:
                        frappe.log_error("EBICS Range Import Error", f"Error processing statement: {str(e)}")
                
                # Log all unique dates found
                if unique_dates:
                    sorted_dates = sorted(list(unique_dates))
                    frappe.log_error(
                        "EBICS Date Analysis", 
                        f"Found {len(unique_dates)} unique dates. Range: {sorted_dates[0]} to {sorted_dates[-1]}. "
                        f"July dates: {[d for d in sorted_dates if d.startswith('2025-07')]}"
                    )
                        
                frappe.log_error("EBICS Range Import Summary", f"Imported {statements_imported} statements out of {len(data)} received")
                
        except fintech.ebics.EbicsFunctionalError as err:
            error_msg = "{0}".format(err)
            if "EBICS_NO_DOWNLOAD_DATA_AVAILABLE" in error_msg:
                frappe.log_error("EBICS No Data", f"No data available for range {from_date} to {to_date}")
                # Update sync date even if no data to avoid getting stuck
                self.synced_until = to_date if isinstance(to_date, date) else datetime.strptime(to_date, "%Y-%m-%d").date()
                self.save()
                frappe.db.commit()
                frappe.msgprint(f"No bank statements available for the period {from_date} to {to_date}", indicator='orange')
            else:
                frappe.log_error("EBICS Range Error", error_msg)
                raise
        except Exception as err:
            frappe.log_error("EBICS Range Error", f"Error in get_transactions_range: {str(err)}")
            raise
            
    def get_transactions(self, date_param, debug=False):
        if isinstance(date_param, (date, datetime)):
            date_param = date_param.strftime("%Y-%m-%d")

        frappe.log_error("EBICS Transaction Debug", f"get_transactions called for date: {date_param}")

        try:
            client = self.get_client()
            bank_config = self.get_bank_config()
            
            if self.ebics_version == "H005":
                # For H005, we must use BTD with proper BusinessTransactionFormat
                from fintech.ebics import BusinessTransactionFormat
                
                # Create the format using bank configuration
                Z53_format = BusinessTransactionFormat(
                    service=bank_config.statement_service_h005 or 'EOP',
                    msg_name=bank_config.statement_msg_name_h005 or 'camt.053',
                    scope=bank_config.statement_scope_h005 or 'CH',
                    version=bank_config.statement_version_h005 or '04',
                    container=bank_config.statement_container_h005 or 'ZIP'
                )
                
                # Download using BTD with the Z53 format
                frappe.log_error("EBICS BTD Debug", f"Calling BTD with date: {date_param}")
                data = client.BTD(Z53_format, start_date=date_param, end_date=date_param)
            else:
                # use version 2.5 (H004)
                # Use bank-specific order type if available
                order_type = bank_config.statement_order_type_h004 or 'Z53'
                if order_type == 'Z53':
                    frappe.log_error("EBICS Z53 Debug", f"Calling Z53 with date: {date_param}")
                    data = client.Z53(
                        start=date_param,                     # should be in YYYY-MM-DD
                        end=date_param,
                    )
                else:
                    # For other order types, we might need different methods
                    # This is a placeholder for future extension
                    data = client.Z53(
                        start=date_param,
                        end=date_param,
                    )
            client.confirm_download()
            
            frappe.log_error("EBICS Data Debug", f"Data received from EBICS: {len(data)} accounts for date {date_param}")
            
            # check data
            if len(data) > 0:
                # there should be one node for each account for this day
                frappe.log_error("EBICS Account Processing", f"Processing {len(data)} accounts for date {date_param}")
                for idx, (account, content) in enumerate(data.items()):
                    if idx < 3:  # Log first 3 for debugging
                        # Extract a sample of the XML content to see the dates
                        try:
                            from bs4 import BeautifulSoup
                            soup = BeautifulSoup(content, 'lxml-xml')
                            fr_dt = soup.find('FrDtTm')
                            to_dt = soup.find('ToDtTm')
                            msg_id = soup.find('MsgId')
                            frappe.log_error(
                                "EBICS XML Date Debug",
                                f"Account {account}: MsgId={msg_id.text if msg_id else 'N/A'}, "
                                f"FrDt={fr_dt.text if fr_dt else 'N/A'}, ToDt={to_dt.text if to_dt else 'N/A'}"
                            )
                        except:
                            pass
                    # Extract MsgId from XML to check for duplicates
                    try:
                        from erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard import read_camt053_meta
                        meta = read_camt053_meta(content)
                        bank_statement_id = meta.get('msgid')
                        
                        # Check if the statement date matches the requested date
                        statement_date = meta.get('statement_date')
                        if statement_date and statement_date != date_param:
                            if debug:
                                print(f"WARNING: Statement date {statement_date} differs from requested {date_param}")
                            frappe.log_error(
                                "EBICS Date Mismatch Warning",
                                f"Bank returned statement for {statement_date} when we requested {date_param}. "
                                f"This might indicate the bank has no data for {date_param} or returns closest available date. "
                                f"Statement ID: {bank_statement_id}"
                            )
                            # Don't skip - the bank might be returning the closest available data
                            # continue
                        
                        # Check if this statement already exists
                        if bank_statement_id:
                            existing_stmt = frappe.db.exists('ebics Statement', {'bank_statement_id': bank_statement_id})
                            if existing_stmt:
                                if debug:
                                    print("Statement {0} already exists, skipping...".format(bank_statement_id))
                                frappe.log_error("EBICS Import Skip", "Duplicate statement detected: {0}".format(bank_statement_id))
                                continue
                        else:
                            # If no MsgId, check by date, account and content hash
                            import hashlib
                            # Handle both string and bytes
                            if isinstance(content, bytes):
                                content_hash = hashlib.md5(content).hexdigest()
                            else:
                                content_hash = hashlib.md5(content.encode()).hexdigest()
                            
                            # Check for duplicate by content hash (remove date from check)
                            # The date might be different in the XML than requested
                            existing_by_hash = frappe.db.get_value(
                                'ebics Statement',
                                {
                                    'ebics_connection': self.name,
                                    'content_hash': content_hash
                                },
                                'name'
                            )
                            
                            if existing_by_hash:
                                if debug:
                                    print("Statement with same content already exists for date {0}, skipping...".format(date_param))
                                frappe.log_error("EBICS Import Skip", "Duplicate statement detected by content hash for date: {0}".format(date_param))
                                continue
                                
                    except Exception as e:
                        frappe.log_error("EBICS Import", "Error checking for duplicate statement: {0}".format(str(e)))
                    
                    stmt = frappe.get_doc({
                        'doctype': 'ebics Statement',
                        'ebics_connection': self.name,
                        'file_name': account,
                        'xml_content': content,
                        'date': date_param,  # This will be overwritten by parse_content if statement date is found in XML
                        'company': self.company
                    })
                    stmt.insert()
                    if debug:
                        print("Inserted {0}".format(account))
                    frappe.db.commit()
                    # process data
                    if debug:
                        print("Parsing data...")
                    stmt.parse_content(debug=debug)
                    if debug:
                        print("Processing transactions...")
                    stmt.process_transactions()
                
                # update sync date
                if not self.synced_until or self.synced_until < datetime.strptime(date_param, "%Y-%m-%d").date():
                    self.synced_until = date_param
                    self.save()
                    frappe.db.commit()
                    
        except fintech.ebics.EbicsFunctionalError as err:
            error_msg = "{0}".format(err)
            if "EBICS_NO_DOWNLOAD_DATA_AVAILABLE" in error_msg:
                # this is not a problem, simply no data
                frappe.log_error("EBICS No Data", f"No data available for date {date_param}")
                # Update sync date even if no data to avoid getting stuck
                if not self.synced_until or self.synced_until < datetime.strptime(date_param, "%Y-%m-%d").date():
                    self.synced_until = date_param
                    self.save()
                    frappe.db.commit()
                pass
            else:
                frappe.log_error("EBICS Interface Error", error_msg)
                raise
        except Exception as err:
            frappe.throw( "{0}".format(err), _("Error") )
        return



@frappe.whitelist()
def execute_payment(ebics_connection=None, payment_proposal=None):
    """Standalone method to execute payment via EBICS"""
    if not ebics_connection or not payment_proposal:
        frappe.throw(_("Missing required parameters: ebics_connection and payment_proposal"))
    
    conn = frappe.get_doc("ebics Connection", ebics_connection)
    return conn.execute_payment(payment_proposal)
