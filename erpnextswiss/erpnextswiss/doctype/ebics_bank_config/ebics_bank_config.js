// Copyright (c) 2025, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('ebics Bank Config', {
    refresh: function(frm) {
        // Add button to test configuration
        if (!frm.doc.__islocal) {
            frm.add_custom_button(__("Test Configuration"), function() {
                // Find EBICS connections using this bank config
                frappe.call({
                    method: 'frappe.client.get_list',
                    args: {
                        doctype: 'ebics Connection',
                        filters: {
                            bank_config: frm.doc.name
                        },
                        fields: ['name', 'title', 'activated']
                    },
                    callback: function(r) {
                        if (r.message && r.message.length > 0) {
                            // Show connections using this config
                            var connections_html = '<h5>' + __('EBICS Connections using this configuration:') + '</h5><ul>';
                            r.message.forEach(function(conn) {
                                connections_html += '<li>' + conn.title + ' (' + (conn.activated ? __('Activated') : __('Not activated')) + ')</li>';
                            });
                            connections_html += '</ul>';
                            
                            frappe.msgprint({
                                title: __('Bank Configuration Test'),
                                message: connections_html + '<p>' + __('You can test each connection individually from the EBICS Connection form.') + '</p>',
                                indicator: 'blue'
                            });
                        } else {
                            frappe.msgprint({
                                title: __('Bank Configuration Test'),
                                message: __('No EBICS connections are using this bank configuration yet.'),
                                indicator: 'orange'
                            });
                        }
                    }
                });
            });
        }
    },
    
    bank_name: function(frm) {
        // Try to auto-detect settings based on bank name
        if (frm.doc.bank_name) {
            var bank_lower = frm.doc.bank_name.toLowerCase();
            
            if (bank_lower.includes('raiffeisen')) {
                frm.set_value('bank_code', 'RAIFCH22');
                frm.set_value('payment_order_type_h004', 'XE2');
                frm.set_value('use_swiss_namespace', 1);
            } else if (bank_lower.includes('ubs')) {
                frm.set_value('bank_code', 'UBSWCHZH');
            } else if (bank_lower.includes('credit suisse') || bank_lower.includes('credit-suisse')) {
                frm.set_value('bank_code', 'CRESCHZZ');
            } else if (bank_lower.includes('postfinance')) {
                frm.set_value('bank_code', 'POFICHBE');
            } else if (bank_lower.includes('zkb') || bank_lower.includes('zürcher kantonalbank')) {
                frm.set_value('bank_code', 'ZKBKCHZZ');
            }
        }
    }
});