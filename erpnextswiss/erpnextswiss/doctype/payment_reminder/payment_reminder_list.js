frappe.listview_settings['Payment Reminder'] = {
    onload: function(listview) {
        var list = listview;
        listview.page.add_button( __("Create Payment Reminders"), function() {
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Company",
                    fields: ["name"]
                },
                callback: function(response) {
                    if (response && response.message) {
                        number_of_companies = response.message.length;
                        if(number_of_companies == 1){
                            create_payment_reminders({'company': response.message[0].name});
                        } else {
                            frappe.prompt(
                                [
                                    {'fieldname': 'company', 'fieldtype': 'Link', 'options': 'Company', 'label': __('Company'), 'reqd': 1, 'default': frappe.defaults.get_user_default('company')}
                                ],
                                function(values){
                                    console.log(list);
                                    create_payment_reminders(values);
                                },
                                __("Create Payment Reminders"),
                                __("Create")
                            );
                        }
                    }
                }
            });
        }); 
        function create_payment_reminders(values) {
            frappe.call({
                'method': "erpnextswiss.erpnextswiss.doctype.payment_reminder.payment_reminder.create_payment_reminders",
                'args': {
                    'company': values.company
                },
                'callback': function() {
                    frappe.show_alert( __("Payment Reminders created") );
                    setTimeout(function() { window.location.reload(); }, 1000);
                    listview.refresh();
                }
            });
        } 
    }
}

function create_payment_reminders(values) {
    frappe.call({
        'method': "erpnextswiss.erpnextswiss.doctype.payment_reminder.payment_reminder.enqueue_create_payment_reminders",
        'args': {
            'company': values.company
        },
        'callback': function(response) {
            frappe.show_alert( __("Payment Reminders created") );
        }
    });
}
