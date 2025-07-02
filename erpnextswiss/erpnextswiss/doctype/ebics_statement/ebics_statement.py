# -*- coding: utf-8 -*-
# Copyright (c) 2024-2025, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard import read_camt053_meta, read_camt053, make_payment_entry, get_default_accounts
from frappe import _
import ast

class ebicsStatement(Document):
    def onload(self):
        # Always load transactions from database to ensure they're visible
        if self.name and not self.is_new():
            # Force load child table data
            self.load_transactions_from_db()
            
        # Ensure transactions are loaded and visible
        if not hasattr(self, 'transactions') or self.transactions is None:
            self.transactions = []
        
        # Force the transactions field to be visible
        if hasattr(self, 'set_onload'):
            self.set_onload('show_transactions', True)
            # Also set the transactions data in onload
            self.set_onload('transactions', self.transactions)
        
        # Debug logging
        frappe.logger().debug(f"ebics Statement onload - {self.name}: {len(self.transactions)} transactions loaded, status: {self.status}")
        
        return
    
    def load_transactions_from_db(self):
        """Force load transactions from database"""
        if self.name:
            transactions = frappe.db.sql("""
                SELECT * FROM `tabebics Statement Transaction`
                WHERE parent = %s AND parenttype = 'ebics Statement'
                ORDER BY idx
            """, self.name, as_dict=True)
            
            self.transactions = []
            for transaction in transactions:
                self.append('transactions', transaction)
    
    def before_save(self):
        if self.status != "Completed":
            self.update_status_from_transactions()
        return
        
    def update_status_from_transactions(self):
        all_completed = True
        for t in self.transactions:
            if t.status != "Completed":
                all_completed = False
                break
        if all_completed:
            self.status = "Completed"
        return
        
    def parse_content(self, debug=False):
        """
        Read the xml content and parse into the doctype record
        """
        if not self.xml_content:
            frappe.throw( _("Cannot parse this file: {0}. No content found.").format(self.name) )
            
        # Calculate content hash for duplicate detection
        import hashlib
        # Handle both string and bytes
        if isinstance(self.xml_content, bytes):
            content_hash = hashlib.md5(self.xml_content).hexdigest()
        else:
            content_hash = hashlib.md5(self.xml_content.encode()).hexdigest()
        
        # read meta data
        meta = read_camt053_meta(self.xml_content)
        self.update({
            'currency': meta.get('currency'),
            'opening_balance': meta.get('opening_balance'),
            'closing_balance': meta.get('closing_balance'),
            'bank_statement_id': meta.get('msgid'),
            'content_hash': content_hash
        })
        
        # Update statement date from XML content if available
        if meta.get('statement_date'):
            self.date = meta.get('statement_date')
            if debug:
                print("Statement date from XML: {0}".format(self.date))
            
            # Log if the date from XML doesn't match expected date
            if hasattr(self, 'expected_date') and self.expected_date != self.date:
                frappe.log_error(
                    f"Date mismatch: Expected {self.expected_date}, got {self.date} from XML",
                    "EBICS Date Mismatch"
                )
        account_matches = frappe.db.sql("""
            SELECT `name`, `company`
            FROM `tabAccount`
            WHERE `iban` = "{iban}" AND `account_type` = "Bank";
            """.format(iban=meta.get('iban')), as_dict=True)
        print("{0}".format(account_matches))
        if len(account_matches) > 0:
            self.account = account_matches[0]['name']
            self.company = account_matches[0]['company']
            self.transactions = []
            self.status = "Pending"             # reset status: transaction being added
            
            # read transactions (only if account is available) - note: transactions that are already recorded as payment entry are supressed
            transactions = read_camt053(self.xml_content, self.account)
            
            if debug:
                print("Txns: {0}".format(transactions))
            # read transactions into the child table
            for transaction in transactions.get('transactions'):
                if debug:
                    print("{0}".format(transaction))
                # verify that this unique ID has not already been imported (happens do to the licence block in fintech)
                duplicates = frappe.db.sql("""
                    SELECT `name`
                    FROM `tabebics Statement Transaction`
                    WHERE `unique_reference` = %(ref)s
                      AND `date` = %(date)s
                      AND `parent` != %(stmt)s;""",
                    {
                        'ref': transaction.get("unique_reference"),
                        'date': transaction.get("date"),
                        'stmt': self.name
                    },
                    as_dict=True
                )
                if len(duplicates) > 0:
                    continue                # skip, this transaction has 
                # stringify lists to store them in child table
                if transaction.get("invoice_matches"):
                    transaction['invoice_matches'] = "{0}".format(transaction.get("invoice_matches"))
                if transaction.get("expense_matches"):
                    transaction['expense_matches'] = "{0}".format(transaction.get("expense_matches"))
                
                transaction['status'] = "Pending"
                
                self.append("transactions", transaction)
                
        else:
            frappe.log_error( _("Unable to find matching account: please check your accounts and set IBAN {0}").format(meta.get('iban')), _("ebics statement parsing failed") )
        
        # save
        self.save()
        frappe.db.commit()
        
        return

    def process_transactions(self):
        """
        Analyse transactions and if possible, match them
        """
        default_accounts = get_default_accounts(self.account)
        
        for t in self.transactions:
            # if matched amount equals the transaction amount, create and submit payment
            if t.status == "Pending" and not t.payment_entry and t.matched_amount == t.amount and (t.party_match or t.employee_match):
                payment = {
                    'amount': t.amount,
                    'date': t.date,
                    'reference_no': t.unique_reference,
                    'party_iban': t.party_iban
                }
                if t.credit_debit == "DBIT":
                    # outflow: purchase invoice or expense
                    if t.invoice_matches:
                        payment.update({
                            'paid_from': self.account,
                            'paid_to': default_accounts.get('payable_account'),
                            'type': "Pay",
                            'party_type': "Supplier",
                            'party': t.party_match,
                            'references': t.invoice_matches,            # note: string will be parsed in make_payment_entry
                            'remarks': "{0}, {1}, {2}".format(t.transaction_reference or "", t.party_name or "", t.party_address or ""),
                            'auto_submit': 1,
                            'company': self.company
                        })
                    elif t.expense_matches:
                        payment.update({
                            'paid_from': self.account,
                            'paid_to': default_accounts.get('payable_account'),
                            'type': "Pay",
                            'party_type': "Employee",
                            'party': t.employee_match,
                            'references': t.expense_matches,            # note: string will be parsed in make_payment_entry
                            'remarks': "{0}, {1}, {2}".format(t.transaction_reference or "", t.party_name or "", t.party_address or ""),
                            'auto_submit': 1,
                            'company': self.company
                        })
                else:
                    # inflow: debtor
                    payment.update({
                        'paid_from': default_accounts.get('receivable_account'),
                        'paid_to': self.account,
                        'type': "Receive",
                        'party_type': "Customer",
                        'party': t.party_match,
                        'references': t.invoice_matches,            # note: string will be parsed in make_payment_entry
                        'remarks': "{0}, {1}, {2}".format(t.transaction_reference or "", t.party_name or "", t.party_address or ""),
                        'auto_submit': 1,
                        'company': self.company
                    })
                
                try:
                    payment = make_payment_entry(**payment)
                    t.payment_entry = payment.get('payment_entry')
                    t.status = "Completed"
                except Exception as err:
                    t.status == "Error"
                    t.remarks = "{0}".format(err)
        
        # save
        self.save()
        frappe.db.commit()
        
        # run post-processing triggers
        self.post_process()
        
        return

    def post_process(self):
        """
        Use this hook to add post processing actions, i.e. custom matching
        
        Add in your custom hooks.py:
            doc_events = {
                "ebics Statement": {
                    "post_process": "myapp.mymodule.ebics.post_process_ebics"
                }
            }
        """
        events = frappe.get_hooks("doc_events")
        if events:
            ebics_events = events.get('ebics Statement')
            if ebics_events:
                post_processing_hooks = ebics_events.get('post_process')
                for hook in post_processing_hooks:
                    frappe.call(hook, self, "post_process")
                    
        return

@frappe.whitelist()
def delete_all_statements():
    """Delete all ebics Statement records"""
    try:
        # Check permission
        if not frappe.has_permission("ebics Statement", "delete"):
            frappe.throw(_("You don't have permission to delete ebics Statements"))
        
        # Get count before deletion
        count = frappe.db.count("ebics Statement")
        
        if count == 0:
            return {
                'success': True,
                'deleted': 0,
                'message': _('No statements to delete')
            }
        
        # Delete all statements
        frappe.db.sql("DELETE FROM `tabebics Statement Transaction`")
        frappe.db.sql("DELETE FROM `tabebics Statement`")
        frappe.db.commit()
        
        # Clear cache
        frappe.clear_cache(doctype="ebics Statement")
        
        return {
            'success': True,
            'deleted': count,
            'message': _('Successfully deleted {0} statement(s)').format(count)
        }
        
    except Exception as e:
        frappe.log_error(str(e), "Delete All Statements Error")
        return {
            'success': False,
            'deleted': 0,
            'message': str(e)
        }

@frappe.whitelist()
def reparse_xml(docname):
    """Re-parse XML content to recreate transactions"""
    try:
        doc = frappe.get_doc('ebics Statement', docname)
        
        if not doc.xml_content:
            return {
                'success': False,
                'message': _('No XML content found')
            }
        
        # Store current status
        current_status = doc.status
        
        # Clear existing transactions
        doc.transactions = []
        
        # Parse XML directly to get all transactions (including those already imported)
        meta = read_camt053_meta(doc.xml_content)
        
        # Get account info
        account_matches = frappe.db.sql("""
            SELECT `name`, `company`
            FROM `tabAccount`
            WHERE `iban` = %s AND `account_type` = "Bank";
            """, meta.get('iban'), as_dict=True)
            
        if not account_matches:
            return {
                'success': False,
                'message': _('No matching bank account found for IBAN {0}').format(meta.get('iban'))
            }
        
        # Read ALL transactions without filtering - parse directly from XML
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(doc.xml_content, 'lxml-xml')
        
        transactions = {'transactions': []}
        txid = 0
        
        # Process each entry (transaction)
        for entry in soup.find_all('Ntry'):
            try:
                # Get transaction details
                for transaction_detail in entry.find_all('TxDtls'):
                    amount = float(transaction_detail.find('Amt').get_text())
                    currency = transaction_detail.find('Amt').get('Ccy')
                    credit_debit = transaction_detail.find('CdtDbtInd').get_text()
                    unique_reference = transaction_detail.find('AcctSvcrRef').get_text() if transaction_detail.find('AcctSvcrRef') else ''
                    date = entry.find('BookgDt').find('Dt').get_text()
                    
                    # Get party info
                    party_name = ''
                    party_iban = ''
                    party_address = ''
                    
                    if credit_debit == "DBIT":
                        # Outgoing payment
                        cdtr = transaction_detail.find('RltdPties').find('Cdtr')
                        if cdtr:
                            party_name = cdtr.find('Nm').get_text() if cdtr.find('Nm') else ''
                            if cdtr.find('PstlAdr'):
                                addr_parts = []
                                if cdtr.find('PstlAdr').find('StrtNm'):
                                    addr_parts.append(cdtr.find('PstlAdr').find('StrtNm').get_text())
                                if cdtr.find('PstlAdr').find('BldgNb'):
                                    addr_parts.append(cdtr.find('PstlAdr').find('BldgNb').get_text())
                                if cdtr.find('PstlAdr').find('PstCd'):
                                    addr_parts.append(cdtr.find('PstlAdr').find('PstCd').get_text())
                                if cdtr.find('PstlAdr').find('TwnNm'):
                                    addr_parts.append(cdtr.find('PstlAdr').find('TwnNm').get_text())
                                party_address = ', '.join(addr_parts)
                        cdtr_acct = transaction_detail.find('RltdPties').find('CdtrAcct')
                        if cdtr_acct and cdtr_acct.find('IBAN'):
                            party_iban = cdtr_acct.find('IBAN').get_text()
                    else:
                        # Incoming payment
                        dbtr = transaction_detail.find('RltdPties').find('Dbtr')
                        if dbtr:
                            party_name = dbtr.find('Nm').get_text() if dbtr.find('Nm') else ''
                            if dbtr.find('PstlAdr'):
                                addr_parts = []
                                if dbtr.find('PstlAdr').find('StrtNm'):
                                    addr_parts.append(dbtr.find('PstlAdr').find('StrtNm').get_text())
                                if dbtr.find('PstlAdr').find('BldgNb'):
                                    addr_parts.append(dbtr.find('PstlAdr').find('BldgNb').get_text())
                                if dbtr.find('PstlAdr').find('PstCd'):
                                    addr_parts.append(dbtr.find('PstlAdr').find('PstCd').get_text())
                                if dbtr.find('PstlAdr').find('TwnNm'):
                                    addr_parts.append(dbtr.find('PstlAdr').find('TwnNm').get_text())
                                party_address = ', '.join(addr_parts)
                        dbtr_acct = transaction_detail.find('RltdPties').find('DbtrAcct')
                        if dbtr_acct and dbtr_acct.find('IBAN'):
                            party_iban = dbtr_acct.find('IBAN').get_text()
                    
                    # Get reference
                    transaction_reference = ''
                    if transaction_detail.find('RmtInf') and transaction_detail.find('RmtInf').find('Ref'):
                        transaction_reference = transaction_detail.find('RmtInf').find('Ref').get_text()
                    
                    # Create transaction
                    new_txn = {
                        'txid': str(txid),
                        'date': date,
                        'currency': currency,
                        'amount': amount,
                        'party_name': party_name,
                        'party_address': party_address,
                        'credit_debit': credit_debit,
                        'party_iban': party_iban,
                        'unique_reference': unique_reference,
                        'transaction_reference': transaction_reference,
                        'party_match': None,
                        'invoice_matches': None,
                        'matched_amount': 0.0
                    }
                    
                    transactions['transactions'].append(new_txn)
                    txid += 1
                    
            except Exception as e:
                frappe.log_error(f"Error parsing transaction: {str(e)}", "EBICS Re-parse Transaction")
        
        # Add transactions to document
        for transaction in transactions.get('transactions', []):
            # Check if this transaction has a payment entry
            payment_entry = frappe.db.get_value('Payment Entry', 
                {'reference_no': transaction.get("unique_reference"), 'company': account_matches[0]['company']}, 
                'name')
            
            if payment_entry:
                transaction['payment_entry'] = payment_entry
                transaction['status'] = "Completed"
            else:
                transaction['status'] = "Pending"
            
            # stringify lists to store them in child table
            if transaction.get("invoice_matches"):
                transaction['invoice_matches'] = "{0}".format(transaction.get("invoice_matches"))
            if transaction.get("expense_matches"):
                transaction['expense_matches'] = "{0}".format(transaction.get("expense_matches"))
                
            doc.append("transactions", transaction)
        
        # Restore the status
        doc.status = current_status
        doc.save()
        
        return {
            'success': True,
            'transaction_count': len(doc.transactions)
        }
    except Exception as e:
        frappe.log_error(str(e), "Re-parse XML Error")
        return {
            'success': False,
            'message': str(e)
        }

@frappe.whitelist()
def get_transactions(docname):
    """Get transactions for a specific ebics Statement"""
    try:
        transactions = frappe.db.sql("""
            SELECT * FROM `tabebics Statement Transaction`
            WHERE parent = %s AND parenttype = 'ebics Statement'
            ORDER BY idx
        """, docname, as_dict=True)
        
        return {
            'success': True,
            'transactions': transactions
        }
    except Exception as e:
        frappe.log_error(str(e), "Get Transactions Error")
        return {
            'success': False,
            'message': str(e)
        }

@frappe.whitelist()
def find_and_merge_duplicates():
    """Find and merge duplicate ebics Statements based on bank_statement_id"""
    try:
        # Check permission
        if not frappe.has_permission("ebics Statement", "delete"):
            frappe.throw(_("You don't have permission to merge ebics Statements"))
        
        # Find duplicates
        duplicates = frappe.db.sql("""
            SELECT bank_statement_id, COUNT(*) as count, GROUP_CONCAT(name) as names
            FROM `tabebics Statement`
            WHERE bank_statement_id IS NOT NULL AND bank_statement_id != ''
            GROUP BY bank_statement_id
            HAVING count > 1
        """, as_dict=True)
        
        if not duplicates:
            return {
                'success': True,
                'message': _('No duplicate statements found'),
                'duplicates_found': 0,
                'statements_deleted': 0
            }
        
        statements_deleted = 0
        
        for dup in duplicates:
            statement_names = dup.names.split(',')
            # Keep the first one, delete the rest
            keep_statement = statement_names[0]
            
            for stmt_name in statement_names[1:]:
                # Delete transactions first
                frappe.db.sql("""
                    DELETE FROM `tabebics Statement Transaction`
                    WHERE parent = %s
                """, stmt_name)
                
                # Delete the statement
                frappe.db.sql("""
                    DELETE FROM `tabebics Statement`
                    WHERE name = %s
                """, stmt_name)
                
                statements_deleted += 1
        
        frappe.db.commit()
        frappe.clear_cache(doctype="ebics Statement")
        
        return {
            'success': True,
            'message': _('Successfully merged {0} duplicate groups, deleted {1} statements').format(
                len(duplicates), statements_deleted
            ),
            'duplicates_found': len(duplicates),
            'statements_deleted': statements_deleted
        }
        
    except Exception as e:
        frappe.log_error(str(e), "Merge Duplicates Error")
        return {
            'success': False,
            'message': str(e)
        }