// Copyright (c) 2024, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.query_reports["VAT Report"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default" : frappe.defaults.get_default("Company"),
			"reqd": 1
		},
		{
			"fieldname":"from_date",
			"label": __("From date"),
			"fieldtype": "Date",
			"default": new Date().getFullYear() + "-01-01",
			"reqd": 1
		},
		{
			"fieldname":"to_date",
			"label": __("To date"),
			"fieldtype": "Date",
			"default" : frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname":"vat_type",
			"label": __("VAT Type"),
			"fieldtype": "Select",
			"options": "effective - agreed counterclaims\n" +
				"effective - counterclaims received\n" +
				"flat rate - agreed counterclaims\n" +
				"flat rate - counterclaims received",
			"default": "effective - agreed counterclaims",
			"reqd": 1
		},
		{
			"fieldname":"document_type",
			"label": __("Document Type"),
			"fieldtype": "Select",
			"options": "All\nSales Invoice\nPurchase Invoice\nJournal Entry",
			"default": "All",
			"reqd": 1
		}
	],
};
