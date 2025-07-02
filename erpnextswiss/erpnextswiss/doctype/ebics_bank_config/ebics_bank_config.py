# -*- coding: utf-8 -*-
# Copyright (c) 2025, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json

class ebicsBankConfig(Document):
    def validate(self):
        # Validate JSON format for supported_payment_types
        if self.supported_payment_types:
            try:
                json.loads(self.supported_payment_types)
            except:
                frappe.throw("Supported Payment Types must be a valid JSON array")
        
        # Set default values if empty
        if not self.payment_order_type_h004:
            self.payment_order_type_h004 = "XE2"
        if not self.statement_order_type_h004:
            self.statement_order_type_h004 = "Z53"
        if not self.payment_service_h005:
            self.payment_service_h005 = "MCT"
        if not self.payment_scope_h005:
            self.payment_scope_h005 = "CH"
        if not self.payment_msg_name_h005:
            self.payment_msg_name_h005 = "pain.001"
        if not self.statement_service_h005:
            self.statement_service_h005 = "EOP"
        if not self.statement_scope_h005:
            self.statement_scope_h005 = "CH"
        if not self.statement_msg_name_h005:
            self.statement_msg_name_h005 = "camt.053"
        if not self.statement_version_h005:
            self.statement_version_h005 = "04"
        if not self.statement_container_h005:
            self.statement_container_h005 = "ZIP"
    
    def get_supported_payment_types(self):
        """Return supported payment types as a list"""
        if self.supported_payment_types:
            try:
                return json.loads(self.supported_payment_types)
            except:
                return ["SEPA", "IBAN", "ESR", "QRR", "SCOR"]
        return ["SEPA", "IBAN", "ESR", "QRR", "SCOR"]

@frappe.whitelist()
def create_default_configs():
    """Create default bank configurations - can be called from UI"""
    created_banks = []
    existing_banks = []
    errors = []
    
    # Check if DocType exists
    if not frappe.db.exists("DocType", "ebics Bank Config"):
        return {
            'created': 0,
            'existing': 0,
            'details': ["ERROR: DocType 'ebics Bank Config' does not exist. Please run bench migrate."],
            'error': True
        }
    
    banks = [
        {
            "bank_name": "Raiffeisen",
            "bank_code": "RAIFCH22",
            "country": "Switzerland",
            "payment_order_type_h004": "XE2",
            "statement_order_type_h004": "Z53",
            "payment_service_h005": "MCT",
            "payment_scope_h005": "CH",
            "payment_msg_name_h005": "pain.001",
            "statement_service_h005": "EOP",
            "statement_scope_h005": "CH",
            "statement_msg_name_h005": "camt.053",
            "statement_version_h005": "04",
            "statement_container_h005": "ZIP",
            "use_swiss_namespace": 1,
            "supported_payment_types": '["SEPA", "IBAN", "ESR", "QRR", "SCOR"]'
        },
        {
            "bank_name": "UBS",
            "bank_code": "UBSWCHZH",
            "country": "Switzerland",
            "payment_order_type_h004": "XE2",
            "statement_order_type_h004": "Z53",
            "payment_service_h005": "MCT",
            "payment_scope_h005": "CH",
            "payment_msg_name_h005": "pain.001",
            "statement_service_h005": "EOP",
            "statement_scope_h005": "CH",
            "statement_msg_name_h005": "camt.053",
            "statement_version_h005": "04",
            "statement_container_h005": "ZIP",
            "use_swiss_namespace": 1,
            "supported_payment_types": '["SEPA", "IBAN", "ESR", "QRR", "SCOR"]'
        },
        {
            "bank_name": "Credit Suisse",
            "bank_code": "CRESCHZZ",
            "country": "Switzerland",
            "payment_order_type_h004": "XE2",
            "statement_order_type_h004": "Z53",
            "payment_service_h005": "MCT",
            "payment_scope_h005": "CH",
            "payment_msg_name_h005": "pain.001",
            "statement_service_h005": "EOP",
            "statement_scope_h005": "CH",
            "statement_msg_name_h005": "camt.053",
            "statement_version_h005": "04",
            "statement_container_h005": "ZIP",
            "use_swiss_namespace": 1,
            "supported_payment_types": '["SEPA", "IBAN", "ESR", "QRR", "SCOR"]'
        },
        {
            "bank_name": "PostFinance",
            "bank_code": "POFICHBE",
            "country": "Switzerland",
            "payment_order_type_h004": "XE2",
            "statement_order_type_h004": "Z53",
            "payment_service_h005": "MCT",
            "payment_scope_h005": "CH",
            "payment_msg_name_h005": "pain.001",
            "statement_service_h005": "EOP",
            "statement_scope_h005": "CH",
            "statement_msg_name_h005": "camt.053",
            "statement_version_h005": "04",
            "statement_container_h005": "ZIP",
            "use_swiss_namespace": 1,
            "supported_payment_types": '["SEPA", "IBAN", "ESR", "QRR", "SCOR"]'
        },
        {
            "bank_name": "ZKB",
            "bank_code": "ZKBKCHZZ",
            "country": "Switzerland",
            "payment_order_type_h004": "XE2",
            "statement_order_type_h004": "Z53",
            "payment_service_h005": "MCT",
            "payment_scope_h005": "CH",
            "payment_msg_name_h005": "pain.001",
            "statement_service_h005": "EOP",
            "statement_scope_h005": "CH",
            "statement_msg_name_h005": "camt.053",
            "statement_version_h005": "04",
            "statement_container_h005": "ZIP",
            "use_swiss_namespace": 1,
            "supported_payment_types": '["SEPA", "IBAN", "ESR", "QRR", "SCOR"]'
        }
    ]
    
    for bank in banks:
        if not frappe.db.exists("ebics Bank Config", bank["bank_name"]):
            try:
                doc = frappe.get_doc({
                    "doctype": "ebics Bank Config",
                    **bank
                })
                doc.insert(ignore_permissions=True)
                created_banks.append(f"Created ebics Bank Config for {bank['bank_name']}")
            except Exception as e:
                error_msg = f"Failed to create {bank['bank_name']}: {str(e)}"
                errors.append(error_msg)
                frappe.log_error(error_msg, "ebics Bank Config Creation")
        else:
            existing_banks.append(f"ebics Bank Config for {bank['bank_name']} already exists")
    
    if created_banks:
        frappe.db.commit()
    
    # Add errors to details
    all_details = created_banks + existing_banks + errors
    
    return {
        'created': len(created_banks),
        'existing': len(existing_banks),
        'errors': len(errors),
        'details': all_details
    }