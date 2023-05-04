// Copyright (c) 2018-2022, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

frappe.ui.form.on('VAT Declaration', {
    refresh: function(frm) {
        frm.add_custom_button(__("Get values"), function() 
        {
            get_values(frm);
        });
        frm.add_custom_button(__("Recalculate"), function() 
        {
            recalculate(frm);
        });
        
        update_taxable_revenue(frm);
        update_tax_amounts(frm);
        update_payable_tax(frm);
    },
    onload: function(frm) {
        if (frm.doc.__islocal) {
            // this function is called when a new VAT declaration is created
            // get current month (0..11)
            var d = new Date();
            var n = d.getMonth();
            // define title as Qn YYYY of the last complete quarter
            var title = " / " + d.getFullYear();
            if ((n > (-1)) && (n < 3)) {
                title = "Q4 / " + (d.getFullYear() - 1);
                frm.set_value('start_date', (d.getFullYear() - 1) + "-10-01");
                frm.set_value('end_date', (d.getFullYear() - 1) + "-12-31");
            } else if ((n > (2)) && (n < 6)) {
                title = "Q1" + title;
                frm.set_value('start_date', d.getFullYear() + "-01-01");
                frm.set_value('end_date', d.getFullYear() + "-03-31");
            } else if ((n > (5)) && (n < 9)) {
                title = "Q2" + title;
                frm.set_value('start_date', d.getFullYear() + "-04-01");
                frm.set_value('end_date', d.getFullYear() + "-06-30");
            } else {
                title = "Q3" + title;
                frm.set_value('start_date', d.getFullYear() + "-07-01");
                frm.set_value('end_date', d.getFullYear() + "-09-30");
            } 

            cur_frm.set_value('title', title + " - " + (frm.doc.cmp_abbr || ""));
        }
    },
    onload_post_render: function(frm) {
        if (frm.doc.__islocal) {
            get_tax_rates(frm);
        }
    },
    company: function(frm) {
        if ((frm.doc.__islocal) && (frm.doc.company)) {
            // replace company key
            var parts = frm.doc.title.split(" - ");
            if (parts.length > 1) {
                var new_title = [];
                for (var i = 0; i < (parts.length - 1); i++) {
                    new_title.push(parts[i]);
                }
                new_title.push(frm.doc.cmp_abbr);
                cur_frm.set_value("title", new_title.join(" - "));
            } else if (parts.length === 0) {
                // key missing
                cur_frm.set_value("title", frm.doc.title + " - " + frm.doc.cmp_abbr);
            }
            
        }
    }
});

function get_tax_rates(frm) {
    console.log("get tax rates")
    frappe.db.get_value("Account", {"tax_code": "302", "company": frm.doc.company}, "tax_rate").then((r) => {
        frm.set_value("normal_rate", r.message.tax_rate);
    });
    frappe.db.get_value("Account", {"tax_code": "312", "company": frm.doc.company}, "tax_rate").then((r) => {
        frm.set_value("reduced_rate", r.message.tax_rate);
    });
    frappe.db.get_value("Account", {"tax_code": "342", "company": frm.doc.company}, "tax_rate").then((r) => {
        frm.set_value("lodging_rate", r.message.tax_rate);
    });
}
// retrieve values from database
function get_values(frm) {
    let method = ''
    if(frm.doc.vat_type == "effective invoiced" || frm.doc.vat_type == "flat") {
        method = 'erpnextswiss.erpnextswiss.doctype.vat_declaration.vat_declaration.get_totals_from_invoices'
    } else {
        method = 'erpnextswiss.erpnextswiss.doctype.vat_declaration.vat_declaration.get_total_payments'
    }

    frappe.call({
        method: method,
        args: {
            start_date: frm.doc.start_date,
            end_date: frm.doc.end_date,
            company: frm.doc.company
        },
        callback: function(r) {
            if (r.message) {
                let res = r.message;
                frm.set_value('total_revenue', res.net_sell.total_credit - res.net_sell.total_debit);
                // get_total(frm, "viewVAT_205", 'non_taxable_revenue');
                // Deductions
                /*frm.set_value(frm, "viewVAT_220", 'tax_free_services',);
                frm.set_value(frm, "viewVAT_221", 'revenue_abroad',);
                frm.set_value(frm, "viewVAT_225", 'transfers',);
                frm.set_value(frm, "viewVAT_230", 'non_taxable_services',);
                frm.set_value(frm, "viewVAT_235", 'losses',);*/
                // Tax calculation
                if (frm.doc.vat_type.includes("effective")) {
                    frm.set_value('normal_tax', res.sums_by_tax_code['302'] ? (res.sums_by_tax_code['302'].total_credit - res.sums_by_tax_code['302'].total_debit) : 0);
                    frm.set_value('reduced_tax', res.sums_by_tax_code['312'] ? (res.sums_by_tax_code['312'].total_credit - res.sums_by_tax_code['312'].total_debit) : 0);
                    frm.set_value('lodging_tax', res.sums_by_tax_code['342'] ? (res.sums_by_tax_code['342'].total_credit - res.sums_by_tax_code['342'].total_debit) : 0);
                }
                else {
                    //frm.set_value(frm, "viewVAT_322", 'amount_1',);
                    //frm.set_value(frm, "viewVAT_332", 'amount_2',);
                }
                //frm.set_value(frm, "viewVAT_382", 'additional_amount',);
                //frm.set_value(frm, "viewVAT_382", 'additional_tax',);
                // Pretaxes
                if (frm.doc.vat_type.includes("effective")) {
                    frm.set_value('pretax_material', res.sums_by_tax_code['400'] ? (res.sums_by_tax_code['400'].total_debit - res.sums_by_tax_code['400'].total_credit) : 0);
                    frm.set_value('pretax_investments', res.sums_by_tax_code['405'] ? (res.sums_by_tax_code['405'].total_debit - res.sums_by_tax_code['405'].total_credit) : 0);
                    frm.set_value('missing_pretax', res.sums_by_tax_code['410'] ? (res.sums_by_tax_code['410'].total_debit - res.sums_by_tax_code['410'].total_credit) : 0);
                    frm.set_value('pretax_correction_mixed', res.sums_by_tax_code['415'] ? (res.sums_by_tax_code['415'].total_debit - res.sums_by_tax_code['415'].total_credit) : 0);
                    frm.set_value('pretax_correction_other', res.sums_by_tax_code['420'] ? (res.sums_by_tax_code['420'].total_debit - res.sums_by_tax_code['420'].total_credit) : 0);
                }
                frm.refresh_fields();
            }
        }
    });
}

// force recalculate
function recalculate(frm) {
    update_taxable_revenue(frm);
    update_tax_amounts(frm);
    update_payable_tax(frm);
}

// add change handlers for tax positions
frappe.ui.form.on("VAT Declaration", "normal_amount", function(frm) { update_tax_or_amount(frm, "normal", true) } );
frappe.ui.form.on("VAT Declaration", "normal_rate", function(frm) { update_tax_or_amount(frm, "normal", true) } );
frappe.ui.form.on("VAT Declaration", "normal_tax", function(frm) { update_tax_or_amount(frm, "normal", false) } );
frappe.ui.form.on("VAT Declaration", "reduced_amount", function(frm) { update_tax_or_amount(frm, "reduced", true) } );
frappe.ui.form.on("VAT Declaration", "reduced_rate", function(frm) { update_tax_or_amount(frm, "reduced", true) } );
frappe.ui.form.on("VAT Declaration", "reduced_tax", function(frm) { update_tax_or_amount(frm, "reduced", false) } );
frappe.ui.form.on("VAT Declaration", "lodging_amount", function(frm) { update_tax_or_amount(frm, "lodging", true) } );
frappe.ui.form.on("VAT Declaration", "lodging_rate", function(frm) { update_tax_or_amount(frm, "lodging", true) } );
frappe.ui.form.on("VAT Declaration", "lodging_tax", function(frm) { update_tax_or_amount(frm, "lodging", false) } );
frappe.ui.form.on("VAT Declaration", "additional_amount", function(frm) { update_tax_or_amount(frm, "additional", true) } );
frappe.ui.form.on("VAT Declaration", "additional_tax", function(frm) { update_tax_or_amount(frm, "additional", false) } );
frappe.ui.form.on("VAT Declaration", "amount_1", function(frm) { update_tax_or_amount(frm, "_1", true) } );
frappe.ui.form.on("VAT Declaration", "rate_1", function(frm) { update_tax_or_amount(frm, "_1", true) } );
frappe.ui.form.on("VAT Declaration", "tax_1", function(frm) { update_tax_or_amount(frm, "_1", false) } );
frappe.ui.form.on("VAT Declaration", "amount_2", function(frm) { update_tax_or_amount(frm, "_2", true) } );
frappe.ui.form.on("VAT Declaration", "rate_2", function(frm) { update_tax_or_amount(frm, "_2", true) } );
frappe.ui.form.on("VAT Declaration", "tax_2", function(frm) { update_tax_or_amount(frm, "_2", false) } );

function update_tax_or_amount(frm, concerned_tax, from_amount=false) {
    if(concerned_tax != "additional") {
        if (from_amount) {
            let amount = null;
            let tax_rate = null;
            let tax_field = null;
            if(concerned_tax != "_1" && concerned_tax != "_2") {
                amount = frm.get_field(concerned_tax + '_amount').value;
                tax_rate = frm.get_field(concerned_tax + '_rate').value;
                tax_field = concerned_tax + '_tax';
            } else {
                amount = frm.get_field('amount' + concerned_tax).value;
                tax_rate = frm.get_field('rate' +concerned_tax).value;
                tax_field = 'tax' + concerned_tax;
            }
            let new_tax = amount * tax_rate / 100;
            frm.get_field(tax_field).set_input(new_tax);
            //frm.set_value(tax, amount * (frm.doc[tax.replace('amount', 'rate')] / 100));
        } else {
            let tax = null;
            let tax_rate = null;
            let amount_field = null;
            if(concerned_tax != "_1" && concerned_tax != "_2") {
                tax = frm.get_field(concerned_tax + '_tax').value;
                tax_rate = frm.get_field(concerned_tax + '_rate').value;
                amount_field = concerned_tax + '_amount';
            } else {
                tax = frm.get_field('tax' + concerned_tax).value;
                tax_rate = frm.get_field('rate' + concerned_tax).value;
                amount_field = 'amount' + concerned_tax;
            }
            let new_amount = tax / (tax_rate / 100);
            frm.get_field(amount_field).set_input(new_amount);
        }
    }
    //frm.refresh_fields();
    let total_taxes = (frm.get_field("normal_tax").value || 0) + (frm.get_field("reduced_tax").value || 0) + (frm.get_field("lodging_tax").value || 0) + (frm.get_field("tax_1").value || 0) + (frm.get_field("tax_2").value || 0) + (frm.get_field("additional_tax").value || 0);
    frm.set_value('total_tax', total_taxes);
}

function update_tax_amounts(frm) {
    // effective tax: tax rate on net amount
    var normal_tax = frm.doc.normal_amount * (frm.doc.normal_rate / 100);
    var reduced_tax = frm.doc.reduced_amount * (frm.doc.reduced_rate / 100);
    var lodging_tax = frm.doc.lodging_amount * (frm.doc.lodging_rate / 100);
    // saldo tax: rate on gross amount
    var tax_1 = frm.doc.amount_1  * (frm.doc.rate_1 / 100);
    var tax_2 = frm.doc.amount_2 * (frm.doc.rate_2 / 100);
    var total_tax = normal_tax + reduced_tax + lodging_tax + tax_1 + tax_2 + frm.doc.additional_tax;
    frm.set_value('normal_tax', normal_tax);
    frm.set_value('reduced_tax', reduced_tax);
    frm.set_value('lodging_tax', lodging_tax);
    frm.set_value('tax_1', tax_1);
    frm.set_value('tax_2', tax_2);
    frm.set_value('total_tax', total_tax);
}

// add change handlers for deduction positions
frappe.ui.form.on("VAT Declaration", "tax_free_services", function(frm) { update_taxable_revenue(frm) } );
frappe.ui.form.on("VAT Declaration", "revenue_abroad", function(frm) { update_taxable_revenue(frm) } );
frappe.ui.form.on("VAT Declaration", "transfers", function(frm) { update_taxable_revenue(frm) } );
frappe.ui.form.on("VAT Declaration", "non-taxable_services", function(frm) { update_taxable_revenue(frm) } );
frappe.ui.form.on("VAT Declaration", "losses", function(frm) { update_taxable_revenue(frm) } );
frappe.ui.form.on("VAT Declaration", "misc", function(frm) { update_taxable_revenue(frm) } );

function update_taxable_revenue(frm) {
    var deductions =  frm.doc.tax_free_services +
        frm.doc.revenue_abroad +
        frm.doc.transfers + 
        frm.doc.non_taxable_services + 
        frm.doc.losses +
        frm.doc.misc;
    var taxable = frm.doc.total_revenue - frm.doc.non_taxable_revenue - deductions;
    frm.set_value('total_deductions', deductions);
    frm.set_value('taxable_revenue', taxable);
}

/* view: view to use
 * target: target field
 */
function get_total(frm, view, target) {
    // total revenues is the sum of all base grand totals in the period
    frappe.call({
        method: 'erpnextswiss.erpnextswiss.doctype.vat_declaration.vat_declaration.get_view_total',
        args: { 
            start_date: frm.doc.start_date,
            end_date: frm.doc.end_date,
            view_name: view,
            company: frm.doc.company
        },
        callback: function(r) {
            if (r.message) {
                frm.set_value(target, r.message.total);
            }
        }
    });
}

/* view: view to use
 * target: target field
 */
function get_tax(frm, view, target) {
    // total tax is the sum of all taxes in the period
    frappe.call({
        method: 'erpnextswiss.erpnextswiss.doctype.vat_declaration.vat_declaration.get_view_tax',
        args: { 
            start_date: frm.doc.start_date,
            end_date: frm.doc.end_date,
            view_name: view,
            company: frm.doc.company
        },
        callback: function(r) {
            if (r.message) {
                frm.set_value(target, r.message.total);
            }
        }
    }); 
}

// add change handlers for pretax
frappe.ui.form.on("VAT Declaration", "total_tax", function(frm) { update_payable_tax(frm) } );
frappe.ui.form.on("VAT Declaration", "pretax_material", function(frm) { update_payable_tax(frm) } );
frappe.ui.form.on("VAT Declaration", "pretax_investments", function(frm) { update_payable_tax(frm) } );
frappe.ui.form.on("VAT Declaration", "missing_pretax", function(frm) { update_payable_tax(frm) } );
frappe.ui.form.on("VAT Declaration", "pretax_correction_mixed", function(frm) { update_payable_tax(frm) } );
frappe.ui.form.on("VAT Declaration", "pretax_correction_other", function(frm) { update_payable_tax(frm) } );
        
function update_payable_tax(frm) {
    var pretax = frm.doc.pretax_material 
        + frm.doc.pretax_investments 
        + frm.doc.missing_pretax 
        - frm.doc.pretax_correction_mixed
        - frm.doc.pretax_correction_other
        + frm.doc.form_1050
        + frm.doc.form_1055;
    frm.set_value('total_pretax_reductions', pretax);
    var payable_tax = frm.doc.total_tax - pretax;
    if(payable_tax < 0) {
        frm.set_value('balance', Math.abs(payable_tax));
        frm.set_value('payable_tax', 0);
    } else if(payable_tax == 0) {
        frm.set_value('payable_tax', 0);
        frm.set_value('balance', 0);
    } else {
        frm.set_value('payable_tax', payable_tax);
        frm.set_value('balance', 0);
    }
}
