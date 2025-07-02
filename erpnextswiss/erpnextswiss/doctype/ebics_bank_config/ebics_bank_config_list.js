// Copyright (c) 2025, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.listview_settings['ebics Bank Config'] = {
    onload: function(listview) {
        listview.page.add_inner_button(__('Create Default Banks'), function() {
            frappe.confirm(
                __('This will create default configurations for Swiss banks (Raiffeisen, UBS, Credit Suisse, PostFinance, ZKB). Continue?'),
                function() {
                    frappe.call({
                        method: 'erpnextswiss.erpnextswiss.doctype.ebics_bank_config.ebics_bank_config.create_default_configs',
                        freeze: true,
                        freeze_message: __('Creating default bank configurations...'),
                        callback: function(r) {
                            if (r.message) {
                                // Check for errors first
                                if (r.message.error) {
                                    frappe.msgprint({
                                        title: __('Error'),
                                        message: r.message.details.join('<br>'),
                                        indicator: 'red'
                                    });
                                    return;
                                }
                                
                                if (r.message.created > 0) {
                                    frappe.msgprint({
                                        title: __('Success'),
                                        message: __('Created {0} bank configuration(s)', [r.message.created]),
                                        indicator: 'green'
                                    });
                                    listview.refresh();
                                } else if (r.message.existing > 0) {
                                    frappe.msgprint({
                                        title: __('Information'),
                                        message: __('All default bank configurations already exist'),
                                        indicator: 'blue'
                                    });
                                } else if (r.message.errors > 0) {
                                    frappe.msgprint({
                                        title: __('Warning'),
                                        message: __('Some configurations could not be created. Check details below.'),
                                        indicator: 'orange'
                                    });
                                } else {
                                    frappe.msgprint({
                                        title: __('Information'),
                                        message: __('No configurations were created or found.'),
                                        indicator: 'blue'
                                    });
                                }
                                
                                // Show details if any
                                if (r.message.details && r.message.details.length > 0) {
                                    var details_html = '<h5>' + __('Details:') + '</h5><ul>';
                                    r.message.details.forEach(function(detail) {
                                        details_html += '<li>' + detail + '</li>';
                                    });
                                    details_html += '</ul>';
                                    
                                    setTimeout(function() {
                                        frappe.msgprint({
                                            title: __('Creation Details'),
                                            message: details_html,
                                            indicator: 'blue'
                                        });
                                    }, 1000);
                                }
                            }
                        },
                        error: function(r) {
                            frappe.msgprint({
                                title: __('Error'),
                                message: __('Failed to create default configurations. Please check the error log.'),
                                indicator: 'red'
                            });
                        }
                    });
                }
            );
        }).addClass('btn-primary');
    }
};