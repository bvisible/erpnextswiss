// Copyright (c) 2018-2024, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('Payment Proposal', {
     refresh: function(frm) {
        if (frm.doc.docstatus == 1) {
            // add download pain.001 button on submitted record
            frm.add_custom_button(__("Download bank file"), function() {
                // Directly show the payment file dialog using create_bank_file
                show_payment_file_dialog(frm);
            }).addClass("btn-primary");
            frm.add_custom_button(__("Download Wise file"), function() {
                generate_wise_file(frm);
            });
            // check if this account has an active ebic connection
            frappe.call({
                'method': 'has_active_ebics_connection',
                'doc': frm.doc,
                'callback': function(response) {
                    if (response.message && response.message.length > 0) {
                        frm.ebics_connection = response.message[0]['name'];
                        frm.add_custom_button(__("Transmit by ebics"), function() {
                            transmit_ebics(frm);
                        }).addClass("btn-success");
                    }
                }
            });
        } else if (frm.doc.docstatus == 0) {
             // add set payment date
             frm.add_custom_button(__("Set Payment Date"), function() {
                  set_payment_date(frm);
             });
        }
        // filter for bank account
        cur_frm.fields_dict['pay_from_account'].get_query = function(doc) {
            return {
                filters: {
                    "account_type": "Bank",
                    "company": frm.doc.company
                }
            }
        }
        cur_frm.fields_dict['intermediate_account'].get_query = function(doc) {
            return {
                filters: {
                    "account_type": "Bank",
                    "company": frm.doc.company
                }
            }
        }
        // remove add grid buttons
        var grid_add_btns = document.getElementsByClassName("grid-add-row") || [];
        for (var b = 0; b < grid_add_btns.length; b++) {
            grid_add_btns[b].style.visibility = "Hidden";
        }
     },
     validate: function(frm) {
        if (frm.doc.pay_from_account == null) {
            frappe.msgprint( __("Please select an account to pay from.") );
            frappe.validated = false;
        }
        if ((frm.doc.use_intermediate == 1) && (frm.doc.intermediate_account == null)) {
            frappe.msgprint( __("Please select an intermediate account.") );
            frappe.validated = false;
        }
     }
});

function generate_bank_file(frm) {
     console.log("creating file...");
     frappe.call({
          'method': 'create_bank_file',
          'doc': frm.doc,
          'callback': function(r) {
               if (r.message) {
                    // prepare the xml file for download
                    download("payments.xml", r.message.content);
                    
                    // Attach the file to the document
                    frappe.call({
                         'method': 'attach_generated_file',
                         'doc': frm.doc,
                         'args': {
                              'file_content': r.message.content,
                              'file_name': 'payment_ebics_' + frm.doc.name + '.xml',
                              'file_type': 'EBICS'
                         },
                         'callback': function(attach_r) {
                              if (attach_r.message) {
                                   frappe.show_alert({
                                        message: __('File attached successfully'),
                                        indicator: 'green'
                                   });
                                   frm.reload_doc();
                              }
                         }
                    });
               } 
          }
     });     
}

function generate_wise_file(frm) {
     frappe.call({
          'method': 'create_wise_file',
          'doc': frm.doc,
          'callback': function(r) {
               if (r.message) {
                    // prepare the xml file for download
                    download("wise_payments.csv", r.message.content);
               } 
          }
     });     
}

function download(filename, content) {
    var element = document.createElement('a');
    element.setAttribute('href', 'data:application/octet-stream;charset=utf-8,' + encodeURIComponent(content));
    element.setAttribute('download', filename);

    element.style.display = 'none';
    document.body.appendChild(element);

    element.click();

    document.body.removeChild(element);
}

function set_payment_date(frm) {
    var d = new Date();
    d = new Date(d.setDate(d.getDate() + 1));
    frappe.prompt([
            {'fieldname': 'date', 'fieldtype': 'Date', 'label': __('Execute Payments On'), 'reqd': 1, 'default': d}  
        ],
        function(values){
            // loop through purchase invoices and set skonto date (this will be the execution date)
            var items = cur_frm.doc.purchase_invoices;
            items.forEach(function(entry) {
                frappe.model.set_value(entry.doctype, entry.name, 'skonto_date', values.date);
            });
            // set execution date
            cur_frm.set_value('date', values.date);
        },
        __('Execution Date'),
        __('Set')
    );
}

frappe.ui.form.on('Payment Proposal Purchase Invoice', {
    purchase_invoices_remove: function(frm) {
        recalculate_total(frm);
    },
    skonto_amount: function(frm) {
        recalculate_total(frm);
    }
});

frappe.ui.form.on('Payment Proposal Expense', {
    expenses_remove: function(frm) {
        recalculate_total(frm);
    }
});

function recalculate_total(frm) {
    var total = 0;
    for (var i = 0; i < frm.doc.purchase_invoices.length; i++) {
        total += frm.doc.purchase_invoices[i].skonto_amount
    }
    for (var i = 0; i < frm.doc.expenses.length; i++) {
        total += frm.doc.expenses[i].amount
    }
    cur_frm.set_value('total', total);
}

function show_payment_file_dialog(frm) {
    // Generate payment file using create_bank_file
    frappe.call({
        'method': 'create_bank_file',
        'doc': frm.doc,
        'callback': function(r) {
            if (r.message && r.message.content) {
                // Create dialog with download button
                var d = new frappe.ui.Dialog({
                    'fields': [
                        {
                            'fieldname': 'ht',
                            'fieldtype': 'HTML',
                            'options': '<p>' + __('Click on the button below to download the payment file.') + '</p>' +
                                       '<p style="margin-top: 20px;"><a id="btn-download-xml" class="btn btn-primary btn-sm" ' +
                                       'href="data:application/octet-stream;charset=utf-8,' + encodeURIComponent(r.message.content) + '" ' +
                                       'download="payment_' + frm.doc.name + '.xml">' + 
                                       __('Download payment file') + '</a></p>' +
                                       '<p id="download-status" style="display: none; color: green; margin-bottom: 20px;">' + __('File downloaded successfully!') + '</p>' +
                                       '<div id="validation-section" style="display: none; margin-top: 30px; border-top: 1px solid #d1d8dd; padding-top: 20px;">' +
                                       '<p>' + __('Now you can create and validate the payment entries:') + '</p>' +
                                       '<p style="margin-top: 10px;"><button id="btn-validate-payments" class="btn btn-success btn-sm' + 
                                       (frm.doc.payment_entries_generated ? ' disabled' : '') + '"' +
                                       (frm.doc.payment_entries_generated ? ' disabled' : '') + '>' + 
                                       (frm.doc.payment_entries_generated ? __('Payment Entries Already Generated') : __('Create and Submit Payment Entries')) + 
                                       '</button></p>' +
                                       (frm.doc.payment_entries_generated ? '<p class="text-muted small">' + __('Payment entries have already been created for this proposal.') + '</p>' : '') +
                                       '</div>'
                        }
                    ],
                    size: 'small',
                    title: __('Download Payment File'),
                    primary_action_label: __('Close'),
                    primary_action: function() {
                        d.hide();
                    }
                });
                
                d.show();
                
                // Store dialog reference for validation
                frm._payment_dialog = d;
                
                // Use jQuery to attach click handler for download button
                d.$wrapper.on('click', '#btn-download-xml', function(e) {
                    // Show download status and validation section
                    d.$wrapper.find('#download-status').show();
                    d.$wrapper.find('#validation-section').show();
                    
                    // Attach the file to the document
                    frappe.call({
                        'method': 'attach_generated_file',
                        'doc': frm.doc,
                        'args': {
                            'file_content': r.message.content,
                            'file_name': 'payment_' + frm.doc.name + '.xml',
                            'file_type': 'CAMT'
                        },
                        'callback': function(attach_r) {
                            if (attach_r.message) {
                                frappe.show_alert({
                                    message: __('File attached successfully'),
                                    indicator: 'green'
                                });
                                // Update checkbox
                                if (!frm.doc.bank_camt_file_generated) {
                                    frm.set_value('bank_camt_file_generated', 1);
                                    frm.save();
                                }
                                frm.reload_doc();
                            }
                        }
                    });
                });
                
                // Handle validation button click
                d.$wrapper.on('click', '#btn-validate-payments', function(e) {
                    // Check if payment entries already generated
                    if (frm.doc.payment_entries_generated) {
                        frappe.msgprint({
                            title: __('Payment Entries Already Generated'),
                            message: __('Payment entries have already been created for this proposal. You cannot regenerate them.'),
                            indicator: 'orange'
                        });
                        return;
                    }
                    
                    // Disable the button to prevent multiple clicks
                    $(this).prop('disabled', true).text(__('Creating...'));
                    
                    // Call validate function
                    validate_payment_entries(frm, function(success) {
                        if (success) {
                            d.hide();
                        } else {
                            // Re-enable button if there was an error
                            $(e.target).prop('disabled', false).text(__('Create and Submit Payment Entries'));
                        }
                    });
                });
            } else {
                frappe.msgprint(__('Error generating payment file'));
            }
        },
        'error': function(r) {
            frappe.msgprint(__('Error generating payment file: ') + (r.message || r.exc));
        }
    });
}

function validate_payment_entries(frm, callback) {
    frappe.call({
        'method': 'create_payment_entries_from_proposal',
        'doc': frm.doc,
        'callback': function(r) {
            if (r.message && r.message.created) {
                frappe.msgprint(__('Successfully created {0} payment entries', [r.message.created]));
                
                // Update checkbox using frappe.db.set_value for immediate effect
                if (!frm.doc.payment_entries_generated) {
                    frappe.db.set_value(frm.doc.doctype, frm.doc.name, 'payment_entries_generated', 1)
                        .then(() => {
                            // Refresh the form after the value is saved
                            frm.reload_doc();
                            if (callback) callback(true);
                        });
                } else {
                    // Refresh the form
                    frm.reload_doc();
                    if (callback) callback(true);
                }
            } else {
                if (callback) callback(false);
            }
        },
        'error': function(r) {
            frappe.msgprint(__('Error creating payment entries: ') + (r.message || r.exc));
            if (callback) callback(false);
        }
    });
}

function transmit_ebics(frm) {
    if (!frm.ebics_connection) {
        frappe.msgprint(__("No EBICS connection found"));
        return;
    }
    
    // Check if already sent
    if (frm.doc.file_sent_to_ebics) {
        frappe.confirm(
            __('This payment file has already been transmitted via EBICS. Do you want to send it again?'),
            function() {
                // User clicked Yes - proceed with transmission
                do_transmit_ebics(frm);
            },
            function() {
                // User clicked No - do nothing
            }
        );
    } else {
        // Not yet sent - show normal confirmation
        frappe.confirm(
            __('Are you sure you want to transmit this payment file via EBICS?'),
            function() {
                // User clicked Yes
                do_transmit_ebics(frm);
            },
            function() {
                // User clicked No - do nothing
            }
        );
    }
}

function do_transmit_ebics(frm) {
    frappe.call({
        'method': 'erpnextswiss.erpnextswiss.doctype.ebics_connection.ebics_connection.execute_payment',
        'args': {
            'ebics_connection': frm.ebics_connection,
            'payment_proposal': frm.doc.name
        },
        'callback': function () {
            frappe.msgprint( __("Payments transferred using ebics") );
            // Update checkbox
            if (!frm.doc.file_sent_to_ebics) {
                frm.set_value('file_sent_to_ebics', 1);
                frm.save();
            }
        },
        'error': function(r) {
            frappe.msgprint(__("Error transmitting payment: ") + (r.message || r.exc));
        }
    });
}
