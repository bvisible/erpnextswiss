# -*- coding: utf-8 -*-
# Copyright (c) 2017-2024, libracore and contributors
# License: AGPL v3. See LICENCE

import frappe
from frappe import throw, _
import hashlib
import json
from bs4 import BeautifulSoup
import ast
import six
from frappe.utils import cint, flt
from frappe.utils.data import get_url_to_form
from erpnext.setup.utils import get_exchange_rate

# this function tries to match the amount to an open sales invoice
#
# returns the sales invoice reference (name string) or None
def match_by_amount(amount):
    # get sales invoices
    sql_query = ("""
        SELECT `name` 
        FROM `tabSales Invoice` 
        WHERE `docstatus` = 1 
        AND `grand_total` = {0} 
        AND `status` != 'Paid'; """.format(amount) )
    open_sales_invoices = frappe.db.sql(sql_query, as_dict=True)
    if open_sales_invoices:
        if len(open_sales_invoices) == 1:
            # found exactly one match
            return open_sales_invoices[0].name
        else:
            # multiple sales invoices with this amount found
            return None
    else:
        # no open sales invoice with this amount found
        return None
        
# this function tries to match the comments to an open sales invoice
# 
# returns the sales invoice reference (name sting) or None
def match_by_comment(comment):
    # get sales invoices (submitted, not paid)
    sql_query = """
        SELECT `name` 
        FROM `tabSales Invoice` 
        WHERE `docstatus` = 1  
        AND `status` != 'Paid';"""
    open_sales_invoices = frappe.db.sql(sql_query, as_dict=True)
    if open_sales_invoices:
        # find sales invoice referernce in the comment
        for reference in open_sales_invoices.name:
            if reference in comment:
                # found a match
                return reference
    return None

# find unpaid invoices for a customer
#
# returns a dict (name) of sales invoice references or None
def get_unpaid_sales_invoices_by_customer(customer):
    # get sales invoices (submitted, not paid)
    sql_query = """
        SELECT `name`
        FROM `tabSales Invoice` 
        WHERE `docstatus` = 1 
        AND `customer` = '{0}' 
        AND `status` != 'Paid'; """.format(customer)
    open_sales_invoices = frappe.db.sql(sql_query, as_dict=True)
    return open_sales_invoices   

# create a payment entry
def create_payment_entry(date, to_account, received_amount, transaction_id, remarks, party_iban=None, auto_submit=False):
    # get default customer
    default_customer = get_default_customer()
    if not frappe.db.exists('Payment Entry', {'reference_no': transaction_id}):
        # create new payment entry
        new_payment_entry = frappe.get_doc({
            'doctype': 'Payment Entry',
            'payment_type': "Receive",
            'party_type': "Customer",
            'party': default_customer,
            # date is in DD.MM.YYYY
            'posting_date': date,
            'paid_to': to_account,
            'received_amount': received_amount,
            'paid_amount': received_amount,
            'reference_no': transaction_id,
            'reference_date': date,
            'remarks': remarks,
            'bank_account_no': party_iban
        })
        inserted_payment_entry = new_payment_entry.insert()
        if auto_submit:
            new_payment_entry.submit()
        frappe.db.commit()
        return inserted_payment_entry
    else:
        return None
    
# creates the reference record in a payment entry
def create_reference(payment_entry, sales_invoice):
    # create a new payment entry reference
    reference_entry = frappe.get_doc({
        'doctype': "Payment Entry Reference",
        'parent': payment_entry,
        'parentfield': "references",
        'parenttype': "Payment Entry",
        'reference_doctype': "Sales Invoice",
        'reference_name': sales_invoice,
        'total_amount': frappe.get_value("Sales Invoice", sales_invoice, "base_grand_total"),
        'outstanding_amount': frappe.get_value("Sales Invoice", sales_invoice, "outstanding_amount")
    })
    paid_amount = frappe.get_value("Payment Entry", payment_entry, "paid_amount")
    if paid_amount > reference_entry.outstanding_amount:
        reference_entry.allocated_amount = reference_entry.outstanding_amount
    else:
        reference_entry.allocated_amount = paid_amount
    reference_entry.insert();
    return
    
def log(comment):
    new_comment = frappe.get_doc({"doctype": "Log"})
    new_comment.comment = comment
    new_comment.insert()
    return new_comment

# converts a parameter to a bool
def assert_bool(param):
    result = param
    if result == 'false':
        result = False
    elif result == 'true':
        result = True	
    return result  

def get_default_customer():
    default_customer = frappe.get_value("ERPNextSwiss Settings", "ERPNextSwiss Settings", "default_customer")
    if not default_customer:
        default_customer = "Guest"
    return default_customer

@frappe.whitelist()
def get_bank_accounts():
    accounts = frappe.get_list('Account', filters={'account_type': 'Bank', 'is_group': 0}, fields=['name'], order_by='account_number')
    selectable_accounts = []
    for account in accounts:
        selectable_accounts.append(account.name)

    # frappe.throw(selectable_accounts)
    return {'accounts': selectable_accounts }

@frappe.whitelist()
def get_default_accounts(bank_account=None):
    if not bank_account:
        # Return empty defaults if no bank account provided
        return {
            'company': None,
            'receivable_account': None,
            'payable_account': None,
            'expense_payable_account': None,
            'auto_process_matches': frappe.get_value('ERPNextSwiss Settings', 'ERPNextSwiss Settings', 'auto_process_matches')
        }
    
    company = frappe.get_value("Account", bank_account, "company")
    receivable_account = frappe.get_value('Company', company, 'default_receivable_account')
    payable_account = frappe.get_value('Company', company, 'default_payable_account')
    expense_payable_account = frappe.get_value('Company', company, 'default_expense_claim_payable_account') or payable_account
    auto_process_matches = frappe.get_value('ERPNextSwiss Settings', 'ERPNextSwiss Settings', 'auto_process_matches')
    return { 
        'company': company, 
        'receivable_account': receivable_account, 
        'payable_account': payable_account, 
        'expense_payable_account': expense_payable_account,
        'auto_process_matches': auto_process_matches
    }

@frappe.whitelist()
def get_intermediate_account():
    account = frappe.get_value('ERPNextSwiss Settings', 'ERPNextSwiss Settings', 'intermediate_account')
    return {'account': account or "" }

@frappe.whitelist()
def get_default_customer():
    customer = frappe.get_value('ERPNextSwiss Settings', 'ERPNextSwiss Settings', 'default_customer')
    return {'customer': customer or "" }
    
@frappe.whitelist()
def get_default_supplier():
    supplier = frappe.get_value('ERPNextSwiss Settings', 'ERPNextSwiss Settings', 'default_supplier')
    return {'supplier': supplier or "" }
    
@frappe.whitelist()
def get_receivable_account(company=None):
    if not company:
        company = get_first_company()
    account = frappe.get_value('Company', company, 'default_receivable_account')
    return {'account': account or "" }

@frappe.whitelist()
def get_payable_account(company=None, employee=False):
    if not company:
        company = get_first_company()
    account = frappe.get_value('Company', company, 'default_payable_account')
    if employee:
        account = frappe.get_value('Company', company, 'default_expense_claim_payable_account') or account
    return {'account': account or "" }

def get_first_company():
    companies = frappe.get_all("Company", filters=None, fields=['name'])
    return companies[0]['name']

"""
Interpret meta information of the camt.053 record

Input: camt.053-xml-string
Output: meta-dict
"""
def read_camt053_meta(content):
    soup = BeautifulSoup(content, 'lxml-xml')  # Use lxml-xml for better namespace handling
    meta = {}
    
    try:
        # Try to get IBAN - handle both lowercase and uppercase tags
        iban_element = soup.find('IBAN') or soup.find('iban')
        if iban_element:
            meta['iban'] = iban_element.get_text().strip()
        else:
            meta['iban'] = 'n/a'
            frappe.log_error("Could not find IBAN in XML", "CAMT053 Parsing")
        
        # Try to get electronic sequence number
        elec_seq = soup.find('ElctrncSeqNb') or soup.find('elctrncseqnb')
        if elec_seq:
            meta['electronic_sequence_number'] = elec_seq.get_text().strip()
        else:
            meta['electronic_sequence_number'] = 'n/a'
        
        # Try to get message ID from Stmt
        stmt = soup.find('Stmt') or soup.find('stmt')
        if stmt:
            stmt_id = stmt.find('Id') or stmt.find('id')
            if stmt_id:
                meta['msgid'] = stmt_id.get_text().strip()
            else:
                meta['msgid'] = 'n/a'
        else:
            meta['msgid'] = 'n/a'
        
        # Try to get currency from balance or account
        # First try from Bal/Amt
        amt_element = soup.find('Amt') or soup.find('amt')
        if amt_element and amt_element.has_attr('Ccy'):
            meta['currency'] = amt_element['Ccy']
        elif amt_element and amt_element.has_attr('ccy'):
            meta['currency'] = amt_element['ccy']
        else:
            # Try from account currency
            ccy_element = soup.find('Ccy') or soup.find('ccy')
            if ccy_element:
                meta['currency'] = ccy_element.get_text().strip()
            else:
                meta['currency'] = 'CHF'
                
    except Exception as e:
        frappe.log_error("Error parsing CAMT053 meta: {0}".format(str(e)), "CAMT053 Parsing Error")
        meta = {
            'iban': 'n/a',
            'electronic_sequence_number': 'n/a',
            'msgid': 'n/a',
            'currency': 'CHF'
        }
    # find balances - handle both uppercase and lowercase
    try:
        balances = soup.find_all('Bal') or soup.find_all('bal')
        for balance in balances:
            try:
                # Get balance type
                cd_element = balance.find('Cd') or balance.find('cd')
                if cd_element:
                    balance_type = cd_element.get_text().strip()
                    # Get amount
                    amt_element = balance.find('Amt') or balance.find('amt')
                    if amt_element:
                        amount_text = amt_element.get_text().strip()
                        amount = float(amount_text)
                        
                        # Check if debit or credit
                        cdtdbtind_element = balance.find('CdtDbtInd') or balance.find('cdtdbtind')
                        if cdtdbtind_element:
                            cdtdbt = cdtdbtind_element.get_text().strip()
                            if cdtdbt == "DBIT":
                                amount = -amount
                        
                        if balance_type == "OPBD":
                            meta['opening_balance'] = amount
                        elif balance_type == "CLBD":
                            meta['closing_balance'] = amount
            except Exception as e:
                frappe.log_error("Error parsing balance: {0}".format(str(e)), "CAMT053 Balance Parsing")
                continue
    except Exception as e:
        frappe.log_error("Error finding balances: {0}".format(str(e)), "CAMT053 Balance Search")
        
    # Set default values if not found
    if 'opening_balance' not in meta:
        meta['opening_balance'] = 0.0
    if 'closing_balance' not in meta:
        meta['closing_balance'] = 0.0
    
    # Extract statement date from FrDtTm or ToDtTm
    try:
        # Try to find statement date/time elements
        # First try FrDtTm (From Date Time)
        fr_dt_tm_element = soup.find('FrDtTm') or soup.find('frdttm')
        if fr_dt_tm_element:
            dt_element = fr_dt_tm_element.find('Dt') or fr_dt_tm_element.find('dt')
            if dt_element:
                date_text = dt_element.get_text().strip()
                # Ensure the date is in YYYY-MM-DD format
                if len(date_text) == 10 and date_text[4] == '-' and date_text[7] == '-':
                    meta['statement_date'] = date_text
                else:
                    frappe.log_error(f"Unexpected date format in FrDtTm: {date_text}", "CAMT053 Date Format")
        
        # If not found, try ToDtTm (To Date Time)
        if 'statement_date' not in meta:
            to_dt_tm_element = soup.find('ToDtTm') or soup.find('todttm')
            if to_dt_tm_element:
                dt_element = to_dt_tm_element.find('Dt') or to_dt_tm_element.find('dt')
                if dt_element:
                    date_text = dt_element.get_text().strip()
                    # Ensure the date is in YYYY-MM-DD format
                    if len(date_text) == 10 and date_text[4] == '-' and date_text[7] == '-':
                        meta['statement_date'] = date_text
                    else:
                        frappe.log_error(f"Unexpected date format in ToDtTm: {date_text}", "CAMT053 Date Format")
        
        # If still not found, try CreDtTm (Creation Date Time) as fallback
        if 'statement_date' not in meta:
            cre_dt_tm_element = soup.find('CreDtTm') or soup.find('credttm')
            if cre_dt_tm_element:
                # CreDtTm usually contains datetime directly as text
                datetime_str = cre_dt_tm_element.get_text().strip()
                # Extract just the date part (YYYY-MM-DD)
                if 'T' in datetime_str:
                    meta['statement_date'] = datetime_str.split('T')[0]
                else:
                    meta['statement_date'] = datetime_str[:10]
                    
    except Exception as e:
        frappe.log_error("Error extracting statement date: {0}".format(str(e)), "CAMT053 Date Parsing")
        meta['statement_date'] = None
            
    return meta

@frappe.whitelist()
def read_camt053(content, account):
    settings = frappe.get_doc("ERPNextSwiss Settings", "ERPNextSwiss Settings")
    
    #read_camt_transactions_re(content)
    soup = BeautifulSoup(content, 'lxml-xml')  # Use lxml-xml for better namespace handling
    
    # general information
    try:
        # Try to find IBAN - handle both uppercase and lowercase
        iban_element = soup.find('IBAN') or soup.find('iban')
        if iban_element:
            iban = iban_element.get_text().strip()
        else:
            # fallback (Credit Suisse will provide bank account number instead of IBAN)
            iban = "n/a"
            othr_element = soup.find('Othr') or soup.find('othr')
            if othr_element:
                id_element = othr_element.find('Id') or othr_element.find('id')
                if id_element:
                    iban = id_element.get_text().strip()
    except Exception as e:
        # node not found, probably wrong format
        iban = "n/a"
        frappe.log_error("Unable to read IBAN: {0}".format(str(e)), "BankWizard read_camt053")
            
    # verify iban
    account_iban = frappe.get_value("Account", account, "iban")
    if not account_iban and cint(settings.iban_check_mandatory):
        frappe.throw( _("Bank account has no IBAN.").format(account_iban, iban), _("Bank Import IBAN validation") )
    if account_iban and account_iban.replace(" ", "") != iban.replace(" ", ""):
        if cint(settings.iban_check_mandatory):
            frappe.throw( _("IBAN mismatch {0} (account) vs. {1} (file)").format(account_iban, iban), _("Bank Import IBAN validation") )
        else:
            frappe.log_error( _("IBAN mismatch {0} (account) vs. {1} (file)").format(account_iban, iban), _("Bank Import IBAN validation") )
            frappe.msgprint( _("IBAN mismatch {0} (account) vs. {1} (file)").format(account_iban, iban), _("Bank Import IBAN validation") )

    # transactions - handle both uppercase and lowercase
    entries = soup.find_all('Ntry') or soup.find_all('ntry')
    transactions = read_camt_transactions(entries, account, settings)
    html = render_transactions(transactions)
    
    return { 'transactions': transactions, 'html': html } 

@frappe.whitelist()
def render_transactions(transactions):
    if type(transactions) == str:
        transactions = json.loads(transactions)
    
    html = frappe.render_template('erpnextswiss/erpnextswiss/page/bank_wizard/transaction_table.html', { 'transactions': transactions }  )
    return html

def read_camt_transactions(transaction_entries, account, settings, debug=False):
    company = frappe.get_value("Account", account, "company")
    txns = []
    for entry in transaction_entries:
        if six.PY2:
            entry_soup = BeautifulSoup(unicode(entry), 'lxml')
        else:
            entry_soup = BeautifulSoup(str(entry), 'lxml')
        date = entry_soup.bookgdt.dt.get_text()
        transactions = entry_soup.find_all('txdtls')
        # fetch entry amount as fallback
        entry_amount = float(entry_soup.amt.get_text())
        entry_currency = entry_soup.amt['ccy']
        # fetch global account service reference
        try:
            global_account_service_reference = entry_soup.acctsvcrref.get_text()
        except:
            global_account_service_reference = ""
        transaction_count = 0
        if transactions and len(transactions) > 0:
            for transaction in transactions:
                transaction_count += 1
                if six.PY2:
                    transaction_soup = BeautifulSoup(unicode(transaction), 'lxml')
                else:
                    transaction_soup = BeautifulSoup(str(transaction), 'lxml')
                # --- find transaction type: paid or received: (DBIT: paid, CRDT: received)
                if settings.always_use_entry_transaction_type:
                    credit_debit = entry_soup.cdtdbtind.get_text()
                else:
                    try:
                        credit_debit = transaction_soup.cdtdbtind.get_text()
                    except:
                        # fallback to entry indicator
                        credit_debit = entry_soup.cdtdbtind.get_text()
                
                # collect payment instruction id
                try:
                    payment_instruction_id = transaction_soup.pmtinfid.get_text()
                except:
                    payment_instruction_id = None
                
                # --- find unique reference
                try:
                    # try to use the account service reference
                    unique_reference = transaction_soup.txdtls.refs.acctsvcrref.get_text()
                except:
                    # fallback: use tx id
                    try:
                        unique_reference = transaction_soup.txid.get_text()
                    except:
                        # fallback to pmtinfid
                        try:
                            unique_reference = transaction_soup.pmtinfid.get_text()
                        except:
                            # fallback to group account service reference plus transaction_count
                            if global_account_service_reference != "":
                                unique_reference = "{0}-{1}".format(global_account_service_reference, transaction_count)
                            else:
                                # fallback to ustrd (do not use)
                                # unique_reference = transaction_soup.ustrd.get_text()
                                # fallback to hash
                                amount = transaction_soup.txdtls.amt.get_text()
                                party = transaction_soup.nm.get_text()
                                code = "{0}:{1}:{2}".format(date, amount, party)
                                if settings.debug_mode:
                                    frappe.log_error("Code: {0}".format(code))
                                unique_reference = hashlib.md5(code.encode("utf-8")).hexdigest()
                # --- find amount and currency
                try:
                    # try to find as <TxAmt>
                    amount = float(transaction_soup.txdtls.txamt.amt.get_text())
                    currency = transaction_soup.txdtls.txamt.amt['ccy']
                except:
                    try:
                        # fallback to pure <AMT>
                        amount = float(transaction_soup.txdtls.amt.get_text())
                        currency = transaction_soup.txdtls.amt['ccy']
                    except:
                        # fallback to amount from entry level
                        amount = entry_amount
                        currency = entry_currency
                try:
                    # --- find party IBAN
                    if credit_debit == "DBIT":
                        # use RltdPties:Cdtr
                        if six.PY2:
                            party_soup = BeautifulSoup(unicode(transaction_soup.txdtls.rltdpties.cdtr), 'lxml') 
                        else:
                            party_soup = BeautifulSoup(str(transaction_soup.txdtls.rltdpties.cdtr), 'lxml') 
                        try:
                            party_iban = transaction_soup.cdtracct.id.iban.get_text()
                        except:
                            party_iban = ""
                    else:
                        # CRDT: use RltdPties:Dbtr
                        if six.PY2:
                            party_soup = BeautifulSoup(unicode(transaction_soup.txdtls.rltdpties.dbtr), 'lxml')
                        else:
                            party_soup = BeautifulSoup(str(transaction_soup.txdtls.rltdpties.dbtr), 'lxml')
                        try:
                            party_iban = transaction_soup.dbtracct.id.iban.get_text()
                        except:
                            party_iban = ""
                    try:
                        party_name = party_soup.nm.get_text()
                        if party_soup.strtnm:
                            # parse by street name, ...
                            try:
                                street = party_soup.strtnm.get_text()
                                try:
                                    street_number = party_soup.bldgnb.get_text()
                                    address_line1 = "{0} {1}".format(street, street_number)
                                except:
                                    address_line1 = street
                                    
                            except:
                                address_line1 = ""
                            try:
                                plz = party_soup.pstcd.get_text()
                            except:
                                plz = ""
                            try:
                                town = party_soup.twnnm.get_text()
                            except:
                                town = ""
                            address_line2 = "{0} {1}".format(plz, town)
                        else:
                            # parse by address lines
                            try:
                                address_lines = party_soup.find_all("adrline")
                                address_line1 = address_lines[0].get_text()
                                address_line2 = address_lines[1].get_text()
                            except:
                                # in case no address is provided
                                address_line1 = ""
                                address_line2 = ""                            
                    except:
                        # party is not defined (e.g. DBIT from Bank)
                        try:
                            # this is a fallback for ZKB which does not provide nm tag, but address line
                            address_lines = party_soup.find_all("adrline")
                            party_name = address_lines[0].get_text()
                        except:
                            party_name = "not found"
                        address_line1 = ""
                        address_line2 = ""
                    try:
                        country = party_soup.ctry.get_text()
                    except:
                        country = ""
                    if (address_line1 != "") and (address_line2 != ""):
                        party_address = "{0}, {1}, {2}".format(
                            address_line1,
                            address_line2,
                            country)
                    elif (address_line1 != ""):
                        party_address = "{0}, {1}".format(address_line1, country)
                    else:
                        party_address = "{0}".format(country)
                except:
                    # key related parties not found / no customer info
                    party_name = ""
                    party_address = ""
                    party_iban = ""
                try:
                    charges = float(transaction_soup.chrgs.ttlchrgsandtaxamt[text])
                except:
                    charges = 0.0

                try:
                    # try to find ESR reference
                    transaction_reference = transaction_soup.rmtinf.strd.cdtrrefinf.ref.get_text()
                except:
                    try:
                        # try to find a user-defined reference (e.g. SINV.)
                        transaction_reference = transaction_soup.rmtinf.ustrd.get_text()
                    except:
                        try:
                            # try to find an end-to-end ID
                            transaction_reference = transaction_soup.endtoendid.get_text() 
                        except:
                            try:
                                # try to find an AddtlTxInf
                                transaction_reference = transaction_soup.addtltxinf.get_text() 
                            except:
                                # in case of numeric only matching, do not fall back to transaction id
                                if cint(settings.numeric_only_debtor_matching) == 1:
                                    transaction_reference = "???"
                                else:
                                    transaction_reference = unique_reference
                # debug: show collected record in error log
                if settings.debug_mode:
                    frappe.log_error("""type:{type}\ndate:{date}\namount:{currency} {amount}\nunique ref:{unique}
                        party:{party}\nparty address:{address}\nparty iban:{iban}\nremarks:{remarks}
                        payment_instruction_id:{payment_instruction_id}""".format(
                        type=credit_debit, date=date, currency=currency, amount=amount, unique=unique_reference, 
                        party=party_name, address=party_address, iban=party_iban, remarks=transaction_reference,
                        payment_instruction_id=payment_instruction_id))
                
                # check if this transaction is already recorded
                match_payment_entry = frappe.get_all('Payment Entry', 
                    filters={'reference_no': unique_reference, 'company': company}, 
                    fields=['name'])
                if match_payment_entry:
                    if debug or settings.debug_mode:
                        frappe.log_error("Transaction {0} is already imported in {1}.".format(unique_reference, match_payment_entry[0]['name']))
                else:
                    # try to find matching parties & invoices
                    party_match = None
                    employee_match = None
                    invoice_matches = []
                    expense_matches = None
                    matched_amount = 0.0
                    if credit_debit == "DBIT":
                        # match by payment instruction id
                        possible_pinvs = []
                        if payment_instruction_id:
                            try:
                                payment_instruction_fields = payment_instruction_id.split("-")
                                try:
                                    payment_instruction_row = int(payment_instruction_fields[-1]) + 1
                                except:
                                    # invalid payment instruction id (cannot parse, e.g. on LSV or foreign pain.001 source) - no match
                                    payment_instruction_row = None
                                if len(payment_instruction_fields) > 3:
                                    # revision in payment proposal
                                    payment_proposal_id = "{0}-{1}".format(payment_instruction_fields[1], payment_instruction_fields[2])
                                elif len(payment_instruction_fields) > 1:
                                    payment_proposal_id = payment_instruction_fields[1]
                                else:
                                    payment_proposal_id = None
                                # find original instruction record
                                payment_proposal_payments = frappe.get_all("Payment Proposal Payment", 
                                    filters={'parent': payment_proposal_id, 'idx': payment_instruction_row},
                                    fields=['receiver', 'receiver_address_line1', 'receiver_address_line2', 'iban', 'reference', 'receiver_id', 'esr_reference'])
                                # supplier
                                if payment_proposal_payments:
                                    if payment_proposal_payments[0]['receiver_id'] and frappe.db.exists("Supplier", payment_proposal_payments[0]['receiver_id']):
                                        party_match = payment_proposal_payments[0]['receiver_id']
                                    else:
                                        # fallback to supplier name
                                        match_suppliers = frappe.get_all("Supplier", filters={'supplier_name': payment_proposal_payments[0]['receiver']}, 
                                            fields=['name'])
                                        if match_suppliers and len(match_suppliers) > 0:
                                            party_match = match_suppliers[0]['name']
                                    # purchase invoice reference match (take each part separately)
                                    if payment_proposal_payments[0]['esr_reference']:
                                        # match by esr reference number
                                        possible_pinvs = frappe.get_all("Purchase Invoice",
                                            filters=[['docstatus', '=', 1],
                                                ['outstanding_amount', '>', 0],
                                                ['esr_reference_number', '=', payment_proposal_payments[0]['esr_reference']]
                                            ],
                                            fields=['name', 'supplier', 'outstanding_amount', 'bill_no', 'esr_reference_number'])
                                    else:
                                        # check each individual reference (combined pinvs)
                                        possible_pinvs = frappe.get_all("Purchase Invoice",
                                                filters=[['docstatus', '=', 1],
                                                    ['outstanding_amount', '>', 0],
                                                    ['bill_no', 'IN', payment_proposal_payments[0]['reference']]
                                                ],
                                                fields=['name', 'supplier', 'outstanding_amount', 'bill_no', 'esr_reference_number'])
                            except Exception as err:
                                # this can be the case for malformed instruction ids
                                frappe.log_error(err, "Match payment instruction error")
                        # suppliers 
                        if not possible_pinvs:
                            # no payment proposal, try to estimate from other data
                            if not party_match:
                                # find suplier from name
                                match_suppliers = frappe.get_all("Supplier", 
                                    filters={'supplier_name': party_name, 'disabled': 0}, 
                                    fields=['name'])
                                if match_suppliers:
                                    party_match = match_suppliers[0]['name']
                            if party_match:
                                # restrict pinvs to supplier
                                possible_pinvs = frappe.get_all("Purchase Invoice",
                                    filters=[['docstatus', '=', 1], ['outstanding_amount', '>', 0], ['supplier', '=', party_match]],
                                    fields=['name', 'supplier', 'outstanding_amount', 'bill_no', 'esr_reference_number'])
                            else:
                                # purchase invoices
                                possible_pinvs = frappe.get_all("Purchase Invoice", 
                                    filters=[['docstatus', '=', 1], ['outstanding_amount', '>', 0]], 
                                    fields=['name', 'supplier', 'outstanding_amount', 'bill_no', 'esr_reference_number'])
                        if possible_pinvs:
                            for pinv in possible_pinvs:
                                if ((pinv['name'] in transaction_reference) \
                                    or ((pinv['bill_no'] or pinv['name']) in transaction_reference) \
                                    or (pinv['esr_reference_number'] and (pinv['esr_reference_number'].replace(" ", "") in transaction_reference.replace(" ", ""))) \
                                    or (payment_instruction_id == transaction_reference)):              # this is an override for Postfinance combined transactions that will not relay transaction ids
                                    invoice_matches.append(pinv['name'])
                                    # override party match in case there is one from the sales invoice
                                    party_match = pinv['supplier']
                                    # add total matched amount
                                    matched_amount += float(pinv['outstanding_amount'])
                        # employees 
                        match_employees = frappe.get_all("Employee", 
                            filters={'employee_name': party_name, 'status': 'active'}, 
                            fields=['name'])
                        if match_employees:
                            employee_match = match_employees[0]['name']
                        # expense claims
                        possible_expenses = frappe.get_all("Expense Claim", 
                            filters=[['docstatus', '=', 1], ['status', '=', 'Unpaid']], 
                            fields=['name', 'employee', 'total_claimed_amount'])
                        if possible_expenses:
                            expense_matches = []
                            for exp in possible_expenses:
                                if exp['name'] in transaction_reference:
                                    expense_matches.append(exp['name'])
                                    # override party match in case there is one from the sales invoice
                                    employee_match = exp['employee']
                                    # add total matched amount
                                    matched_amount += float(exp['total_claimed_amount'])           
                    else:
                        # customers & sales invoices
                        match_customers = frappe.get_all("Customer", filters={'customer_name': party_name, 'disabled': 0}, fields=['name'])
                        if match_customers:
                            party_match = match_customers[0]['name']
                        # sales invoices
                        possible_sinvs = frappe.get_all("Sales Invoice", 
                            filters=[['outstanding_amount', '>', 0], ['docstatus', '=', 1]], 
                            fields=['name', 'customer', 'customer_name', 'outstanding_amount', 'esr_reference'])
                        if possible_sinvs:
                            invoice_matches = []
                            for sinv in possible_sinvs:
                                is_match = False
                                if sinv['name'] in transaction_reference or ('esr_reference' in sinv and sinv['esr_reference'] and sinv['esr_reference'] == transaction_reference):
                                    # matched exact sales invoice reference or ESR reference
                                    is_match = True
                                elif cint(settings.numeric_only_debtor_matching) == 1:
                                    # allow the numeric part matching
                                    if get_numeric_only_reference(sinv['name']) in transaction_reference: 
                                        # matched numeric part and customer name
                                        is_match = True
                                elif cint(settings.ignore_special_characters) == 1:
                                    if remove_special_characters(sinv['name']) in remove_special_characters(transaction_reference):
                                        # matched without special characters
                                        is_match = True

                                if is_match:
                                    invoice_matches.append(sinv['name'])
                                    # override party match in case there is one from the sales invoice
                                    party_match = sinv['customer']
                                    # add total matched amount
                                    matched_amount += float(sinv['outstanding_amount'])
                                        
                    # reset invoice matches in case there are no matches
                    try:
                        if len(invoice_matches) == 0:
                            invoice_matches = None
                        if len(expense_matches) == 0:
                            expense_matches = None                            
                    except:
                        pass                                                                                                
                    new_txn = {
                        'txid': len(txns),
                        'date': date,
                        'currency': currency,
                        'amount': amount,
                        'party_name': party_name,
                        'party_address': party_address,
                        'credit_debit': credit_debit,
                        'party_iban': party_iban,
                        'unique_reference': unique_reference,
                        'transaction_reference': transaction_reference,
                        'party_match': party_match,
                        'invoice_matches': invoice_matches,
                        'matched_amount': round(matched_amount, 2),
                        'employee_match': employee_match,
                        'expense_matches': expense_matches
                    }
                    txns.append(new_txn)
        else:
            # transaction without TxDtls: occurs at CS when transaction is from a pain.001 instruction
            # get unique ID
            try:
                unique_reference = entry_soup.acctsvcrref.get_text()
            except:
                # fallback: use tx id
                try:
                    unique_reference = entry_soup.txid.get_text()
                except:
                    # fallback to pmtinfid
                    try:
                        unique_reference = entry_soup.pmtinfid.get_text()
                    except:
                        # fallback to hash
                        code = "{0}:{1}:{2}".format(date, entry_currency, entry_amount)
                        unique_reference = hashlib.md5(code.encode("utf-8")).hexdigest()
            # check if this transaction is already recorded
            match_payment_entry = frappe.get_all('Payment Entry', filters={'reference_no': unique_reference}, fields=['name'])
            if match_payment_entry:
                if debug or settings.debug_mode:
                    frappe.log_error("Transaction {0} is already imported in {1}.".format(unique_reference, match_payment_entry[0]['name']))
            else:
                # --- find transaction type: paid or received: (DBIT: paid, CRDT: received)
                credit_debit = entry_soup.cdtdbtind.get_text()
                # find payment instruction ID
                try:
                    payment_instruction_id = entry_soup.pmtinfid.get_text()     # instruction ID, PMTINF-[payment proposal]-row
                    payment_instruction_fields = payment_instruction_id.split("-")
                    payment_instruction_row = int(payment_instruction_fields[-1]) + 1
                    payment_proposal_id = payment_instruction_fields[1]
                    # find original instruction record
                    payment_proposal_payments = frappe.get_all("Payment Proposal Payment", 
                        filters={'parent': payment_proposal_id, 'idx': payment_instruction_row},
                        fields=['receiver', 'receiver_address_line1', 'receiver_address_line2', 'iban', 'reference'])
                    # suppliers 
                    party_match = None
                    if payment_proposal_payments:
                        match_suppliers = frappe.get_all("Supplier", filters={'supplier_name': payment_proposal_payments[0]['receiver']}, 
                            fields=['name'])
                        if match_suppliers:
                            party_match = match_suppliers[0]['name']
                    # purchase invoices 
                    invoice_match = None
                    matched_amount = 0
                    if payment_proposal_payments:
                        match_invoices = frappe.get_all("Purchase Invoice", 
                            filters=[['name', '=', payment_proposal_payments[0]['reference']], ['outstanding_amount', '>', 0]], 
                            fields=['name', 'grand_total'])
                        if match_invoices:
                            invoice_match = [match_invoices[0]['name']]
                            matched_amount = match_invoices[0]['grand_total']
                    if payment_proposal_payments:
                        new_txn = {
                            'txid': len(txns),
                            'date': date,
                            'currency': entry_currency,
                            'amount': entry_amount,
                            'party_name': payment_proposal_payments[0]['receiver'],
                            'party_address': "{0}, {1}".format(
                                payment_proposal_payments[0]['receiver_address_line1'], 
                                payment_proposal_payments[0]['receiver_address_line2']),
                            'credit_debit': credit_debit,
                            'party_iban': payment_proposal_payments[0]['iban'],
                            'unique_reference': unique_reference,
                            'transaction_reference': payment_proposal_payments[0]['reference'],
                            'party_match': party_match,
                            'invoice_matches': invoice_match,
                            'matched_amount': matched_amount
                        }
                        txns.append(new_txn)
                    else:
                        # not matched against payment instruction
                        new_txn = {
                            'txid': len(txns),
                            'date': date,
                            'currency': entry_currency,
                            'amount': entry_amount,
                            'party_name': "???",
                            'party_address': "???",
                            'credit_debit': credit_debit,
                            'party_iban': "???",
                            'unique_reference': unique_reference,
                            'transaction_reference': unique_reference,
                            'party_match': None,
                            'invoice_matches': None,
                            'matched_amount': None
                        }
                        txns.append(new_txn)
                except Exception as err:
                    # no payment instruction
                    new_txn = {
                        'txid': len(txns),
                        'date': date,
                        'currency': entry_currency,
                        'amount': entry_amount,
                        'party_name': "???",
                        'party_address': "???",
                        'credit_debit': credit_debit,
                        'party_iban': "???",
                        'unique_reference': unique_reference,
                        'transaction_reference': unique_reference,
                        'party_match': None,
                        'invoice_matches': None,
                        'matched_amount': None
                    }
                    txns.append(new_txn)

    return txns

@frappe.whitelist()
def make_payment_entry(amount, date, reference_no, paid_from=None, paid_to=None, type="Receive", 
    party=None, party_type=None, references=None, remarks=None, auto_submit=False, exchange_rate=1,
    party_iban=None, company=None):
    # assert list
    if references:
        references = ast.literal_eval(references)
    if str(auto_submit) == "1":
        auto_submit = True
    reference_type = "Sales Invoice"
    # find company
    if not company:
        if paid_from:
            company = frappe.get_value("Account", paid_from, "company")
        elif paid_to:
            company = frappe.get_value("Account", paid_to, "company")
    # prepare to verify exchange rates
    company_currency = frappe.get_value("Company", company, "default_currency")
    if type == "Receive":
        account_currency = frappe.get_value("Account", paid_to, "account_currency")
    else:
        account_currency = frappe.get_value("Account", paid_from, "account_currency")
    if account_currency != company_currency and exchange_rate == 1:
        # re-evaluate exchange rate
        exchange_rate = get_exchange_rate(from_currency=account_currency, to_currency=company_currency, transaction_date=date)
    if type == "Receive":
        # receive
        payment_entry = frappe.get_doc({
            'doctype': 'Payment Entry',
            'payment_type': 'Receive',
            'party_type': party_type,
            'party': party,
            'paid_to': paid_to,
            'paid_amount': float(amount),
            'received_amount': float(amount),
            'reference_no': reference_no,
            'reference_date': date,
            'posting_date': date,
            'remarks': remarks,
            'camt_amount': float(amount),
            'bank_account_no': party_iban,
            'company': company,
            'source_exchange_rate': exchange_rate,
            'target_exchange_rate': exchange_rate
        })
    elif type == "Pay":
        # pay
        payment_entry = frappe.get_doc({
            'doctype': 'Payment Entry',
            'payment_type': 'Pay',
            'party_type': party_type,
            'party': party,
            'paid_from': paid_from,
            'paid_amount': float(amount),
            'received_amount': float(amount),
            'reference_no': reference_no,
            'reference_date': date,
            'posting_date': date,
            'remarks': remarks,
            'camt_amount': float(amount),
            'bank_account_no': party_iban,
            'company': company,
            'source_exchange_rate': exchange_rate,
            'target_exchange_rate': exchange_rate
        })
        if party_type == "Employee":
            reference_type = "Expense Claim"
        else:
            reference_type = "Purchase Invoice"
    else:
        # internal transfer (against intermediate account)
        payment_entry = frappe.get_doc({
            'doctype': 'Payment Entry',
            'payment_type': 'Internal Transfer',
            'paid_from': paid_from,
            'paid_to': paid_to,
            'paid_amount': float(amount),
            'received_amount': float(amount),
            'reference_no': reference_no,
            'reference_date': date,
            'posting_date': date,
            'remarks': remarks,
            'camt_amount': float(amount),
            'bank_account_no': party_iban,
            'company': company,
            'source_exchange_rate': exchange_rate,
            'target_exchange_rate': exchange_rate
        })
    if party_type == "Employee":
        payment_entry.paid_to = get_payable_account(company, employee=True)['account'] or paid_to         # note: at creation, this is ignored
    new_entry = payment_entry.insert()
    # add references after insert (otherwise they are overwritten)
    if references:
        for reference in references:
            create_reference(new_entry.name, reference, reference_type)
    # automatically submit if enabled
    if auto_submit:
        matched_entry = frappe.get_doc("Payment Entry", new_entry.name) # include changes from reference
        if matched_entry.difference_amount != 0:
            # for auto-submit, we need to clear this out to the exchange account
            exchange_account = frappe.get_cached_value("Company", matched_entry.company, "exchange_gain_loss_account")
            cost_center = frappe.get_cached_value("Company", matched_entry.company, "round_off_cost_center")
            matched_entry.append("deductions", {
                'account': exchange_account,
                'cost_center': cost_center,
                'amount': matched_entry.difference_amount
            })
            matched_entry.save()
        matched_entry.submit()
        frappe.db.commit()
    return {'link': get_url_to_form("Payment Entry", new_entry.name), 'payment_entry': new_entry.name}

# creates the reference record in a payment entry
def create_reference(payment_entry, invoice_reference, invoice_type="Sales Invoice"):
    # create a new payment entry reference
    reference_entry = frappe.get_doc({"doctype": "Payment Entry Reference"})
    reference_entry.parent = payment_entry
    reference_entry.parentfield = "references"
    reference_entry.parenttype = "Payment Entry"
    reference_entry.reference_doctype = invoice_type
    reference_entry.reference_name = invoice_reference
    if "Invoice" in invoice_type:
        reference_entry.total_amount = frappe.get_value(invoice_type, invoice_reference, "base_grand_total")
        reference_entry.outstanding_amount = frappe.get_value(invoice_type, invoice_reference, "outstanding_amount")
        paid_amount = frappe.get_value("Payment Entry", payment_entry, "paid_amount")
        if paid_amount > reference_entry.outstanding_amount:
            reference_entry.allocated_amount = reference_entry.outstanding_amount
        else:
            reference_entry.allocated_amount = paid_amount
    else:
        # expense claim:
        reference_entry.total_amount = frappe.get_value(invoice_type, invoice_reference, "total_claimed_amount")
        reference_entry.outstanding_amount = reference_entry.total_amount
        paid_amount = frappe.get_value("Payment Entry", payment_entry, "paid_amount")
        if paid_amount > reference_entry.outstanding_amount:
            reference_entry.allocated_amount = reference_entry.outstanding_amount
        else:
            reference_entry.allocated_amount = paid_amount
    reference_entry.insert();
    # update unallocated amount
    payment_record = frappe.get_doc("Payment Entry", payment_entry)
    payment_record.unallocated_amount -= reference_entry.allocated_amount
    payment_record.save()
    return

def get_numeric_only_reference(s):
    n = ""
    for c in s:
        if c.isdigit():
            n += c
    return n

def remove_special_characters(s):
    return (s or "").replace(" ", "").replace("-", "")

@frappe.whitelist()
def validate_journal_template(template_name, transaction_type, bank_account):
    """
    Validate if the journal entry template is compatible with the transaction.
    Check if there's a bank account in the template that matches the transaction type.
    """
    template = frappe.get_doc("Journal Entry Template", template_name)
    bank_account_type = frappe.get_value("Account", bank_account, "account_type")
    
    # Get all accounts from the template
    template_accounts = []
    
    # Check in the standard accounts field
    if hasattr(template, 'accounts') and template.accounts:
        for account_row in template.accounts:
            account_type = frappe.get_value("Account", account_row.account, "account_type")
            if account_type == "Bank":
                template_accounts.append(account_row.account)
    
    # Check in accounting_entry_counterparty (if exists - custom field)
    if hasattr(template, 'accounting_entry_counterparty') and template.accounting_entry_counterparty:
        for account_row in template.accounting_entry_counterparty:
            account_type = frappe.get_value("Account", account_row.account, "account_type")
            if account_type == "Bank":
                template_accounts.append(account_row.account)
    
    # Check in accounting_entry_totalization (if exists - custom field)
    if hasattr(template, 'accounting_entry_totalization') and template.accounting_entry_totalization:
        for account_row in template.accounting_entry_totalization:
            account_type = frappe.get_value("Account", account_row.account, "account_type")
            if account_type == "Bank":
                template_accounts.append(account_row.account)
    
    if not template_accounts:
        return {
            'valid': False,
            'message': _('The selected template does not contain any bank account. Please select a template with at least one bank account.')
        }
    
    return {
        'valid': True,
        'bank_accounts': template_accounts
    }

@frappe.whitelist()
def make_journal_entry_from_template(template_name, transaction, bank_account, company, user_remark=None):
    """
    Create a journal entry from a template for the given transaction.
    """
    import json
    
    # Parse transaction if it's a string
    if isinstance(transaction, str):
        transaction = json.loads(transaction)
    
    # Get the template
    template = frappe.get_doc("Journal Entry Template", template_name)
    
    # Create new journal entry
    journal_entry = frappe.new_doc("Journal Entry")
    journal_entry.voucher_type = template.voucher_type
    journal_entry.company = company
    journal_entry.posting_date = transaction['date']
    
    # Use provided user_remark or create default one
    if user_remark:
        journal_entry.user_remark = user_remark
    else:
        journal_entry.user_remark = "{0} - {1}".format(
            transaction.get('transaction_reference', ''),
            transaction.get('party_name', '')
        )
    
    # Use template naming series if available
    if hasattr(template, 'naming_series') and template.naming_series:
        journal_entry.naming_series = template.naming_series
    
    # Determine which account should be the bank account
    bank_account_added = False
    
    # Process standard accounts from template
    if hasattr(template, 'accounts') and template.accounts:
        for template_account in template.accounts:
            account_type = frappe.get_value("Account", template_account.account, "account_type")
            
            # Add account entry
            je_account = journal_entry.append('accounts', {})
            je_account.account = template_account.account
            
            # If this is a bank account, use the transaction's bank account and amount
            if account_type == "Bank" and not bank_account_added:
                je_account.account = bank_account
                if transaction['credit_debit'] == 'DBIT':
                    je_account.credit_in_account_currency = float(transaction['amount'])
                else:
                    je_account.debit_in_account_currency = float(transaction['amount'])
                bank_account_added = True
            else:
                # For non-bank accounts, set the opposite amount
                if transaction['credit_debit'] == 'DBIT':
                    je_account.debit_in_account_currency = float(transaction['amount'])
                else:
                    je_account.credit_in_account_currency = float(transaction['amount'])
    
    # Process custom accounting_entry_counterparty (if exists)
    if hasattr(template, 'accounting_entry_counterparty') and template.accounting_entry_counterparty:
        for template_account in template.accounting_entry_counterparty:
            account_type = frappe.get_value("Account", template_account.account, "account_type")
            
            je_account = journal_entry.append('accounts', {})
            je_account.account = template_account.account
            
            if hasattr(template_account, 'user_remark'):
                je_account.user_remark = template_account.user_remark
            
            # If this is a bank account, use the transaction's bank account
            if account_type == "Bank" and not bank_account_added:
                je_account.account = bank_account
                if transaction['credit_debit'] == 'DBIT':
                    je_account.credit_in_account_currency = float(transaction['amount'])
                else:
                    je_account.debit_in_account_currency = float(transaction['amount'])
                bank_account_added = True
            else:
                # Counterparty accounts get the opposite of the bank movement
                if transaction['credit_debit'] == 'DBIT':
                    je_account.debit_in_account_currency = float(transaction['amount'])
                else:
                    je_account.credit_in_account_currency = float(transaction['amount'])
    
    # Process custom accounting_entry_totalization (if exists)
    if hasattr(template, 'accounting_entry_totalization') and template.accounting_entry_totalization:
        for template_account in template.accounting_entry_totalization:
            account_type = frappe.get_value("Account", template_account.account, "account_type")
            
            je_account = journal_entry.append('accounts', {})
            je_account.account = template_account.account
            
            if hasattr(template_account, 'user_remark'):
                je_account.user_remark = template_account.user_remark
            
            # If this is a bank account, use the transaction's bank account
            if account_type == "Bank" and not bank_account_added:
                je_account.account = bank_account
                if transaction['credit_debit'] == 'DBIT':
                    je_account.credit_in_account_currency = float(transaction['amount'])
                else:
                    je_account.debit_in_account_currency = float(transaction['amount'])
                bank_account_added = True
            else:
                # Totalization accounts should have the opposite of the counterparty
                # This ensures the balance is zero
                if transaction['credit_debit'] == 'DBIT':
                    je_account.debit_in_account_currency = float(transaction['amount'])
                else:
                    je_account.credit_in_account_currency = float(transaction['amount'])
    
    # Set multi currency if template specifies it
    if hasattr(template, 'multi_currency') and template.multi_currency:
        journal_entry.multi_currency = 1
    
    # Add reference to the EBICS transaction
    journal_entry.cheque_no = transaction.get('unique_reference', '')
    journal_entry.cheque_date = transaction['date']
    
    # Add reference to the template used
    if hasattr(journal_entry, 'from_template'):
        journal_entry.from_template = template_name
    
    # Save the journal entry
    journal_entry.insert()
    
    return {
        'journal_entry': journal_entry.name,
        'link': get_url_to_form("Journal Entry", journal_entry.name)
    }
    
