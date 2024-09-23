frappe.query_reports["Account Sheets"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "reqd": 1,
            "default": frappe.defaults.get_user_default("company") || frappe.defaults.get_global_default("company")
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": (new Date(new Date().getFullYear(), 0, 1)), /* use first day of current year */
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        },
        {
            "fieldname": "from_account",
            "label": __("From Account"),
            "fieldtype": "Link",
            "options": "Account",
            "get_query": function() {
                return {
                    filters: {
                        "is_group": 0
                    }
                };
            }
        },
        {
            "fieldname": "to_account",
            "label": __("To Account"),
            "fieldtype": "Link",
            "options": "Account",
            "get_query": function() {
                return {
                    filters: {
                        "is_group": 0
                    }
                };
            }
        },
        {
            "fieldname": "cost_center",
            "label": __("Cost Center"),
            "fieldtype": "Link",
            "options": "Cost Center"
        },
        {
            "fieldname": "max_rows",
            "label": __("Max Rows In Report (Ignored In Print"),
            "fieldtype": "Int",
            "default": 1000,
            "on_change": function(query_report) {
                let maxRowsField = query_report.page.fields_dict.max_rows;
                let value = maxRowsField.get_value();
                if (!value) { // This checks for null, undefined, and 0
                    maxRowsField.set_value(1000);
                }
                query_report.refresh();
            }
        },
        {
            "fieldname": "remark_max_length",
            "label": __("Remark Max Length"),
            "fieldtype": "Int",
            "default": 100,
            "on_change": function(query_report) {
                let remarkMaxLength = query_report.page.fields_dict.remark_max_length;
                let value = remarkMaxLength.get_value();
                if (!value) { // This checks for null, undefined, and 0
                    remarkMaxLength.set_value(100);
                }
                query_report.refresh();
            }
        },
        {
            "fieldname": "hide_null_accounts",
            "label": __("Hide Null Accounts"),
            "fieldtype": "Check",
            "default": 1
        },
        {
            "fieldname": "include_cancelled",
            "label": __("Show Cancelled Entries"),
            "fieldtype": "Check",
            "default": 0
        }
    ]
};
