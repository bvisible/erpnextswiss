// Copyright (c) 2024, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('ebics Connection', {
    refresh: function(frm) {
        if (!frm.doc.__islocal) {
            if (frm.doc.activated) {
                cur_frm.dashboard.add_comment( __("This ebics connection is activated."), 'green', true);
            }
            
            // Always show the activation wizard button
            frm.add_custom_button( __("Activation Wizard"), function() {
                activation_wizard(frm);
            });
            
            // Add test connection button
            frm.add_custom_button( __("Test Connection"), function() {
                frappe.call({
                    'method': 'test_connection',
                    'doc': frm.doc,
                    'callback': function (response) {
                        // Response is shown in msgprint
                    }
                });
            });
            
            // Add individual step buttons for manual control
            frm.add_custom_button( __("1. Create Keys"), function() {
                frappe.confirm(
                    __('This will create new keys. Continue?'),
                    function() {
                        frappe.call({
                            'method': 'create_keys',
                            'doc': frm.doc,
                            'callback': function (response) {
                                cur_frm.reload_doc();
                            }
                        });
                    }
                );
            }, __("Manual Steps"));
            
            frm.add_custom_button( __("1b. Create Certificates Only"), function() {
                frappe.call({
                    'method': 'create_certificate',
                    'doc': frm.doc,
                    'callback': function (response) {
                        frappe.msgprint(__("Certificates created successfully"));
                        cur_frm.reload_doc();
                    }
                });
            }, __("Manual Steps"));
            
            frm.add_custom_button( __("2. Send Signature"), function() {
                frappe.call({
                    'method': 'send_signature',
                    'doc': frm.doc,
                    'callback': function (response) {
                        frappe.msgprint(__("Signature sent successfully"));
                        cur_frm.reload_doc();
                    }
                });
            }, __("Manual Steps"));
            
            frm.add_custom_button( __("3. Send Keys"), function() {
                frappe.call({
                    'method': 'send_keys',
                    'doc': frm.doc,
                    'callback': function (response) {
                        frappe.msgprint(__("Keys sent successfully"));
                        cur_frm.reload_doc();
                    }
                });
            }, __("Manual Steps"));
            
            frm.add_custom_button( __("4. Create INI Letter"), function() {
                frappe.call({
                    'method': 'create_ini_letter',
                    'doc': frm.doc,
                    'callback': function (response) {
                        frappe.msgprint(__("INI Letter created successfully"));
                        cur_frm.reload_doc();
                    }
                });
            }, __("Manual Steps"));
            
            frm.add_custom_button( __("5. Download Public Keys"), function() {
                frappe.call({
                    'method': 'download_public_keys',
                    'doc': frm.doc,
                    'callback': function (response) {
                        frappe.msgprint(__("Public keys downloaded successfully"));
                        cur_frm.reload_doc();
                    }
                });
            }, __("Manual Steps"));
            
            frm.add_custom_button( __("6. Activate Account"), function() {
                frappe.call({
                    'method': 'activate_account',
                    'doc': frm.doc,
                    'callback': function (response) {
                        frappe.msgprint(__("Account activated successfully"));
                        cur_frm.reload_doc();
                    }
                });
            }, __("Manual Steps"));
        }
    }
});

function activation_wizard(frm) {
    frappe.call({
        'method': 'get_activation_wizard',
        'doc': frm.doc,
        'callback': function (response) {
            var d = new frappe.ui.Dialog({
                'fields': [
                    {'fieldname': 'ht', 'fieldtype': 'HTML'}
                ],
                primary_action: function(){
                    d.hide();
                    // depending on the stage, initiate next step
                    if (response.message.stage === 0) {
                        // do nothing, user needs to fill in the form
                    } else if (response.message.stage === 1) {
                        // create keys
                        frappe.call({
                            'method': 'create_keys',
                            'doc': frm.doc,
                            'callback': function (response) {
                                cur_frm.reload_doc();
                            }
                        });
                    } else if (response.message.stage === 2) {
                        // send signature
                        frappe.call({
                            'method': 'send_signature',
                            'doc': frm.doc,
                            'callback': function (response) {
                                cur_frm.reload_doc();
                            }
                        });
                    } else if (response.message.stage === 3) {
                        // send keys
                        frappe.call({
                            'method': 'send_keys',
                            'doc': frm.doc,
                            'callback': function (response) {
                                cur_frm.reload_doc();
                            }
                        });
                    } else if (response.message.stage === 4) {
                        // create INI letter
                        frappe.call({
                            'method': 'create_ini_letter',
                            'doc': frm.doc,
                            'callback': function (response) {
                                cur_frm.reload_doc();
                            }
                        });
                    } else if (response.message.stage === 5) {
                        // download public keys
                        frappe.call({
                            'method': 'download_public_keys',
                            'doc': frm.doc,
                            'callback': function (response) {
                                cur_frm.reload_doc();
                            }
                        });
                    } else if (response.message.stage === 6) {
                        // activate connection
                        frappe.call({
                            'method': 'activate_account',
                            'doc': frm.doc,
                            'callback': function (response) {
                                cur_frm.reload_doc();
                            }
                        });
                    } else {
                        // do nothing, all set
                    }
                },
                primary_action_label: __('Next'),
                secondary_action_label: __('Close')
            });
            d.fields_dict.ht.$wrapper.html(response.message.html);
            
            // Add manual step buttons in the dialog
            var manual_buttons_html = `
                <div style="margin-top: 20px; border-top: 1px solid #ddd; padding-top: 15px;">
                    <h5>${__("Manual Steps (click to execute)")}</h5>
                    <div class="btn-group-vertical" style="width: 100%;">
                        <button class="btn btn-default btn-sm" onclick="execute_ebics_step(${frm.doc.name ? "'" + frm.doc.name + "'" : 'null'}, 'create_keys')">${__("1. Create Keys")}</button>
                        <button class="btn btn-primary btn-sm" onclick="execute_ebics_step(${frm.doc.name ? "'" + frm.doc.name + "'" : 'null'}, 'create_certificate')">${__("1b. Create Certificates Only")}</button>
                        <button class="btn btn-default btn-sm" onclick="execute_ebics_step(${frm.doc.name ? "'" + frm.doc.name + "'" : 'null'}, 'send_signature')">${__("2. Send Signature (INI)")}</button>
                        <button class="btn btn-default btn-sm" onclick="execute_ebics_step(${frm.doc.name ? "'" + frm.doc.name + "'" : 'null'}, 'send_keys')">${__("3. Send Keys (HIA)")}</button>
                        <button class="btn btn-default btn-sm" onclick="execute_ebics_step(${frm.doc.name ? "'" + frm.doc.name + "'" : 'null'}, 'create_ini_letter')">${__("4. Create INI Letter")}</button>
                        <button class="btn btn-default btn-sm" onclick="execute_ebics_step(${frm.doc.name ? "'" + frm.doc.name + "'" : 'null'}, 'download_public_keys')">${__("5. Download Public Keys (HPB)")}</button>
                        <button class="btn btn-default btn-sm" onclick="execute_ebics_step(${frm.doc.name ? "'" + frm.doc.name + "'" : 'null'}, 'activate_account')">${__("6. Activate Account")}</button>
                    </div>
                </div>
            `;
            d.fields_dict.ht.$wrapper.append(manual_buttons_html);
            
            d.show();
        }
    });
}

// Global function to execute EBICS steps
window.execute_ebics_step = function(doc_name, method) {
    if (!doc_name) {
        frappe.msgprint(__("Please save the document first"));
        return;
    }
    
    frappe.call({
        'method': 'frappe.client.get',
        'args': {
            'doctype': 'ebics Connection',
            'name': doc_name
        },
        'callback': function(r) {
            if (r.message) {
                frappe.call({
                    'method': method,
                    'doc': r.message,
                    'callback': function (response) {
                        frappe.msgprint(__("Step executed successfully"));
                        cur_frm.reload_doc();
                    }
                });
            }
        }
    });
}