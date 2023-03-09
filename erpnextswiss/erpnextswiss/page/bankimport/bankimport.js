frappe.pages['bankimport'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Bank import'),
		single_column: true
	});

	frappe.bankimport.make(page);
	frappe.bankimport.run();
	
	// add the application reference
	frappe.breadcrumbs.add("ERPNextSwiss");
}

frappe.bankimport = {
	start: 0,
	make: function(page) {
		var me = frappe.bankimport;
		me.page = page;
		me.body = $('<div></div>').appendTo(me.page.main);
		var data = "";
		$(frappe.render_template('bankimport', data)).appendTo(me.body);

		// add menu button
		/*
		this.page.add_menu_item(__("Match payments"), function() {
			window.location.href="/app/match_payments";
		});
		this.page.add_menu_item(__("Debug Template"), function() {
			$('.btn-parse-file').trigger('click', [true]);
		});*/

		// attach button handlers
		this.page.main.find(".btn-parse-file").on('click', function(event, debug=false) {
			
			var me = frappe.bankimport;
			
			// get selected bank
			var bank = document.getElementById("bank").value;
			// get selected account
			var account = document.getElementById("payment_account").value;
			// get selected option
			//var auto_submit = document.getElementById("auto_submit").checked;
			var auto_submit = false;
			// get format type
			var format = document.getElementById("format").value;

			//console.log("format: " + format);
			
			// read the file 
			var file = document.getElementById("input_file").files[0];
			var content = "";
			if (file) {
				// create a new reader instance
				var reader = new FileReader();
				// assign load event to process the file
				reader.onload = function (event) {
					// enable waiting gif
					////frappe.bankimport.start_wait();
					frappe.dom.freeze(__("Please wait while the file is being processed..."));
					// read file content
					var bytes = new Uint8Array(event.target.result);
					var content = '';
					for (var i = 0; i < bytes.length; i++) {
						content += String.fromCharCode(bytes[i]);
					}
					//content = event.target.result;

					// Get iban selected
					var ibanSelected = $(cur_page.page).find("#payment_account").val();
					var ibanBank = "";
					//get IBAN bank
					frappe.db.get_value("Account", ibanSelected, "iban", function(r) {
						ibanBank = r.iban;
						if (format == "csv") {
							// call bankimport method with file content
							frappe.call({
								method: 'erpnextswiss.erpnextswiss.page.bankimport.bankimport.parse_file',
								args: {
									content: content,
									bank: bank,
									account: account,
									auto_submit: auto_submit,
									debug : debug
								},
								callback: function(r) {
									var message = r.message.message;
									var new_payment_entries = r.message.records[0];
									var return_amounts = r.message.records[1];
									var return_customer_names = r.message.records[2];
									var return_date = r.message.records[3];
									var return_unique_reference = r.message.records[4];
									var return_transaction_reference = r.message.records[5];
									var return_info = r.message.records[6];

									if (r.message) {
										frappe.bankimport.render_response(page, message, new_payment_entries, return_amounts, return_customer_names, return_date, return_unique_reference, return_transaction_reference, return_info );
									}
								}
							});
						}
						else if (format == "camt054") {
							// call bankimport method with file content
							frappe.call({
								method: 'erpnextswiss.erpnextswiss.page.bankimport.bankimport.check_iban_xml',
								args: {
									content: content,
									ibanSelected: ibanBank,
								},
								callback: function(r) {
									// if iban is correct
									if (r.message == true) {
										frappe.call({
											method: 'erpnextswiss.erpnextswiss.page.bankimport.bankimport.read_camt054',
											args: {
												content: content,
												bank: bank,
												account: account,
												auto_submit: auto_submit
											},
											callback: function(r) {
												var message = r.message.message;
												var new_payment_entries = r.message.records[0];
												var return_amounts = r.message.records[1];
												var return_customer_names = r.message.records[2];
												var return_date = r.message.records[3];
												var return_unique_reference = r.message.records[4];
												var return_transaction_reference = r.message.records[5];
												var return_info = r.message.records[6];

												if (r.message) {
													frappe.bankimport.render_response(page, message, new_payment_entries, return_amounts, return_customer_names, return_date, return_unique_reference, return_transaction_reference, return_info );
												}
											}
										});
										frappe.show_alert({
											message:__('The iban of the selected bank and the iban of the XML file are identical'),
											indicator:'green'
										}, 5);
									} else {
										frappe.dom.unfreeze();
										frappe.warn(__('Are you sure you want to proceed?'),
											__('The iban of the selected bank and the iban of the XML file are not identical'),
											() => {
												// call bankimport method with file content
												frappe.dom.freeze(__("Please wait while the file is being processed..."));
												frappe.call({
													method: 'erpnextswiss.erpnextswiss.page.bankimport.bankimport.read_camt054',
													args: {
														content: content,
														bank: bank,
														account: account,
														auto_submit: auto_submit
													},
													callback: function(r) {
														var message = r.message.message;
														var new_payment_entries = r.message.records[0];
														var return_amounts = r.message.records[1];
														var return_customer_names = r.message.records[2];
														var return_date = r.message.records[3];
														var return_unique_reference = r.message.records[4];
														var return_transaction_reference = r.message.records[5];
														var return_info = r.message.records[6];

														if (r.message) {
															frappe.bankimport.render_response(page, message, new_payment_entries, return_amounts, return_customer_names, return_date, return_unique_reference, return_transaction_reference, return_info );
														}
													}
												});
											},
											__('Continue'),
											true // Sets dialog as minimizable
										)
									}
								}
							});
						}
						else if (format == "camt053") {
							// call bankimport method with file content
							frappe.call({
								method: 'erpnextswiss.erpnextswiss.page.bankimport.bankimport.read_camt053',
								args: {
									content: content,
									bank: bank,
									account: account,
									auto_submit: auto_submit
								},
								callback: function(r) {
									var message = r.message.message;
									var new_payment_entries = r.message.records[0];
									var return_amounts = r.message.records[1];
									var return_customer_names = r.message.records[2];
									var return_date = r.message.records[3];
									var return_unique_reference = r.message.records[4];
									var return_transaction_reference = r.message.records[5];
									var return_info = r.message.records[6];

									if (r.message) {
										frappe.bankimport.render_response(page, message, new_payment_entries, return_amounts, return_customer_names, return_date, return_unique_reference, return_transaction_reference, return_info );
									}
								}
							});
						} else {
							frappe.msgprint(__("Unknown format."));
						}
					});
				}
				// assign an error handler event
				reader.onerror = function (event) {
					frappe.msgprint(__("Error reading file"), __("Error"));
				}
				reader.readAsArrayBuffer(file);
				//reader.readAsText(file, "ANSI");
			}
			else
			{
				frappe.msgprint(__("Please select a file."), __("Information"));
			}
			
		});
	},
	run: function() {
		// populate bank accounts
		frappe.call({
			method: 'erpnextswiss.erpnextswiss.page.bankimport.bankimport.get_bank_accounts',
			args: { },
			callback: function(r) {
				if (r.message) {
					setTimeout(function() {
						var select = document.getElementById("payment_account");
						var defaultValue = $("#bank").val().toLowerCase();
						for (var i = 0; i < r.message.accounts.length; i++) {
							var opt = document.createElement("option");
							opt.value = r.message.accounts[i];
							opt.innerHTML = r.message.accounts[i];
							if (r.message.accounts[i].toLowerCase().indexOf(defaultValue) !== -1) {
								opt.selected = true;
							}
							select.appendChild(opt);
						}
					}, 200);
				}
			}
		});
		frappe.call({
			method: 'erpnextswiss.erpnextswiss.page.bankimport.bankimport.get_bank_settings',
			args: { },
			callback: function(r) {
				if (r.message.banks) {
					var select = document.getElementById("bank");
					// Change format selection based on bank setting information
					select.onchange = function() {
						frappe.bankimport.change_option("format",r.message.banks[select.selectedIndex].file_format.split('(').pop().split(')')[0]);
					}
					// Build enabled banks for import
					for (var i = 0; i < r.message.banks.length; i++) {
						var opt = document.createElement("option");
						if(r.message.banks[i].legacy_ref){
							opt.value = r.message.banks[i].legacy_ref;
						}else{
							opt.value = r.message.banks[i].bank_name;
						}
						//opt.setAttribute("importType",r.message.banks[i].filetype);
						//// opt.innerHTML = r.message.banks[i].bank_name;
						////
						opt.innerHTML = r.message.banks[i].legacy_ref;

						select.appendChild(opt);
					}
					// Build import formats based on doctype "
					/*
					var formatOption = document.getElementById("format");
					for (var i = 0; i < r.message.formats.length; i++) {
						var opt = document.createElement("option");
						opt.value = r.message.formats[i].format_ref;
						opt.innerHTML = __(r.message.formats[i].format_name);
						formatOption.appendChild(opt);
					}
					*/
					frappe.bankimport.change_option("format",r.message.banks[0].file_format.split('(').pop().split(')')[0])
				}
			}
		}); 
	},
	start_wait: function() {
		//document.getElementById("waitingScreen").style.display = "block";
	},
	end_wait: function() {
		//document.getElementById("waitingScreen").style.display = "none";
	},
	render_response: function(page, message, new_payment_entries, return_amounts, return_customer_names, return_date, return_unique_reference, return_transaction_reference, return_info) {
		// disable waiting gif
		////frappe.bankimport.end_wait();
		frappe.dom.unfreeze();
		page.main.find(".insert-log-messages").removeClass("hide");
		var parent = page.main.find(".insert-log-messages #message").empty();
		var trtable = page.main.find(".insert-log-messages #log_messages").empty();
		var trtablenot = page.main.find(".insert-log-messages #log_messages_not_imported").empty();
		var count_new_payment_entries = new_payment_entries.length;
		var count_payment_not_imported = 0;

		if (new_payment_entries) {
			for (var i = 0; i < count_new_payment_entries; i++) {
				if(new_payment_entries[i] != 0) {
					$('<tr>').appendTo(trtable);
						$('<td>' + return_date[i] + '</td>').appendTo(trtable);
						$('<td><a href="/app/payment-entry/'
							+ new_payment_entries[i] + '">'
							+ new_payment_entries[i] + '</a></td>').appendTo(trtable);
						$('<td>' + return_amounts[i] + '</td>').appendTo(trtable);
						$('<td>' + return_customer_names[i] + '</td>').appendTo(trtable);
						$('<td>' + return_unique_reference[i] + '</td>').appendTo(trtable);
						$('<td>' + return_transaction_reference[i] + '</td>').appendTo(trtable);
					$('</tr>').appendTo(trtable);
				} else {
					count_payment_not_imported++;
					$('<tr>').appendTo(trtablenot);
						$('<td>' + return_date[i] + '</td>').appendTo(trtablenot);
						$('<td>' + return_amounts[i] + '</td>').appendTo(trtablenot);
						$('<td>' + return_customer_names[i] + '</td>').appendTo(trtablenot);
						$('<td>' + return_unique_reference[i] + '</td>').appendTo(trtablenot);
						$('<td><a id="' + return_transaction_reference[i] + '">' + return_transaction_reference[i] + '</a></td>').appendTo(trtablenot);
						$('<td>' + __(return_info[i]) + '</td>').appendTo(trtablenot);
					$('</tr>').appendTo(trtablenot);
					$("#payment_not_matched").removeClass("hide");
					// Get invoice name from QR reference
					$("#" + return_transaction_reference[i]).click(function() {
						var transaction_reference = $(this).attr('id');
						// Open the invoice in a new tab
						frappe.db.get_value("Sales Invoice", {"qr_ref": return_unique_reference[i]}, "name", function(r) {
							if(r.name) {
								window.open("/app/sales-invoice/" + r.name);
							}
						});
					});
				}
			}
			count_new_payment_entries = count_new_payment_entries - count_payment_not_imported;

			$('<div class="alert alert-info" style="font-weight: 600;">' + __("Successfully imported ") + "<strong>" + count_new_payment_entries + "</strong>" + __(" payments and ") + "<strong>" + count_payment_not_imported + "</strong>" + __(" not imported.") + '</div>').appendTo(parent);
		}

	},
	change_option: function(id, valueToSelect) {
		var element = document.getElementById(id);
		element.value = valueToSelect;
	}
}
