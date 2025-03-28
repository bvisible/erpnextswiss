frappe.ui.form.on('Purchase Invoice', {
    refresh(frm) {
        if (frm.doc.__islocal||cur_frm.doc.docstatus == '0') {
            frm.add_custom_button(__("Scan Invoice"), function() {
                check_defaults(frm);
            });
        }
        if (frm.doc.__islocal) {
            frm.set_value("set_posting_time", 1);
            pull_supplier_defaults(frm);
        }
        if ((frm.doc.docstatus === 1) && (frm.doc.is_proposed === 1)) {
            cur_frm.dashboard.add_comment(__('This document has been transmitted to the bank for payment'), 'blue', true);
        }
        if(!cur_frm.doc.supplier){
            let d = new frappe.ui.Dialog({
                title: 'New Purchase Invoice',
                fields: [
                    {
                        label: 'Scan QR invoice',
                        fieldname: 'btn_scan_dialog',
                        fieldtype: 'Button',
                        click: () => {
                            check_defaults(frm);
                            d.hide();
                        }
                    },
                    {
                        label: 'Supplier',
                        fieldname: 'supplier',
                        fieldtype: 'Link',
                        options: 'Supplier',
                        reqd: 1
                    }
                ],
                primary_action_label: __('Choose'),
                primary_action(values) {
                    //console.log(values.customer);
                    cur_frm.set_value("supplier",values.supplier);
                    $('html,body').animate({scrollTop: $('[data-fieldname="scan_barcode"]').offset().top});
                    d.hide();
                }
            });
            d.show();
        }
    },
    validate: function(frm) {
        if (frm.doc.payment_type == "ESR") {
            if (frm.doc.esr_reference_number) {
                if ((!frm.doc.esr_reference_number.startsWith("RF")) && (!check_esr(frm.doc.esr_reference_number))) {
                    frappe.msgprint( __("ESR code not valid") ); 
                    frappe.validated=false;
                } 
            } else {
                frappe.msgprint( __("ESR code missing") ); 
                frappe.validated=false;
            }
        }

        if ((frm.doc.supplier) && (frm.doc.bill_no)) {
            frappe.call({
                'method': "frappe.client.get_list",
                'args': {
                    'doctype': "Purchase Invoice",
                    'filters': [
                        ['supplier', '=', frm.doc.supplier],
                        ['bill_no', '=', frm.doc.bill_no],
                        ['docstatus', '<', 2]
                    ],
                    'fields': ['name'],
                    'async': false
                },
                'callback': function(r) {
                    r.message.forEach(function(pinv) { 
                        if (pinv.name != frm.doc.name) {
                            frappe.msgprint(  __("This invoice is already recorded in") + " " + pinv.name );
                            frappe.validated=false;
                        }
                    });
                }
            });     
        }
    },
    supplier: function(frm) {
        pull_supplier_defaults(frm);
    }
});

function check_defaults(frm) {
    frappe.call({
        'method': "erpnextswiss.scripts.esr_qr_tools.check_defaults",
        'callback': function(response) {
            if (response.message.error) {
                frappe.msgprint(response.message.error);
            } else {
                var default_settings = response.message;
                scan_invoice_code(frm, default_settings);
            }
        }
    });
}

function scan_invoice_code(frm, default_settings) {
    var scan_invoice_txt = __("Scan Invoice");
    frappe.prompt([
        {'fieldname': 'code_scan', 'fieldtype': 'Small Text', 'label': __('Code'), 'reqd': 1}
    ],
    function(values){
        //console.log(values.code_scan);
        //check_scan_input(frm, default_settings, values.code_scan);
        frappe.call({
            'method': "neoffice_theme.events.check_qr_invoice",
            'args': {
                'code_scan': values.code_scan
            }
        }).then(r => {
            console.log(r.message);
            if(r.message == "Error reading this QR Code"){
                frappe.msgprint( __("Error reading this QR Codethis QR Code has a structural problem. It is impossible to extract the information.") ); 
                frappe.validated=false;
            }
            let [qr_type, amount, reference, participant, supplier_name, address, street_number, zip_code, city, country, supplier_exists] = r.message.split('|');
            show_esr_detail_dialog(frm, participant, reference, amount, default_settings, supplier_name, [], address, street_number, zip_code, city, country, supplier_name, qr_type, supplier_exists=="True");
        })
    },
    scan_invoice_txt,
    __('OK')
    )
    ////
    setTimeout(() => {
        cur_dialog.$wrapper.find(".control-input").append(
            `<span class="link-btn">
                <a class="btn-open no-decoration" style="position: absolute; right: 5px; top: 25px;" title="${__("Scan")}">
                    ${frappe.utils.icon("scan", "sm")}
                </a>
            </span>`
        );
        cur_dialog.$scan_btn = cur_dialog.$wrapper.find(".link-btn");
        cur_dialog.$scan_btn.toggle(true);
        const me = cur_dialog.fields_dict.code_scan;
        cur_dialog.$scan_btn.on("click", "a", () => {
            new frappe.ui.Scanner({
                dialog: true,
                multiple: false,
                on_scan(data) {
                    if (data && data.result && data.result.text) {
                        me.set_value(data.result.text);
                    }
                },
            });
        });
    }, 1000);
    ////
}

function check_scan_input(frm, default_settings, code_scan) {
    // ESR section
    var regex_9_27 = /[0-9]{13}[>][0-9]{27}[+][ ][0-9]{9}[>]/g; // 0100003949753>120000000000234478943216899+ 010001628>
    var regex_9_27p = /[0-9]{3}[>][0-9]{27}[+][ ][0-9]{9}[>]/g; // 042>120000000000234478943216899+ 010001628>
    var regex_9_16 = /[0-9]{13}[>][0-9]{16}[+][ ][0-9]{9}[>]/g; // 0100003949753>3804137405061016+ 010001628>
    var regex_9_16p = /[0-9]{3}[>][0-9]{16}[+][ ][0-9]{9}[>]/g; // 042>3804137405061016+ 010001628>
    var regex_5_15 = /[<][0-9]{15}[>][0-9]{15}[+][ ][0-9]{5}[>]/g; // <010001000017720>000013230243627+ 73723>
    var regex_5_15p = /[0-9]{15}[+][ ][0-9]{5}[>]/g; // 000013230243627+ 73723>
    if (regex_9_27.test(code_scan) === true){
        var occupancy = code_scan.split(">")[0].substring(0,2); // Belegart; z.B. 01
        var amount_int = parseInt(code_scan.split(">")[0].substring(2,10));
        var amount_dec = parseInt(code_scan.split(">")[0].substring(10,12));
        var amount = String(amount_int) + "." + String(amount_dec).padStart(2,'0'); // Betrag in CHF; z.B. 3949.75
        var reference = code_scan.split(">")[1].substring(0,27); // ESR-Referenznummer; z.B. 120000000000234478943216899
        var participant = code_scan.split("+ ")[1].substring(0,9); // ESR-Teilnehmer; z.B. 010001628
        get_data_based_on_esr(frm, participant, reference, amount, default_settings);
    } else if (regex_9_27p.test(code_scan) === true){
        var occupancy = code_scan.split(">")[0].substring(0,2); // Belegart; z.B. 01
        var amount = "0.0";
        var reference = code_scan.split(">")[1].substring(0,27); // ESR-Referenznummer; z.B. 120000000000234478943216899
        var participant = code_scan.split("+ ")[1].substring(0,9); // ESR-Teilnehmer; z.B. 010001628
        get_data_based_on_esr(frm, participant, reference, amount, default_settings);
    } else if (regex_9_16.test(code_scan) === true){
        var occupancy = code_scan.split(">")[0].substring(0,2); // Belegart; z.B. 01
        var amount_int = parseInt(code_scan.split(">")[0].substring(2,10));
        var amount_dec = parseInt(code_scan.split(">")[0].substring(10,12));
        var amount = String(amount_int) + "." + String(amount_dec).padStart(2,'0'); // Betrag in CHF; z.B. 3949.75
        var reference = code_scan.split(">")[1].substring(0,16); // ESR-Referenznummer; z.B. 3804137405061016
        var participant = code_scan.split("+ ")[1].substring(0,9); // ESR-Teilnehmer; z.B. 010001628
        get_data_based_on_esr(frm, participant, reference, amount, default_settings);
    } else if (regex_9_16p.test(code_scan) === true){
        var occupancy = code_scan.split(">")[0].substring(0,2); // Belegart; z.B. 01
        var amount = "0.0";
        var reference = code_scan.split(">")[1].substring(0,16); // ESR-Referenznummer; z.B. 3804137405061016
        var participant = code_scan.split("+ ")[1].substring(0,9); // ESR-Teilnehmer; z.B. 010001628
        get_data_based_on_esr(frm, participant, reference, amount, default_settings);
    } else if (regex_5_15.test(code_scan) === true){
        var occupancy = code_scan.split(">")[0].substring(1,3); // Belegart; z.B. 01
        var amount_int = parseInt(code_scan.split(">")[0].substring(7,13));
        var amount_dec = parseInt(code_scan.split(">")[0].substring(14,16));
        var amount = String(amount_int) + "." + String(amount_dec).padStart(2,'0'); // Betrag in CHF; z.B. 3949.75
        var reference = code_scan.split(">")[1].substring(0,15); // ESR-Referenznummer; z.B. 3804137405061016
        var participant = code_scan.split("+ ")[1].substring(0,5); // ESR-Teilnehmer; z.B. 010001628
        get_data_based_on_esr(frm, participant, reference, amount, default_settings);
    } else if (regex_5_15p.test(code_scan) === true){
        var occupancy = "00";
        var amount = "0.0";
        var reference = code_scan.split(">")[0].substring(0,15); // ESR-Referenznummer; z.B. 3804137405061016
        var participant = code_scan.split("+ ")[1].substring(0,5); // ESR-Teilnehmer; z.B. 010001628
        get_data_based_on_esr(frm, participant, reference, amount, default_settings);
    } else {
        // QR Section 
        var lines = code_scan.split("\n");      // separate lines
        //console.log(lines);
        if (lines.length < 28) {
            var invalid_esr_code_line = __("Invalid ESR Code Line or QR-Code");
            frappe.msgprint(invalid_esr_code_line);
        } else {
            var amount = parseFloat(lines[18]);
            var qr_type = lines[27].replace("\r","").replace("\n","");
            var reference = lines[28].replace("\r","").replace("\n","");
            var participant = lines[3].replace("\r","").replace("\n","");
            var supplier_name = lines[5].replace("\r","").replace("\n","");
            var address = lines[6].replace("\r","").replace("\n","");
            var address_number = address.replace(/\D/g, "");
            // if address as number
            if(address_number.length > 0){
                var street_number = address_number;
                var zip = lines[7].replace(/\D/g, "");
                var zip_number = zip.replace(/\D/g, "");
                // if zip is only number
                if(zip_number == zip){
                    var city = lines[7].replace(/[^a-zA-Z]+/g, '');
                    var country = lines[10].replace("\r","").replace("\n","");
                } else {
                    zip = zip_number;
                    var city = zip.replace(/[0-9]/g, '').replace(/\s/g, '');
                    var country = lines[10].replace("\r","").replace("\n","");
                }
            } else {
                var street_number = lines[7].replace("\r","").replace("\n","");
                var street_number_check = street_number.replace(/\D/g, "");
                // if street_number is not zip
                if(street_number == street_number_check){
                    var zip = lines[8].replace("\r","").replace("\n","");
                    var zip_number = zip.replace(/\D/g, "");
                    // if zip is only number
                    if(zip_number == zip){
                        var city = lines[9].replace("\r","").replace("\n","");
                        var country = lines[10].replace("\r","").replace("\n","");
                    } else {
                        zip = zip_number;
                        var city = zip.replace(/[0-9]/g, '').replace(/\s/g, '');
                        var country = lines[10].replace("\r","").replace("\n","");
                    }
                } else {
                    var zip = street_number_check;
                    var city = street_number.replace(/[0-9]/g, '').replace(/\s/g, '');
                    var country = lines[10].replace("\r","").replace("\n","");
                    street_number = "";
                }
            }

            function containsOnlyNumbers(str) {
                return /^\d+$/.test(str);
            }

            function containsNumbers(str) {
                return /\d/.test(str);
            }

            // if street_number is not only number
            if (containsOnlyNumbers(street_number) == false){
                street_number = "";
            }

            // if address as number
            if (containsNumbers(address) == true){
                street_number = "";
            }

            // if zip is not only number
            if (containsOnlyNumbers(zip) == false){
                zip = 1000;
                frappe.show_alert({
                    message:__("The address is not valid. The postcode is replaced by 1000."),
                    indicator:'red'
                }, 5);
            }

            // if zip is not only number
            if (city == ""){
                city = "Lausanne";
                frappe.show_alert({
                    message:__("The address is not valid. The city is replaced by Lausanne."),
                    indicator:'red'
                }, 5);
            }

            // if qr_type = NON
            if (qr_type == "NON"){
                qr_type = "IBAN";
                frappe.show_alert({
                    message:__("This invoice is not a QRR."),
                    indicator:'orange'
                }, 5);
            }


            //console.log("type: " + qr_type);
            //console.log("amount: " + amount);
            //console.log("reference: " + reference);
            //console.log("participant: " + participant);
            //console.log("supplier_name: " + supplier_name);
            //console.log("address: " + address);
            //console.log("street_number: " + street_number);
            //console.log("zip: " + zip);
            //console.log("city: " + city);
            //console.log("country: " + country);

            get_data_based_on_esr(frm, participant, reference, amount, default_settings, address, street_number, zip, city, country, supplier_name, qr_type);
        }
    }
}

function get_data_based_on_esr(frm, participant, reference, amount, default_settings, address=null, street_number=null, zip=null, city=null, country=null, supplier_name=null, qr_type=null) {
    let methodCall = "erpnextswiss.scripts.esr_qr_tools.get_supplier_based_on_esr";
    if(qr_type == "IBAN"){
        methodCall = "erpnextswiss.scripts.esr_qr_tools.get_supplier_based_on_iban";
    }
    frappe.call({
        "method": methodCall,
        "args": {
            "participant": participant
        },
        "callback": function(response) {
            var error = response.message.error;
            if (!error) {
                var more_than_one_supplier = response.message.more_than_one_supplier;
                if (!more_than_one_supplier) {
                    // exatly one supplier
                    var supplier = response.message.supplier;
                    show_esr_detail_dialog(frm, participant, reference, amount, default_settings, supplier, [], address=address, street_number=street_number, zip=zip, city=city, country=country, supplier_name=supplier_name, qr_type=qr_type);
                } else {
                    // more than one supplier
                    var _suppliers = response.message.supplier;
                    var suppliers = [];
                    for (var i = 0; i < _suppliers.length; i++) {
                        suppliers.push(_suppliers[i]["supplier_name"] + " // (" + _suppliers[i]["name"] + ")");
                    }
                    suppliers = suppliers.join('\n');
                    show_esr_detail_dialog(frm, participant, reference, amount, default_settings, false, suppliers, address=address, street_number=street_number, zip=zip, city=city, country=country, supplier_name=supplier_name, qr_type=qr_type);
                }
            } else {
                show_esr_detail_dialog(frm, participant, reference, amount, default_settings, false, [], address=address, street_number=street_number, zip=zip, city=city, country=country, supplier_name=supplier_name, qr_type=qr_type);
            }
        }
    });
}

function show_esr_detail_dialog(frm, participant, reference, amount, default_settings, supplier, supplier_list, address=null, street_number=null, zip=null, city=null, country=null, supplier_name=null, qr_type=null, supplier_exists=false) {
    //console.log("show_esr_detail_dialog");
    var field_list = [];
    //console.log(supplier);
    if (supplier_exists) {
        if (!cur_frm.doc.supplier||cur_frm.doc.supplier == supplier) {
            var supplier_matched_txt = `<p style='color: green;'>${__("Supplier matched")} (${supplier_name})</p>`;
            field_list.push({'fieldname': 'supplier', 'fieldtype': 'Link', 'label': __('Supplier'), 'reqd': 1, 'options': 'Supplier', 'default': supplier, 'description': supplier_matched_txt});
        } else {
            var supplier_missmatch_txt = `<p style='color: orange;'>${__("Supplier found, but does not match with Invoice Supplier!")}</p>`;
            field_list.push({'fieldname': 'supplier', 'fieldtype': 'Link', 'label': __('Supplier'), 'reqd': 1, 'options': 'Supplier', 'default': supplier, 'description': supplier_missmatch_txt});
        }
    } else {
        if (supplier_list.length < 1) {
            var supplier_not_found_txt = `<p style='color: red;'>${__("No Supplier found! Fetched default Supplier.")}</p>`;
            field_list.push({'fieldname': 'supplier', 'fieldtype': 'Link', 'label': __('Supplier'), 'reqd': 1, 'options': 'Supplier', 'default': default_settings.supplier, 'description': supplier_not_found_txt});
            field_list.push({'fieldname': 'create_supplier', 'fieldtype': 'HTML', 'options': '<div class="form-group"> <div class="clearfix">  </div> <div class="control-input-wrapper"> <div class="control-input"> <button class="btn btn-default btn-sm btn-attach" id="create_supplier" >Create</button> </div> </div> </div>'});

            setTimeout(() => {
                cur_dialog.fields_dict.supplier.$input.on("change", function(){
                    $('[data-fieldname="supplier"] .help-box p').attr("style","color: blue;").html('<p>' + __("Do you want to update the supplier?") + '</p><div class="form-group"> <div class="clearfix">  </div> <div class="control-input-wrapper"> <div class="control-input"> <button class="btn btn-default btn-sm btn-attach" id="update_supplier" >' + __("Update supplier") + '</button> </div> </div> </div>');
                    $('#update_supplier').on('click', function() {
                        frappe.db.set_value('Supplier', cur_dialog.fields_dict.supplier.value, 'esr_participation_number', participant)
                        $('[data-fieldname="supplier"] .help-box p').attr("style","color: green;").text(__("Supplier update !"));
                    });
                })
                $('.modal-body [data-fieldname="supplier"]').on('click','[role="listbox"]', function() {
                    $('[data-fieldname="supplier"] .help-box p').attr("style","color: blue;").html('<p>' + __("Do you want to update the supplier?") + '</p><div class="form-group"> <div class="clearfix">  </div> <div class="control-input-wrapper"> <div class="control-input"> <button class="btn btn-default btn-sm btn-attach" id="update_supplier" >' + __("Update supplier") + '</button> </div> </div> </div>');
                    $('#update_supplier').on('click', function() {
                        frappe.db.set_value('Supplier', cur_dialog.fields_dict.supplier.value, 'esr_participation_number', participant)
                        $('[data-fieldname="supplier"] .help-box p').attr("style","color: green;").text(__("Supplier update !"));
                    });
                });
            }, 1000);


            setTimeout(() => {
                //console.log("Create supplier loaded");
                $(cur_dialog.$wrapper).on('click','#create_supplier', function() {
                    //console.log("Create supplier");
                    frappe.call({
                        method: 'neoffice_theme.events.create_supplier',
                        args: {
                            'supplier_name': supplier_name,
                            'participant': participant,
                            'default_payment_method': qr_type
                        },
                        callback: function(r) {
                            //console.log("Supplier created");
                            //console.log(r)
                            if (!address || address === '' || address === null || address === undefined) {
                                address = __("No address");
                                frappe.warn(__("No address in the QR"),
                                    __('The supplier has been created but without an address. Go to the supplier to correct the address.'),
                                    () => {
                                    },
                                    __('OK'),
                                    true 
                                )
                            }
                            frappe.call({
                                method: 'neoffice_theme.events.create_supplier_address',
                                args: {
                                    'supplier_name': supplier_name,
                                    'address': address,
                                    'street_number': street_number,
                                    'city': city,
                                    'zip_code': zip
                                },
                                callback: function(r) {
                                    //console.log("Address created")
                                    //console.log(r)
                                    frappe.db.set_value('Supplier', supplier_name, 'supplier_primary_address', r.message.name)
                                    cur_dialog.set_value("supplier", supplier_name)
                                    $('[data-fieldname="supplier"] .help-box p').attr("style","color: green;").text(__("Supplier create !"));
                                }
                            });
                        }
                    });
                });
            }, 1000);

        } else {
            var multiple_supplier_txt = `<p style='color: orange;'>${__("Multiple Supplier found, please choose one!")}</p>`;
            field_list.push({'fieldname': 'supplier', 'fieldtype': 'Select', 'label': __('Supplier'), 'reqd': 1, 'options': supplier_list, 'description': multiple_supplier_txt});
        }
    }
    
    if (cur_frm.doc.grand_total > 0) {
        if (cur_frm.doc.grand_total != parseFloat(amount)) {
            var deviation = parseFloat(amount) - cur_frm.doc.grand_total;
            field_list.push({'fieldname': 'amount', 'fieldtype': 'Currency', 'label': __('Amount'), 'read_only': 0, 'default': parseFloat(amount)});
            field_list.push({'fieldname': 'deviation', 'fieldtype': 'Currency', 'label': __('Amount Deviation'), 'read_only': 0, 'default': parseFloat(deviation)});
            if (deviation < 0) {
                field_list.push({'fieldname': 'negative_deviation', 'fieldtype': 'Check', 'label': __('Add negative deviation as discount'), 'default': default_settings.negative_deviation});
            } else {
                field_list.push({'fieldname': 'positive_deviation', 'fieldtype': 'Check', 'label': __('Add positive deviation as additional item'), 'default': default_settings.positive_deviation});
                field_list.push({'fieldname': 'positive_deviation_item', 'fieldtype': 'Link', 'options': 'Item', 'label': __('Positive Deviation Item'), 'default': default_settings.positive_deviation_item});
            }
        } else {
            var esr_amount_matched_txt = "<p style='color: green;'>" + __("Invoice amount matched") + "</p>";
            field_list.push({'fieldname': 'amount', 'fieldtype': 'Currency', 'label': __('Amount'), 'read_only': 0, 'default': parseFloat(amount), 'description': esr_amount_matched_txt});
        }
    } else {
        if(qr_type == "IBAN"){
            field_list.push({'fieldname': 'amount', 'fieldtype': 'Currency', 'label': __('Amount'), 'read_only': 0, 'default': parseFloat(amount)});
        } else {
            field_list.push({'fieldname': 'amount', 'fieldtype': 'Currency', 'label': __('Amount'), 'read_only': 0, 'default': parseFloat(amount)});
        }
        field_list.push({'fieldname': 'default_item', 'fieldtype': 'Link', 'options': 'Item', 'label': __('Default Item'), 'default': default_settings.default_item});
    }

    //field_list.push({'fieldname': 'tax_rate', 'fieldtype': 'Float', 'label': __('Tax Rate in %'), 'default': default_settings.default_tax_rate});
    function checkReferenceExists(reference) {
        frappe.db.get_list('Purchase Invoice', {
            fields: ['name'],
            filters: {
                'esr_reference_number': reference
            }
        }).then(records => {
            if(records.length > 0) {

                frappe.msgprint({
                    title: __('Are you sure you want to proceed?'),
                    message: __('This reference is already used in a Purchase Invoice.'),
                    primary_action: {
                        'label': __('Continue'),
                        'action': () => {
                            cur_dialog.hide();
                        }
                    },
                    secondary_action: {
                        'label': __('Cancel'),
                        'action': () => {
                            cur_dialog.hide();
                            frappe.set_route('List', 'Purchase Invoice');
                        }
                    }
                });
            }
        });
    }

    field_list.push({'fieldname': 'posting_date', 'fieldtype': 'Date', 'label': __('Date'), 'read_only': 0, 'default': "Today"});
    if(qr_type == "IBAN"){
        field_list.push({'fieldname': 'iban', 'fieldtype': 'Data', 'label': __('IBAN'), 'read_only': 1, 'default': participant});
    } else {
        field_list.push({'fieldname': 'reference', 'fieldtype': 'Data', 'label': __('Reference'), 'read_only': 0, 'default': reference});
        field_list.push({'fieldname': 'participant', 'fieldtype': 'Data', 'label': __('Participant'), 'read_only': 0, 'default': participant});
    }

    field_list.push({'fieldname': 'cost_center', 'fieldtype': 'Link', 'label': __('Cost Center'), 'options': "Cost Center", 'default': locals[":Company"][frappe.defaults.get_user_default("company")]['cost_center'] });

    setTimeout(() => {
        frappe.db.get_value("Supplier", supplier_name, "product_default",(r) => {
            if(r.product_default){
                setTimeout(() => {
                    //console.log(r.product_default);
                    cur_dialog.set_value("default_item", r.product_default);
                }, 200);
            }
        });
        if(qr_type != "IBAN"){
            checkReferenceExists(reference);
        }
    }, 1000);

    field_list.push({'fieldname': 'customer_reference', 'fieldtype': 'Data', 'label': __('Supplier reference'), 'read_only': 0});

    frappe.prompt(field_list,
    function(values){
        if (supplier_list.length > 0) {
            values.supplier = values.supplier.split(" // (")[1].replace(")", "");
        }
        if (frm.doc.__islocal) {
            if ((!cur_frm.doc.items) || (cur_frm.doc.items.length === 0) || (!cur_frm.doc.items[0].item_code)) {
                fetch_esr_details_to_new_sinv(frm, values);
            } else {
                fetch_esr_details_to_existing_sinv(frm, values);
            }
        } else {
            fetch_esr_details_to_existing_sinv(frm, values);
        }
    },
    __('Details'),
    __('Process')
    )
}

function fetch_esr_details_to_new_sinv(frm, values) {
    //console.log("fetch_esr_details_to_new_sinv");
    // remove all rows
    var tbl = cur_frm.doc.items || [];
    var i = tbl.length;
    while (i--)
    {
        if (!cur_frm.get_field("items").grid.grid_rows[i].doc.item_code) {
            cur_frm.get_field("items").grid.grid_rows[i].remove();
        }
    }
    cur_frm.doc.supplier = values.supplier;
    cur_frm.refresh_field("supplier");
    frappe.db.get_value("Supplier", values.supplier, "tax_category",(r) => {
        cur_frm.refresh_field('items');
        if(values.reference){
            if(values.reference.includes("RF")) {
                cur_frm.set_value("payment_type", 'SCOR');
                cur_frm.set_value("bic", values.bic);
                cur_frm.set_value("esr_participation_number", values.participant);
            } else {
                // check if values.participant is note empty
                if(values.participant){
                    if(values.participant.charAt(4) == "3" && values.participant.charAt(0) == "C" && values.participant.charAt(1) == "H") {
                        cur_frm.set_value("payment_type", 'QRR');
                        cur_frm.set_value("esr_participation_number", values.participant);
                    } else {
                        if(values.participant.charAt(0) == "C" && values.participant.charAt(1) == "H") {
                            cur_frm.set_value("payment_type", 'IBAN');
                            cur_frm.set_value("iban", values.iban);
                        } else {
                            cur_frm.set_value("payment_type", 'SEPA');
                            cur_frm.set_value("iban", values.iban);
                            cur_frm.set_value("bic", values.bic);
                        }
                    }
                }
            }
            if(values.reference){
                cur_frm.set_value("esr_reference_number", values.reference);
            }
        } else {
            if(values.participant){
                if(values.participant.charAt(0) == "C" && values.participant.charAt(1) == "H") {
                    cur_frm.set_value("payment_type", 'IBAN');
                } else {
                    cur_frm.set_value("payment_type", 'SEPA');
                    cur_frm.set_value("bic", values.bic);
                }
            }
            if(values.iban){
                cur_frm.set_value("iban", values.iban);
            }
        }

        cur_frm.set_value("taxes_and_charges", cur_frm.doc.taxes_and_charges);
        cur_frm.set_value("tax_category", r.tax_category);
        cur_frm.set_value("set_posting_time", 1);
        cur_frm.set_value("customer_reference", values.customer_reference);
        setTimeout(() => {
            cur_frm.set_value("posting_date", values.posting_date);
        }, 100);
        //var rate = (values.amount / (100 + values.tax_rate)) * 100;
        var rate = values.amount;

        var child = cur_frm.add_child('items');
        frappe.model.set_value(child.doctype, child.name, 'item_code', values.default_item);
        frappe.model.set_value(child.doctype, child.name, 'qty', 1.000);
        //frappe.model.set_value(child.doctype, child.name, 'item_tax_template', "TVA 7.7% Achat revente - pri");
        frappe.model.set_value(child.doctype, child.name, 'rate', rate);
        cur_frm.refresh_field('items');

        setTimeout(function(){
            cur_frm.set_value("taxes_and_charges", cur_frm.doc.taxes_and_charges);
            frappe.model.set_value(child.doctype, child.name, 'rate', rate);
            frappe.model.set_value(child.doctype, child.name, 'cost_center', values.cost_center);
            //frappe.model.set_value(child.doctype, child.name, 'item_tax_template', "TVA 7.7% Achat revente - pri");
            cur_frm.refresh_field('items');
        }, 1000);
    });
}

function fetch_esr_details_to_existing_sinv(frm, values) {
    //console.log("fetch_esr_details_to_existing_sinv");
    cur_frm.set_value("supplier", values.supplier);
    frappe.db.get_value("Supplier", values.supplier, "tax_category",(r) => {
        if(values.reference){
            cur_frm.set_value("payment_type", 'QRR');
            cur_frm.set_value("esr_reference_number", values.reference);
            //cur_frm.set_value("bic", values.reference);
            cur_frm.set_value("esr_participation_number", values.participant);
        } else {
            cur_frm.set_value("payment_type", 'IBAN');
            cur_frm.set_value("iban", values.iban);
        }
        cur_frm.set_value("taxes_and_charges", cur_frm.doc.taxes_and_charges);
        cur_frm.set_value("tax_category", r.tax_category);
        cur_frm.set_value("posting_date", values.posting_date);
        cur_frm.set_value("customer_reference", values.customer_reference);

        if (values.negative_deviation) {
            cur_frm.set_value("apply_discount_on", 'Grand Total');
            var discount_amount = values.deviation * -1;
            cur_frm.set_value("discount_amount", discount_amount);
        }

        if (values.positive_deviation) {
            //var rate = (values.deviation / (100 + values.tax_rate)) * 100;
            var rate = values.deviation

            var child = cur_frm.add_child('items');
            frappe.model.set_value(child.doctype, child.name, 'item_code', values.positive_deviation_item);
            frappe.model.set_value(child.doctype, child.name, 'qty', 1.000);
            //frappe.model.set_value(child.doctype, child.name, 'item_tax_template', "TVA 7.7% Achat revente - pri");
            frappe.model.set_value(child.doctype, child.name, 'rate', rate);
            cur_frm.refresh_field('items');
            setTimeout(function(){
                cur_frm.set_value("taxes_and_charges", cur_frm.doc.taxes_and_charges);
                frappe.model.set_value(child.doctype, child.name, 'rate', rate);
                //frappe.model.set_value(child.doctype, child.name, 'item_tax_template', "TVA 7.7% Achat revente - pri");
                frappe.model.set_value(child.doctype, child.name, 'cost_center', values.cost_center);
                cur_frm.refresh_field('items');
            }, 1000);
        }
    });
}

function pull_supplier_defaults(frm) {
    //console.log("pull_supplier_defaults");
    if (frm.doc.supplier) {
        frappe.call({
            'method': "frappe.client.get",
            'args': {
                'doctype': "Supplier",
                "name": frm.doc.supplier
            },
            "callback": function(response) {
                var supplier = response.message;
                cur_frm.set_value("payment_type", supplier.default_payment_method);
            }
        });
    }
}
