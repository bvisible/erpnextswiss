// Copyright (c) 2024, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('ebics Connection', {
    refresh: function(frm) {
        // Auto-detect bank configuration when URL changes
        if (!frm.doc.bank_config && frm.doc.url) {
            frm.trigger('auto_detect_bank');
        }
        if (!frm.doc.__islocal) {
            if (frm.doc.activated) {
                cur_frm.dashboard.add_comment( __("This ebics connection is activated."), 'green', true);
                
                // Add sync button for activated connections
                if (frm.doc.enable_sync) {
                    frm.add_custom_button( __("Sync Now"), function() {
                        // Calculate default dates
                        var today = frappe.datetime.get_today();
                        var last_sync = frm.doc.synced_until || frappe.datetime.add_days(today, -7);
                        // Ensure from_date is not more than 1 day before synced_until
                        var from_date = last_sync ? frappe.datetime.add_days(last_sync, 1) : frappe.datetime.add_days(today, -7);
                        // Make sure from_date is not after today
                        if (frappe.datetime.get_diff(from_date, today) > 0) {
                            from_date = today;
                        }
                        
                        // Create dialog for sync options
                        var sync_dialog = new frappe.ui.Dialog({
                            title: __('Synchronize Bank Statements'),
                            fields: [
                                {
                                    fieldname: 'info_html',
                                    fieldtype: 'HTML',
                                    options: `<div class="alert alert-info">
                                        <p><strong>${__('Connection:')}</strong> ${frm.doc.name} (${frm.doc.ebics_version || 'H004'})</p>
                                        <p><strong>${__('Last synchronized:')}</strong> ${frm.doc.synced_until ? frappe.datetime.str_to_user(frm.doc.synced_until) : __('Never')}</p>
                                        <p><strong>${__('Today:')}</strong> ${frappe.datetime.str_to_user(today)}</p>
                                    </div>`
                                },
                                {
                                    fieldname: 'section_break_1',
                                    fieldtype: 'Section Break',
                                    label: __('Date Range')
                                },
                                {
                                    fieldname: 'from_date',
                                    fieldtype: 'Date',
                                    label: __('From Date'),
                                    default: from_date,
                                    reqd: 1,
                                    description: __('Start date for synchronization')
                                },
                                {
                                    fieldname: 'sync_mode',
                                    fieldtype: 'Select',
                                    label: __('Sync Mode'),
                                    options: 'Range\nDaily',
                                    default: 'Range',
                                    description: __('Range: Get all at once, Daily: Day by day')
                                },
                                {
                                    fieldname: 'column_break_1',
                                    fieldtype: 'Column Break'
                                },
                                {
                                    fieldname: 'to_date',
                                    fieldtype: 'Date',
                                    label: __('To Date'),
                                    default: today,
                                    reqd: 1,
                                    description: __('End date for synchronization (inclusive)')
                                },
                                {
                                    fieldname: 'section_break_2',
                                    fieldtype: 'Section Break'
                                },
                                {
                                    fieldname: 'preview_btn',
                                    fieldtype: 'Button',
                                    label: __('Check Availability'),
                                    click: function() {
                                        var values = sync_dialog.get_values();
                                        if (values.from_date && values.to_date) {
                                            var days = frappe.datetime.get_diff(values.to_date, values.from_date) + 1;
                                            
                                            // Show loading message
                                            sync_dialog.set_df_property('preview_html', 'options', 
                                                `<div class="alert alert-info">
                                                    <i class="fa fa-spinner fa-spin"></i> ${__('Checking existing statements and EBICS availability...')}
                                                </div>`
                                            );
                                            
                                            // Call server to check what's available
                                            frappe.call({
                                                method: 'erpnextswiss.erpnextswiss.ebics.preview_sync_range_detailed',
                                                args: {
                                                    connection_name: frm.doc.name,
                                                    from_date: values.from_date,
                                                    to_date: values.to_date,
                                                    debug: values.debug_mode
                                                },
                                                callback: function(r) {
                                                    if (r.message) {
                                                        var info = r.message;
                                                        var status_color = info.statements_to_import > 0 ? 'success' : (info.existing_count > 0 ? 'warning' : 'info');
                                                        var preview_html = `
                                                            <div class="alert alert-${status_color}">
                                                                <h5>${__('EBICS Availability Check')}</h5>
                                                                <div class="row">
                                                                    <div class="col-sm-6">
                                                                        <p><strong>${__('Date Range:')}</strong> ${frappe.datetime.str_to_user(values.from_date)} - ${frappe.datetime.str_to_user(values.to_date)}</p>
                                                                        <p><strong>${__('Total Days:')}</strong> ${days}</p>
                                                                        <p><strong>${__('EBICS Version:')}</strong> ${frm.doc.ebics_version || 'H004'}</p>
                                                                    </div>
                                                                    <div class="col-sm-6">
                                                                        <p><strong>${__('Total Available from Bank:')}</strong> <span class="badge badge-info">${info.total_available_from_bank || 0}</span></p>
                                                                        <p><strong>${__('Statements in Your Date Range:')}</strong> <span class="badge badge-primary">${info.statements_in_range || 0}</span></p>
                                                                        <p><strong>${__('New Statements to Import:')}</strong> <span class="badge badge-success">${info.statements_to_import || 0}</span></p>
                                                                    </div>
                                                                </div>
                                                                <hr>
                                                                <h6>${__('Import Summary')}</h6>
                                                                <div class="row">
                                                                    <div class="col-sm-4 text-center">
                                                                        <h3>${info.statements_in_range || 0}</h3>
                                                                        <p class="text-muted">${__('Available in Range')}</p>
                                                                    </div>
                                                                    <div class="col-sm-4 text-center">
                                                                        <h3>${info.existing_count || 0}</h3>
                                                                        <p class="text-muted">${__('Already Imported')}</p>
                                                                    </div>
                                                                    <div class="col-sm-4 text-center">
                                                                        <h3 class="text-success">${info.statements_to_import || 0}</h3>
                                                                        <p class="text-muted">${__('Will Be Imported')}</p>
                                                                    </div>
                                                                </div>
                                                                ${info.date_breakdown && info.date_breakdown.length > 0 ? `
                                                                <hr>
                                                                <h6>${__('Available Dates from Bank')}</h6>
                                                                <div style="max-height: 200px; overflow-y: auto;">
                                                                    <table class="table table-sm table-bordered">
                                                                        <thead>
                                                                            <tr>
                                                                                <th>${__('Date')}</th>
                                                                                <th>${__('Statements')}</th>
                                                                                <th>${__('In Range')}</th>
                                                                                <th>${__('Status')}</th>
                                                                            </tr>
                                                                        </thead>
                                                                        <tbody>
                                                                            ${info.date_breakdown.slice(0, 15).map(d => `
                                                                                <tr class="${d.in_range ? (d.exists ? '' : 'table-success') : 'text-muted'}">
                                                                                    <td>${frappe.datetime.str_to_user(d.date)}</td>
                                                                                    <td>${d.count}</td>
                                                                                    <td>${d.in_range ? '<i class="fa fa-check text-success"></i>' : '<i class="fa fa-times text-muted"></i>'}</td>
                                                                                    <td>${d.exists ? '<span class="badge badge-default">Imported</span>' : (d.in_range ? '<span class="badge badge-success">New</span>' : '<span class="badge badge-muted">Out of range</span>')}</td>
                                                                                </tr>
                                                                            `).join('')}
                                                                        </tbody>
                                                                    </table>
                                                                    ${info.date_breakdown.length > 15 ? `<p class="text-muted text-center">... and ${info.date_breakdown.length - 15} more dates</p>` : ''}
                                                                </div>
                                                                ` : ''}
                                                                <hr>
                                                                <p><small class="text-muted">
                                                                    <i class="fa fa-info-circle"></i> ${__('Bank returned')} ${info.total_available_from_bank} ${__('total statements. Only statements within your selected date range will be imported.')}
                                                                </small></p>
                                                            </div>
                                                        `;
                                                        sync_dialog.set_df_property('preview_html', 'options', preview_html);
                                                    }
                                                },
                                                error: function(r) {
                                                    sync_dialog.set_df_property('preview_html', 'options', 
                                                        `<div class="alert alert-danger">
                                                            <p>${__('Error checking availability:')}</p>
                                                            <p>${r.message || __('Unknown error')}</p>
                                                        </div>`
                                                    );
                                                }
                                            });
                                        }
                                    }
                                },
                                {
                                    fieldname: 'get_all_btn',
                                    fieldtype: 'Button',
                                    label: __('Get All Available'),
                                    description: __('Retrieve all available statements from bank without date restrictions'),
                                    click: function() {
                                        // Show loading message
                                        sync_dialog.set_df_property('preview_html', 'options', 
                                            `<div class="alert alert-info">
                                                <i class="fa fa-spinner fa-spin"></i> ${__('Retrieving all available statements from EBICS...')}
                                            </div>`
                                        );
                                        
                                        // Call server to get all available data
                                        frappe.call({
                                            method: 'erpnextswiss.erpnextswiss.ebics.get_all_available_statements',
                                            args: {
                                                connection_name: frm.doc.name,
                                                debug: sync_dialog.get_value('debug_mode') || false
                                            },
                                            callback: function(r) {
                                                if (r.message) {
                                                    var info = r.message;
                                                    var preview_html = `
                                                        <div class="alert alert-info">
                                                            <h5>${__('All Available Statements from Bank')}</h5>
                                                            <div class="row">
                                                                <div class="col-sm-6">
                                                                    <p><strong>${__('Total Statements Found:')}</strong> <span class="badge badge-info">${info.total_found || 0}</span></p>
                                                                    <p><strong>${__('Date Range:')}</strong> ${info.date_range || 'N/A'}</p>
                                                                </div>
                                                                <div class="col-sm-6">
                                                                    <p><strong>${__('New Statements:')}</strong> <span class="badge badge-success">${info.new_statements || 0}</span></p>
                                                                    <p><strong>${__('Already Imported:')}</strong> <span class="badge badge-warning">${info.existing_statements || 0}</span></p>
                                                                </div>
                                                            </div>
                                                            ${info.dates_summary ? `
                                                            <hr>
                                                            <h6>${__('Statements by Date')}</h6>
                                                            <div style="max-height: 300px; overflow-y: auto;">
                                                                <table class="table table-sm table-bordered">
                                                                    <thead>
                                                                        <tr>
                                                                            <th>${__('Date')}</th>
                                                                            <th>${__('Count')}</th>
                                                                            <th>${__('Status')}</th>
                                                                        </tr>
                                                                    </thead>
                                                                    <tbody>
                                                                        ${info.dates_summary.map(d => `
                                                                            <tr class="${d.exists ? '' : 'table-success'}">
                                                                                <td>${frappe.datetime.str_to_user(d.date)}</td>
                                                                                <td>${d.count}</td>
                                                                                <td>${d.exists ? '<span class="badge badge-default">Imported</span>' : '<span class="badge badge-success">New</span>'}</td>
                                                                            </tr>
                                                                        `).join('')}
                                                                    </tbody>
                                                                </table>
                                                            </div>
                                                            ` : ''}
                                                            <hr>
                                                            <div class="text-center">
                                                                <button class="btn btn-primary" onclick="
                                                                    frappe.call({
                                                                        method: 'erpnextswiss.erpnextswiss.ebics.import_all_available',
                                                                        args: {
                                                                            connection_name: '${frm.doc.name}',
                                                                            debug: ${sync_dialog.get_value('debug_mode') || false}
                                                                        },
                                                                        callback: function(r) {
                                                                            if (r.message && r.message.success) {
                                                                                sync_dialog.hide();
                                                                                frappe.msgprint({
                                                                                    title: __('Import Complete'),
                                                                                    message: r.message.message,
                                                                                    indicator: 'green'
                                                                                });
                                                                                cur_frm.reload_doc();
                                                                            }
                                                                        }
                                                                    });
                                                                ">${__('Import All Available Statements')}</button>
                                                            </div>
                                                        </div>
                                                    `;
                                                    sync_dialog.set_df_property('preview_html', 'options', preview_html);
                                                }
                                            },
                                            error: function(r) {
                                                sync_dialog.set_df_property('preview_html', 'options', 
                                                    `<div class="alert alert-danger">
                                                        <p>${__('Error retrieving statements:')}</p>
                                                        <p>${r.message || __('Unknown error')}</p>
                                                    </div>`
                                                );
                                            }
                                        });
                                    }
                                },
                                {
                                    fieldname: 'preview_html',
                                    fieldtype: 'HTML',
                                    options: ''
                                }
                            ],
                            primary_action_label: __('Synchronize'),
                            primary_action: function(values) {
                                sync_dialog.hide();
                                
                                // Show progress dialog
                                var progress_dialog = frappe.msgprint({
                                    title: __('Synchronization in Progress'),
                                    message: `<div id="sync-progress">
                                        <div class="progress">
                                            <div class="progress-bar progress-bar-striped active" role="progressbar" style="width: 100%">
                                                ${__('Connecting to EBICS...')}
                                            </div>
                                        </div>
                                        <p class="text-muted" style="margin-top: 10px;">
                                            <i class="fa fa-info-circle"></i> ${__('This may take a few minutes depending on the date range.')}
                                        </p>
                                    </div>`,
                                    indicator: 'blue'
                                });
                                
                                // Call custom sync method with date range
                                frappe.call({
                                    'method': 'erpnextswiss.erpnextswiss.ebics.sync_date_range_advanced',
                                    'args': {
                                        'connection_name': frm.doc.name,
                                        'from_date': values.from_date,
                                        'to_date': values.to_date,
                                        'sync_mode': values.sync_mode,
                                        'debug': values.debug_mode
                                    },
                                    'freeze': false,  // Don't freeze, use our custom progress
                                    'callback': function (response) {
                                        progress_dialog.hide();
                                        if (response.message && response.message.success) {
                                            frappe.msgprint({
                                                title: __('Synchronization Complete'),
                                                message: response.message.message,
                                                indicator: 'green'
                                            });
                                            cur_frm.reload_doc();
                                        } else {
                                            frappe.msgprint({
                                                title: __('Synchronization Failed'),
                                                message: response.message.message || __("Please check the error log."),
                                                indicator: 'red'
                                            });
                                        }
                                    }
                                });
                            }
                        });
                        
                        // Show initial preview
                        sync_dialog.show();
                        sync_dialog.fields_dict.preview_btn.click();
                        
                    }).addClass("btn-primary");
                }
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
    },
    
    url: function(frm) {
        // Auto-detect bank when URL changes
        if (!frm.doc.bank_config) {
            frm.trigger('auto_detect_bank');
        }
    },
    
    auto_detect_bank: function(frm) {
        // Auto-detect bank configuration based on URL
        if (frm.doc.url) {
            frappe.call({
                'method': 'detect_bank_config',
                'doc': frm.doc,
                'callback': function(r) {
                    if (r.message) {
                        frm.set_value('bank_config', r.message);
                        frappe.show_alert({
                            message: __('Bank configuration auto-detected: {0}', [r.message]),
                            indicator: 'green'
                        });
                    }
                }
            });
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