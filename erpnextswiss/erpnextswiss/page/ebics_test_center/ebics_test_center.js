frappe.pages['ebics-test-center'].on_page_load = function(wrapper) {
	console.log('EBICS Test Center: Page loading...');
	
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'EBICS Test Center',
		single_column: true
	});

	// Add custom CSS
	$('<style>').text(`
		.test-section {
			margin-bottom: 30px;
			padding: 20px;
			border: 1px solid #d1d8dd;
			border-radius: 5px;
		}
		.test-result {
			margin-top: 15px;
			padding: 15px;
			border-radius: 5px;
			font-family: monospace;
			white-space: pre-wrap;
			max-height: 400px;
			overflow-y: auto;
		}
		.test-success {
			background-color: #d4edda;
			border: 1px solid #c3e6cb;
		}
		.test-error {
			background-color: #f8d7da;
			border: 1px solid #f5c6cb;
		}
		.test-info {
			background-color: #d1ecf1;
			border: 1px solid #bee5eb;
		}
		.test-button {
			margin: 5px;
		}
		.status-indicator {
			display: inline-block;
			width: 10px;
			height: 10px;
			border-radius: 50%;
			margin-right: 5px;
		}
		.status-green { background-color: #28a745; }
		.status-red { background-color: #dc3545; }
		.status-yellow { background-color: #ffc107; }
	`).appendTo('head');

	// Create main container
	let $container = $(`
		<div class="ebics-test-container">
			<!-- API Status Section -->
			<div class="test-section">
				<h3>🔌 API Server Status</h3>
				<p>Test the EBICS API Server connection and health</p>
				<button class="btn btn-primary test-button" id="test-api-health">
					<i class="fa fa-heartbeat"></i> Test API Health
				</button>
				<button class="btn btn-info test-button" id="start-api-server">
					<i class="fa fa-play"></i> Start API Server
				</button>
				<button class="btn btn-warning test-button" id="stop-api-server">
					<i class="fa fa-stop"></i> Stop API Server
				</button>
				<div id="api-status-result" class="test-result" style="display:none;"></div>
			</div>

			<!-- Connection Test Section -->
			<div class="test-section">
				<h3>🔗 Connection Tests</h3>
				<p>Test EBICS connections and their status</p>
				<div class="form-group">
					<label>Select Connection:</label>
					<select id="connection-select" class="form-control">
						<option value="">-- Select a connection --</option>
					</select>
				</div>
				<button class="btn btn-primary test-button" id="test-connection" disabled>
					<i class="fa fa-link"></i> Test Connection
				</button>
				<button class="btn btn-info test-button" id="get-order-types" disabled>
					<i class="fa fa-list"></i> Get Available Order Types
				</button>
				<div id="connection-result" class="test-result" style="display:none;"></div>
			</div>

			<!-- Key Management Section -->
			<div class="test-section">
				<h3>🔐 Key Management</h3>
				<p>Test key generation and initialization</p>
				<button class="btn btn-primary test-button" id="generate-keys" disabled>
					<i class="fa fa-key"></i> Generate Keys
				</button>
				<button class="btn btn-info test-button" id="send-ini" disabled>
					<i class="fa fa-upload"></i> Send INI
				</button>
				<button class="btn btn-info test-button" id="send-hia" disabled>
					<i class="fa fa-upload"></i> Send HIA
				</button>
				<button class="btn btn-success test-button" id="download-hpb" disabled>
					<i class="fa fa-download"></i> Download HPB
				</button>
				<button class="btn btn-warning test-button" id="print-ini-letter" disabled>
					<i class="fa fa-print"></i> Print INI Letter
				</button>
				<div id="key-management-result" class="test-result" style="display:none;"></div>
			</div>

			<!-- Statement Download Section -->
			<div class="test-section">
				<h3>📊 Statement Downloads</h3>
				<p>Test downloading bank statements</p>
				<div class="row">
					<div class="col-md-3">
						<label>From Date:</label>
						<input type="date" id="from-date" class="form-control">
					</div>
					<div class="col-md-3">
						<label>To Date:</label>
						<input type="date" id="to-date" class="form-control">
					</div>
					<div class="col-md-3">
						<label>Order Type:</label>
						<select id="order-type" class="form-control">
							<option value="z53">Z53 - Swiss Statement</option>
							<option value="z52">Z52 - Swiss Intraday</option>
							<option value="c53">C53 - CAMT.053</option>
							<option value="c52">C52 - CAMT.052</option>
						</select>
					</div>
				</div>
				<br>
				<button class="btn btn-primary test-button" id="download-statements" disabled>
					<i class="fa fa-download"></i> Download Statements
				</button>
				<div id="statement-result" class="test-result" style="display:none;"></div>
			</div>

			<!-- Payment Upload Section -->
			<div class="test-section">
				<h3>💳 Payment Upload</h3>
				<p>Test uploading payment files</p>
				<div class="form-group">
					<label>Payment Proposal:</label>
					<select id="payment-proposal-select" class="form-control">
						<option value="">-- Select a payment proposal --</option>
					</select>
				</div>
				<button class="btn btn-primary test-button" id="test-payment-upload" disabled>
					<i class="fa fa-upload"></i> Test Payment Upload
				</button>
				<div id="payment-result" class="test-result" style="display:none;"></div>
			</div>

			<!-- Comparison Section -->
			<div class="test-section">
				<h3>⚖️ Fintech vs API Comparison</h3>
				<p>Compare results between fintech and EBICS API</p>
				<button class="btn btn-primary test-button" id="run-comparison">
					<i class="fa fa-balance-scale"></i> Run Comparison Test
				</button>
				<div id="comparison-result" class="test-result" style="display:none;"></div>
			</div>

			<!-- Logs Section -->
			<div class="test-section">
				<h3>📝 Test Logs</h3>
				<div id="test-logs" class="test-result test-info" style="display:block; height: 200px;">
					Test logs will appear here...
				</div>
			</div>
		</div>
	`).appendTo(page.body);

	// Helper functions
	function showResult(elementId, content, type = 'info') {
		let $element = $(`#${elementId}`);
		$element.removeClass('test-success test-error test-info');
		$element.addClass(`test-${type}`);
		$element.html(content);
		$element.show();
		
		// Add to logs
		addLog(`[${type.toUpperCase()}] ${elementId}: ${content.substring(0, 100)}...`);
	}

	function addLog(message) {
		let timestamp = new Date().toLocaleTimeString();
		let $logs = $('#test-logs');
		$logs.append(`[${timestamp}] ${message}\n`);
		$logs.scrollTop($logs[0].scrollHeight);
	}

	// Load connections
	function loadConnections() {
		frappe.call({
			method: 'frappe.client.get_list',
			args: {
				doctype: 'ebics Connection',
				fields: ['name', 'title', 'activated'],
				limit: 100
			},
			callback: function(r) {
				if (r.message) {
					let $select = $('#connection-select');
					$select.empty().append('<option value="">-- Select a connection --</option>');
					r.message.forEach(conn => {
						let status = conn.activated ? '✅' : '⭕';
						$select.append(`<option value="${conn.name}">${status} ${conn.title || conn.name}</option>`);
					});
					addLog(`Loaded ${r.message.length} connections`);
				}
			}
		});
	}

	// Load payment proposals
	function loadPaymentProposals() {
		frappe.call({
			method: 'frappe.client.get_list',
			args: {
				doctype: 'Payment Proposal',
				fields: ['name', 'date', 'total'],
				filters: [['docstatus', '=', 1]],
				limit: 50,
				order_by: 'creation desc'
			},
			callback: function(r) {
				if (r.message) {
					let $select = $('#payment-proposal-select');
					$select.empty().append('<option value="">-- Select a payment proposal --</option>');
					r.message.forEach(pp => {
						$select.append(`<option value="${pp.name}">${pp.name} (${pp.date} - ${pp.total})</option>`);
					});
					addLog(`Loaded ${r.message.length} payment proposals`);
				}
			}
		});
	}

	// Event handlers
	$('#test-api-health').click(function() {
		frappe.call({
			method: 'erpnextswiss.erpnextswiss.ebics_api.test_ebics_api',
			callback: function(r) {
				if (r.message) {
					let type = r.message.success ? 'success' : 'error';
					showResult('api-status-result', JSON.stringify(r.message, null, 2), type);
				}
			}
		});
	});

	$('#connection-select').change(function() {
		let hasSelection = $(this).val() !== '';
		$('#test-connection, #get-order-types, #generate-keys, #send-ini, #send-hia, #download-hpb, #print-ini-letter, #download-statements, #test-payment-upload')
			.prop('disabled', !hasSelection);
	});

	$('#test-connection').click(function() {
		let connection = $('#connection-select').val();
		if (!connection) return;
		
		frappe.call({
			method: 'erpnextswiss.erpnextswiss.doctype.ebics_connection.ebics_connection.test_connection',
			args: {
				connection_name: connection
			},
			callback: function(r) {
				if (r.message) {
					showResult('connection-result', r.message, 'info');
				}
			}
		});
	});

	$('#get-order-types').click(function() {
		let connection = $('#connection-select').val();
		if (!connection) return;
		
		frappe.call({
			method: 'erpnextswiss.erpnextswiss.doctype.ebics_connection.ebics_connection.get_available_order_types',
			args: {
				connection_name: connection
			},
			callback: function(r) {
				if (r.message) {
					showResult('connection-result', 'Available Order Types:\n' + JSON.stringify(r.message, null, 2), 'info');
				} else {
					showResult('connection-result', 'No order types available or not supported by this bank', 'warning');
				}
			},
			error: function(r) {
				showResult('connection-result', 'Error: ' + (r.message || 'Failed to get order types'), 'error');
			}
		});
	});

	$('#download-statements').click(function() {
		let connection = $('#connection-select').val();
		let fromDate = $('#from-date').val();
		let toDate = $('#to-date').val();
		let orderType = $('#order-type').val();
		
		if (!connection || !fromDate || !toDate) {
			frappe.msgprint('Please select connection and date range');
			return;
		}
		
		frappe.call({
			method: 'erpnextswiss.erpnextswiss.page.ebics_test_center.ebics_test_center.test_download_statements',
			args: {
				connection: connection,
				from_date: fromDate,
				to_date: toDate,
				order_type: orderType
			},
			callback: function(r) {
				if (r.message) {
					let type = r.message.success ? 'success' : 'error';
					showResult('statement-result', JSON.stringify(r.message, null, 2), type);
				}
			}
		});
	});

	$('#run-comparison').click(function() {
		frappe.call({
			method: 'erpnextswiss.erpnextswiss.page.ebics_test_center.ebics_test_center.run_comparison_test',
			callback: function(r) {
				if (r.message) {
					showResult('comparison-result', JSON.stringify(r.message, null, 2), 'info');
				}
			}
		});
	});

	// Key Management handlers
	console.log('EBICS Test Center: Setting up key management handlers...');
	console.log('Generate keys button found:', $('#generate-keys').length);
	console.log('Print INI letter button found:', $('#print-ini-letter').length);
	console.log('All test buttons found:', $('.test-button').length);
	
	$('#generate-keys').click(function() {
		console.log('Generate keys clicked!');
		let connection = $('#connection-select').val();
		if (!connection) {
			frappe.msgprint('Please select a connection first');
			return;
		}
		
		let $btn = $(this);
		$btn.prop('disabled', true).html('<i class="fa fa-spinner fa-spin"></i> Generating...');
		
		frappe.confirm(
			'This will generate new RSA keys and deactivate the connection. Continue?',
			function() {
				frappe.call({
					method: 'erpnextswiss.erpnextswiss.page.ebics_test_center.ebics_test_center.generate_keys',
					args: {
						connection: connection
					},
					callback: function(r) {
						$btn.prop('disabled', false).html('<i class="fa fa-key"></i> Generate Keys');
						if (r.message) {
							let type = r.message.success ? 'success' : 'error';
							showResult('key-management-result', JSON.stringify(r.message, null, 2), type);
							if (r.message.success) {
								frappe.msgprint('Keys generated successfully!');
								loadConnections(); // Reload to update status
							}
						}
					},
					error: function(r) {
						$btn.prop('disabled', false).html('<i class="fa fa-key"></i> Generate Keys');
						showResult('key-management-result', 'Error: ' + (r.message || 'Failed to generate keys'), 'error');
					}
				});
			},
			function() {
				$btn.prop('disabled', false).html('<i class="fa fa-key"></i> Generate Keys');
			}
		);
	});

	$('#send-ini').click(function() {
		let connection = $('#connection-select').val();
		if (!connection) {
			frappe.msgprint('Please select a connection first');
			return;
		}
		
		let $btn = $(this);
		$btn.prop('disabled', true).html('<i class="fa fa-spinner fa-spin"></i> Sending INI...');
		showResult('key-management-result', 'Sending INI order to bank...', 'info');
		
		frappe.call({
			method: 'erpnextswiss.erpnextswiss.page.ebics_test_center.ebics_test_center.send_ini',
			args: {
				connection: connection
			},
			callback: function(r) {
				$btn.prop('disabled', false).html('<i class="fa fa-upload"></i> Send INI');
				if (r.message) {
					let type = r.message.success ? 'success' : 'error';
					showResult('key-management-result', JSON.stringify(r.message, null, 2), type);
					if (r.message.success) {
						frappe.msgprint('INI sent successfully!');
					} else {
						frappe.msgprint('Failed to send INI: ' + (r.message.error || 'Unknown error'));
					}
				}
			},
			error: function(r) {
				$btn.prop('disabled', false).html('<i class="fa fa-upload"></i> Send INI');
				showResult('key-management-result', 'Error: ' + (r.message || 'Failed to send INI'), 'error');
				frappe.msgprint('Error sending INI');
			}
		});
	});

	$('#send-hia').click(function() {
		let connection = $('#connection-select').val();
		if (!connection) {
			frappe.msgprint('Please select a connection first');
			return;
		}
		
		let $btn = $(this);
		$btn.prop('disabled', true).html('<i class="fa fa-spinner fa-spin"></i> Sending HIA...');
		showResult('key-management-result', 'Sending HIA order to bank...', 'info');
		
		frappe.call({
			method: 'erpnextswiss.erpnextswiss.page.ebics_test_center.ebics_test_center.send_hia',
			args: {
				connection: connection
			},
			callback: function(r) {
				$btn.prop('disabled', false).html('<i class="fa fa-upload"></i> Send HIA');
				if (r.message) {
					let type = r.message.success ? 'success' : 'error';
					showResult('key-management-result', JSON.stringify(r.message, null, 2), type);
					if (r.message.success) {
						frappe.msgprint('HIA sent successfully!');
					} else {
						frappe.msgprint('Failed to send HIA: ' + (r.message.error || 'Unknown error'));
					}
				}
			},
			error: function(r) {
				$btn.prop('disabled', false).html('<i class="fa fa-upload"></i> Send HIA');
				showResult('key-management-result', 'Error: ' + (r.message || 'Failed to send HIA'), 'error');
				frappe.msgprint('Error sending HIA');
			}
		});
	});

	$('#download-hpb').click(function() {
		let connection = $('#connection-select').val();
		if (!connection) {
			frappe.msgprint('Please select a connection first');
			return;
		}
		
		let $btn = $(this);
		$btn.prop('disabled', true).html('<i class="fa fa-spinner fa-spin"></i> Downloading HPB...');
		showResult('key-management-result', 'Downloading bank public keys...', 'info');
		
		frappe.call({
			method: 'erpnextswiss.erpnextswiss.page.ebics_test_center.ebics_test_center.download_hpb',
			args: {
				connection: connection
			},
			callback: function(r) {
				$btn.prop('disabled', false).html('<i class="fa fa-download"></i> Download HPB');
				if (r.message) {
					let type = r.message.success ? 'success' : 'error';
					showResult('key-management-result', JSON.stringify(r.message, null, 2), type);
					if (r.message.success) {
						frappe.msgprint('HPB downloaded successfully! Connection activated.');
						loadConnections(); // Reload to update status
					} else {
						frappe.msgprint('Failed to download HPB: ' + (r.message.error || 'Unknown error'));
					}
				}
			},
			error: function(r) {
				$btn.prop('disabled', false).html('<i class="fa fa-download"></i> Download HPB');
				showResult('key-management-result', 'Error: ' + (r.message || 'Failed to download HPB'), 'error');
				frappe.msgprint('Error downloading HPB');
			}
		});
	});

	$('#print-ini-letter').click(function() {
		console.log('Print INI Letter clicked');
		let connection = $('#connection-select').val();
		console.log('Selected connection:', connection);
		
		if (!connection) {
			frappe.msgprint('Please select a connection first');
			return;
		}
		
		let $btn = $(this);
		$btn.prop('disabled', true).html('<i class="fa fa-spinner fa-spin"></i> Generating...');
		showResult('key-management-result', 'Generating INI letter...', 'info');
		
		console.log('Calling create_bank_letter method...');
		frappe.call({
			method: 'erpnextswiss.erpnextswiss.page.ebics_test_center.ebics_test_center.create_bank_letter',
			args: {
				connection: connection
			},
			callback: function(r) {
				console.log('Response received:', r);
				$btn.prop('disabled', false).html('<i class="fa fa-print"></i> Print INI Letter');
				
				if (r.message && r.message.success && r.message.pdf_base64) {
					console.log('PDF generated, opening...');
					
					// Create blob from base64 PDF
					const pdfData = atob(r.message.pdf_base64);
					const pdfArray = new Uint8Array(pdfData.length);
					for (let i = 0; i < pdfData.length; i++) {
						pdfArray[i] = pdfData.charCodeAt(i);
					}
					const pdfBlob = new Blob([pdfArray], { type: 'application/pdf' });
					const pdfUrl = URL.createObjectURL(pdfBlob);
					
					// Open PDF in new tab
					window.open(pdfUrl, '_blank');
					
					showResult('key-management-result', 'PDF generated successfully', 'success');
					frappe.msgprint('INI letter PDF opened in new tab!');
					return;
				}
				
				// If we have an error
				if (r.message && !r.message.success) {
					console.error('Error generating letter:', r.message.error || 'Unknown error');
					showResult('key-management-result', 'Failed to generate INI letter: ' + (r.message.error || 'Unknown error'), 'error');
					frappe.msgprint('Failed to generate INI letter: ' + (r.message.error || 'Unknown error'));
				} else if (!r.message) {
					console.error('No message in response:', r);
					showResult('key-management-result', 'No response from server', 'error');
				}
			},
			error: function(r) {
				console.error('AJAX error:', r);
				$btn.prop('disabled', false).html('<i class="fa fa-print"></i> Print INI Letter');
				showResult('key-management-result', 'Error: ' + (r.message || 'Failed to generate INI letter'), 'error');
				frappe.msgprint('Error generating INI letter');
			}
		});
	});

	// Initialize
	console.log('EBICS Test Center: Initializing...');
	loadConnections();
	loadPaymentProposals();
	
	// Set default dates
	let today = new Date();
	let yesterday = new Date(today);
	yesterday.setDate(yesterday.getDate() - 1);
	
	$('#to-date').val(today.toISOString().split('T')[0]);
	$('#from-date').val(yesterday.toISOString().split('T')[0]);
	
	addLog('EBICS Test Center initialized');
};