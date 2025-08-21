frappe.listview_settings["ebics Log"] = {
	add_fields: ["status", "details", "operation"],
	onload: function (listview) {
		// Add "Copy Logs" button
		listview.page.add_button(__("Copy EBICS Logs"), function () {
			let selected_docs = listview.get_checked_items();
			if (!selected_docs || selected_docs.length === 0) {
				frappe.msgprint(__("Please select at least one log entry."));
				return;
			}

			let output = "=== EBICS LOGS ===\n\n";
			selected_docs.forEach(function (doc) {
				let timestamp = doc.timestamp || "(No timestamp)";
				let operation = doc.operation || "(No operation)";
				let status = doc.status || "(No status)";
				let connection = doc.connection || "(No connection)";
				let user = doc.user || "(No user)";
				let details = doc.details || "(No details)";
				
				output += "Timestamp: " + timestamp + "\n";
				output += "Operation: " + operation + "\n";
				output += "Status: " + status + "\n";
				output += "Connection: " + connection + "\n";
				output += "User: " + user + "\n";
				output += "Details: " + details + "\n";
				output += "-".repeat(50) + "\n\n";
			});

			// Copy to clipboard
			if (navigator.clipboard && navigator.clipboard.writeText) {
				navigator.clipboard.writeText(output)
					.then(function () {
						frappe.show_alert({
							message: __("EBICS logs have been copied to the clipboard."),
							indicator: "green"
						});
					})
					.catch(function (err) {
						frappe.msgprint(__("Error while copying to clipboard: ") + err);
					});
			} else {
				// Fallback for older browsers
				let textarea = document.createElement("textarea");
				textarea.value = output;
				document.body.appendChild(textarea);
				textarea.select();
				try {
					document.execCommand("copy");
					frappe.show_alert({
						message: __("EBICS logs have been copied to the clipboard."),
						indicator: "green"
					});
				} catch (err) {
					frappe.msgprint(__("Error while copying to clipboard: ") + err);
				}
				document.body.removeChild(textarea);
			}
		});
		
		// Add "Clear EBICS Logs" button (for System Manager only)
		if (frappe.user_roles.includes("System Manager")) {
			listview.page.add_button(__("Clear EBICS Logs"), function () {
				frappe.confirm(
					__("Are you sure you want to clear all EBICS logs? This action cannot be undone."),
					function() {
						frappe.call({
							method: "erpnextswiss.erpnextswiss.ebics_utils.clear_ebics_logs",
							callback: function () {
								frappe.show_alert({
									message: __("EBICS logs have been cleared."),
									indicator: "green"
								});
								listview.refresh();
							},
							error: function(err) {
								frappe.msgprint(__("Error clearing logs: ") + err);
							}
						});
					}
				);
			});
		}
	},
	
	get_indicator: function(doc) {
		// Color indicators based on status
		if (doc.status === "success") {
			return [__("Success"), "green", "status,=,success"];
		} else if (doc.status === "error") {
			return [__("Error"), "red", "status,=,error"];
		} else if (doc.status === "warning") {
			return [__("Warning"), "orange", "status,=,warning"];
		} else {
			return [__("Info"), "blue", "status,=,info"];
		}
	},
	
	formatters: {
		operation: function(value) {
			// Format operation names with icons
			const icon_map = {
				"GENERATE_KEYS": "fa fa-key",
				"INI": "fa fa-upload",
				"HIA": "fa fa-upload",
				"HPB": "fa fa-download",
				"GET_INI_LETTER": "fa fa-file-pdf-o",
				"Z53": "fa fa-bank",
				"Z54": "fa fa-bank",
				"RESET_CONNECTION": "fa fa-refresh",
				"TEST_CONNECTION": "fa fa-plug"
			};
			
			let icon = icon_map[value] || "fa fa-circle";
			return `<i class="${icon}"></i> ${value}`;
		},
		timestamp: function(value) {
			// Format timestamp to be more readable
			if (value) {
				return frappe.datetime.str_to_user(value);
			}
			return "";
		}
	}
};