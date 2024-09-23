// Copyright (c) 2018-2023, libracore (https://www.libracore.com) and contributors
// For license information, please see license.txt

var allow_trigger = true;
frappe.ui.form.on('VAT Declaration', {
    refresh: function(frm) {
        if(frappe.user.name != "Administrator") {
            $('div[data-fieldname="section_break_tables"]').css('display', 'none');
        }
        update_tables(frm);

        const table_fields = ['si_details', 'no_vat_si_details', 'pi_details', 'no_vat_pi_details', 'je_details', 'pe_details'];
        table_fields.forEach(function(field) {
            $(frm.fields_dict[field].grid.wrapper).find('.btn-secondary').on('click', function() {
                update_tables(frm);
            });
        });
        
        frm.add_custom_button(__("Get values"), function()
        {
            get_values(frm);
            setTimeout(() => {

                table_fields.forEach(function(field) {
                    $(frm.fields_dict[field].grid.wrapper).find('.btn-secondary').on('click', function() {
                        update_tables(frm);
                    });
                });
            }, 500);
        });
        if (frm.doc.__islocal) {
            get_tax_rates(frm);
        }
        frm.set_df_property('purchase_invoice_summary', 'hidden', true);
        frm.set_df_property('sales_invoice_summary', 'hidden', true);
        frm.set_df_property('sales_invoice_summary_2023', 'hidden', true);
        frm.set_df_property('journal_entry_summary', 'hidden', true);
        frm.set_df_property('journal_entry_summary_2023', 'hidden', true);
        if(frm.doc.vat_type.includes("flat rate")) {
            frm.set_df_property('no_vat_summary_tab', 'hidden', true);
            frm.set_df_property('no_vat_si_details', 'hidden', true);
            frm.set_df_property('no_vat_pi_details', 'hidden', true);
        }
        /*frm.add_custom_button(__("Recalculate"), function()
        {
            recalculate(frm);
        });*/

        /*update_taxable_revenue(frm);
        update_tax_amounts(frm);
        update_payable_tax(frm);*/
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

            frm.set_value('title', title + " - " + (frm.doc.cmp_abbr || ""));
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
                frm.set_value("title", new_title.join(" - "));
            } else if (parts.length === 0) {
                // key missing
                frm.set_value("title", frm.doc.title + " - " + frm.doc.cmp_abbr);
            }

        }
    },
    end_date: function(frm) {
        if (frm.doc.end_date) {
            var endYear = new Date(frm.doc.end_date).getFullYear();
            if(endYear > 2023) new_vat_percent = true;
            else new_vat_percent = false;
        }
    },
    vat_type: function(frm) {
        if(frm.doc.vat_type.includes("flat rate")) {
            frm.set_df_property('no_vat_summary_tab', 'hidden', true);
            frm.set_df_property('no_vat_si_details', 'hidden', true);
            frm.set_df_property('no_vat_pi_details', 'hidden', true);
        } else {
            frm.set_df_property('no_vat_summary_tab', 'hidden', false);
            frm.set_df_property('no_vat_si_details', 'hidden', false);
            frm.set_df_property('no_vat_pi_details', 'hidden', false);
        }
    }
});

function update_tables(frm) {
    remove_columns(frm, 'si_details', ['payment_type', 'net_purchase', 'total_vat', 'total_net_sell', 'total_net_purchase'])
    remove_columns(frm, 'no_vat_si_details', ['payment_type', 'net_purchase', "debit", "credit", "against", 'total_vat', 'total_net_sell', 'total_net_purchase'])
    remove_columns(frm, 'pi_details', ['payment_type', 'net_sell', 'total_vat', 'total_net_sell', 'total_net_purchase'])
    remove_columns(frm, 'no_vat_pi_details', ['payment_type', 'net_sell', "debit", "credit", "against", 'total_vat', 'total_net_sell', 'total_net_purchase'])
    remove_columns(frm, 'je_details', ['payment_type', "paid_date", 'total_vat', 'total_net_sell', 'total_net_purchase'])
    remove_columns(frm, 'pe_details', ["paid_date", 'against_account', 'total_vat', 'total_net_sell', 'total_net_purchase'])
    remove_columns(frm, 'si_details_totals', ['posting_date', 'paid_date', 'voucher_no', 'remarks', 'payment_type', 'against', 'tax_rate', 'debit', 'credit', 'against_account', 'net_sell', 'net_purchase', 'total_net_purchase'])
    remove_columns(frm, 'pi_details_totals', ['posting_date', 'paid_date', 'voucher_no', 'remarks', 'payment_type', 'against', 'debit', 'credit', 'against_account', 'net_sell', 'net_purchase', 'total_net_sell'])
    remove_columns(frm, 'je_details_totals', ['posting_date', 'paid_date', 'voucher_no', 'remarks', 'payment_type', 'against', 'debit', 'credit', 'against_account', 'net_sell', 'net_purchase'])
    remove_columns(frm, 'pe_details_totals', ['posting_date', 'paid_date', 'voucher_no', 'remarks', 'payment_type', 'against', 'tax_rate', 'debit', 'credit', 'against_account', 'net_sell', 'net_purchase'])
    $('.form-clickable-section').css('display', 'inherit')
    $('.form-grid .with-filter').removeClass('with-filter')
    $('.form-grid .filter-row').remove()
    frm.refresh_field('pdf_tables')
}

function remove_columns(frm, tablename, fields) {
    let columns_count = frm.fields_dict[tablename].grid.visible_columns.length - fields.length
    console.log(columns_count)
    let width_percent = 100 / columns_count
    let width_px = 40 / columns_count
    columns_labels = ""
    columns_names = ""
    //setTimeout(() => {
    frm.fields_dict[tablename].grid.visible_columns = frm.fields_dict[tablename].grid.visible_columns.filter(function (cn) {
        return !fields.includes(cn.fieldname);
    });

    frm.fields_dict[tablename].grid.wrapper.find('.col-xs-1').each((key, element) => {
        $(element).removeClass('col-xs-1')
        $(element).css('width', 'calc(' + width_percent.toString() + '% - ' + width_px.toString() + 'px)')
    })
    frm.fields_dict[tablename].grid.wrapper.find('.sortable-handle').each((key, element) => {
        $(element).addClass('grid-static-col')
        $(element).css('width', '40px' )
    })
    if(tablename.includes("totals")){
        frm.fields_dict[tablename].grid.wrapper.find("[data-fieldname=tax_code], [data-fieldname=tax_rate]").each((key, elem) => {
            if(["0", "0.000"].includes($(elem).find(".static-area div").html())){
                $(elem).find(".static-area div").html("")
            }
        })
    }
    fields.forEach((field) => {
        frm.fields_dict[tablename].grid.wrapper.find('.grid-static-col[data-fieldname='+field+']').each((key, element) => {
            $(element).remove()
        })
    })
    cur_frm.fields_dict[tablename].grid.wrapper.find('.grid-heading-row .grid-static-col').each((key, element) => {
        if(element.title)
            columns_labels += element.title + ","

        if(element.dataset.fieldname)
            columns_names += element.dataset.fieldname + ","
    })
    columns_labels = columns_labels.slice(0, -1).replace(__("Posting Date"), __("Date")).replace(__("Paid Date"), __("Paid")).replace(__("Voucher No"), __("Reference")).replace(__("Tax Code"), __("Code")).replace(__("Tax Rate"), __("Tax")).replace(__("Payment Type"), __("Type"))
    columns_names = columns_names.slice(0, -1)
    let exists = false
    if(frm.doc.pdf_tables){
        frm.doc.pdf_tables.forEach((table) => {
            if(table.table_name == tablename){
                frappe.model.set_value(table.doctype, table.name, 'columns', columns_labels + '|' + columns_names)
                exists = true
            }
        })
    }
    if(!exists){
        let child = cur_frm.add_child('pdf_tables')
        frappe.model.set_value(child.doctype, child.name, 'table_name', tablename)
        frappe.model.set_value(child.doctype, child.name, 'columns', columns_labels + '|' + columns_names)
    }
    //}, 500);
}

var new_vat_percent = false;
function get_tax_rates(frm) {
    //console.log("get tax rates")
    frappe.db.get_value("Account", {"tax_code": "302", "company": frm.doc.company}, "tax_rate").then((r) => {
        frm.doc.normal_rate_2023 = r.message.tax_rate;
        frm.refresh_field("normal_rate_2023");
    });
    frappe.db.get_value("Account", {"tax_code": "312", "company": frm.doc.company}, "tax_rate").then((r) => {
        frm.doc.reduced_rate_2023 = r.message.tax_rate;
        frm.refresh_field("reduced_rate_2023");
    });
    frappe.db.get_value("Account", {"tax_code": "342", "company": frm.doc.company}, "tax_rate").then((r) => {
        frm.doc.lodging_rate_2023 = r.message.tax_rate;
        frm.refresh_field("lodging_rate_2023");
    });

    frappe.db.get_value("Account", {"tax_code": "303", "company": frm.doc.company}, "tax_rate").then((r) => {
        frm.doc.normal_rate = r.message.tax_rate;
        frm.refresh_field("normal_rate");
    });
    frappe.db.get_value("Account", {"tax_code": "313", "company": frm.doc.company}, "tax_rate").then((r) => {
        frm.doc.reduced_rate = r.message.tax_rate;
        frm.refresh_field("reduced_rate");
    });
    frappe.db.get_value("Account", {"tax_code": "343", "company": frm.doc.company}, "tax_rate").then((r) => {
        frm.doc.lodging_rate = r.message.tax_rate;
        frm.refresh_field("lodging_rate");
    });
}
// retrieve values from database
function get_values(frm) {
    let method = ''
    if(frm.doc.vat_type == "effective - agreed counterclaims" || frm.doc.vat_type == "flat rate - agreed counterclaims") {
        method = 'erpnextswiss.erpnextswiss.doctype.vat_declaration.vat_declaration.get_total_invoiced'
    } else {
        method = 'erpnextswiss.erpnextswiss.doctype.vat_declaration.vat_declaration.get_total_payments'
    }
    frm.trigger('clear_all_except_four').then(() => {
        frappe.call({
            method: method,
            args: {
                start_date: frm.doc.start_date,
                end_date: frm.doc.end_date,
                company: frm.doc.company,
                flat: frm.doc.vat_type.includes("flat rate")
            },
            freeze: true,
            callback: function (r) {
                if (r.message) {
                    allow_trigger = false;
                    let res = r.message;
                    console.log(res);

                    /*frm.set_value('purchase_invoice_summary', res.summary_purchase_invoice)
                    frm.set_value('sales_invoice_summary', res.summary_sales_invoice_new)
                    frm.set_value('sales_invoice_summary_2023', res.summary_sales_invoice_old)
                    frm.set_value('journal_entry_summary', res.summary_journal_entry_new)
                    frm.set_value('journal_entry_summary_2023', res.summary_journal_entry_old)*/
                    frm.set_value('si_details', res.si_gl_entries);
                    frm.set_value('pi_details', res.pi_gl_entries);
                    frm.set_value('je_details', res.je_gl_entries);
                    frm.set_value('pe_details', res.pe_gl_entries);
                    if(!frm.doc.vat_type.includes("flat rate")) {
                        frm.set_value('no_vat_si_details', res.no_vat_si_entries);
                        frm.set_value('no_vat_pi_details', res.no_vat_pi_entries);
                        frm.set_value('si_details_totals', res.si_vat_summary);
                        frm.set_value('pi_details_totals', res.pi_vat_summary);
                        frm.set_value('je_details_totals', res.je_vat_summary);
                        frm.set_value('pe_details_totals', res.pe_vat_summary);
                        frm.set_value('no_vat_summary', res.summary_no_vat)
                    }
                    
                    let total = (res.net_sell.total_credit - res.net_sell.total_debit + (res.no_vat_sell.total_debit - res.no_vat_sell.total_credit));// - (res.net_purchase.total_debit - res.net_purchase.total_credit);
                    frm.set_value('total_revenue', total);
                    // get_total(frm, "viewVAT_205", 'non_taxable_revenue');
                    // Deductions
                    /*frm.set_value(frm, "viewVAT_220", 'tax_free_services',);
                    frm.set_value(frm, "viewVAT_221", 'revenue_abroad',);
                    frm.set_value(frm, "viewVAT_225", 'transfers',);
                    frm.set_value(frm, "viewVAT_230", 'non_taxable_services',);
                    frm.set_value(frm, "viewVAT_235", 'losses',);*/
                    // Tax calculation
                    frm.set_value("tax_free_services", 0);
                    frm.set_value("revenue_abroad", 0);
                    frm.set_value("transfers", 0);
                    frm.set_value("non_taxable_services", 0);
                    frm.set_value("losses", 0);
                    frm.set_value("misc", 0);
                    frm.set_value("additional_amount_2023", 0);
                    frm.set_value("additional_tax_2023", 0);
                    frm.set_value("additional_amount", 0);
                    frm.set_value("additional_tax", 0);
                    frm.set_value("grants", 0);
                    frm.set_value("donations", 0);
                    if (frm.doc.vat_type.includes("effective")) {
                        frm.set_value('non_taxable_revenue', res.no_vat_sell.total_debit - res.no_vat_sell.total_credit);
                        let normal_tax_2023 = res.sums_by_tax_code['302'] ? (res.sums_by_tax_code['302'].total_credit - res.sums_by_tax_code['302'].total_debit) : 0;
                        let normal_rate_2023 = frm.doc.normal_rate_2023;
                        let reduced_tax_2023 = res.sums_by_tax_code['312'] ? (res.sums_by_tax_code['312'].total_credit - res.sums_by_tax_code['312'].total_debit) : 0;
                        let reduced_rate_2023 = frm.doc.reduced_rate_2023;
                        let lodging_tax_2023 = res.sums_by_tax_code['342'] ? (res.sums_by_tax_code['342'].total_credit - res.sums_by_tax_code['342'].total_debit) : 0;
                        let lodging_rate_2023 = frm.doc.lodging_rate_2023;
                        let normal_tax = res.sums_by_tax_code['303'] ? (res.sums_by_tax_code['303'].total_credit - res.sums_by_tax_code['303'].total_debit) : 0;
                        let normal_rate = frm.doc.normal_rate;
                        let reduced_tax = res.sums_by_tax_code['313'] ? (res.sums_by_tax_code['313'].total_credit - res.sums_by_tax_code['313'].total_debit) : 0;
                        let reduced_rate = frm.doc.reduced_rate;
                        let lodging_tax = res.sums_by_tax_code['343'] ? (res.sums_by_tax_code['343'].total_credit - res.sums_by_tax_code['343'].total_debit) : 0;
                        let lodging_rate = frm.doc.lodging_rate;
                        frm.set_value('normal_tax_2023', normal_tax_2023);
                        frm.set_value('normal_amount_2023', normal_tax_2023 / (normal_rate_2023 / 100));
                        frm.set_value('reduced_tax_2023', reduced_tax_2023);
                        frm.set_value('reduced_amount_2023', reduced_tax_2023 / (reduced_rate_2023 / 100));
                        frm.set_value('lodging_tax_2023', lodging_tax_2023);
                        frm.set_value('lodging_amount_2023', lodging_tax_2023 / (lodging_rate_2023 / 100));

                        frm.set_value('normal_tax', normal_tax);
                        frm.set_value('normal_amount', normal_tax / (normal_rate / 100));
                        frm.set_value('reduced_tax', reduced_tax);
                        frm.set_value('reduced_amount', reduced_tax / (reduced_rate / 100));
                        frm.set_value('lodging_tax', lodging_tax);
                        frm.set_value('lodging_amount', lodging_tax / (lodging_rate / 100));

                        //console.log(res.sums_by_tax_code['302'], res.sums_by_tax_code['312'], res.sums_by_tax_code['342'])
                        //console.log(res.sums_by_tax_code['302'].total_credit, res.sums_by_tax_code['302'].total_debit, res.sums_by_tax_code['302'].total_credit - res.sums_by_tax_code['302'].total_debit)
                        frm.set_value('total_tax', normal_tax_2023 + reduced_tax_2023 + lodging_tax_2023 + normal_tax + reduced_tax + lodging_tax);
                        // Pretaxes
                        frm.set_value('pretax_material', res.sums_by_tax_code['400'] ? (res.sums_by_tax_code['400'].total_debit - res.sums_by_tax_code['400'].total_credit) : 0);
                        frm.set_value('pretax_investments', res.sums_by_tax_code['405'] ? (res.sums_by_tax_code['405'].total_debit - res.sums_by_tax_code['405'].total_credit) : 0);
                        frm.set_value('missing_pretax', res.sums_by_tax_code['410'] ? (res.sums_by_tax_code['410'].total_debit - res.sums_by_tax_code['410'].total_credit) : 0);
                        frm.set_value('pretax_correction_mixed', res.sums_by_tax_code['415'] ? (res.sums_by_tax_code['415'].total_debit - res.sums_by_tax_code['415'].total_credit) : 0);
                        frm.set_value('pretax_correction_other', res.sums_by_tax_code['420'] ? (res.sums_by_tax_code['420'].total_debit - res.sums_by_tax_code['420'].total_credit) : 0);
                    } else {
                        /*let sell_vat = {};
                        let purchase_vat = {};
                        sell_vat['credit'] = 0;
                        sell_vat['debit'] = 0;
                        purchase_vat['credit'] = 0;
                        purchase_vat['debit'] = 0;
                        Object.keys(res.sums_by_tax_code).forEach(function(key) {
                            if(parseInt(key) >= 300 && parseInt(key) < 400) {
                                sell_vat['credit'] += res.sums_by_tax_code[key].total_credit;
                                sell_vat['debit'] += res.sums_by_tax_code[key].total_debit;
                            }
                            if(parseInt(key) >= 400 && parseInt(key) < 500) {
                                purchase_vat['credit'] += res.sums_by_tax_code[key].total_credit;
                                purchase_vat['debit'] += res.sums_by_tax_code[key].total_debit;
                            }
                        });*/
                        frm.set_value('rate_2_2023', 0);
                        frm.set_value('amount_2_2023', 0);
                        frm.set_value('rate_2', 0);
                        frm.set_value('amount_2', 0);
                        if (new_vat_percent) {
                            frm.set_value('amount_1_2023', 0);
                            frm.set_value('amount_1', total);
                        } else {
                            frm.set_value('amount_1_2023', total);
                            frm.set_value('amount_1', 0);
                        }

                        //frm.set_value(frm, "viewVAT_322", 'amount_1',);
                        //frm.set_value(frm, "viewVAT_332", 'amount_2',);
                    }
                    //frm.refresh_fields();
                    setTimeout(function () {
                        update_taxable_revenue(frm);
                        update_payable_tax(frm);
                        update_taxable_revenue(frm);
                        update_tables(frm);
                    }, 200);
                    setTimeout(function () {
                        allow_trigger = true;
                    }, 5000);
                }
            }
        });
    });
}

// force recalculate
function recalculate(frm) {
    update_taxable_revenue(frm);
    update_tax_amounts(frm);
    update_payable_tax(frm);
    update_taxable_revenue(frm);
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

frappe.ui.form.on("VAT Declaration", "normal_amount_2023", function(frm) { update_tax_or_amount(frm, "normal", true) } );
frappe.ui.form.on("VAT Declaration", "normal_rate_2023", function(frm) { update_tax_or_amount(frm, "normal", true) } );
frappe.ui.form.on("VAT Declaration", "normal_tax_2023", function(frm) { update_tax_or_amount(frm, "normal", false) } );
frappe.ui.form.on("VAT Declaration", "reduced_amount_2023", function(frm) { update_tax_or_amount(frm, "reduced", true) } );
frappe.ui.form.on("VAT Declaration", "reduced_rate_2023", function(frm) { update_tax_or_amount(frm, "reduced", true) } );
frappe.ui.form.on("VAT Declaration", "reduced_tax_2023", function(frm) { update_tax_or_amount(frm, "reduced", false) } );
frappe.ui.form.on("VAT Declaration", "lodging_amount_2023", function(frm) { update_tax_or_amount(frm, "lodging", true) } );
frappe.ui.form.on("VAT Declaration", "lodging_rate_2023", function(frm) { update_tax_or_amount(frm, "lodging", true) } );
frappe.ui.form.on("VAT Declaration", "lodging_tax_2023", function(frm) { update_tax_or_amount(frm, "lodging", false) } );
frappe.ui.form.on("VAT Declaration", "additional_amoun_2023t", function(frm) { update_tax_or_amount(frm, "additional", true) } );
frappe.ui.form.on("VAT Declaration", "additional_tax_2023", function(frm) { update_tax_or_amount(frm, "additional", false) } );
frappe.ui.form.on("VAT Declaration", "amount_1_2023", function(frm) { update_tax_or_amount(frm, "_1", true) } );
frappe.ui.form.on("VAT Declaration", "rate_1_2023", function(frm) { update_tax_or_amount(frm, "_1", true) } );
frappe.ui.form.on("VAT Declaration", "tax_1_2023", function(frm) { update_tax_or_amount(frm, "_1", false) } );
frappe.ui.form.on("VAT Declaration", "amount_2_2023", function(frm) { update_tax_or_amount(frm, "_2", true) } );
frappe.ui.form.on("VAT Declaration", "rate_2_2023", function(frm) { update_tax_or_amount(frm, "_2", true) } );
frappe.ui.form.on("VAT Declaration", "tax_2_2023", function(frm) { update_tax_or_amount(frm, "_2", false) } );

function update_tax_or_amount(frm, concerned_tax, from_amount=false) {
    if(allow_trigger) {
        setTimeout(function () {
            if (concerned_tax != "additional") {
                if (from_amount) {
                    let amount_2023 = null;
                    let tax_rate_2023 = null;
                    let tax_field_2023 = null;
                    let amount = null;
                    let tax_rate = null;
                    let tax_field = null;
                    if (concerned_tax != "_1" && concerned_tax != "_2") {
                        amount_2023 = frm.get_field(concerned_tax + '_amount_2023').value;
                        tax_rate_2023 = frm.get_field(concerned_tax + '_rate_2023').value;
                        tax_field_2023 = concerned_tax + '_tax_2023';

                        amount = frm.get_field(concerned_tax + '_amount').value;
                        tax_rate = frm.get_field(concerned_tax + '_rate').value;
                        tax_field = concerned_tax + '_tax';
                    } else {
                        amount_2023 = frm.get_field('amount' + concerned_tax + '_2023').value;
                        tax_rate_2023 = frm.get_field('rate' + concerned_tax + '_2023').value;
                        tax_field_2023 = 'tax' + concerned_tax + '_2023';

                        amount = frm.get_field('amount' + concerned_tax).value;
                        tax_rate = frm.get_field('rate' + concerned_tax).value;
                        tax_field = 'tax' + concerned_tax;
                    }
                    let new_tax_2023 = amount_2023 * tax_rate_2023 / 100;
                    let new_tax = amount * tax_rate / 100;
                    //frm.get_field(tax_field).set_input(new_tax);
                    //frm.set_value(tax, amount * (frm.doc[tax.replace('amount', 'rate')] / 100));
                    frappe.model.set_value(frm.doctype, frm.docname, tax_field_2023, new_tax_2023);
                    frm.doc.tax_field_2023 = new_tax_2023;
                    frappe.model.set_value(frm.doctype, frm.docname, tax_field, new_tax);
                    frm.doc.tax_field = new_tax;
                } else {
                    let tax_2023 = null;
                    let tax_rate_2023 = null;
                    let amount_field_2023 = null;
                    let tax = null;
                    let tax_rate = null;
                    let amount_field = null;
                    if (concerned_tax != "_1" && concerned_tax != "_2") {
                        tax_2023 = frm.get_field(concerned_tax + '_tax_2023').value;
                        tax_rate_2023 = frm.get_field(concerned_tax + '_rate_2023').value;
                        amount_field_2023 = concerned_tax + '_amount_2023';

                        tax = frm.get_field(concerned_tax + '_tax').value;
                        tax_rate = frm.get_field(concerned_tax + '_rate').value;
                        amount_field = concerned_tax + '_amount';
                    } else {
                        tax_2023 = frm.get_field('tax' + concerned_tax + '_2023').value;
                        tax_rate_2023 = frm.get_field('rate' + concerned_tax + '_2023').value;
                        amount_field_2023 = 'amount' + concerned_tax + '_2023';

                        tax = frm.get_field('tax' + concerned_tax).value;
                        tax_rate = frm.get_field('rate' + concerned_tax).value;
                        amount_field = 'amount' + concerned_tax;
                    }
                    let new_amount_2023 = tax_2023 / (tax_rate_2023 / 100);
                    let new_amount = tax / (tax_rate / 100);
                    //frm.get_field(amount_field).set_input(flt(new_amount));
                    if(!isNaN(new_amount_2023)) {
                        frappe.model.set_value(frm.doctype, frm.docname, amount_field_2023, new_amount_2023);
                    }
                    if(!isNaN(new_amount)) {
                        frappe.model.set_value(frm.doctype, frm.docname, amount_field, new_amount);
                    }
                }
            }
            //frm.refresh_fields();
            let total_taxes = 0
            if (frm.doc.vat_type.includes("flat rate")) {
                total_taxes = (frm.get_field("tax_1_2023").value || 0) + (frm.get_field("tax_2_2023").value || 0) + (frm.get_field("additional_tax_2023").value || 0);
                total_taxes += (frm.get_field("tax_1").value || 0) + (frm.get_field("tax_2").value || 0) + (frm.get_field("additional_tax").value || 0);
            } else {
                total_taxes = (frm.get_field("normal_tax_2023").value || 0) + (frm.get_field("reduced_tax_2023").value || 0) + (frm.get_field("lodging_tax_2023").value || 0) + (frm.get_field("additional_tax_2023").value || 0);
                total_taxes += (frm.get_field("normal_tax").value || 0) + (frm.get_field("reduced_tax").value || 0) + (frm.get_field("lodging_tax").value || 0) + (frm.get_field("additional_tax").value || 0);
            }
            frm.set_value('total_tax', total_taxes);
            frm.doc.total_tax = total_taxes;
            frm.refresh_fields()
        }, 400);
    }
}

function update_tax_amounts(frm) {
    // effective tax: tax rate on net amount
    var normal_tax_2023 = frm.doc.normal_amount_2023 * (frm.doc.normal_rate_2023 / 100);
    var reduced_tax_2023 = frm.doc.reduced_amount_2023 * (frm.doc.reduced_rate_2023 / 100);
    var lodging_tax_2023 = frm.doc.lodging_amount_2023 * (frm.doc.lodging_rate_2023 / 100);
    var normal_tax = frm.doc.normal_amount * (frm.doc.normal_rate / 100);
    var reduced_tax = frm.doc.reduced_amount * (frm.doc.reduced_rate / 100);
    var lodging_tax = frm.doc.lodging_amount * (frm.doc.lodging_rate / 100);
    // saldo tax: rate on gross amount
    var tax_1_2023 = frm.doc.amount_1_2023  * (frm.doc.rate_1_2023 / 100);
    var tax_2_2023 = frm.doc.amount_2_2023 * (frm.doc.rate_2_2023 / 100);
    var tax_1 = frm.doc.amount_1  * (frm.doc.rate_1 / 100);
    var tax_2 = frm.doc.amount_2 * (frm.doc.rate_2 / 100);
    var total_tax = 0;
    if(frm.doc.vat_type.includes("flat rate")) {
        total_taxes = tax_1_2023 + tax_2_2023 + frm.doc.additional_tax_2023 + tax_1 + tax_2 + frm.doc.additional_tax;
    } else {
        total_tax = normal_tax_2023 + reduced_tax_2023 + lodging_tax_2023 + frm.doc.additional_tax_2023 + normal_tax + reduced_tax + lodging_tax + frm.doc.additional_tax;
    }
    frm.set_value('normal_tax_2023', normal_tax_2023);
    frm.set_value('reduced_tax_2023', reduced_tax_2023);
    frm.set_value('lodging_tax_2023', lodging_tax_2023);
    frm.set_value('tax_1_2023', tax_1_2023);
    frm.set_value('tax_2_2023', tax_2_2023);
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
frappe.ui.form.on("VAT Declaration", "non_taxable_services", function(frm) { update_taxable_revenue(frm) } );
frappe.ui.form.on("VAT Declaration", "losses", function(frm) { update_taxable_revenue(frm) } );
frappe.ui.form.on("VAT Declaration", "misc", function(frm) { update_taxable_revenue(frm) } );

function update_taxable_revenue(frm) {
    //console.log("update taxable revenue")
    var deductions = (frm.get_field("tax_free_services").value || 0) +
        (frm.get_field("revenue_abroad").value || 0) +
        (frm.get_field("transfers").value || 0) +
        (frm.get_field("non_taxable_services").value || 0) +
        (frm.get_field("losses").value || 0) +
        (frm.get_field("misc").value || 0);
    //console.log(deductions, frm.get_field("total_revenue").value || 0, frm.get_field("non_taxable_revenue").value || 0);
    var taxable = (frm.get_field("total_revenue").value || 0) - (frm.get_field("non_taxable_revenue").value || 0) - deductions;
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
    var pretax = (frm.get_field("pretax_material").value || 0)
        + (frm.get_field("pretax_investments").value || 0)
        + (frm.get_field("missing_pretax").value || 0)
        - (frm.get_field("pretax_correction_mixed").value || 0)
        - (frm.get_field("pretax_correction_other").value || 0)
        + (frm.get_field("form_1050").value || 0)
        + (frm.get_field("form_1055").value || 0);
    frm.set_value('total_pretax_reductions', pretax);
    var payable_tax = frm.doc.total_tax - pretax;
    if (payable_tax < 0) {
        frm.set_value('balance', Math.abs(payable_tax));
        frm.set_value('payable_tax', 0);
    } else if (payable_tax == 0) {
        frm.set_value('payable_tax', 0);
        frm.set_value('balance', 0);
    } else {
        frm.set_value('payable_tax', payable_tax);
        frm.set_value('balance', 0);
    }
}

frappe.ui.form.on('VAT Declaration', {
    clear_all_except_four: function(frm) {
        return new Promise((resolve) => {
            ///var fields_to_keep = ['company', 'start_date', 'end_date', 'vat_type', 'rate_1', 'rate_2', 'normal_rate', 'reduced_rate', 'lodging_rate'];

            $.each(frm.fields_dict, function(fieldname, field) {
                if (['Currency', 'Table', 'Float'].includes(field.df.fieldtype)) { // If fieldname is not in the fields_to_keep list
                    frm.set_value(fieldname, 0);
                } else if(field.df.fieldtype == 'Table') {
                    frm.set_value(fieldname, null);
                }
            });
            resolve();
        });
    }
});

function download_transfer_file(frm) {
    frappe.call({
        'method': 'create_transfer_file',
        'doc': frm.doc,
        'callback': function(r) {
            if (r.message) {
                // prepare the xml file for download
                download("estv.xml", r.message.content);
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
