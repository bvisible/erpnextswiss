# Copyright (c) 2024, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
import frappe
from erpnextswiss.erpnextswiss.doctype.vat_declaration.vat_declaration import get_total_payments, get_total_invoiced
from frappe import _


def execute(filters=None):
	is_flat = "flat" in filters.vat_type
	is_agreed = "agreed" in filters.vat_type
	if is_agreed:
		res = get_total_payments(filters.from_date, filters.to_date, filters.company, is_flat)
	else:
		res = get_total_invoiced(filters.from_date, filters.to_date, filters.company, is_flat)
	if filters.document_type == "All":
		data = res.get("summary_sales_invoice_old")[:-1] + res.get("summary_sales_invoice_new")[:-1] + res.get("summary_purchase_invoice")[:-1] + res.get("summary_journal_entry_old")[:-1] + res.get("summary_journal_entry_new")[:-1]
	elif filters.document_type == "Sales Invoice":
		data = res.get("summary_sales_invoice_old")[:-1] + res.get("summary_sales_invoice_new")[:-1]
	elif filters.document_type == "Purchase Invoice":
		data = res.get("summary_purchase_invoice")[:-1]
	else:
		data = res.get("summary_sales_invoice_old")[:-1] + res.get("summary_sales_invoice_new")[:-1]
	columns, data = get_columns(filters.document_type), data
	return columns, data

def get_columns(type):
	base_columns = [
		{
			"fieldname": "document_type",
			"label": _("Document Type"),
			"fieldtype": "Link",
			"options": "DocType",
			"width": 120
		},
		{
			"fieldname": "document_name",
			"label": _("Document Name"),
			"fieldtype": "Dynamic Link",
			"options": "document_type",
			"width": 120
		},
		{
			"fieldname": "posting_date",
			"label": _("Posting Date"),
			"fieldtype": "Date",
			"width": 120
		},
	]
	sale_columns = [
		{
			"fieldname": "net_sell",
			"label": _("Net Sell"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "vat_302",
			"label": _("VAT 302"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "vat_312",
			"label": _("VAT 312"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "vat_342",
			"label": _("VAT 342"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "vat_303",
			"label": _("VAT 303"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "vat_313",
			"label": _("VAT 313"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "vat_343",
			"label": _("VAT 343"),
			"fieldtype": "Currency",
			"width": 120
		},
	]
	purchase_columns = [
		{
			"fieldname": "net_purchase",
			"label": _("Net Purchase"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "vat_400",
			"label": _("VAT 400"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "vat_405",
			"label": _("VAT 405"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "vat_410",
			"label": _("VAT 410"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "vat_415",
			"label": _("VAT 415"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "vat_420",
			"label": _("VAT 420"),
			"fieldtype": "Currency",
			"width": 120
		}
	]
	if type == "Sales Invoice":
		columns = base_columns + sale_columns
	elif type == "Purchase Invoice":
		columns = base_columns + purchase_columns
	else:
		columns = base_columns + sale_columns + purchase_columns
	return columns

