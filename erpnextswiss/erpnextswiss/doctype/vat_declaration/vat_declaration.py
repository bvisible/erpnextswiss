# -*- coding: utf-8 -*-
# Copyright (c) 2017-2023, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from datetime import datetime
from frappe.utils import flt

@frappe.whitelist()
def get_total_payments(start_date, end_date, company=None, flat=False):
    flat = str(flat).lower() == "true"
    sums_by_tax_code = {}
    sell_account_start = 3000
    sell_account_end = 3999
    purchase_account_start = 4000
    purchase_account_end = 6999
    net_sell = {"total_debit": 0, "total_credit": 0}
    net_purchase = {"total_debit": 0, "total_credit": 0}
    no_vat_sell = {"total_debit": 0, "total_credit": 0}

    summary_payment_entry = []
    summary_sales_invoice = []
    summary_journal_entry = []
    summary_payment_entry = []
    summary_no_vat = []
    summary_purchase_invoice = []
    summaries = {
        "Sales Invoice": summary_sales_invoice,
        "Purchase Invoice": summary_purchase_invoice,
        "Journal Entry": summary_journal_entry,
        "Payment Entry": summary_payment_entry
    }
    no_vat_si_entries = []
    no_vat_pi_entries = []
    no_vat_entries = {
        "Sales Invoice": no_vat_si_entries,
        "Purchase Invoice": no_vat_pi_entries
    }
    si_gl_entries = []
    pi_gl_entries = []
    je_gl_entries = []
    pe_gl_entries = []
    entries = {
        "Sales Invoice": si_gl_entries,
        "Purchase Invoice": pi_gl_entries,
        "Journal Entry": je_gl_entries,
        "Payment Entry": pe_gl_entries
    }

    if company:
        payment_entries = frappe.db.get_all("Payment Entry", filters={"posting_date": ["between", [start_date, end_date]], "docstatus": 1, "company": company}, fields=["name"])
    else:
        payment_entries = frappe.db.get_all("Payment Entry", filters={"posting_date": ["between", [start_date, end_date]], "docstatus": 1}, fields=["name"])
    frappe.neolog("payment_entries", payment_entries)
    for payment_entry in payment_entries:
        summary_sums_by_tax_code = {}
        '''summary_net_sell = {"total_debit": 0, "total_credit": 0}
        summary_net_purchase = {"total_debit": 0, "total_credit": 0}
        summary_no_vat_sell = {"total_debit": 0, "total_credit": 0}'''
        summary_no_vat_purchase = {"total_debit": 0, "total_credit": 0}
        si_merge_taxable_accounts = {}
        pi_merge_taxable_accounts = {}
        split_si_gl_entries = []
        split_pi_gl_entries = []
        split_je_gl_entries = []
        split_entries = {
            "Sales Invoice": split_si_gl_entries,
            "Purchase Invoice": split_pi_gl_entries,
            "Journal Entry": split_je_gl_entries
        }
        doc = frappe.get_doc("Payment Entry", payment_entry.name)
        #frappe.neolog("references", doc.references)
        for reference in doc.references:
            handle_entries(reference.reference_doctype, reference.reference_name, flat, sums_by_tax_code, sell_account_start, sell_account_end, purchase_account_start, purchase_account_end, net_sell, net_purchase, no_vat_sell, summaries, summary_no_vat, entries, no_vat_entries, received=True, reference=reference, summary_sums_by_tax_code=summary_sums_by_tax_code, summary_no_vat_purchase=summary_no_vat_purchase, split_entries=split_entries, pe_date=doc.posting_date)
        
        '''if not frappe.db.get_all("Payment Entry Deduction", filters={"parent": payment_entry.name}):
            continue
        handle_entries("Payment Entry", payment_entry.name, flat, sums_by_tax_code, sell_account_start, sell_account_end, purchase_account_start, purchase_account_end, net_sell, net_purchase, no_vat_sell, summaries, summary_no_vat, entries, no_vat_entries, reference=payment_entry)'''
    frappe.neolog("pi_gl_entries pi", pi_gl_entries)
         

    if company:
        consolidated_invoices = frappe.db.get_all("Sales Invoice", filters={"posting_date": ["between", [start_date, end_date]], "is_consolidated": 1, "docstatus": 1, "company": company}, fields=["name", "posting_date"])
    else:
        consolidated_invoices = frappe.db.get_all("Sales Invoice", filters={"posting_date": ["between", [start_date, end_date]], "is_consolidated": 1, "docstatus": 1}, fields=["name", "posting_date"])
    for invoice in consolidated_invoices:
        handle_entries("Sales Invoice", invoice.name, flat, sums_by_tax_code, sell_account_start, sell_account_end, purchase_account_start, purchase_account_end, net_sell, net_purchase, no_vat_sell, summaries, summary_no_vat, entries, no_vat_entries, pe_date=invoice.posting_date)

    if company:
        journal_entries = frappe.db.get_all("Journal Entry", filters={"posting_date": ["between", [start_date, end_date]], "docstatus":1, "company": company}, fields=["name"])
    else:
        journal_entries = frappe.db.get_all("Journal Entry", filters={"posting_date": ["between", [start_date, end_date]], "docstatus":1}, fields=["name"])
    for journal_entry in journal_entries:
        handle_entries("Journal Entry", journal_entry.name, flat, sums_by_tax_code, sell_account_start, sell_account_end, purchase_account_start, purchase_account_end, net_sell, net_purchase, no_vat_sell, summaries, summary_no_vat, entries, no_vat_entries)             
    
    summary_journal_entry, summary_journal_entry_old, summary_journal_entry_new = sort_split_list(summary_journal_entry, [], [])                

    summary_sales_invoice, summary_sales_invoice_old, summary_sales_invoice_new = sort_split_list(summary_sales_invoice, [], [])

    summary_purchase_invoice = sort_split_list(summary_purchase_invoice)

    summary_no_vat = sort_split_list(summary_no_vat)
    #frappe.neolog("si_gl_entries", si_gl_entries)
    
    si_vat_summary = get_recap_values(si_gl_entries, "Sales Invoice", flat)
    
    pi_vat_summary = get_recap_values(pi_gl_entries, "Purchase Invoice", flat)
    
    je_vat_summary = get_recap_values(je_gl_entries, "Journal Entry", flat)
    
    pe_vat_summary = get_recap_values(pe_gl_entries, "Payment Entry", flat)
    
    si_gl_entries = sort_entries(si_gl_entries)
    
    pi_gl_entries = sort_entries(pi_gl_entries)
    
    je_gl_entries = sort_entries(je_gl_entries)
    
    pe_gl_entries = sort_entries(pe_gl_entries)
    
    no_vat_si_entries = sort_entries(no_vat_si_entries)
    
    no_vat_pi_entries = sort_entries(no_vat_pi_entries)
    
    # Dictionary to count occurrences
    counts = {}

    # Loop through the list of dictionaries and count occurrences
    for record in pi_gl_entries:
        key = (record["voucher_no"], record["debit"], record["credit"])
        if key in counts:
            counts[key].append(record)
        else:
            counts[key] = [record]

    # Extract all entries that have more than one occurrence
    repeated_entries = [entries for entries in counts.values() if len(entries) > 1]

    # Flatten the list of repeated entries
    repeated_entries_flat = [item for sublist in repeated_entries for item in sublist]

    # Display the repeated entries
    for entry in repeated_entries_flat:
        pass
    frappe.neolog("repeated_entries", repeated_entries_flat)
    
    payment_references = frappe.get_all(
            'Payment Entry Reference',
            filters={'reference_name': "ACC-PINV-2024-00196"},
            fields=['name', 'parent', 'reference_name']
        )
    frappe.neolog("payment_references", payment_references)

    return {"sums_by_tax_code": sums_by_tax_code, "net_sell": net_sell, "net_purchase": net_purchase,
            "no_vat_sell": no_vat_sell, "summary_sales_invoice_old": summary_sales_invoice_old,
            "summary_sales_invoice_new": summary_sales_invoice_new, "summary_sales_invoice": summary_sales_invoice,
            "summary_journal_entry_old": summary_journal_entry_old, "summary_journal_entry_new": summary_journal_entry_new,
            "summary_payment_entry": summary_payment_entry,  "summary_no_vat": summary_no_vat, "summary_purchase_invoice": summary_purchase_invoice,
            "si_gl_entries": si_gl_entries, "pi_gl_entries": pi_gl_entries, "je_gl_entries": je_gl_entries, "pe_gl_entries": pe_gl_entries,
            "no_vat_si_entries": no_vat_si_entries, "no_vat_pi_entries": no_vat_pi_entries, "si_vat_summary": si_vat_summary,
            "pi_vat_summary": pi_vat_summary, "je_vat_summary": je_vat_summary, "pe_vat_summary": pe_vat_summary}

@frappe.whitelist()
def get_total_invoiced(start_date, end_date, company=None, flat=False):
    flat = str(flat).lower() == "true"
    sums_by_tax_code = {}
    sell_account_start = 3000
    sell_account_end = 3999
    purchase_account_start = 4000
    purchase_account_end = 6999
    net_sell = {"total_debit": 0, "total_credit": 0}
    net_purchase = {"total_debit": 0, "total_credit": 0}
    no_vat_sell = {"total_debit": 0, "total_credit": 0}

    summary_sales_invoice = []
    summary_purchase_invoice = []
    summary_journal_entry = []
    summary_payment_entry = []
    summary_no_vat = []
    summaries = {
        "Sales Invoice": summary_sales_invoice,
        "Purchase Invoice": summary_purchase_invoice,
        "Journal Entry": summary_journal_entry,
        "Payment Entry": summary_payment_entry
    }
    no_vat_si_entries = []
    no_vat_pi_entries = []
    no_vat_entries = {
        "Sales Invoice": no_vat_si_entries,
        "Purchase Invoice": no_vat_pi_entries
    }
    si_gl_entries = []
    pi_gl_entries = []
    je_gl_entries = []
    pe_gl_entries = []
    entries = {
        "Sales Invoice": si_gl_entries,
        "Purchase Invoice": pi_gl_entries,
        "Journal Entry": je_gl_entries,
        "Payment Entry": pe_gl_entries
    }

    if company:
        invoices = frappe.db.get_all("Sales Invoice", filters={"posting_date": ["between", [start_date, end_date]], "docstatus": 1, "company": company}, fields=["name"])
    else:
        invoices = frappe.db.get_all("Sales Invoice", filters={"posting_date": ["between", [start_date, end_date]], "docstatus": 1}, fields=["name"])
    for invoice in invoices:
        handle_entries("Sales Invoice", invoice.name, flat, sums_by_tax_code, sell_account_start, sell_account_end, purchase_account_start, purchase_account_end, net_sell, net_purchase, no_vat_sell, summaries, summary_no_vat, entries, no_vat_entries)

    if company:
        invoices = frappe.db.get_all("Purchase Invoice", filters={"posting_date": ["between", [start_date, end_date]], "docstatus": 1, "company": company}, fields=["name"])
    else:
        invoices = frappe.db.get_all("Purchase Invoice", filters={"posting_date": ["between", [start_date, end_date]], "docstatus": 1}, fields=["name"])
    for invoice in invoices:
        handle_entries("Purchase Invoice", invoice.name, flat, sums_by_tax_code, sell_account_start, sell_account_end, purchase_account_start, purchase_account_end, net_sell, net_purchase, no_vat_sell, summaries, summary_no_vat, entries, no_vat_entries)

    if company:
        journal_entries = frappe.db.get_all("Journal Entry", filters={"posting_date": ["between", [start_date, end_date]], "docstatus":1, "company": company}, fields=["name"])
    else:
        journal_entries = frappe.db.get_all("Journal Entry", filters={"posting_date": ["between", [start_date, end_date]], "docstatus":1}, fields=["name"])
    for journal_entry in journal_entries:
        handle_entries("Journal Entry", journal_entry.name, flat, sums_by_tax_code, sell_account_start, sell_account_end, purchase_account_start, purchase_account_end, net_sell, net_purchase, no_vat_sell, summaries, summary_no_vat, entries, no_vat_entries)

    if company:
        payment_entries = frappe.db.get_all("Payment Entry", filters={"posting_date": ["between", [start_date, end_date]], "docstatus": 1, "company": company}, fields=["name", "payment_type"])
    else:
        payment_entries = frappe.db.get_all("Payment Entry", filters={"posting_date": ["between", [start_date, end_date]], "docstatus": 1}, fields=["name", "payment_type"])

    for payment_entry in payment_entries:
        if not frappe.db.get_all("Payment Entry Deduction", filters={"parent": payment_entry.name}):
            continue
        handle_entries("Payment Entry", payment_entry.name, flat, sums_by_tax_code, sell_account_start, sell_account_end, purchase_account_start, purchase_account_end, net_sell, net_purchase, no_vat_sell, summaries, summary_no_vat, entries, no_vat_entries, reference=payment_entry, payment_type=payment_entry.payment_type)

    '''if company:
        payment_entries = frappe.db.get_all("Payment Entry", filters={"posting_date": ["between", [start_date, end_date]], "docstatus": 1, "company": company}, fields=["name"])
    else:
        payment_entries = frappe.db.get_all("Payment Entry", filters={"posting_date": ["between", [start_date, end_date]], "docstatus": 1}, fields=["name"])
    for payment_entry in payment_entries:
        summary_sums_by_tax_code = {}
        summary_net_sell = {"total_debit": 0, "total_credit": 0}
        summary_net_purchase = {"total_debit": 0, "total_credit": 0}
        summary_no_vat_sell = {"total_debit": 0, "total_credit": 0}
        summary_no_vat_purchase = {"total_debit": 0, "total_credit": 0}
        si_merge_taxable_accounts = {}
        pi_merge_taxable_accounts = {}
        split_si_gl_entries = []
        split_pi_gl_entries = []
        split_je_gl_entries = []
        doc = frappe.get_doc("Payment Entry", payment_entry.name)
        frappe.neolog("references", doc.references)


        accounts = []
        for account_data in payment_entry.deductions:
            if account_data.account not in accounts:
                accounts.append(account_data.account)
        gl_entries = frappe.db.get_all("GL Entry", filters={"voucher_no": payment_entry.name, "is_cancelled": 0}, fields=['*'])
        for gl_entry in gl_entries:
            if gl_entry.account in accounts:
                acc_number = frappe.db.get_value("Account", gl_entry.account, "account_number")
                if acc_number >= sell_account_start and acc_number <= sell_account_end:
                    net_sell["total_debit"] += gl_entry.debit
                    net_sell["total_credit"] += gl_entry.credit
                else:
                    net_purchase["total_debit"] += gl_entry.debit
                    net_purchase["total_credit"] += gl_entry.credit'''
      
    summary_journal_entry, summary_journal_entry_old, summary_journal_entry_new = sort_split_list(summary_journal_entry, [], [])                

    summary_sales_invoice, summary_sales_invoice_old, summary_sales_invoice_new = sort_split_list(summary_sales_invoice, [], [])

    summary_purchase_invoice = sort_split_list(summary_purchase_invoice)

    summary_no_vat = sort_split_list(summary_no_vat)
    
    si_vat_summary = get_recap_values(si_gl_entries, "Sales Invoice", flat)
    
    pi_vat_summary = get_recap_values(pi_gl_entries, "Purchase Invoice", flat)
    
    je_vat_summary = get_recap_values(je_gl_entries, "Journal Entry", flat)
    
    pe_vat_summary = get_recap_values(pe_gl_entries, "Payment Entry", flat)
    
    si_gl_entries = sort_entries(si_gl_entries)
    
    pi_gl_entries = sort_entries(pi_gl_entries)
    
    je_gl_entries = sort_entries(je_gl_entries)
    
    pe_gl_entries = sort_entries(pe_gl_entries)
    
    no_vat_si_entries = sort_entries(no_vat_si_entries)
    
    no_vat_pi_entries = sort_entries(no_vat_pi_entries)
    
    return {"sums_by_tax_code": sums_by_tax_code, "net_sell": net_sell, "net_purchase": net_purchase, "no_vat_sell": no_vat_sell,
            "summary_sales_invoice": summary_sales_invoice,
            "summary_sales_invoice_old": summary_sales_invoice_old, "summary_sales_invoice_new": summary_sales_invoice_new,
            "summary_journal_entry_old": summary_journal_entry_old, "summary_journal_entry_new": summary_journal_entry_new,
            "summary_purchase_invoice": summary_purchase_invoice, "summary_no_vat": summary_no_vat,
            "si_gl_entries": si_gl_entries, "pi_gl_entries": pi_gl_entries, "je_gl_entries": je_gl_entries, "pe_gl_entries": pe_gl_entries,
            "no_vat_si_entries": no_vat_si_entries, "no_vat_pi_entries": no_vat_pi_entries, "si_vat_summary": si_vat_summary,
            "pi_vat_summary": pi_vat_summary, "je_vat_summary": je_vat_summary, "pe_vat_summary": pe_vat_summary}

def split_vat_items(base_list, force_new=False):
    list_with_2 = []
    list_with_3 = []
    for item in base_list:
        #vat_with_2 = any(key.endswith('2') and value > 0 for key, value in item.items() if key.startswith('vat_'))
        vat_with_2 = False
        for key, value in item.items():
            if key.startswith('vat_') and key.endswith('2') and value > 0:
                vat_with_2 = True
                break
        if force_new:
            #vat_2_are_zero = all(value == 0 for key, value in item.items() if key.startswith('vat_') and key.endswith('2'))
            vat_with_3 = True
            for key, value in item.items():
                if key.startswith('vat_') and key.endswith('2') and value != 0:
                    vat_with_3 = False
                    break
        else:
            #vat_with_3 = any(key.endswith('3') and value > 0 for key, value in item.items() if key.startswith('vat_')) and vat_2_are_zero
            vat_with_3 = False
            for key, value in item.items():
                if key.startswith('vat_') and key.endswith('3') and value > 0:
                    vat_with_3 = True
                    break
        if vat_with_2:
            list_with_2.append(item)
        if vat_with_3:
            list_with_3.append(item)

    return list_with_2, list_with_3

def sort_split_list(base_list, old_list=None, new_list=None):
    base_list = sorted(base_list, key=lambda x: x['posting_date'])
    if old_list is not None and new_list is not None:
        old_list, new_list = split_vat_items(base_list)
        sum_dict = {}
        for d in old_list:
            for key, value in d.items():
                if key not in ["document_type", "document_name", "posting_date"]:
                    sum_dict[key] = sum_dict.get(key, 0) + value
        old_list.append(sum_dict)
        sum_dict = {}
        for d in new_list:
            for key, value in d.items():
                if key not in ["document_type", "document_name", "posting_date"]:
                    sum_dict[key] = sum_dict.get(key, 0) + value
        new_list.append(sum_dict)
        return base_list, old_list, new_list
    else:
        sum_dict = {}
        for d in base_list:
            for key, value in d.items():
                if key not in ["document_type", "document_name", "posting_date"]:
                    sum_dict[key] = sum_dict.get(key, 0) + value
        base_list.append(sum_dict)
        return base_list
    
def sort_entries(data):
    if data:
        sorted_df = data
        date_sort = 'paid_date' if sorted_df[0].get('paid_date') else 'posting_date'
        '''import pandas as pd
        df = pd.DataFrame(data)
        df['posting_date'] = pd.to_datetime(df['posting_date'])
        df['paid_date'] = pd.to_datetime(df['paid_date']) if data[0].get('paid_date') else None 
        df['effective_date'] = df['paid_date'] if data[0].get('paid_date') else df['posting_date']
        sorted_df = df.sort_values(by=['effective_date', 'voucher_no'])
        sorted_df = sorted_df.drop(columns='effective_date')  # Clean up the DataFrame'''
        sums = {"credit": 0, "debit": 0, "net_sell": 0, "net_purchase": 0}
        for record in data:
            sums["credit"] += record["credit"] if record.get("credit") else 0
            sums["debit"] += record["debit"] if record.get("debit") else 0
            sums["net_sell"] += record["net_sell"] if record.get("net_sell") else 0
            sums["net_purchase"] += record["net_purchase"] if record.get("net_purchase") else 0
        sorted_final = sorted(sorted_df, key=lambda x: x[date_sort])
        #sorted_final = sorted_df
        sum_row = {"posting_date": "", "voucher_type": "", "voucher_no": "", "remarks": "", "payment_type": "", "against": "", "tax_rate": "", "debit": sums["debit"], "credit": sums["credit"],
            "tax_code": "", "against_account": "", "net_sell": "", "net_purchase": "", "total_vat": "", "net_sell": sums["net_sell"], "net_purchase": sums["net_purchase"],
        }
        sorted_final += [sum_row]
        return sorted_final
    return data
    
def handle_entries(dt, dn, flat, sums_by_tax_code, sell_account_start, sell_account_end, purchase_account_start, purchase_account_end, net_sell, net_purchase, no_vat_sell, summaries, summary_no_vat, entries, no_vat_entries, received=False, reference=None, summary_sums_by_tax_code={}, summary_no_vat_purchase=None, split_entries=None, payment_type=None, pe_date=None):
    summary_dt = summaries[dt]
    dt_gl_entries = entries[dt]
    summary_net_sell = {"total_debit": 0, "total_credit": 0}
    summary_net_purchase = {"total_debit": 0, "total_credit": 0}
    summary_no_vat_sell = {"total_debit": 0, "total_credit": 0}
    gl_entries = frappe.db.get_all("GL Entry", filters={"voucher_no": dn, "is_cancelled": 0}, fields=['*'])
    has_vat = False
    add_sell_debit = 0
    add_sell_credit = 0
    add_purchase_debit = 0
    add_purchase_credit = 0
    merge_taxable_accounts = {}
    split_dt_gl_entries = []
    posting_date = frappe.db.get_value(dt, dn, "posting_date")
    if received:
        ratio = 1
        if dt != "Payment Entry":
            allocated = reference.allocated_amount
            meta = frappe.get_meta(reference.reference_doctype)
            rounded_total = None
            grand_total = None
            if meta.has_field("grand_total"):
                grand_total = frappe.db.get_value(reference.reference_doctype, reference.reference_name, "grand_total")
            if meta.has_field("rounded_total"):
                rounded_total = frappe.db.get_value(reference.reference_doctype, reference.reference_name, "rounded_total")
            if not rounded_total and not grand_total:
                grand_total = reference.total_amount
            posting_date = frappe.db.get_value(reference.reference_doctype, reference.reference_name, "posting_date")
            ref_doc_total = rounded_total or grand_total
            ratio = allocated / ref_doc_total
            #frappe.neolog("voucher: {}, ratio: {}".format(reference.reference_name, ratio))
            summary_sums_by_tax_code_variable = {}

    for gl_entry in gl_entries:
        tax_code, tax_rate = frappe.db.get_value("Account", gl_entry.account, ["tax_code", "tax_rate"])
        if tax_code:
            if tax_code not in sums_by_tax_code:
                sums_by_tax_code[tax_code] = {
                    "total_debit": 0,
                    "total_credit": 0
                }
            sums_by_tax_code[tax_code]["total_debit"] += gl_entry.debit * ratio if received else gl_entry.debit
            sums_by_tax_code[tax_code]["total_credit"] += gl_entry.credit * ratio if received else gl_entry.credit
            if int(tax_code) == 400:
                debit = gl_entry.debit * ratio if received else gl_entry.debit
                credit = gl_entry.credit * ratio if received else gl_entry.credit
            # for summary table
            if tax_code not in summary_sums_by_tax_code:
                summary_sums_by_tax_code[tax_code] = {
                    "total_debit": 0,
                    "total_credit": 0
                }
            summary_sums_by_tax_code[tax_code]["total_debit"] += gl_entry.debit * ratio if received else gl_entry.debit
            summary_sums_by_tax_code[tax_code]["total_credit"] += gl_entry.credit * ratio if received else gl_entry.credit
            
            if received and dt != "Payment Entry":
                if tax_code not in summary_sums_by_tax_code_variable:
                    summary_sums_by_tax_code_variable[tax_code] = {
                        "total_debit": 0,
                        "total_credit": 0
                    }
                if tax_code not in summary_sums_by_tax_code:
                    summary_sums_by_tax_code[tax_code] = {
                        "total_debit": 0,
                        "total_credit": 0
                    }
                summary_sums_by_tax_code[tax_code]["total_debit"] += gl_entry.debit * ratio if received else gl_entry.debit
                summary_sums_by_tax_code[tax_code]["total_credit"] += gl_entry.credit * ratio if received else gl_entry.credit
                summary_sums_by_tax_code_variable[tax_code]["total_debit"] += gl_entry.debit * ratio if received else gl_entry.debit
                summary_sums_by_tax_code_variable[tax_code]["total_credit"] += gl_entry.credit * ratio if received else gl_entry.credit
            # end summary table
            if not has_vat and (gl_entry.debit != 0 or gl_entry.credit != 0):
                has_vat = True

            entry_gl = {
                "debit": gl_entry.debit * ratio if received else gl_entry.debit,
                "credit": gl_entry.credit * ratio if received else gl_entry.credit,
                "account": gl_entry.account,
                "against": gl_entry.against,
                "voucher_type": gl_entry.voucher_type,
                "posting_date": posting_date,
                "tax_code": str(tax_code),
                "tax_rate": str(tax_rate),
                "voucher_no": gl_entry.voucher_no,
                "remarks": gl_entry.remarks,
            }
            if dt == "Payment Entry":
                if reference:
                    entry_gl["payment_type"] = reference.payment_type
            if pe_date:
                entry_gl["paid_date"] = pe_date
            if dt == "Journal Entry":
                split_remarks = gl_entry.remarks.split("Note : ")
                entry_gl["remarks"] = split_remarks[1] if len(split_remarks) > 1 else None
                entry_gl["against_account"] = split_remarks[0] if split_remarks else None
            split_dt_gl_entries.append(entry_gl)
        else:
            account_number = frappe.db.get_value("Account", gl_entry.account, "account_number")
            if not account_number:
                account_link = frappe.utils.get_link_to_form("Account", gl_entry.account)
                doc_link = frappe.utils.get_link_to_form(dt, dn)

                frappe.throw(
                    _("Le compte {0} utilisé dans {1} n'a pas de numéro de compte configuré. Veuillez :\n"
                      "1. Aller dans la configuration du compte\n"
                      "2. Ajouter un numéro de compte dans le champ 'Numéro de compte'\n"
                      "3. Sauvegarder les modifications").format(
                        account_link,
                        doc_link
                    ),
                    title=_("Numéro de compte manquant")
                )

            if int(sell_account_start) <= int(account_number) <= int(sell_account_end):
                entry_debit = gl_entry.debit * ratio if received else gl_entry.debit
                entry_credit = gl_entry.credit * ratio if received else gl_entry.credit
                add_sell_debit += entry_debit
                add_sell_credit += entry_credit
                if flat:
                    entry_gl = {
                        "debit": entry_debit,
                        "credit": entry_credit,
                        "account": gl_entry.account,
                        "against": gl_entry.against,
                        "voucher_type": gl_entry.voucher_type,
                        "posting_date": posting_date,
                        "voucher_no": gl_entry.voucher_no,
                        "remarks": gl_entry.remarks,
                        "against_account": account_number,
                        "net_sell": add_sell_credit - add_sell_debit
                    }
                    if pe_date:
                        entry_gl["paid_date"] = pe_date
                    if dt == "Journal Entry":
                        split_remarks = gl_entry.remarks.split("Note : ")
                        entry_gl["remarks"] = split_remarks[1] if len(split_remarks) > 1 else None
                    split_dt_gl_entries.append(entry_gl)
            elif int(purchase_account_start) <= int(account_number) <= int(purchase_account_end):
                add_purchase_debit += gl_entry.debit * ratio if received else gl_entry.debit
                add_purchase_credit += gl_entry.credit * ratio if received else gl_entry.credit
                
    if any(keyword in dt for keyword in ["Sales", "Purchase"]):
        fields = ["item_tax_template", "income_account", "net_amount", "amount"] if "Sales" in dt else ["item_tax_template", "expense_account", "net_amount", "amount"]
        items = frappe.db.get_all(dt + " Item", filters={"parent": dn}, fields=fields)
        net_sell_vat = 0
        net_purchase_vat = 0
        no_vat_entry = {
            "voucher_type": dt,
            "voucher_no": dn,
            "posting_date": posting_date,
        }
        if pe_date:
            no_vat_entry["paid_date"] = pe_date
        for item in items:
            if item.item_code in ["Freeline", "Freeline"]:
                continue
            item_account = item.income_account if "Sales" in dt else item.expense_account
            taxable_account_data = get_taxable_account(item_account, item.item_tax_template)
            if taxable_account_data:
                rate = taxable_account_data[0].get("rate")
                account = frappe.db.get_value("Account", item_account, "account_number")
                item_amount = item.net_amount if item.net_amount else item.amount
                
                if rate not in merge_taxable_accounts:
                    merge_taxable_accounts[rate] = {}
                    merge_taxable_accounts[rate]["account"] = account
                    merge_taxable_accounts[rate]["net_sell"] = 0
                    merge_taxable_accounts[rate]["net_purchase"] = 0
                    
                if account not in merge_taxable_accounts[rate]["account"]:
                    merge_taxable_accounts[rate]["account"] += ", " + account
            
                if item.item_tax_template:
                    if "Sales" in dt:
                        merge_taxable_accounts[rate]["net_sell"] += item_amount * ratio if received else item_amount
                    else:
                        merge_taxable_accounts[rate]["net_purchase"] += item_amount * ratio if received else item_amount
                elif not item.item_tax_template or not rate:
                    if "0" not in merge_taxable_accounts:
                        merge_taxable_accounts["0"] = {}
                        merge_taxable_accounts["0"]["account"] = account
                        merge_taxable_accounts["0"]["net_sell"] = 0
                        merge_taxable_accounts["0"]["net_purchase"] = 0
                    if account not in merge_taxable_accounts["0"]["account"]:
                        merge_taxable_accounts["0"]["account"] += ", " + account
                    if "Sales" in dt:
                        merge_taxable_accounts["0"]["net_sell"] += item_amount * ratio if received else item_amount
                    else:
                        merge_taxable_accounts["0"]["net_purchase"] += item_amount * ratio if received else item_amount
             
        
        if merge_taxable_accounts:
            for rate, values in merge_taxable_accounts.items():
                if rate == "0":
                    no_vat_entry["against_account"] = values["account"]
                    no_vat_entry["net_sell"] = values["net_sell"]
                    no_vat_entry["net_purchase"] = values["net_purchase"]
                    if values["net_sell"] and not has_vat:
                        if values["net_sell"] > 0:
                            no_vat_sell["total_credit"] += values["net_sell"]
                        else:
                            no_vat_sell["total_debit"] += values["net_sell"]
                    
                else:
                    for entry_gl in split_dt_gl_entries:
                        if flt(entry_gl.get("tax_rate")) == flt(rate):
                            entry_gl["against_account"] = values["account"]
                            entry_gl["net_sell"] = values["net_sell"]
                            entry_gl["net_purchase"] = values["net_purchase"]
                            break
        
        if "net_sell" in no_vat_entry:
            if no_vat_entry["net_sell"] != 0 or no_vat_entry["net_purchase"] != 0:
                no_vat_entries[dt].append(no_vat_entry)
            if no_vat_entry["net_sell"] > 0:
                no_vat_sell["total_credit"] += values["net_sell"]
            elif no_vat_entry["net_sell"] < 0:
                no_vat_sell["total_debit"] += values["net_sell"]
    else:
        for entry_gl in split_dt_gl_entries:
            entry_gl["net_purchase"] = add_purchase_debit - add_purchase_credit
            entry_gl["net_sell"] = add_sell_credit - add_sell_debit
            
    dt_gl_entries.extend(split_dt_gl_entries)
    
    entry = {
        "document_type": dt,
        "document_name": dn,
        "posting_date": posting_date,
    }
    
    if has_vat:
        net_sell["total_debit"] += add_sell_debit
        net_sell["total_credit"] += add_sell_credit
        summary_net_sell["total_debit"] = add_sell_debit
        summary_net_sell["total_credit"] = add_sell_credit
        if not flat:
            net_purchase["total_debit"] += add_purchase_debit
            net_purchase["total_credit"] += add_purchase_credit
            summary_net_purchase["total_debit"] = add_purchase_debit
            summary_net_purchase["total_credit"] = add_purchase_credit
        if received and dt != "Payment Entry":
            entry["net_sell"] = add_sell_credit - add_sell_debit
            entry["net_purchase"] = add_purchase_debit - add_purchase_credit
            for tax_code in summary_sums_by_tax_code_variable:
                index_name = "vat_" + str(tax_code).replace('.', '')
                tax_credit = summary_sums_by_tax_code_variable[tax_code]["total_credit"]
                tax_debit = summary_sums_by_tax_code_variable[tax_code]["total_debit"]
                entry[index_name] = tax_credit - tax_debit if int(tax_code) < 400 else tax_debit - tax_credit
        else:
            for tax_code in summary_sums_by_tax_code:
                index_name = "vat_" + str(tax_code).replace('.', '')
                tax_credit = summary_sums_by_tax_code[tax_code]["total_credit"]
                tax_debit = summary_sums_by_tax_code[tax_code]["total_debit"]
                entry[index_name] = tax_credit - tax_debit if int(tax_code) < 400 else tax_debit - tax_credit
                entry["net_sell"] = summary_net_sell["total_credit"] - summary_net_sell["total_debit"]
                entry["net_purchase"] = summary_net_purchase["total_debit"] - summary_net_purchase["total_credit"]
        summary_dt.append(entry)
    else:
        no_vat_sell["total_debit"] += add_sell_debit
        no_vat_sell["total_credit"] += add_sell_credit
        
        summary_no_vat_sell["total_debit"] = add_sell_debit
        summary_no_vat_sell["total_credit"] = add_sell_credit
        if summary_no_vat_purchase:
            summary_no_vat_purchase["total_debit"] = add_purchase_debit
            summary_no_vat_purchase["total_credit"] = add_purchase_credit
        
        if summary_no_vat_sell["total_credit"] != 0 or summary_no_vat_sell["total_debit"] != 0:
            entry["no_vat_sell"] = summary_no_vat_sell["total_credit"] - summary_no_vat_sell['total_debit']
        if summary_no_vat_purchase and (summary_no_vat_purchase["total_credit"] != 0 or summary_no_vat_purchase["total_debit"] != 0):
            entry["no_vat_purchase"] = summary_no_vat_purchase["total_debit"] - summary_no_vat_purchase["total_credit"]
        summary_no_vat.append(entry)

                    
@frappe.whitelist()
def get_taxable_account(account, item_tax_template=None):
    if item_tax_template:
        return frappe.db.sql(
            """SELECT ittd.tax_rate as rate
                FROM `tabItem Tax Template` itt
                LEFT JOIN `tabItem Tax Template Detail`ittd on itt.name=ittd.parent
                WHERE ittd.tax_rate > 0
                AND itt.name = %s""", (item_tax_template), as_dict=True
        )
    return frappe.db.sql(
        """SELECT acc.account_number as account, ittd.tax_rate as rate
            FROM `tabAccount` acc
            LEFT JOIN `tabItem Tax Template`itt on acc.taxable_account=itt.name
            LEFT JOIN `tabItem Tax Template Detail`ittd on itt.name=ittd.parent
            WHERE ittd.tax_rate > 0
            AND acc.name = %s""", (account), as_dict=True
    )
    
def get_recap_values(data, dt, flat=False):
    if flat:
        return []
    out = []
    buy_taxes = {}
    taxes = {}
    for item in data:
        tax_code = item["tax_code"]
        tax_rate = item["tax_rate"]
        if tax_code not in taxes:
            taxes[tax_code] = {"total_vat": 0, "total_net_sell": 0, "total_net_purchase": 0}
        if int(tax_code) >= 400:
            if tax_code not in buy_taxes:
                buy_taxes[tax_code] = {}
            if tax_rate not in buy_taxes[tax_code]:
                buy_taxes[tax_code][tax_rate] = {"total_vat": 0, "total_net_sell": 0, "total_net_purchase": 0}
            buy_taxes[tax_code][tax_rate]["total_vat"] += (item["debit"] - item["credit"])
            buy_taxes[tax_code][tax_rate]["total_net_sell"] += item["net_sell"] if "net_sell" in item else 0
            buy_taxes[tax_code][tax_rate]["total_net_purchase"] += item["net_purchase"] if "net_purchase" in item else 0
            
        if dt == "Sales Invoice":
            taxes[tax_code]["total_vat"] += (item["credit"] - item["debit"])
            taxes[tax_code]["total_net_sell"] += item["net_sell"] if "net_sell" in item else 0
        elif dt == "Purchase Invoice":
            taxes[tax_code]["total_vat"] += (item["debit"] - item["credit"])
            taxes[tax_code]["total_net_purchase"] += item["net_purchase"] if "net_purchase" in item else 0
        elif dt == "Journal Entry":
            taxes[tax_code]["total_vat"] += (item["credit"] - item["debit"]) if int(tax_code) < 400 else (item["debit"] - item["credit"])
            taxes[tax_code]["total_net_sell"] += item["net_sell"] if "net_sell" in item else 0
            taxes[tax_code]["total_net_purchase"] += item["net_purchase"] if "net_purchase" in item else 0
        elif dt == "Payment Entry":
            taxes[tax_code]["total_vat"] += (item["credit"] - item["debit"]) if item["payment_type"] == "Receive" else (item["debit"] - item["credit"])
            taxes[tax_code]["total_net_sell"] += item["net_sell"] if "net_sell" in item else 0
            taxes[tax_code]["total_net_purchase"] += item["net_purchase"] if "net_purchase" in item else 0
    total_vat, total_net_sell, total_net_purchase = 0, 0, 0
    for key, values in taxes.items():
        total_vat += values["total_vat"]
        total_net_sell += values["total_net_sell"]
        total_net_purchase += values["total_net_purchase"]
        if key in buy_taxes:
            for tax_rate, tax_values in buy_taxes[key].items():
                out.append({
                    "tax_code": str(key),
                    "tax_rate": str(tax_rate),
                    "total_vat": tax_values["total_vat"],
                    "total_net_sell": tax_values["total_net_sell"],
                    "total_net_purchase": tax_values["total_net_purchase"]
                })
        out.append({
            "tax_code": "total " + str(key),
            "tax_rate": "",
            "total_vat": values["total_vat"],
            "total_net_sell": values["total_net_sell"],
            "total_net_purchase": values["total_net_purchase"]
        })
    out.append({
        "tax_code": "",
        "tax_rate": "",
        "total_vat": total_vat,
        "total_net_sell": total_net_sell,
        "total_net_purchase": total_net_purchase
    })
    return out

@frappe.whitelist()
def set_table_cache(fieldname, remove_fields):
    meta = frappe.get_meta("VAT Detail")
    remaining_fields = [field for field in meta.fields if field.fieldname not in remove_fields]
    frappe.cache().set_value(fieldname, remaining_fields)
    frappe.neolog("cache", frappe.cache().get_value(fieldname))
    
    
class VATDeclaration(Document):
    def create_transfer_file(self):
        tax_id = frappe.get_value("Company", self.company, "tax_id")
        if not tax_id or len(tax_id) < 12:
            frappe.throw( _("Tax ID/UID missing or invalid. Please configure for company {0}.").format(self.company) )

        data = {
            'uid': (tax_id[3:].replace(".", "").replace("-", "")).strip(),
            'company': self.company,
            'generation_datetime': datetime.now(),
            'from_date': self.start_date,
            'to_date': self.end_date,
            'title': self.title,
            'z200': self.total_revenue,
            'z205': self.non_taxable_revenue,
            'z220': self.tax_free_services,
            'z221': self.revenue_abroad,
            'z225': self.transfers,
            'z230': self.non_taxable_services,
            'z235': self.losses,
            'z302': self.normal_amount,
            'z303': self.normal_amount_2024,
            'z312': self.reduced_amount,
            'z313': self.reduced_amount_2024,
            'z322': self.amount_1,
            'z323': self.amount_1_2024,
            'z332': self.amount_2,
            'z333': self.amount_2_2024,
            'z342': self.lodging_amount,
            'z343': self.lodging_amount_2024,
            'z382': self.additional_amount,
            'z383': self.additional_amount_2024,
            'z400': self.pretax_material,
            'z405': self.pretax_investments,
            'z410': self.missing_pretax,
            'z415': self.pretax_correction_mixed,
            'z420': self.pretax_correction_other,
            'z500': self.payable_tax,
            'z900': self.grants,
            'z910': self.donations,
            'acquisition_rate': 7.7 if self.start_date < "2024-01-01" else 8.1,
            'rate1': self.rate_1,
            'rate1_2024': self.rate_1,
            'rate2': self.rate_2,
            'rate2_2024': self.rate_2
        }
        # render file
        if self.vat_type == "flat":
            template = 'erpnextswiss/templates/xml/taxes_net.html'
        else:
            template = 'erpnextswiss/templates/xml/taxes_effective.html'
        content = frappe.render_template(template, data)
        return { 'content': content }
