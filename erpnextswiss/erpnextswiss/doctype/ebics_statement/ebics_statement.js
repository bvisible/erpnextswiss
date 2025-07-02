// Copyright (c) 2024, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('ebics Statement', {
    refresh: function(frm) {
        // Debug logging
        console.log(`ebics Statement refresh - ${frm.doc.name}: ${frm.doc.transactions ? frm.doc.transactions.length : 0} transactions, status: ${frm.doc.status}`);
        
        // If document exists but transactions are not loaded, fetch them
        if (!frm.is_new() && (!frm.doc.transactions || frm.doc.transactions.length === 0)) {
            frappe.call({
                method: 'erpnextswiss.erpnextswiss.doctype.ebics_statement.ebics_statement.get_transactions',
                args: {
                    docname: frm.doc.name
                },
                callback: function(r) {
                    if (r.message && r.message.success && r.message.transactions.length > 0) {
                        console.log(`Loaded ${r.message.transactions.length} transactions from server`);
                        frm.doc.transactions = r.message.transactions;
                        frm.refresh_field('transactions');
                        
                        // Re-run the display functions with loaded transactions
                        check_display_bank_wizard(frm);
                        show_linked_documents(frm);
                    } else {
                        console.log("No transactions found in database");
                        frm.doc.transactions = [];
                        
                        // If we have XML content but no transactions, automatically re-parse
                        if (frm.doc.xml_content) {
                            console.log("XML content found but no transactions - automatically re-parsing...");
                            frappe.call({
                                method: 'erpnextswiss.erpnextswiss.doctype.ebics_statement.ebics_statement.reparse_xml',
                                args: {
                                    docname: frm.doc.name
                                },
                                callback: function(r) {
                                    if (r.message && r.message.success) {
                                        frappe.show_alert({
                                            message: __('Transactions automatically loaded from XML: {0} transactions found.', [r.message.transaction_count]),
                                            indicator: 'green'
                                        });
                                        frm.reload_doc();
                                    } else {
                                        frappe.show_alert({
                                            message: __('Error loading transactions from XML: {0}', [r.message.message || 'Unknown error']),
                                            indicator: 'red'
                                        });
                                    }
                                }
                            });
                        }
                    }
                }
            });
        }
        
        // Ensure transactions are visible even if empty
        if (!frm.doc.transactions) {
            frm.doc.transactions = [];
        }
        
        check_display_bank_wizard(frm);
        prepare_defaults(frm);
        show_linked_documents(frm);
    }
});

function check_display_bank_wizard(frm) {
    if (frm.doc.transactions) {
        for (let i = 0; i < frm.doc.transactions.length; i++) {
            if (frm.doc.transactions[i].status === "Pending") {
                frm.add_custom_button(__("Bank Wizard"), function() {
                    start_bank_wizard();
                });
                break;
            }
        }
    }
}

function prepare_defaults(frm) {
    locals.bank_wizard = {};
    frappe.call({
        'method': 'erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard.get_default_accounts',
        'args': {
            'bank_account': cur_frm.doc.account
        },
        'callback': function(r) {
            if (r.message) {
                locals.bank_wizard.payable_account = r.message.payable_account;
                locals.bank_wizard.receivable_account = r.message.receivable_account;
                locals.bank_wizard.expense_payable_account = r.message.expense_payable_account;
            } else {
                frappe.msgprint( __("Please set the <b>default accounts</b> in <a href=\"/desk#Form/Company/{0}\">{0}</a>.").replace("{0}", r.message.company) );
            }
        }
    });
    frappe.call({
        'method': 'erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard.get_default_customer',
        'callback': function(r) {
            if ((r.message) && (r.message.customer != "")) {
                locals.bank_wizard.default_customer = r.message.customer;
            } else {
                frappe.msgprint( __("Please set the <b>default customer</b> in <a href=\"/desk#Form/ERPNextSwiss Settings\">ERPNextSwiss Settings</a>.") );
            }
        }
    }); 
    frappe.call({
        'method': 'erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard.get_default_supplier',
        'callback': function(r) {
            if ((r.message) && (r.message.supplier != "")) {
                locals.bank_wizard.default_supplier = r.message.supplier;
            } else {
                frappe.msgprint( __("Please set the <b>default supplier</b> in <a href=\"/desk#Form/ERPNextSwiss Settings\">ERPNextSwiss Settings</a>.") );
            }
        }
    });
    frappe.call({
        'method': 'erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard.get_intermediate_account',
        'callback': function(r) {
            if ((r.message) && (r.message.account != "")) {
               locals.bank_wizard.intermediate_account = r.message.account;
            } else {
                frappe.msgprint( __("Please set the <b>intermediate bank account</b> in <a href=\"/desk#Form/ERPNextSwiss Settings\">ERPNextSwiss Settings</a>.") );
            }
        }
    }); 
}

function start_bank_wizard() {
    // get pending transactions
    let pending_transactions = [];
    for (let i = 0; i < cur_frm.doc.transactions.length; i++) {
        if (cur_frm.doc.transactions[i].status === "Pending") {
            pending_transactions.push(cur_frm.doc.transactions[i]);
        }
    }
    
    if (pending_transactions.length > 0) {
        frappe.call({
            'method': 'erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard.render_transactions',
            'args': {
                'transactions': pending_transactions
            },
            'callback': function(r) {
    
                let transaction_content = r.message;
                let d = new frappe.ui.Dialog({
                    'fields': [
                        {
                            'fieldname': 'transaction_table', 
                            'fieldtype': 'HTML', 
                            'label': __('Transactions'), 
                            'options': transaction_content
                        },
                    ],
                    'primary_action': function(){
                        d.hide();
                        // and remove the old dialog (otherwise, it cannot be opened again without F5)
                        clear_dialog_content();
                    },
                    'primary_action_label': __('Close'),
                    'title': __('Bank Wizard'),
                    'size': 'extra-large'
                });
                d.show();
                
                setTimeout(function () {
                    let modals = document.getElementsByClassName("modal-dialog");
                    if (modals.length > 0) {
                        modals[modals.length - 1].style.width = "90%";
                        modals[modals.length - 1].style.maxWidth = "1400px";
                    }
                    
                    // Add another delay to ensure DOM is ready
                    setTimeout(function() {
                        attach_button_handlers(pending_transactions);
                    }, 500);
                }, 300);
                
            }
        });
    }
}

function clear_dialog_content() {
    let modals = document.getElementsByClassName("modal-dialog");
    if (modals.length > 0) {
        modals[modals.length - 1].remove();
    }
}

function attach_button_handlers(transactions) {
    // Initialize Bootstrap tooltips for all buttons with data-toggle="tooltip"
    $('[data-toggle="tooltip"]').tooltip({
        container: 'body',
        html: true,
        boundary: 'viewport'
    });
    
    // attach button handlers
    var bank_account = cur_frm.doc.account;
    var company = cur_frm.doc.company;
    var intermediate_account = locals.bank_wizard.intermediate_account;
    var payable_account = locals.bank_wizard.payable_account;
    var expense_payable_account = locals.bank_wizard.expense_payable_account || locals.bank_wizard.payable_account;
    var receivable_account = locals.bank_wizard.receivable_account;
    var default_customer = locals.bank_wizard.default_customer;
    var default_supplier = locals.bank_wizard.default_supplier;
    transactions.forEach(function (transaction) {
        // add generic payables/receivables handler
        if (transaction.credit_debit == "DBIT") {
            // purchase invoice match
            var button = document.getElementById("btn-close-pinv-" + transaction.txid);
            if (button) {
                button.addEventListener("click", function(e) {
                    e.target.disabled = true;
                    var payment = {
                        'amount': transaction.amount,
                        'date': transaction.date,
                        'paid_from': bank_account,
                        'paid_to': payable_account,
                        'reference_no': transaction.unique_reference,
                        'type': "Pay",
                        'party_type': "Supplier",
                        'party': transaction.party_match,
                        'references': transaction.invoice_matches,
                        'remarks': (transaction.transaction_reference + ", " + transaction.party_name + ", " + transaction.party_address),
                        'party_iban': transaction.party_iban,
                        'company': company
                    }
                    create_payment_entry(payment, transaction.txid);
                });
            }
            // expense claim match
            var button = document.getElementById("btn-close-exp-" + transaction.txid);
            if (button) {
                button.addEventListener("click", function(e) {
                    e.target.disabled = true;
                    var payment = {
                        'amount': transaction.amount,
                        'date': transaction.date,
                        'paid_from': bank_account,
                        'paid_to': expense_payable_account,
                        'reference_no': transaction.unique_reference,
                        'type': "Pay",
                        'party_type': "Employee",
                        'party': transaction.employee_match,
                        'references': transaction.expense_matches,
                        'remarks': (transaction.transaction_reference + ", " + transaction.party_name + ", " + transaction.party_address),
                        'party_iban': transaction.party_iban,
                        'company': company
                    }
                    create_payment_entry(payment, transaction.txid);
                });
            }
            // supplier match
            var button = document.getElementById("btn-close-supplier-" + transaction.txid);
            if (button) {
                button.addEventListener("click", function(e) {
                    e.target.disabled = true;
                    var payment = {
                        'amount': transaction.amount,
                        'date': transaction.date,
                        'paid_from': bank_account,
                        'paid_to': payable_account,
                        'reference_no': transaction.unique_reference,
                        'type': "Pay",
                        'party_type': "Supplier",
                        'party': transaction.party_match,
                        'remarks': (transaction.transaction_reference + ", " + transaction.party_name + ", " + transaction.party_address),
                        'party_iban': transaction.party_iban,
                        'company': company
                    }
                    create_payment_entry(payment, transaction.txid);
                });
            }
            // employee match
            var button = document.getElementById("btn-close-employee-" + transaction.txid);
            if (button) {
                button.addEventListener("click", function(e) {
                    e.target.disabled = true;
                    var payment = {
                        'amount': transaction.amount,
                        'date': transaction.date,
                        'paid_from': bank_account,
                        'paid_to': expense_payable_account,
                        'reference_no': transaction.unique_reference,
                        'type': "Pay",
                        'party_type': "Employee",
                        'party': transaction.employee_match,
                        'remarks': (transaction.transaction_reference + ", " + transaction.party_name + ", " + transaction.party_address),
                        'party_iban': transaction.party_iban,
                        'company': company
                    }
                    create_payment_entry(payment, transaction.txid);
                });
            }
            // payables
            var button = document.getElementById("btn-close-payable-" + transaction.txid);
            if (button) {
                button.addEventListener("click", function(e) {
                    e.target.disabled = true;
                    var payment = {
                        'amount': transaction.amount,
                        'date': transaction.date,
                        'paid_from': bank_account,
                        'paid_to': payable_account,
                        'reference_no': transaction.unique_reference,
                        'type': "Pay",
                        'party_type': "Supplier",
                        'party': default_supplier,
                        'remarks': (transaction.transaction_reference + ", " + transaction.party_name + ", " + transaction.party_address),
                        'party_iban': transaction.party_iban,
                        'company': company
                    }
                    create_payment_entry(payment, transaction.txid);
                });
            }
        } else {
            // quick match button "⇒"
            var quick_button = document.getElementById("btn-quick-sinv-" + transaction.txid);
            if (quick_button) {
                quick_button.addEventListener("click", function(e) {
                    e.target.disabled = true;
                    var payment = {
                        'amount': transaction.amount,
                        'date': transaction.date,
                        'paid_from': receivable_account,
                        'paid_to': bank_account,
                        'reference_no': transaction.unique_reference,
                        'type': "Receive",
                        'party_type': "Customer",
                        'party': transaction.party_match,
                        'references': transaction.invoice_matches,
                        'remarks': (transaction.transaction_reference + ", " + transaction.party_name + ", " + transaction.party_address),
                        'party_iban': transaction.party_iban,
                        'company': company,
                        'auto_submit': 1
                    }
                    create_payment_entry(payment, transaction.txid);
                });
            }
            
            // sales invoice match
            var button = document.getElementById("btn-close-sinv-" + transaction.txid);
            if (button) {
                button.addEventListener("click", function(e) {
                    e.target.disabled = true;
                    var payment = {
                        'amount': transaction.amount,
                        'date': transaction.date,
                        'paid_from': receivable_account,
                        'paid_to': bank_account,
                        'reference_no': transaction.unique_reference,
                        'type': "Receive",
                        'party_type': "Customer",
                        'party': transaction.party_match,
                        'references': transaction.invoice_matches,
                        'remarks': (transaction.transaction_reference + ", " + transaction.party_name + ", " + transaction.party_address),
                        'party_iban': transaction.party_iban,
                        'company': company
                    }
                    create_payment_entry(payment, transaction.txid);
                });
            }
            // customer match
            var button = document.getElementById("btn-close-customer-" + transaction.txid);
            if (button) {
                button.addEventListener("click", function(e) {
                    e.target.disabled = true;
                    var payment = {
                        'amount': transaction.amount,
                        'date': transaction.date,
                        'paid_from': receivable_account,
                        'paid_to': bank_account,
                        'reference_no': transaction.unique_reference,
                        'type': "Receive",
                        'party_type': "Customer",
                        'party': transaction.party_match,
                        'remarks': (transaction.transaction_reference + ", " + transaction.party_name + ", " + transaction.party_address),
                        'party_iban': transaction.party_iban,
                        'company': company
                    }
                    create_payment_entry(payment, transaction.txid);
                });
            }
            // receivables
            var button = document.getElementById("btn-close-receivable-" + transaction.txid);
            if (button) {
                button.addEventListener("click", function(e) {
                    e.target.disabled = true;
                    var payment = {
                        'amount': transaction.amount,
                        'date': transaction.date,
                        'paid_from': receivable_account,
                        'paid_to': bank_account,
                        'reference_no': transaction.unique_reference,
                        'type': "Receive",
                        'party_type': "Customer",
                        'party': default_customer,
                        'remarks': (transaction.transaction_reference + ", " + transaction.party_name + ", " + transaction.party_address),
                        'party_iban': transaction.party_iban,
                        'company': company
                    }
                    create_payment_entry(payment, transaction.txid);
                });
            }
        }
        // add intermediate account handler
        var button = document.getElementById("btn-close-intermediate-" + transaction.txid);
        if (button) {
            button.addEventListener("click", function(e) {
                e.target.disabled = true;
                var paid_to = bank_account;
                var paid_from = intermediate_account;
                if (transaction.credit_debit == "DBIT") {
                    paid_from = bank_account;
                    paid_to = intermediate_account;
                }
                // note: currency is defined through account currencies of the bank account
                var payment = {
                    'amount': transaction.amount,
                    'date': transaction.date,
                    'paid_from': paid_from,
                    'paid_to': paid_to,
                    'reference_no': transaction.unique_reference,
                    'type': "Internal Transfer",
                    'remarks': (transaction.transaction_reference + ", " + transaction.party_name + ", " + transaction.party_address),
                    'party_iban': transaction.party_iban,
                    'company': company
                }
                create_payment_entry(payment, transaction.txid);
            });
        }
        // add journal entry handler
        var button = document.getElementById("btn-journal-entry-" + transaction.txid);
        if (button) {
            button.addEventListener("click", function(e) {
                e.target.disabled = true;
                create_journal_entry_dialog(transaction, bank_account, company);
            });
        }
    }); 
}

function create_payment_entry(payment, txid) {
    frappe.call({
        'method': "erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard.make_payment_entry",
        'args': payment,
        'callback': function(r) {
            // open new record in a separate tab
            window.open(r.message.link, '_blank');
            close_entry(txid, r.message.payment_entry, 'Payment Entry');
        }
    });    
}

function close_entry(txid, reference_doc, doc_type) {
    // update transaction row
    for (let i = 0; i < cur_frm.doc.transactions.length; i++) {
        if (cur_frm.doc.transactions[i].txid === txid) {
            // Check if it's a Journal Entry or Payment Entry
            if (doc_type === 'Journal Entry') {
                // It's a Journal Entry - store in remarks field with a special prefix
                let remarks = cur_frm.doc.transactions[i].remarks || '';
                if (remarks) {
                    remarks += '\n';
                }
                remarks += 'Journal Entry: ' + reference_doc;
                frappe.model.set_value(cur_frm.doc.transactions[i].doctype, cur_frm.doc.transactions[i].name, 'remarks', remarks);
            } else {
                // It's a Payment Entry
                frappe.model.set_value(cur_frm.doc.transactions[i].doctype, cur_frm.doc.transactions[i].name, 'payment_entry', reference_doc);
            }
            frappe.model.set_value(cur_frm.doc.transactions[i].doctype, cur_frm.doc.transactions[i].name, 'status', "Completed");
            break;
        }
    }
    cur_frm.save();
    // close the entry in the list
    let table_row = document.getElementById("row-transaction-" + txid);
    if (table_row) {
        table_row.classList.add("hidden");
    }
}

function create_journal_entry_dialog(transaction, bank_account, company) {
    // Préparer la remarque par défaut
    let default_remark = `${transaction.transaction_reference} - ${transaction.party_name || ''}`;
    if (transaction.party_address) {
        default_remark += ` - ${transaction.party_address}`;
    }
    
    let d = new frappe.ui.Dialog({
        title: __('Create Journal Entry from Template'),
        fields: [
            {
                'fieldname': 'journal_entry_template',
                'fieldtype': 'Link',
                'label': __('Journal Entry Template'),
                'options': 'Journal Entry Template',
                'reqd': 1,
                'get_query': function() {
                    return {
                        filters: {
                            'company': company
                        }
                    };
                }
            },
            {
                'fieldname': 'user_remark',
                'fieldtype': 'Small Text',
                'label': __('User Remark'),
                'default': default_remark,
                'description': __('This remark will be added to the Journal Entry')
            },
            {
                'fieldname': 'transaction_info',
                'fieldtype': 'HTML',
                'label': __('Transaction Information'),
                'options': `
                    <div class="alert alert-info">
                        <strong>${__('Transaction Details:')}</strong><br>
                        ${__('Date')}: ${frappe.datetime.str_to_user(transaction.date)}<br>
                        ${__('Amount')}: ${transaction.currency} ${transaction.amount}<br>
                        ${__('Type')}: ${transaction.credit_debit == 'DBIT' ? __('Debit') : __('Credit')}<br>
                        ${__('Party')}: ${transaction.party_name || 'N/A'}<br>
                        ${__('Reference')}: ${transaction.transaction_reference}
                    </div>
                `
            }
        ],
        primary_action_label: __('Create'),
        primary_action(values) {
            // Validate the template first
            frappe.call({
                method: 'erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard.validate_journal_template',
                args: {
                    template_name: values.journal_entry_template,
                    transaction_type: transaction.credit_debit,
                    bank_account: bank_account
                },
                callback: function(r) {
                    if (r.message.valid) {
                        // Create the journal entry
                        frappe.call({
                            method: 'erpnextswiss.erpnextswiss.page.bank_wizard.bank_wizard.make_journal_entry_from_template',
                            args: {
                                template_name: values.journal_entry_template,
                                transaction: transaction,
                                bank_account: bank_account,
                                company: company,
                                user_remark: values.user_remark
                            },
                            callback: function(r) {
                                if (r.message) {
                                    d.hide();
                                    frappe.show_alert({
                                        message: __('Journal Entry {0} created successfully', [r.message.journal_entry]),
                                        indicator: 'green'
                                    });
                                    // Open the journal entry in a new tab
                                    window.open(r.message.link, '_blank');
                                    // Update the transaction status
                                    close_entry(transaction.txid, r.message.journal_entry, 'Journal Entry');
                                }
                            }
                        });
                    } else {
                        frappe.msgprint({
                            title: __('Template Not Compatible'),
                            indicator: 'red',
                            message: r.message.message
                        });
                    }
                }
            });
        }
    });
    d.show();
}

function show_linked_documents(frm) {
    console.log("show_linked_documents");
    
    if (!frm.doc.__islocal && frm.doc.transactions) {
        // Remove any existing linked documents sections
        frm.$wrapper.find('[data-fieldname="linked_summary"]').remove();
        frm.$wrapper.find('[data-fieldname="linked_documents"]').remove();
        
        // Collect all linked data
        let payment_entries = [];
        let journal_entries = [];
        let sales_invoices = [];
        let purchase_invoices = [];
        let customers = new Set();
        let suppliers = new Set();
        
        frm.doc.transactions.forEach(function(transaction) {
            if (transaction.payment_entry) {
                payment_entries.push(transaction.payment_entry);
            }
            
            // Check for Journal Entry in remarks
            if (transaction.remarks) {
                let match = transaction.remarks.match(/Journal Entry: ([A-Z0-9-]+)/);
                if (match) {
                    journal_entries.push(match[1]);
                }
            }
            
            if (transaction.invoice_matches) {
                try {
                    let matches = eval(transaction.invoice_matches);
                    if (Array.isArray(matches)) {
                        matches.forEach(function(invoice) {
                            if (transaction.credit_debit === 'CRDT') {
                                sales_invoices.push(invoice);
                            } else {
                                purchase_invoices.push(invoice);
                            }
                        });
                    }
                } catch(e) {}
            }
            
            if (transaction.party_match) {
                if (transaction.credit_debit === 'CRDT') {
                    customers.add(transaction.party_match);
                } else {
                    suppliers.add(transaction.party_match);
                }
            }
        });
        
        // Calculate summary statistics
        let total_debit = 0;
        let total_credit = 0;
        let pending_count = 0;
        let completed_count = 0;
        
        frm.doc.transactions.forEach(function(t) {
            if (t.credit_debit === 'DBIT') {
                total_debit += t.amount;
            } else {
                total_credit += t.amount;
            }
            
            if (t.status === 'Pending') {
                pending_count++;
            } else if (t.status === 'Completed') {
                completed_count++;
            }
        });
        
        // Build the HTML using Frappe standard dashboard structure
        let html = `
            <!-- Summary Stats Section -->
            <div class="row form-dashboard-section form-stats" data-fieldname="linked_summary">
                <div class="section-head">Summary</div>
                <div class="section-body">
                    <div class="row">
                        <div class="col-sm-4">
                            <div class="stat-wrapper text-center">
                                <div class="stat-title text-muted">Total Transactions</div>
                                <div class="stat-value">${frm.doc.transactions.length}</div>
                                <div class="stat-footer">
                                    <span class="text-success">Completed: ${completed_count}</span> | 
                                    <span class="text-warning">Pending: ${pending_count}</span>
                                </div>
                            </div>
                        </div>
                        <div class="col-sm-4">
                            <div class="stat-wrapper text-center">
                                <div class="stat-title text-muted">Net Movement</div>
                                <div class="stat-value ${(total_credit - total_debit) >= 0 ? 'text-success' : 'text-danger'}">
                                    ${format_currency(total_credit - total_debit, frm.doc.currency)}
                                </div>
                                <div class="stat-footer">
                                    <span class="text-success">Credit: ${format_currency(total_credit, frm.doc.currency)}</span><br>
                                    <span class="text-danger">Debit: ${format_currency(total_debit, frm.doc.currency)}</span>
                                </div>
                            </div>
                        </div>
                        <div class="col-sm-4">
                            <div class="stat-wrapper text-center">
                                <div class="stat-title text-muted">Linked Documents</div>
                                <div class="stat-value">${payment_entries.length + journal_entries.length + sales_invoices.length + purchase_invoices.length + customers.size + suppliers.size}</div>
                                <div class="stat-footer">
                                    Payments: ${payment_entries.length} | 
                                    Journal: ${journal_entries.length} |
                                    Invoices: ${sales_invoices.length + purchase_invoices.length} | 
                                    Parties: ${customers.size + suppliers.size}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
        `;
        
        // Only show Linked Documents section if there are linked documents
        if (payment_entries.length > 0 || journal_entries.length > 0 || sales_invoices.length > 0 || purchase_invoices.length > 0 || customers.size > 0 || suppliers.size > 0) {
            html += `
            <!-- Linked Documents Section -->
            <div class="row form-dashboard-section form-links" data-fieldname="linked_documents">
                <div class="section-head">Linked Documents</div>
                <div class="section-body">
                    <div class="row">
            `;
        
                        // Payment Entries
                        if (payment_entries.length > 0) {
                            html += `
                                <div class="col-sm-6">
                                    <h6 class="text-muted">Payment Entries</h6>
                                    <div class="document-links">
                            `;
                            payment_entries.forEach(function(pe) {
                                html += `<a href="/app/payment-entry/${pe}" class="btn btn-sm btn-primary" style="margin: 2px;">${pe}</a>`;
                            });
                            html += `
                                    </div>
                                </div>
                            `;
                        }
                        
                        // Journal Entries
                        if (journal_entries.length > 0) {
                            html += `
                                <div class="col-sm-6">
                                    <h6 class="text-muted">Journal Entries</h6>
                                    <div class="document-links">
                            `;
                            journal_entries.forEach(function(je) {
                                html += `<a href="/app/journal-entry/${je}" class="btn btn-sm btn-info" style="margin: 2px;">${je}</a>`;
                            });
                            html += `
                                    </div>
                                </div>
                            `;
                        }
        
                        // Invoices
                        if (sales_invoices.length > 0 || purchase_invoices.length > 0) {
                            html += `
                                <div class="col-sm-6">
                                    <h6 class="text-muted">Linked Invoices</h6>
                            `;
                            
                            if (sales_invoices.length > 0) {
                                html += `
                                    <div style="margin-bottom: 10px;">
                                        <strong>Sales Invoices:</strong><br/>
                                        <div class="document-links">
                                `;
                                sales_invoices.forEach(function(inv) {
                                    html += `<a href="/app/sales-invoice/${inv}" class="btn btn-sm btn-success" style="margin: 2px;">${inv}</a>`;
                                });
                                html += `</div></div>`;
                            }
                            
                            if (purchase_invoices.length > 0) {
                                html += `
                                    <div>
                                        <strong>Purchase Invoices:</strong><br/>
                                        <div class="document-links">
                                `;
                                purchase_invoices.forEach(function(inv) {
                                    html += `<a href="/app/purchase-invoice/${inv}" class="btn btn-sm btn-danger" style="margin: 2px;">${inv}</a>`;
                                });
                                html += `</div></div>`;
                            }
                            
                            html += `
                                </div>
                            `;
                        }
        
                        // Parties row
                        if (customers.size > 0 || suppliers.size > 0) {
                            html += `
                            </div>
                            <div class="row" style="margin-top: 15px;">
                                <div class="col-sm-12">
                                    <h6 class="text-muted">Related Parties</h6>
            `;
            
            if (customers.size > 0) {
                html += `
                    <div style="margin-bottom: 10px;">
                        <strong>Customers:</strong><br/>
                        <div class="document-links">
                `;
                Array.from(customers).forEach(function(customer) {
                    html += `<a href="/app/customer/${customer}" class="btn btn-sm btn-info" style="margin: 2px;">${customer}</a>`;
                });
                html += `</div></div>`;
            }
            
                            if (suppliers.size > 0) {
                                html += `
                                    <div>
                                        <strong>Suppliers:</strong><br/>
                                        <div class="document-links">
                                `;
                                Array.from(suppliers).forEach(function(supplier) {
                                    html += `<a href="/app/supplier/${supplier}" class="btn btn-sm btn-warning" style="margin: 2px;">${supplier}</a>`;
                                });
                                html += `</div></div>`;
                            }
                            
                            html += `
                                </div>
                            `;
                        }
        
                        html += `
                                </div>
                            `;
                        
            // Close the Linked Documents section
            html += `
                    </div>
                </div>
            </div>
            `;
        }
        
        // Add styles
        html += `
            <style>
                .form-dashboard-section.form-stats .stat-wrapper {
                    padding: 15px;
                    background: var(--color-backgounrd);
                    border-radius: 4px;
                    margin-bottom: 15px;
                }
                .form-dashboard-section.form-stats .stat-title {
                    font-size: 13px;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    margin-bottom: 10px;
                }
                .form-dashboard-section.form-stats .stat-value {
                    font-size: 24px;
                    font-weight: 300;
                    margin: 10px 0;
                }
                .form-dashboard-section.form-stats .stat-footer {
                    font-size: 12px;
                    color: #6c757d;
                }
                .form-dashboard-section.form-links h6 {
                    margin-bottom: 10px;
                    font-weight: 600;
                }
                .document-links {
                    margin-top: 5px;
                }
                .document-links .btn {
                    font-size: 12px;
                    padding: 4px 8px;
                    margin: 2px;
                }
            </style>
        `;
        
        // Insert the HTML in the dashboard section
        let dashboardSection = frm.$wrapper.find('.form-dashboard');
        if (dashboardSection.length) {
            dashboardSection.append(html);
        } else {
            // Fallback: create dashboard section if it doesn't exist
            let mainSection = frm.$wrapper.find('.layout-main-section').first();
            mainSection.prepend('<div class="form-dashboard"></div>');
            mainSection.find('.form-dashboard').append(html);
        }
    }
}