# -*- coding: utf-8 -*-
# Copyright (c) 2017-2023, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from datetime import datetime

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
    summary_no_vat = []
    summary_purchase_invoice = []

    if company:
        payment_entries = frappe.db.get_all("Payment Entry", filters={"posting_date": ["between", [start_date, end_date]], "docstatus": 1, "company": company}, fields=["name"])
    else:
        payment_entries = frappe.db.get_all("Payment Entry", filters={"posting_date": ["between", [start_date, end_date]], "docstatus": 1}, fields=["name"])
    for payment_entry in payment_entries:
        summary_sums_by_tax_code = {}
        summary_net_sell = {"total_debit": 0, "total_credit": 0}
        summary_net_purchase = {"total_debit": 0, "total_credit": 0}
        summary_no_vat_sell = {"total_debit": 0, "total_credit": 0}
        summary_no_vat_purchase = {"total_debit": 0, "total_credit": 0}
        doc = frappe.get_doc("Payment Entry", payment_entry.name)
        for reference in doc.references:
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
            gl_entries = frappe.db.get_all("GL Entry", filters={"voucher_no": reference.reference_name}, fields=["account", "debit", "credit"])
            has_vat = False
            add_sell_debit = 0
            add_sell_credit = 0
            add_purchase_debit = 0
            add_purchase_credit = 0
            summary_sums_by_tax_code_variable = {}
            for gl_entry in gl_entries:
                tax_code = frappe.db.get_value("Account", gl_entry.account, "tax_code")
                if tax_code:
                    if tax_code not in sums_by_tax_code:
                        sums_by_tax_code[tax_code] = {
                            "total_debit": 0,
                            "total_credit": 0
                        }
                    sums_by_tax_code[tax_code]["total_debit"] += gl_entry.debit * ratio
                    sums_by_tax_code[tax_code]["total_credit"] += gl_entry.credit * ratio
                    # for summary table

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
                    summary_sums_by_tax_code[tax_code]["total_debit"] += gl_entry.debit * ratio
                    summary_sums_by_tax_code[tax_code]["total_credit"] += gl_entry.credit * ratio
                    summary_sums_by_tax_code_variable[tax_code]["total_debit"] += gl_entry.debit * ratio
                    summary_sums_by_tax_code_variable[tax_code]["total_credit"] += gl_entry.credit * ratio
                    # for summary table
                    if not has_vat and (gl_entry.debit != 0 or gl_entry.credit != 0):
                        has_vat = True
                else:
                    account_number = frappe.db.get_value("Account", gl_entry.account, "account_number")
                    if int(sell_account_start) <= int(account_number) <= int(sell_account_end):
                        add_sell_debit += gl_entry.debit * ratio
                        add_sell_credit += gl_entry.credit * ratio
                    elif int(purchase_account_start) <= int(account_number) <= int(purchase_account_end):
                        add_purchase_debit += gl_entry.debit * ratio
                        add_purchase_credit += gl_entry.credit * ratio
            if has_vat is True:
                net_sell["total_debit"] += add_sell_debit
                net_sell["total_credit"] += add_sell_credit
                if flat is not True:
                    net_purchase["total_debit"] += add_purchase_debit
                    net_purchase["total_credit"] += add_purchase_credit
                # for summary table
                summary_net_sell["total_debit"] = add_sell_debit
                summary_net_sell["total_credit"] = add_sell_credit
                if flat is not True:
                    summary_net_purchase["total_debit"] = add_purchase_debit
                    summary_net_purchase["total_credit"] = add_purchase_credit
            elif has_vat is False:
                no_vat_sell["total_debit"] += add_sell_debit
                no_vat_sell["total_credit"] += add_sell_credit
            # variable entry summary
            entry = {
                "document_type": reference.reference_doctype,
                "document_name": reference.reference_name,
                "posting_date": posting_date,
            }
            if has_vat is True:
                entry["net_sell"] = add_sell_credit - add_sell_debit
                entry["net_purchase"] = add_purchase_debit - add_purchase_credit
                for tax_code in summary_sums_by_tax_code_variable:
                    index_name = "vat_" + str(tax_code).replace('.', '')
                    tax_credit = summary_sums_by_tax_code_variable[tax_code]["total_credit"]
                    tax_debit = summary_sums_by_tax_code_variable[tax_code]["total_debit"]
                    entry[index_name] = tax_credit - tax_debit if int(tax_code) < 400 else tax_debit - tax_credit
                if reference.reference_doctype == "Sales Invoice":
                    summary_sales_invoice.append(entry)
                elif reference.reference_doctype == "Purchase Invoice":
                    summary_purchase_invoice.append(entry)
            else:
                if add_sell_credit != 0 or add_sell_debit != 0:
                    entry["no_vat_sell"] = add_sell_credit - add_sell_debit
                if add_purchase_credit != 0 or add_purchase_debit != 0:
                    entry["no_vat_purchase"] = add_purchase_credit - add_purchase_debit
                summary_no_vat.append(entry)
            # end variable entry summary

    if company:
        consolidated_invoices = frappe.db.get_all("Sales Invoice", filters={"posting_date": ["between", [start_date, end_date]], "is_consolidated": 1, "docstatus": 1, "company": company}, fields=["name"])
    else:
        consolidated_invoices = frappe.db.get_all("Sales Invoice", filters={"posting_date": ["between", [start_date, end_date]], "is_consolidated": 1, "docstatus": 1}, fields=["name"])
    for invoice in consolidated_invoices:
        summary_sums_by_tax_code = {}
        summary_net_sell = {"total_debit": 0, "total_credit": 0}
        summary_net_purchase = {"total_debit": 0, "total_credit": 0}
        summary_no_vat_sell = {"total_debit": 0, "total_credit": 0}
        gl_entries = frappe.db.get_all("GL Entry", filters={"voucher_no": invoice.name}, fields=["account", "debit", "credit"])
        has_vat = False
        add_sell_debit = 0
        add_sell_credit = 0
        add_purchase_debit = 0
        add_purchase_credit = 0
        posting_date = frappe.db.get_value("Sales Invoice", invoice.name, "posting_date")
        for gl_entry in gl_entries:
            tax_code = frappe.db.get_value("Account", gl_entry.account, "tax_code")
            if tax_code:
                if tax_code not in sums_by_tax_code:
                    sums_by_tax_code[tax_code] = {
                        "total_debit": 0,
                        "total_credit": 0
                    }
                sums_by_tax_code[tax_code]["total_debit"] += gl_entry.debit
                sums_by_tax_code[tax_code]["total_credit"] += gl_entry.credit
                # for summary table
                if tax_code not in summary_sums_by_tax_code:
                    summary_sums_by_tax_code[tax_code] = {
                        "total_debit": 0,
                        "total_credit": 0
                    }
                summary_sums_by_tax_code[tax_code]["total_debit"] += gl_entry.debit
                summary_sums_by_tax_code[tax_code]["total_credit"] += gl_entry.credit
                # end summary table
                if not has_vat and (gl_entry.debit != 0 or gl_entry.credit != 0):
                    has_vat = True
            else:
                account_number = frappe.db.get_value("Account", gl_entry.account, "account_number")
                if int(sell_account_start) <= int(account_number) <= int(sell_account_end):
                    add_sell_debit += gl_entry.debit
                    add_sell_credit += gl_entry.credit
                elif int(purchase_account_start) <= int(account_number) <= int(purchase_account_end):
                    add_purchase_debit += gl_entry.debit
                    add_purchase_credit += gl_entry.credit
        if has_vat is True:
            net_sell["total_debit"] += add_sell_debit
            net_sell["total_credit"] += add_sell_credit
            if flat is not True:
                net_purchase["total_debit"] += add_purchase_debit
                net_purchase["total_credit"] += add_purchase_credit
            # for summary table
            summary_net_sell["total_debit"] = add_sell_debit
            summary_net_sell["total_credit"] = add_sell_credit
            if flat is not True:
                summary_net_purchase["total_debit"] = add_purchase_debit
                summary_net_purchase["total_credit"] = add_purchase_credit
            # end summary table
        elif has_vat is False:
            no_vat_sell["total_debit"] += add_sell_debit
            no_vat_sell["total_credit"] += add_sell_credit
            # for summary table
            summary_no_vat_sell["total_debit"] = add_sell_debit
            summary_no_vat_sell["total_credit"] = add_sell_credit
            # end summary table
        # sales invoice summary
        entry = {
            "document_type": "Sales Invoice",
            "document_name": invoice.name,
            "posting_date": posting_date,
        }
        if has_vat:
            for tax_code in summary_sums_by_tax_code:
                index_name = "vat_" + str(tax_code).replace('.', '')
                tax_credit = summary_sums_by_tax_code[tax_code]["total_credit"]
                tax_debit = summary_sums_by_tax_code[tax_code]["total_debit"]
                entry[index_name] = tax_credit - tax_debit if int(tax_code) < 400 else tax_debit - tax_credit
                entry["net_sell"] = summary_net_sell["total_credit"] - summary_net_sell["total_debit"]
            summary_sales_invoice.append(entry)
        else:
            if summary_no_vat_sell["total_credit"] != 0 or summary_no_vat_sell["total_debit"] != 0:
                entry["no_vat_sell"] = summary_no_vat_sell["total_credit"] - summary_no_vat_sell['total_debit']
            summary_no_vat.append(entry)
        # end sales invoice summary

    if company:
        journal_entries = frappe.db.get_all("Journal Entry", filters={"posting_date": ["between", [start_date, end_date]], "docstatus":1, "company": company}, fields=["name"])
    else:
        journal_entries = frappe.db.get_all("Journal Entry", filters={"posting_date": ["between", [start_date, end_date]], "docstatus":1}, fields=["name"])
    for journal_entry in journal_entries:
        summary_sums_by_tax_code = {}
        summary_net_sell = {"total_debit": 0, "total_credit": 0}
        summary_net_purchase = {"total_debit": 0, "total_credit": 0}
        summary_no_vat_sell = {"total_debit": 0, "total_credit": 0}
        summary_no_vat_purchase = {"total_debit": 0, "total_credit": 0}
        gl_entries = frappe.db.get_all("GL Entry", filters={"voucher_no": journal_entry.name}, fields=["account", "debit", "credit"])
        has_vat = False
        add_sell_debit = 0
        add_sell_credit = 0
        add_purchase_debit = 0
        add_purchase_credit = 0
        posting_date = frappe.db.get_value("Journal Entry", journal_entry.name, "posting_date")
        for gl_entry in gl_entries:
            tax_code = frappe.db.get_value("Account", gl_entry.account, "tax_code")
            if tax_code:
                if tax_code not in sums_by_tax_code:
                    sums_by_tax_code[tax_code] = {
                        "total_debit": 0,
                        "total_credit": 0
                    }
                sums_by_tax_code[tax_code]["total_debit"] += gl_entry.debit
                sums_by_tax_code[tax_code]["total_credit"] += gl_entry.credit
                # for summary table
                if tax_code not in summary_sums_by_tax_code:
                    summary_sums_by_tax_code[tax_code] = {
                        "total_debit": 0,
                        "total_credit": 0
                    }
                summary_sums_by_tax_code[tax_code]["total_debit"] += gl_entry.debit
                summary_sums_by_tax_code[tax_code]["total_credit"] += gl_entry.credit
                # end summary table
                if not has_vat and (gl_entry.debit != 0 or gl_entry.credit != 0):
                    has_vat = True
            else:
                account_number = frappe.db.get_value("Account", gl_entry.account, "account_number")
                if int(sell_account_start) <= int(account_number) <= int(sell_account_end):
                    add_sell_debit += gl_entry.debit
                    add_sell_credit += gl_entry.credit
                elif int(purchase_account_start) <= int(account_number) <= int(purchase_account_end):
                    add_purchase_debit += gl_entry.debit
                    add_purchase_credit += gl_entry.credit
        if has_vat is True:
            net_sell["total_debit"] += add_sell_debit
            net_sell["total_credit"] += add_sell_credit
            if flat is not True:
                net_purchase["total_debit"] += add_purchase_debit
                net_purchase["total_credit"] += add_purchase_credit
            # for summary table
            summary_net_sell["total_debit"] = add_sell_debit
            summary_net_sell["total_credit"] = add_sell_credit
            if flat is not True:
                summary_net_purchase["total_debit"] = add_purchase_debit
                summary_net_purchase["total_credit"] = add_purchase_credit
            # end summary table
        elif has_vat is False:
            no_vat_sell["total_debit"] += add_sell_debit
            no_vat_sell["total_credit"] += add_sell_credit
            # for summary table
            summary_no_vat_sell["total_debit"] = add_sell_debit
            summary_no_vat_sell["total_credit"] = add_sell_credit
            summary_no_vat_purchase["total_debit"] = add_purchase_debit
            summary_no_vat_purchase["total_credit"] = add_purchase_credit
            # end summary table

        # journal entry summary
        entry = {
            "document_type": "Journal Entry",
            "document_name": journal_entry.name,
            "posting_date": posting_date,
        }
        if has_vat:
            for tax_code in summary_sums_by_tax_code:
                index_name = "vat_" + str(tax_code).replace('.', '')
                tax_credit = summary_sums_by_tax_code[tax_code]["total_credit"]
                tax_debit = summary_sums_by_tax_code[tax_code]["total_debit"]
                entry[index_name] = tax_credit - tax_debit if int(tax_code) < 400 else tax_debit - tax_credit
            if summary_net_sell["total_credit"] != 0 or summary_net_sell["total_debit"] != 0:
                entry["net_sell"] = summary_net_sell["total_credit"] - summary_net_sell["total_debit"]
            if summary_net_purchase["total_credit"] != 0 or summary_net_purchase["total_debit"] != 0:
                entry["net_purchase"] = summary_net_purchase["total_debit"] - summary_net_purchase["total_credit"]
            summary_journal_entry.append(entry)
        else:
            if add_sell_debit != 0 or add_sell_credit != 0:
                entry["no_vat_sell"] = summary_no_vat_sell["total_credit"] - summary_no_vat_sell['total_debit']
            if add_purchase_debit != 0 or add_purchase_credit != 0:
                entry["no_vat_purchase"] = summary_no_vat_purchase["total_debit"] - summary_no_vat_purchase["total_credit"]
            summary_no_vat.append(entry)
        # end journal entry summary

    summary_journal_entry = sorted(summary_journal_entry, key=lambda x: x['posting_date'])
    summary_journal_entry_old, summary_journal_entry_new = split_vat_items(summary_journal_entry, True)
    sum_dict = {}
    for d in summary_journal_entry_old:
        for key, value in d.items():
            if key not in ["document_type", "document_name", "posting_date"]:
                sum_dict[key] = sum_dict.get(key, 0) + value
    summary_journal_entry_old.append(sum_dict)
    sum_dict = {}
    for d in summary_journal_entry_new:
        for key, value in d.items():
            if key not in ["document_type", "document_name", "posting_date"]:
                sum_dict[key] = sum_dict.get(key, 0) + value
    summary_journal_entry_new.append(sum_dict)

    summary_sales_invoice = sorted(summary_sales_invoice, key=lambda x: x['posting_date'])
    summary_sales_invoice_old, summary_sales_invoice_new = split_vat_items(summary_sales_invoice)

    sum_dict = {}
    for d in summary_sales_invoice_old:
        for key, value in d.items():
            if key not in ["document_type", "document_name", "posting_date"]:
                sum_dict[key] = sum_dict.get(key, 0) + value
    summary_sales_invoice_old.append(sum_dict)
    sum_dict = {}
    for d in summary_sales_invoice_new:
        for key, value in d.items():
            if key not in ["document_type", "document_name", "posting_date"]:
                sum_dict[key] = sum_dict.get(key, 0) + value
    summary_sales_invoice_new.append(sum_dict)

    summary_purchase_invoice = sorted(summary_purchase_invoice, key=lambda x: x['posting_date'])
    sum_dict = {}
    for d in summary_purchase_invoice:
        for key, value in d.items():
            if key not in ["document_type", "document_name", "posting_date"]:
                sum_dict[key] = sum_dict.get(key, 0) + value
    summary_purchase_invoice.append(sum_dict)

    summary_no_vat = sorted(summary_no_vat, key=lambda x: x['posting_date'])
    sum_dict = {}
    for d in summary_no_vat:
        for key, value in d.items():
            if key not in ["document_type", "document_name", "posting_date"]:
                sum_dict[key] = sum_dict.get(key, 0) + value
    summary_no_vat.append(sum_dict)

    return {"sums_by_tax_code": sums_by_tax_code, "net_sell": net_sell, "net_purchase": net_purchase,
            "no_vat_sell": no_vat_sell, "summary_sales_invoice_old": summary_sales_invoice_old,
            "summary_sales_invoice_new": summary_sales_invoice_new, "summary_sales_invoice": summary_sales_invoice,
            "summary_journal_entry_old": summary_journal_entry_old, "summary_journal_entry_new": summary_journal_entry_new,
            "summary_no_vat": summary_no_vat, "summary_purchase_invoice": summary_purchase_invoice}

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
    summary_no_vat = []

    if company:
        invoices = frappe.db.get_all("Sales Invoice", filters={"posting_date": ["between", [start_date, end_date]], "docstatus": 1, "company": company}, fields=["name"])
    else:
        invoices = frappe.db.get_all("Sales Invoice", filters={"posting_date": ["between", [start_date, end_date]], "docstatus": 1}, fields=["name"])
    for invoice in invoices:
        summary_sums_by_tax_code = {}
        summary_net_sell = {"total_debit": 0, "total_credit": 0}
        summary_net_purchase = {"total_debit": 0, "total_credit": 0}
        summary_no_vat_sell = {"total_debit": 0, "total_credit": 0}
        gl_entries = frappe.db.get_all("GL Entry", filters={"voucher_no": invoice.name}, fields=["account", "debit", "credit"])
        has_vat = False
        add_sell_debit = 0
        add_sell_credit = 0
        add_purchase_debit = 0
        add_purchase_credit = 0
        gl_entries_list = []
        posting_date = frappe.db.get_value("Sales Invoice", invoice.name, "posting_date")
        for gl_entry in gl_entries:
            gl_entries_list.append(gl_entry)
            tax_code = frappe.db.get_value("Account", gl_entry.account, "tax_code")
            if tax_code:
                if tax_code not in sums_by_tax_code:
                    sums_by_tax_code[tax_code] = {
                        "total_debit": 0,
                        "total_credit": 0
                    }
                sums_by_tax_code[tax_code]["total_debit"] += gl_entry.debit
                sums_by_tax_code[tax_code]["total_credit"] += gl_entry.credit
                # for summary child table
                if tax_code not in summary_sums_by_tax_code:
                    summary_sums_by_tax_code[tax_code] = {
                        "total_debit": 0,
                        "total_credit": 0
                    }
                summary_sums_by_tax_code[tax_code]["total_debit"] += gl_entry.debit
                summary_sums_by_tax_code[tax_code]["total_credit"] += gl_entry.credit
                # end summary child table
                if not has_vat and (gl_entry.debit != 0 or gl_entry.credit != 0):
                    has_vat = True
            else:
                account_number = frappe.db.get_value("Account", gl_entry.account, "account_number")
                if int(sell_account_start) <= int(account_number) <= int(sell_account_end):
                    add_sell_debit += gl_entry.debit
                    add_sell_credit += gl_entry.credit
                elif int(purchase_account_start) <= int(account_number) <= int(purchase_account_end):
                    add_purchase_debit += gl_entry.debit
                    add_purchase_credit += gl_entry.credit

        if has_vat is True:
            net_sell["total_debit"] += add_sell_debit
            net_sell["total_credit"] += add_sell_credit
            if flat is not True:
                net_purchase["total_debit"] += add_purchase_debit
                net_purchase["total_credit"] += add_purchase_credit
            # for summary child table
            summary_net_sell["total_debit"] = add_sell_debit
            summary_net_sell["total_credit"] = add_sell_credit
            if flat is not True:
                summary_net_purchase["total_debit"] = add_purchase_debit
                summary_net_purchase["total_credit"] = add_purchase_credit
            # end summary child table
        elif has_vat is False:
            no_vat_sell["total_debit"] += add_sell_debit
            no_vat_sell["total_credit"] += add_sell_credit
            # for summary child table
            summary_no_vat_sell["total_debit"] = add_sell_debit
            summary_no_vat_sell["total_credit"] = add_sell_credit
            # end summary child table
        # sales invoice summary
        entry = {
            "document_type": "Sales Invoice",
            "document_name": invoice.name,
            "posting_date": posting_date
        }
        if has_vat:
            for tax_code in summary_sums_by_tax_code:
                index_name = "vat_" + str(tax_code).replace('.', '')
                tax_credit = summary_sums_by_tax_code[tax_code]["total_credit"]
                tax_debit = summary_sums_by_tax_code[tax_code]["total_debit"]
                entry[index_name] = tax_credit - tax_debit if int(tax_code) < 400 else tax_debit - tax_credit
            entry["net_sell"] = summary_net_sell["total_credit"] - summary_net_sell["total_debit"]
            summary_sales_invoice.append(entry)
        else:
            entry["no_vat_sell"] = summary_no_vat_sell["total_credit"] - summary_no_vat_sell["total_debit"]
            summary_no_vat.append(entry)
        # end sales invoice summary

    if company:
        invoices = frappe.db.get_all("Purchase Invoice", filters={"posting_date": ["between", [start_date, end_date]], "docstatus": 1, "company": company}, fields=["name"])
    else:
        invoices = frappe.db.get_all("Purchase Invoice", filters={"posting_date": ["between", [start_date, end_date]], "docstatus": 1}, fields=["name"])
    for invoice in invoices:
        summary_sums_by_tax_code = {}
        summary_net_sell = {"total_debit": 0, "total_credit": 0}
        summary_net_purchase = {"total_debit": 0, "total_credit": 0}
        summary_no_vat_purchase = {"total_debit": 0, "total_credit": 0}
        gl_entries = frappe.db.get_all("GL Entry", filters={"voucher_no": invoice.name}, fields=["account", "debit", "credit"])
        has_vat = False
        add_sell_debit = 0
        add_sell_credit = 0
        add_purchase_debit = 0
        add_purchase_credit = 0
        gl_entries_list = []
        posting_date = frappe.db.get_value("Purchase Invoice", invoice.name, "posting_date")
        for gl_entry in gl_entries:
            gl_entries_list.append(gl_entry)
            tax_code = frappe.db.get_value("Account", gl_entry.account, "tax_code")
            account_number = frappe.db.get_value("Account", gl_entry.account, "account_number")
            if tax_code:
                if tax_code not in sums_by_tax_code:
                    sums_by_tax_code[tax_code] = {
                        "total_debit": 0,
                        "total_credit": 0
                    }
                sums_by_tax_code[tax_code]["total_debit"] += gl_entry.debit
                sums_by_tax_code[tax_code]["total_credit"] += gl_entry.credit
                # for summary child table
                if tax_code not in summary_sums_by_tax_code:
                    summary_sums_by_tax_code[tax_code] = {
                        "total_debit": 0,
                        "total_credit": 0
                    }
                summary_sums_by_tax_code[tax_code]["total_debit"] += gl_entry.debit
                summary_sums_by_tax_code[tax_code]["total_credit"] += gl_entry.credit
                # end summary child table
                if not has_vat and (gl_entry.debit != 0 or gl_entry.credit != 0):
                    has_vat = True
            else:
                if not flat:
                    account_number = frappe.db.get_value("Account", gl_entry.account, "account_number")
                    if int(sell_account_start) <= int(account_number) <= int(sell_account_end):
                        add_sell_debit += gl_entry.debit
                        add_sell_credit += gl_entry.credit
                    elif int(purchase_account_start) <= int(account_number) <= int(purchase_account_end):
                        add_purchase_debit += gl_entry.debit
                        add_purchase_credit += gl_entry.credit
        if has_vat is True:
            if flat is not True:
                net_purchase["total_debit"] += add_purchase_debit
                net_purchase["total_credit"] += add_purchase_credit
            # for summary child table
            if flat is not True:
                summary_net_purchase["total_debit"] = add_purchase_debit
                summary_net_purchase["total_credit"] = add_purchase_credit
            # end summary child table
        elif has_vat is False:
            no_vat_sell["total_debit"] += add_sell_debit
            no_vat_sell["total_credit"] += add_sell_credit
            # for summary child table
            summary_no_vat_purchase["total_debit"] = add_purchase_debit
            summary_no_vat_purchase["total_credit"] = add_purchase_credit
            # end summary child table
        # purchase invoice summary
        entry = {
            "document_type": "Purchase Invoice",
            "document_name": invoice.name,
            "posting_date": posting_date
        }
        if has_vat:
            for tax_code in summary_sums_by_tax_code:
                index_name = "vat_" + str(tax_code).replace('.', '')
                tax_credit = summary_sums_by_tax_code[tax_code]["total_credit"]
                tax_debit = summary_sums_by_tax_code[tax_code]["total_debit"]
                entry[index_name] = tax_credit - tax_debit if int(tax_code) < 400 else tax_debit - tax_credit
            entry["net_purchase"] = summary_net_purchase["total_debit"] - summary_net_purchase["total_credit"]
            summary_purchase_invoice.append(entry)
        else:
            entry["no_vat_purchase"] = summary_no_vat_purchase["total_debit"] - summary_no_vat_purchase["total_credit"]
            summary_no_vat.append(entry)
        # end purchase invoice summary

    if company:
        journal_entries = frappe.db.get_all("Journal Entry", filters={"posting_date": ["between", [start_date, end_date]], "docstatus":1, "company": company}, fields=["name"])
    else:
        journal_entries = frappe.db.get_all("Journal Entry", filters={"posting_date": ["between", [start_date, end_date]], "docstatus":1}, fields=["name"])
    for journal_entry in journal_entries:
        summary_sums_by_tax_code = {}
        summary_net_sell = {"total_debit": 0, "total_credit": 0}
        summary_net_purchase = {"total_debit": 0, "total_credit": 0}
        summary_no_vat_sell = {"total_debit": 0, "total_credit": 0}
        summary_no_vat_purchase = {"total_debit": 0, "total_credit": 0}
        gl_entries = frappe.db.get_all("GL Entry", filters={"voucher_no": journal_entry.name}, fields=["account", "debit", "credit"])
        has_vat = False
        add_sell_debit = 0
        add_sell_credit = 0
        add_purchase_debit = 0
        add_purchase_credit = 0
        posting_date = frappe.db.get_value("Journal Entry", journal_entry.name, "posting_date")
        for gl_entry in gl_entries:
            tax_code = frappe.db.get_value("Account", gl_entry.account, "tax_code")
            if tax_code:
                if tax_code not in sums_by_tax_code:
                    sums_by_tax_code[tax_code] = {
                        "total_debit": 0,
                        "total_credit": 0
                    }
                sums_by_tax_code[tax_code]["total_debit"] += gl_entry.debit
                sums_by_tax_code[tax_code]["total_credit"] += gl_entry.credit
                # for summary child table
                if tax_code not in summary_sums_by_tax_code:
                    summary_sums_by_tax_code[tax_code] = {
                        "total_debit": 0,
                        "total_credit": 0
                    }
                summary_sums_by_tax_code[tax_code]["total_debit"] += gl_entry.debit
                summary_sums_by_tax_code[tax_code]["total_credit"] += gl_entry.credit
                # end summary child table
                if not has_vat and (gl_entry.debit != 0 or gl_entry.credit != 0):
                    has_vat = True
            else:
                account_number = frappe.db.get_value("Account", gl_entry.account, "account_number")
                if int(sell_account_start) <= int(account_number) <= int(sell_account_end):
                    add_sell_debit += gl_entry.debit
                    add_sell_credit += gl_entry.credit

                elif int(purchase_account_start) <= int(account_number) <= int(purchase_account_end):
                    add_purchase_debit += gl_entry.debit
                    add_purchase_credit += gl_entry.credit
        if has_vat is True:
            net_sell["total_debit"] += add_sell_debit
            net_sell["total_credit"] += add_sell_credit
            if flat is not True:
                net_purchase["total_debit"] += add_purchase_debit
                net_purchase["total_credit"] += add_purchase_credit
            # for summary child table
            summary_net_sell["total_debit"] = add_sell_debit
            summary_net_sell["total_credit"] = add_sell_credit
            if flat is not True:
                summary_net_purchase["total_debit"] = add_purchase_debit
                summary_net_purchase["total_credit"] = add_purchase_credit
            # end summary child table
        elif has_vat is False:
            no_vat_sell["total_debit"] += add_sell_debit
            no_vat_sell["total_credit"] += add_sell_credit
            # for summary child table
            summary_no_vat_sell["total_debit"] = add_sell_debit
            summary_no_vat_sell["total_credit"] = add_sell_credit
            summary_no_vat_purchase["total_debit"] = add_purchase_debit
            summary_no_vat_purchase["total_credit"] = add_purchase_credit
            # end summary child table
        # journal entry summary
        entry = {
            "document_type": "Journal Entry",
            "document_name": journal_entry.name,
            "posting_date": posting_date
        }
        if has_vat:
            for tax_code in summary_sums_by_tax_code:
                index_name = "vat_" + str(tax_code).replace('.', '')
                tax_credit = summary_sums_by_tax_code[tax_code]["total_credit"]
                tax_debit = summary_sums_by_tax_code[tax_code]["total_debit"]
                entry[index_name] = tax_credit - tax_debit if int(tax_code) < 400 else tax_debit - tax_credit
            entry["net_sell"] = summary_net_sell["total_credit"] - summary_net_sell['total_debit']
            entry["net_purchase"] = summary_net_purchase["total_debit"] - summary_net_purchase['total_credit']
            summary_journal_entry.append(entry)
        else:
            entry["no_vat_sell"] = summary_no_vat_sell["total_credit"] - summary_no_vat_sell['total_debit']
            entry["no_vat_purchase"] = summary_no_vat_purchase["total_debit"] - summary_no_vat_purchase['total_credit']
            summary_no_vat.append(entry)
        # end journal entry summary

    summary_journal_entry = sorted(summary_journal_entry, key=lambda x: x['posting_date'])
    summary_journal_entry_old, summary_journal_entry_new = split_vat_items(summary_journal_entry, True)
    sum_dict = {}
    for d in summary_journal_entry_old:
        for key, value in d.items():
            if key not in ["document_type", "document_name", "posting_date"]:
                sum_dict[key] = sum_dict.get(key, 0) + value
    summary_journal_entry_old.append(sum_dict)
    sum_dict = {}
    for d in summary_journal_entry_new:
        for key, value in d.items():
            if key not in ["document_type", "document_name", "posting_date"]:
                sum_dict[key] = sum_dict.get(key, 0) + value
    summary_journal_entry_new.append(sum_dict)

    summary_sales_invoice = sorted(summary_sales_invoice, key=lambda x: x['posting_date'])
    summary_sales_invoice_old, summary_sales_invoice_new = split_vat_items(summary_sales_invoice)

    sum_dict = {}
    for d in summary_sales_invoice_old:
        for key, value in d.items():
            if key not in ["document_type", "document_name", "posting_date"]:
                sum_dict[key] = sum_dict.get(key, 0) + value
    summary_sales_invoice_old.append(sum_dict)
    sum_dict = {}
    for d in summary_sales_invoice_new:
        for key, value in d.items():
            if key not in ["document_type", "document_name", "posting_date"]:
                sum_dict[key] = sum_dict.get(key, 0) + value
    summary_sales_invoice_new.append(sum_dict)

    summary_purchase_invoice = sorted(summary_purchase_invoice, key=lambda x: x['posting_date'])
    sum_dict = {}
    for d in summary_purchase_invoice:
        for key, value in d.items():
            if key not in ["document_type", "document_name", "posting_date"]:
                sum_dict[key] = sum_dict.get(key, 0) + value
    summary_purchase_invoice.append(sum_dict)

    summary_no_vat = sorted(summary_no_vat, key=lambda x: x['posting_date'])
    sum_dict = {}
    for d in summary_no_vat:
        for key, value in d.items():
            if key not in ["document_type", "document_name", "posting_date"]:
                sum_dict[key] = sum_dict.get(key, 0) + value
    summary_no_vat.append(sum_dict)

    return {"sums_by_tax_code": sums_by_tax_code, "net_sell": net_sell, "net_purchase": net_purchase, "no_vat_sell": no_vat_sell,
            "summary_sales_invoice": summary_sales_invoice,
            "summary_sales_invoice_old": summary_sales_invoice_old, "summary_sales_invoice_new": summary_sales_invoice_new,
            "summary_journal_entry_old": summary_journal_entry_old, "summary_journal_entry_new": summary_journal_entry_new,
            "summary_purchase_invoice": summary_purchase_invoice, "summary_no_vat": summary_no_vat}

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

class VATDeclaration(Document):
    def create_transfer_file(self):
        tax_id = frappe.get_value("Company", self.company, "tax_id")
        if not tax_id or len(tax_id) < 12:
            frappe.throw( _("Tax ID/UID missing or invalid. Please configure for company {0}.").format(self.company) )

        data = {
            'uid': tax_id[3:].replace(".", "").replace("-", ""),
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
            'z312': self.reduced_amount,
            'z322': self.amount_1,
            'z332': self.amount_2,
            'z342': self.lodging_amount,
            'z382': self.additional_amount,
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
            'rate2': self.rate_2,
        }
        # render file
        if self.vat_type == "flat":
            template = 'erpnextswiss/templates/xml/taxes_net.html'
        else:
            template = 'erpnextswiss/templates/xml/taxes_effective.html'
        content = frappe.render_template(template, data)
        return { 'content': content }
'''@frappe.whitelist()
def get_view_total(view_name, start_date, end_date, company=None):
    # try to fetch total from VAT query
    if frappe.db.exists("VAT query", view_name):
        sql_query = ("""SELECT IFNULL(SUM(`s`.`base_grand_total`), 0) AS `total` 
                FROM ({query}) AS `s` 
                WHERE `s`.`posting_date` >= '{start_date}' 
                AND `s`.`posting_date` <= '{end_date}'""".format(
            query=frappe.get_value("VAT query", view_name, "query"),
            start_date=start_date, end_date=end_date).replace("{company}", company))
    else:
        # fallback database view
        """ executes a tax lookup query for a total """
        sql_query = ("""SELECT IFNULL(SUM(`base_grand_total`), 0) AS `total` 
                FROM `{0}` 
                WHERE `posting_date` >= '{1}' 
                AND `posting_date` <= '{2}'""".format(view_name, start_date, end_date))
    # execute query
    try:
        total = frappe.db.sql(sql_query, as_dict=True)
    except Exception as err:
        frappe.log_error(err, "VAT declaration {0}".format(view_name))
        total = [{'total': 0}]
    return { 'total': total[0]['total'] }

@frappe.whitelist()
def get_view_tax(view_name, start_date, end_date, company=None):
    # try to fetch total from VAT query
    if frappe.db.exists("VAT query", view_name):
        sql_query = ("""SELECT IFNULL(SUM(`s`.`total_taxes_and_charges`), 0) AS `total` 
                FROM ({query}) AS `s` 
                WHERE `s`.`posting_date` >= '{start_date}' 
                AND `s`.`posting_date` <= '{end_date}'""".format(
            query=frappe.get_value("VAT query", view_name, "query"),
            start_date=start_date, end_date=end_date).replace("{company}", company))
    else:
        # fallback database view
        """ executes a tax lookup query for a tax """
        sql_query = ("""SELECT IFNULL(SUM(`total_taxes_and_charges`), 0) AS `total` 
                FROM `{0}` 
                WHERE `posting_date` >= '{1}' 
                AND `posting_date` <= '{2}'""".format(view_name, start_date, end_date))
    try:
        total = frappe.db.sql(sql_query, as_dict=True)
    except Exception as err:
        frappe.log_error(err, "VAT declaration {0}".format(view_name))
        total = [{'total': 0}]
    return { 'total': total[0]['total'] }

@frappe.whitelist()
def get_tax_rate(taxes_and_charges_template):
    sql_query = ("""SELECT `rate` 
        FROM `tabPurchase Taxes and Charges` 
        WHERE `parent` = '{0}' 
        ORDER BY `idx`;""".format(taxes_and_charges_template))
    result = frappe.db.sql(sql_query, as_dict=True)
    if result:
        return result[0].rate
    else:
        return 0

@frappe.whitelist()
def get_total_invoiced(start_date, end_date, company=None):
    sql_query = ("""SELECT IFNULL(SUM(`debit`), 0) AS `debit_total`,  IFNULL(SUM(`credit`), 0) AS `credit_total`
        FROM `tabGL Entry` 
        WHERE `posting_date` >= '{0}' 
        AND `posting_date` <= '{1}'
        AND `is_cancelled` = 0""".format(start_date, end_date))
    if company:
        sql_query += " AND `company` = '{0}'".format(company)
    totals = frappe.db.sql(sql_query, as_dict=True)
    return { 'debit_total': totals[0]['debit_total'], 'credit_total': totals[0]['credit_total'] }


@frappe.whitelist()
def get_totals_from_invoices(start_date, end_date, company=None):
    je_amounts = get_total_je(start_date, end_date, company)
    invoices_net_amounts = sum_invoices_net_amounts(start_date, end_date, company)
    vat_amounts = sum_invoices_vat_amounts(start_date, end_date, company)
    sell_amounts = {'total_debit': je_amounts['sell_amount']['total_debit'] + invoices_net_amounts['sell_amount']['total_debit'], 'total_credit': je_amounts['sell_amount']['total_credit'] + invoices_net_amounts['sell_amount']['total_credit']}
    purchase_amounts = {'total_debit': je_amounts['purchase_amount']['total_debit'] + invoices_net_amounts['purchase_amount']['total_debit'], 'total_credit': je_amounts['purchase_amount']['total_credit'] + invoices_net_amounts['purchase_amount']['total_credit']}
    return { 'net_sell': sell_amounts, 'net_purchase': purchase_amounts, 'sums_by_tax_code': vat_amounts }

@frappe.whitelist()
def get_total_je(start_date, end_date, company=None):
    account_start = 3000
    account_end = 3999
    doctype = "Journal Entry"
    sql_query = """
    SELECT 
        IFNULL(SUM(`debit`), 0) AS `total_debit`,
        IFNULL(SUM(`credit`), 0) AS `total_credit`
        FROM 
            `tabGL Entry` as gl_entry
        JOIN
            `tabAccount` AS account ON gl_entry.account = account.name
        WHERE
            gl_entry.voucher_no IN (
                SELECT
                    ref_gl_entry.voucher_no
                FROM
                    `tabGL Entry` AS ref_gl_entry
                JOIN
                    `tabAccount` AS ref_account ON ref_gl_entry.account = ref_account.name
                WHERE
                    ref_account.account_number BETWEEN '{0}' AND '{1}'
                AND ref_gl_entry.company = '{5}'
            )
        AND gl_entry.voucher_type = '{2}'
        AND `posting_date` >= '{3}' 
        AND `posting_date` <= '{4}'
        AND `is_cancelled` = 0
        """.format(account_start, account_end, doctype, start_date, end_date, company)
    totals = frappe.db.sql(sql_query, as_dict=True)
    sell_amount = totals[0] if totals else { 'total_debit': 0, 'total_credit': 0 }

    account_start = 4000
    account_end = 6999
    doctype = "Journal Entry"
    sql_query = """
    SELECT 
        IFNULL(SUM(`debit`), 0) AS `total_debit`,
        IFNULL(SUM(`credit`), 0) AS `total_credit`
        FROM 
            `tabGL Entry` as gl_entry
        JOIN
            `tabAccount` AS account ON gl_entry.account = account.name
        WHERE
            gl_entry.voucher_no IN (
                SELECT
                    ref_gl_entry.voucher_no
                FROM
                    `tabGL Entry` AS ref_gl_entry
                JOIN
                    `tabAccount` AS ref_account ON ref_gl_entry.account = ref_account.name
                WHERE
                    ref_account.account_number BETWEEN '{0}' AND '{1}'
                AND ref_gl_entry.company = '{5}'
            )
        AND gl_entry.voucher_type = '{2}'
        AND `posting_date` >= '{3}' 
        AND `posting_date` <= '{4}'
        AND `is_cancelled` = 0
        """.format(account_start, account_end, doctype, start_date, end_date, company)
    totals = frappe.db.sql(sql_query, as_dict=True)
    purchase_amount = totals[0] if totals else { 'total_debit': 0, 'total_credit': 0 }

    return { 'sell_amount': sell_amount, 'purchase_amount': purchase_amount }

@frappe.whitelist()
def sum_invoices_net_amounts(start_date, end_date, company=None):
    doctype = "Sales Invoice"
    account_start = 3000
    account_end = 3999
    vat_account_start = 22000
    vat_account_end = 22100
    query = """
    SELECT
        IFNULL(SUM(gl_entry.debit), 0) AS total_debit,
        IFNULL(SUM(gl_entry.credit), 0) AS total_credit
    FROM
        `tabGL Entry` AS gl_entry
    JOIN
        `tabAccount` AS account ON gl_entry.account = account.name
    WHERE
        gl_entry.voucher_no IN (
            SELECT
                ref_gl_entry.voucher_no
            FROM
                `tabGL Entry` AS ref_gl_entry
            JOIN
                `tabAccount` AS ref_account ON ref_gl_entry.account = ref_account.name
            WHERE
                ref_account.account_number BETWEEN '{0}' AND '{1}'
            AND ref_gl_entry.company = '{7}'
        )
        AND account.account_number BETWEEN '{2}' AND '{3}'
        AND gl_entry.voucher_type = '{4}'
        AND `posting_date` >= '{5}' 
        AND `posting_date` <= '{6}'
        AND `is_cancelled` = 0
    """.format(vat_account_start, vat_account_end, account_start, account_end, doctype, start_date, end_date, company)
    result = frappe.db.sql(query, as_dict=True)
    sell_amount = result[0] if result else {'total_debit': 0, 'total_credit': 0}

    doctype = "Purchase Invoice"
    account_start = 4000
    account_end = 6999
    vat_account_start = 11700
    vat_account_end = 11800
    query = """
        SELECT
            IFNULL(SUM(gl_entry.debit), 0) AS total_debit,
            IFNULL(SUM(gl_entry.credit), 0) AS total_credit
        FROM
            `tabGL Entry` AS gl_entry
        JOIN
            `tabAccount` AS account ON gl_entry.account = account.name
        WHERE
            gl_entry.voucher_no IN (
                SELECT
                    ref_gl_entry.voucher_no
                FROM
                    `tabGL Entry` AS ref_gl_entry
                JOIN
                    `tabAccount` AS ref_account ON ref_gl_entry.account = ref_account.name
                WHERE
                    ref_account.account_number BETWEEN '{0}' AND '{1}'
                AND ref_gl_entry.company = '{7}'
            )
            AND account.account_number BETWEEN '{2}' AND '{3}'
            AND gl_entry.voucher_type = '{4}'
            AND `posting_date` >= '{5}' 
            AND `posting_date` <= '{6}'
            AND `is_cancelled` = 0
        """.format(vat_account_start, vat_account_end, account_start, account_end, doctype, start_date, end_date, company)
    result = frappe.db.sql(query, as_dict=True)
    purchase_amount = result[0] if result else {'total_debit': 0, 'total_credit': 0}
    return { 'sell_amount': sell_amount, 'purchase_amount': purchase_amount }


@frappe.whitelist()
def sum_invoices_vat_amounts(start_date, end_date, company=None, purchase_invoice=False):
    if purchase_invoice:
        doctype = "Purchase Invoice"
    else:
        doctype = "Sales Invoice"
    query = """
    SELECT
        account.tax_code,
        IFNULL(SUM(gl_entry.debit), 0) AS total_debit,
        IFNULL(SUM(gl_entry.credit), 0) AS total_credit
    FROM
        `tabGL Entry` AS gl_entry
    JOIN
        `tabAccount` AS account ON gl_entry.account = account.name
    WHERE
        gl_entry.voucher_type = '{0}'
        AND `posting_date` >= '{1}' 
        AND `posting_date` <= '{2}'
        AND gl_entry.company = '{3}'
        AND `is_cancelled` = 0
        AND account.tax_code IS NOT NULL
    GROUP BY
        account.tax_code
    """.format(doctype, start_date, end_date, company)
    result = frappe.db.sql(query, as_dict=True)
    sums_by_tax_code = {}
    for row in result:
        tax_code = row["tax_code"]
        sums_by_tax_code[tax_code] = {
            "total_debit": row["total_debit"],
            "total_credit": row["total_credit"]
        }
    return sums_by_tax_code
'''

