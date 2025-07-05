frappe.listview_settings['Payment Proposal'] = {
    onload: function(listview) {
        listview.page.add_inner_button(__("Create Payment Proposal"), function() {
            prepare_payment_proposal();
        }).addClass("btn-primary");
    }
}

function prepare_payment_proposal() {
    frappe.call({
        "method": "frappe.client.get",
        "args": {
                "doctype": "ERPNextSwiss Settings",
                "name": "ERPNextSwiss Settings"
        },
        "callback": function(response) {
            try {
                var d = new Date();
                d = new Date(d.setDate(d.getDate() + response.message.planning_days));
                var default_company = frappe.defaults.get_default("Company");
                
                // Create the dialog
                var dialog = frappe.prompt([
                        {'fieldname': 'date', 'fieldtype': 'Date', 'label': __('Include Payments Until'), 'reqd': 1, 'default': d},
                        {'fieldname': 'company', 'fieldtype': 'Link', 'label': __("Company"), 'options': 'Company', 
                         'default': default_company,
                         'onchange': function() {
                             // When company changes, update the default currency
                             var company = dialog.get_value('company');
                             if (company) {
                                 frappe.call({
                                     'method': 'frappe.client.get_value',
                                     'args': {
                                         'doctype': 'Company',
                                         'filters': {'name': company},
                                         'fieldname': 'default_currency'
                                     },
                                     'callback': function(r) {
                                         if (r.message && r.message.default_currency) {
                                             dialog.set_value('currency', r.message.default_currency);
                                         }
                                     }
                                 });
                             }
                         }
                        },
                        {'fieldname': 'currency', 'fieldtype': 'Link', 'label': __('Currency'), 'options': 'Currency'},
                    ],
                    function(values){
                        create_payment_proposal(values.date, values.company, values.currency);
                    },
                    __('Payment Proposal'),
                    __('Create')
                );
                
                // Set initial default currency based on default company
                if (default_company) {
                    frappe.call({
                        'method': 'frappe.client.get_value',
                        'args': {
                            'doctype': 'Company',
                            'filters': {'name': default_company},
                            'fieldname': 'default_currency'
                        },
                        'callback': function(r) {
                            if (r.message && r.message.default_currency) {
                                dialog.set_value('currency', r.message.default_currency);
                            }
                        }
                    });
                }
            } catch (err) {
                frappe.msgprint("Error: " + err.message);
            }
        }
    });
 
}

function create_payment_proposal(date, company, currency) {
    frappe.call({
        "method": "erpnextswiss.erpnextswiss.doctype.payment_proposal.payment_proposal.create_payment_proposal",
        "args": { 
            "date": date, 
            "company": company,
            "currency": currency
        },
        "callback": function(response) {
            if (response.message) {
                // redirect to the new record
                window.location.href = response.message;
            } else {
                // no records found
                frappe.show_alert( __("No suitable invoices found.") );
            }
        }
    });
}
