// Copyright (c) 2017-2022, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Account Sheets"] = {
    "filters": [
        {
            "fieldname":"company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "reqd": 1,
            "default": frappe.defaults.get_user_default("company") || frappe.defaults.get_global_default("company")
        },
        {
            "fieldname":"from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": (new Date(new Date().getFullYear(), 0, 1)), /* use first day of current year */
            "reqd": 1
        },
        {
            "fieldname":"to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        },
        {
            "fieldname":"from_account",
            "label": __("From Account"),
            "fieldtype": "Int"
        },
        {
            "fieldname":"to_account",
            "label": __("To Account"),
            "fieldtype": "Int"
        },
        {
            "fieldname":"cost_center",
            "label": __("Cost Center"),
            "fieldtype": "Link",
            "options": "Cost Center"
        },
        {
            "fieldname":"remark_max_length",
            "label": __("Remark Max Length"),
            "fieldtype": "Int",
            "default": 100
        },
        {
            "fieldname":"hide_null_accounts",
            "label": __("Hide Null Accounts"),
            "fieldtype": "Check",
            "default": 1
        }
    ]
};
