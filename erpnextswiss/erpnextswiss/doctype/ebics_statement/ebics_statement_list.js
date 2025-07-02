// Copyright (c) 2025, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.listview_settings['ebics Statement'] = {
    onload: function(listview) {
        // Add button to delete all statements
        listview.page.add_inner_button(__('Delete All Statements'), function() {
            frappe.confirm(
                __('This will permanently delete ALL ebics Statements. This action cannot be undone. Are you sure you want to continue?'),
                function() {
                    // Second confirmation for safety
                    frappe.confirm(
                        __('Please confirm again: Delete ALL ebics Statements?'),
                        function() {
                            frappe.call({
                                method: 'erpnextswiss.erpnextswiss.doctype.ebics_statement.ebics_statement.delete_all_statements',
                                freeze: true,
                                freeze_message: __('Deleting all statements...'),
                                callback: function(r) {
                                    if (r.message && r.message.success) {
                                        frappe.msgprint({
                                            title: __('Success'),
                                            message: __('Deleted {0} statement(s)', [r.message.deleted]),
                                            indicator: 'green'
                                        });
                                        listview.refresh();
                                    } else {
                                        frappe.msgprint({
                                            title: __('Error'),
                                            message: r.message.message || __('Failed to delete statements'),
                                            indicator: 'red'
                                        });
                                    }
                                },
                                error: function(r) {
                                    frappe.msgprint({
                                        title: __('Error'),
                                        message: __('Failed to delete statements. Please check the error log.'),
                                        indicator: 'red'
                                    });
                                }
                            });
                        }
                    );
                }
            );
        }).addClass('btn-danger');
    }
};