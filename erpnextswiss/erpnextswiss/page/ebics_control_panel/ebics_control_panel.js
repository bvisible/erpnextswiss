frappe.pages['ebics-control-panel'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('EBICS Control Panel'),
		single_column: true
	});

	// Create the control panel and make it globally accessible
	frappe.ebics_control_panel = new EBICSControlPanel(page);
}

class EBICSControlPanel {
	constructor(page) {
		this.page = page;
		this.connection = null;
		this.make();
		this.bind_events();
	}

	make() {
		// Add custom CSS
		this.add_styles();
		
		// Connection selector
		this.make_connection_selector();
		
		// Main content area
		this.make_content_area();
		
		// Load first connection if exists
		this.load_connections();
	}

	add_styles() {
		const style = `
			<style>
				.ebics-control-panel {
					padding: 20px;
				}
				.workflow-timeline {
					display: flex;
					justify-content: space-between;
					margin: 30px 0;
					position: relative;
				}
				.workflow-timeline::before {
					content: '';
					position: absolute;
					top: 25px;
					left: 50px;
					right: 50px;
					height: 2px;
					background: #e0e0e0;
					z-index: 0;
				}
				.workflow-step {
					text-align: center;
					position: relative;
					z-index: 1;
					flex: 1;
				}
				.step-icon {
					width: 50px;
					height: 50px;
					border-radius: 50%;
					background: #f5f5f5;
					display: flex;
					align-items: center;
					justify-content: center;
					margin: 0 auto 10px;
					border: 2px solid #e0e0e0;
					transition: all 0.3s;
				}
				.workflow-step.completed .step-icon {
					background: #28a745;
					border-color: #28a745;
					color: white;
				}
				.workflow-step.active .step-icon {
					background: #007bff;
					border-color: #007bff;
					color: white;
					animation: pulse 2s infinite;
				}
				.workflow-step.error .step-icon {
					background: #dc3545;
					border-color: #dc3545;
					color: white;
				}
				@keyframes pulse {
					0% { box-shadow: 0 0 0 0 rgba(0,123,255,0.7); }
					70% { box-shadow: 0 0 0 10px rgba(0,123,255,0); }
					100% { box-shadow: 0 0 0 0 rgba(0,123,255,0); }
				}
				.step-label {
					font-size: 12px;
					color: #666;
				}
				.workflow-step.completed .step-label {
					color: #28a745;
					font-weight: bold;
				}
				.action-buttons {
					display: grid;
					grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
					gap: 15px;
					margin: 30px 0;
				}
				.action-button {
					padding: 15px;
					text-align: center;
					border: 1px solid #e0e0e0;
					border-radius: 8px;
					cursor: pointer;
					transition: all 0.3s;
				}
				.action-button:hover {
					background: #f8f9fa;
					border-color: #007bff;
					transform: translateY(-2px);
					box-shadow: 0 4px 8px rgba(0,0,0,0.1);
				}
				.action-button.disabled {
					opacity: 0.5;
					cursor: not-allowed;
				}
				.action-button i {
					font-size: 24px;
					margin-bottom: 10px;
					display: block;
				}
				.status-card {
					background: #f8f9fa;
					border-radius: 8px;
					padding: 20px;
					margin: 20px 0;
				}
				.status-grid {
					display: grid;
					grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
					gap: 15px;
				}
				.status-item {
					display: flex;
					align-items: center;
					padding: 10px;
					background: white;
					border-radius: 4px;
				}
				.status-icon {
					margin-right: 10px;
					font-size: 18px;
				}
				.status-icon.success { color: #28a745; }
				.status-icon.error { color: #dc3545; }
				.status-icon.warning { color: #ffc107; }
				.status-icon.info { color: #17a2b8; }
				.result-area {
					margin-top: 30px;
				}
				.result-content {
					background: #f8f9fa;
					border: 1px solid #dee2e6;
					border-radius: 4px;
					padding: 15px;
					font-family: monospace;
					font-size: 12px;
					max-height: 400px;
					overflow-y: auto;
				}
			</style>
		`;
		$(style).appendTo('head');
	}

	make_connection_selector() {
		this.connection_field = frappe.ui.form.make_control({
			parent: this.page.main,
			df: {
				fieldtype: 'Link',
				options: 'ebics Connection',
				label: __('ebics Connection'),
				placeholder: __('Select an ebics Connection'),
				change: () => this.on_connection_change()
			},
			render_input: true
		});
		this.connection_field.refresh();
	}

	make_content_area() {
		// Create tabs structure
		const is_admin = frappe.user_roles.includes('Administrator');
		
		this.content = $(`
			<div class="ebics-control-panel">
				<div class="nav nav-tabs" role="tablist">
					<button class="nav-link active" data-tab="workflow">Workflow</button>
					${is_admin ? `<button class="nav-link" data-tab="developer">Developer Tools</button>` : ''}
				</div>
				
				<div class="tab-content">
					<div class="tab-pane show active" data-pane="workflow">
						<div class="connection-info"></div>
						<div class="workflow-area"></div>
						<div class="action-area"></div>
						<div class="result-area"></div>
					</div>
					${is_admin ? `
					<div class="tab-pane" data-pane="developer" style="display: none;">
						<div class="developer-tools-area"></div>
					</div>
					` : ''}
				</div>
			</div>
		`).appendTo(this.page.main);
		
		// Bind tab switching
		this.content.find('.nav-link').on('click', (e) => {
			const tab = $(e.currentTarget).data('tab');
			this.switch_tab(tab);
		});
		
		// Initialize developer tools if admin
		if (is_admin) {
			this.init_developer_tools();
		}
	}
	
	switch_tab(tab) {
		// Update nav
		this.content.find('.nav-link').removeClass('active');
		this.content.find(`.nav-link[data-tab="${tab}"]`).addClass('active');
		
		// Update content
		this.content.find('.tab-pane').hide();
		this.content.find(`.tab-pane[data-pane="${tab}"]`).show();
	}

	load_connections() {
		// First check localStorage for saved connection
		const savedConnection = localStorage.getItem('ebics_control_panel_connection');
		
		if (savedConnection) {
			// Try to set the saved connection
			this.connection_field.set_value(savedConnection);
		} else {
			// Otherwise load the first connection
			frappe.call({
				method: 'frappe.client.get_list',
				args: {
					doctype: 'ebics Connection',
					fields: ['name'],
					limit: 1
				},
				callback: (r) => {
					if (r.message && r.message.length > 0) {
						this.connection_field.set_value(r.message[0].name);
					}
				}
			});
		}
	}

	on_connection_change() {
		const connection_name = this.connection_field.get_value();
		if (!connection_name) {
			this.clear_content();
			// Remove from localStorage if cleared
			localStorage.removeItem('ebics_control_panel_connection');
			return;
		}

		// Save to localStorage for next time
		localStorage.setItem('ebics_control_panel_connection', connection_name);

		frappe.call({
			method: 'frappe.client.get',
			args: {
				doctype: 'ebics Connection',
				name: connection_name
			},
			callback: (r) => {
				if (r.message) {
					this.connection = r.message;
					this.render_connection();
				}
			}
		});
	}

	render_connection() {
		// Connection info
		this.render_connection_info();
		
		// Workflow timeline
		this.render_workflow();
		
		// Action buttons
		this.render_actions();
		
		// Clear results
		this.content.find('.result-area').empty();
		
		// Refresh developer tools with new connection info
		if (frappe.user_roles.includes('System Manager') || frappe.user_roles.includes('Administrator')) {
			this.init_developer_tools();
		}
	}

	render_connection_info() {
		const info_html = `
			<div class="status-card">
				<h4>${__('Connection Details')}</h4>
				<div class="status-grid">
					<div class="status-item">
						<span class="status-icon info"><i class="fa fa-bank"></i></span>
						<div>
							<div class="text-muted small">${__('Bank')}</div>
							<div><strong>${this.connection.title || 'N/A'}</strong></div>
						</div>
					</div>
					<div class="status-item">
						<span class="status-icon info"><i class="fa fa-server"></i></span>
						<div>
							<div class="text-muted small">${__('Host ID')}</div>
							<div><strong>${this.connection.host_id || 'N/A'}</strong></div>
						</div>
					</div>
					<div class="status-item">
						<span class="status-icon info"><i class="fa fa-user"></i></span>
						<div>
							<div class="text-muted small">${__('User ID')}</div>
							<div><strong>${this.connection.user_id || 'N/A'}</strong></div>
						</div>
					</div>
					<div class="status-item">
						<span class="status-icon ${this.connection.activated ? 'success' : 'warning'}">
							<i class="fa fa-${this.connection.activated ? 'check-circle' : 'clock-o'}"></i>
						</span>
						<div>
							<div class="text-muted small">${__('Status')}</div>
							<div><strong>${this.connection.activated ? __('Active') : __('Not Active')}</strong></div>
						</div>
					</div>
				</div>
			</div>
		`;
		this.content.find('.connection-info').html(info_html);
	}

	render_workflow() {
		const steps = [
			{id: 'keys', label: __('Generate Keys'), icon: 'fa-key', completed: this.connection.keys_created},
			{id: 'ini', label: __('Send INI'), icon: 'fa-upload', completed: this.connection.ini_sent},
			{id: 'hia', label: __('Send HIA'), icon: 'fa-upload', completed: this.connection.hia_sent},
			{id: 'letter', label: __('Print Letter'), icon: 'fa-file-pdf-o', completed: this.connection.ini_letter_created || 0},
			{id: 'bank', label: __('Bank Activation'), icon: 'fa-bank', completed: this.connection.bank_activation_confirmed || 0},
			{id: 'hpb', label: __('Download HPB'), icon: 'fa-download', completed: this.connection.hpb_downloaded},
			{id: 'active', label: __('Active'), icon: 'fa-check-circle', completed: this.connection.activated}
		];

		let workflow_html = '<div class="workflow-timeline">';
		steps.forEach(step => {
			const status = step.completed ? 'completed' : '';
			workflow_html += `
				<div class="workflow-step ${status}" data-step="${step.id}">
					<div class="step-icon">
						<i class="fa ${step.icon}"></i>
					</div>
					<div class="step-label">${step.label}</div>
				</div>
			`;
		});
		workflow_html += '</div>';

		this.content.find('.workflow-area').html(workflow_html);
	}

	render_actions() {
		const actions = [
			{
				id: 'generate_keys',
				label: __('Generate Keys'),
				icon: 'fa-key',
				color: 'primary',
				enabled: !this.connection.keys_created
			},
			{
				id: 'send_ini',
				label: __('Send INI'),
				icon: 'fa-upload',
				color: 'info',
				enabled: this.connection.keys_created && !this.connection.ini_sent
			},
			{
				id: 'send_hia',
				label: __('Send HIA'),
				icon: 'fa-upload',
				color: 'info',
				enabled: this.connection.keys_created && !this.connection.hia_sent
			},
			{
				id: 'generate_letter',
				label: __('Generate INI Letter'),
				icon: 'fa-file-pdf-o',
				color: 'warning',
				enabled: this.connection.ini_sent && this.connection.hia_sent
			},
			{
				id: 'confirm_activation',
				label: __('Check & Confirm Activation'),
				icon: 'fa-check-square',
				color: 'warning',
				enabled: (this.connection.ini_letter_created || 0) && !(this.connection.bank_activation_confirmed || 0)
			},
			{
				id: 'download_hpb',
				label: __('Download Bank Keys (HPB)'),
				icon: 'fa-download',
				color: 'success',
				enabled: (this.connection.bank_activation_confirmed || 0) && !this.connection.hpb_downloaded
			},
			{
				id: 'test_connection',
				label: __('Test Connection'),
				icon: 'fa-plug',
				color: 'secondary',
				enabled: true
			},
			{
				id: 'reset_connection',
				label: __('Reset Connection'),
				icon: 'fa-refresh',
				color: 'danger',
				enabled: true
			}
		];

		let actions_html = '<div class="action-buttons">';
		actions.forEach(action => {
			const disabled = !action.enabled ? 'disabled' : '';
			actions_html += `
				<div class="action-button ${disabled}" data-action="${action.id}">
					<i class="fa ${action.icon} text-${action.color}"></i>
					<div>${action.label}</div>
				</div>
			`;
		});
		actions_html += '</div>';

		this.content.find('.action-area').html(actions_html);
	}

	bind_events() {
		this.content.on('click', '.action-button:not(.disabled)', (e) => {
			const action = $(e.currentTarget).data('action');
			this.execute_action(action);
		});
	}

	execute_action(action) {
		// Special handling for confirm activation - Test if we can download HPB
		if (action === 'confirm_activation') {
			frappe.show_alert({
				message: __('Testing bank activation...'),
				indicator: 'blue'
			});
			
			// Try to download HPB to see if activation is complete
			frappe.call({
				method: 'erpnextswiss.erpnextswiss.ebics_manager.execute_ebics_order',
				args: {
					connection: this.connection.name,
					action: 'HPB'
				},
				freeze: true,
				freeze_message: __('Checking activation status...'),
				callback: (r) => {
					if (r.message && r.message.success) {
						// HPB download successful - mark as activated
						frappe.call({
							method: 'erpnextswiss.erpnextswiss.ebics_manager.confirm_bank_activation',
							args: {
								connection: this.connection.name
							},
							callback: () => {
								frappe.show_alert({
									message: __('Bank activation confirmed! Connection is now active.'),
									indicator: 'green'
								});
								this.refresh_status_only();
							}
						});
					} else {
						// Show the actual error from bank
						const errorMsg = r.message ? (r.message.message || r.message.error) : 'Unknown error';
						frappe.show_alert({
							message: __('Bank has not yet activated your access: ') + errorMsg,
							indicator: 'orange'
						});
					}
				}
			});
			return;
		}

		// Special handling for reset action
		if (action === 'reset_connection') {
			frappe.confirm(
				__('Are you sure you want to reset this EBICS connection? This will delete all keys and reset the initialization process.'),
				() => {
					frappe.call({
						method: 'erpnextswiss.erpnextswiss.ebics_manager.reset_ebics_connection',
						args: {
							connection: this.connection.name
						},
						freeze: true,
						freeze_message: __('Resetting EBICS connection...'),
						callback: (r) => {
							if (r.message.success) {
								frappe.show_alert({
									message: r.message.message,
									indicator: 'green'
								});
								// Reload connection to show reset status
								this.on_connection_change();
							} else {
								frappe.show_alert({
									message: r.message.error || __('Reset failed'),
									indicator: 'red'
								});
							}
						}
					});
				}
			);
			return;
		}

		const action_map = {
			'generate_keys': 'erpnextswiss.erpnextswiss.ebics_manager.execute_ebics_order',
			'send_ini': 'erpnextswiss.erpnextswiss.ebics_manager.execute_ebics_order',
			'send_hia': 'erpnextswiss.erpnextswiss.ebics_manager.execute_ebics_order',
			'generate_letter': 'erpnextswiss.erpnextswiss.ebics_manager.execute_ebics_order',
			'download_hpb': 'erpnextswiss.erpnextswiss.ebics_manager.execute_ebics_order',
			'test_connection': 'erpnextswiss.erpnextswiss.ebics_manager.test_ebics_connection'
		};

		const action_param_map = {
			'generate_keys': 'GENERATE_KEYS',
			'send_ini': 'INI',
			'send_hia': 'HIA',
			'generate_letter': 'GET_INI_LETTER',
			'download_hpb': 'HPB'
		};

		let method = action_map[action];
		
		// Ensure we have a connection loaded
		if (!this.connection || !this.connection.name) {
			frappe.show_alert({
				message: __('No connection selected'),
				indicator: 'red'
			});
			return;
		}
		
		let args = {
			connection: this.connection.name
		};

		if (action !== 'test_connection') {
			args.action = action_param_map[action];
		}

		frappe.call({
			method: method,
			args: args,
			freeze: true,
			freeze_message: __('Processing EBICS request...'),
			callback: (r) => {
				this.handle_response(action, r.message);
				// Only reload the workflow and actions, not everything
				this.refresh_status_only();
			},
			error: (r) => {
				this.show_error(r.message);
			}
		});
	}

	handle_response(action, response) {
		let result_html = '';
		
		// Handle 091002 as a special case - awaiting bank activation
		if (response.code === '091002' || response.awaiting_activation) {
			// This is expected - show as warning, not error
			result_html += `
				<div class="alert alert-warning">
					<i class="fa fa-clock-o"></i> ${__('Awaiting Bank Activation')}
					<div class="mt-2">
						${response.message || __('The bank has not yet activated your EBICS access. Please ensure your INI letter has been processed.')}
					</div>
				</div>
			`;
			
			// If this is INI or HIA with 091002, treat as workflow success
			if (response.workflow_success) {
				result_html += `
					<div class="alert alert-info mt-2">
						<i class="fa fa-info-circle"></i> ${__('Order sent successfully. You can proceed with the next step.')}
					</div>
				`;
			}
		} else if (response.success) {
			result_html += `
				<div class="alert alert-success">
					<i class="fa fa-check-circle"></i> ${__('Success')}
				</div>
			`;
			
			// Special handling for INI letter
			if (action === 'generate_letter' && response.content) {
				this.download_pdf(response);
				// Force refresh after letter generation to update the icon
				setTimeout(() => {
					this.refresh_status_only();
				}, 500);
			}
		} else {
			const message = response.message || response.error || __('Operation failed');
			const code = response.code ? ` (${response.code})` : '';
			
			result_html += `
				<div class="alert alert-danger">
					<i class="fa fa-exclamation-circle"></i> ${__('Error')}${code}
					<div class="mt-2">${message}</div>
				</div>
			`;
		}

		// Show details if available
		if (response.details || response.data) {
			result_html += `
				<div class="result-content">
					<pre>${JSON.stringify(response.details || response.data || response, null, 2)}</pre>
				</div>
			`;
		}

		// Update the existing result-area div
		this.content.find('.result-area').html(result_html);
	}

	// Fonction supprimée - définie uniquement dans init_developer_tools pour éviter la duplication
	
	download_test_file(response) {
		if (response.content && response.format) {
			const blob = new Blob([atob(response.content)], {
				type: response.format === 'XML' ? 'application/xml' : 
				      response.format === 'PDF' ? 'application/pdf' : 
				      'application/octet-stream'
			});
			const url = window.URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = response.filename || `ebics_${response.format}.${response.format.toLowerCase()}`;
			document.body.appendChild(a);
			a.click();
			window.URL.revokeObjectURL(url);
			document.body.removeChild(a);
		}
	}

	download_pdf(response) {
		if (response.format === 'pdf' && response.content) {
			const link = document.createElement('a');
			link.href = 'data:application/pdf;base64,' + response.content;
			link.download = response.filename || 'EBICS_Document.pdf';
			link.click();
			
			frappe.show_alert({
				message: __('PDF downloaded successfully'),
				indicator: 'green'
			});
		}
	}

	show_error(message) {
		this.content.find('.result-area').html(`
			<div class="alert alert-danger">
				<i class="fa fa-exclamation-triangle"></i> ${message || __('An error occurred')}
			</div>
		`);
	}

	refresh_status_only() {
		// Reload connection data without clearing results
		const connection_name = this.connection_field.get_value();
		if (!connection_name) return;

		frappe.call({
			method: 'frappe.client.get',
			args: {
				doctype: 'ebics Connection',
				name: connection_name
			},
			callback: (r) => {
				if (r.message) {
					this.connection = r.message;
					// Only update workflow and actions, keep results
					this.render_workflow();
					this.render_actions();
				}
			}
		});
	}

	clear_content() {
		this.content.find('.connection-info').empty();
		this.content.find('.workflow-area').empty();
		this.content.find('.action-area').empty();
		this.content.find('.result-area').empty();
	}
	
	detectEbicsVersion() {
		// Detect actual EBICS version based on connection settings
		if (!this.connection) {
			return {
				protocol: 'Unknown',
				version: 'Unknown',
				bank: 'No connection',
				description: 'Please select a connection',
				isEbics30: false,
				isEbics25: false
			};
		}
		
		const ebicsVersion = this.connection.ebics_version || 'H005';
		const bankUrl = this.connection.url || this.connection.bank_url || '';
		const bankDomain = this.extractBankDomain(bankUrl);
		
		// Determine actual version based on bank and protocol
		// H005 can be either EBICS 2.5 or 3.0 depending on the bank
		let actualVersion = 'VERSION_25'; // Default
		let isEbics30 = false;
		let isEbics25 = false;
		
		if (ebicsVersion === 'H006') {
			// H006 is always EBICS 3.0
			actualVersion = 'VERSION_30';
			isEbics30 = true;
		} else if (ebicsVersion === 'H005') {
			// H005 depends on the bank
			// Check known banks
			if (bankDomain.includes('ubs.com')) {
				// UBS uses EBICS 3.0 with H005
				actualVersion = 'VERSION_30';
				isEbics30 = true;
			} else if (bankDomain.includes('credit-suisse.com') || 
					   bankDomain.includes('raiffeisen.ch') ||
					   bankDomain.includes('postfinance.ch') ||
					   bankDomain.includes('zkb.ch')) {
				// These banks use EBICS 2.5 with H005
				actualVersion = 'VERSION_25';
				isEbics25 = true;
			} else {
				// Default to 2.5 for unknown banks with H005
				actualVersion = 'VERSION_25';
				isEbics25 = true;
			}
		} else if (ebicsVersion === 'H004') {
			// H004 is EBICS 2.4
			actualVersion = 'VERSION_24';
			isEbics25 = true; // Close enough for our purposes
		}
		
		return {
			protocol: ebicsVersion,
			version: actualVersion,
			bank: bankDomain || 'Unknown',
			description: isEbics30 ? 'Using BTU orders for uploads' : 'Using FUL orders for uploads',
			isEbics30: isEbics30,
			isEbics25: isEbics25
		};
	}
	
	extractBankDomain(url) {
		if (!url) return '';
		try {
			const urlObj = new URL(url);
			return urlObj.hostname;
		} catch (e) {
			// If URL parsing fails, try to extract domain manually
			const match = url.match(/:\/\/([^/]+)/);
			return match ? match[1] : url;
		}
	}
	
	init_developer_tools() {
		const dev_area = this.content.find('.developer-tools-area');
		
		// Calculate default dates (today and 7 days ago)
		const today = new Date();
		const sevenDaysAgo = new Date();
		sevenDaysAgo.setDate(today.getDate() - 7);
		
		// Format dates as YYYY-MM-DD
		const formatDate = (date) => {
			const year = date.getFullYear();
			const month = String(date.getMonth() + 1).padStart(2, '0');
			const day = String(date.getDate()).padStart(2, '0');
			return `${year}-${month}-${day}`;
		};
		
		const todayStr = formatDate(today);
		const sevenDaysAgoStr = formatDate(sevenDaysAgo);
		
		// Detect EBICS version for this connection
		const versionInfo = this.detectEbicsVersion();
		
		// Generate upload buttons based on detected version
		let uploadButtons = '';
		if (versionInfo.isEbics30) {
			// EBICS 3.0 - Use BTU orders (CCT/CDD)
			uploadButtons = `
				<button class="btn btn-sm btn-primary mb-2" data-dev-action="CCT">
					<i class="fa fa-upload"></i> CCT - Credit Transfer (pain.001)
				</button><br>
				<button class="btn btn-sm btn-primary mb-2" data-dev-action="CDD">
					<i class="fa fa-upload"></i> CDD - Direct Debit (pain.008)
				</button><br>
				<button class="btn btn-sm btn-default mb-2" data-dev-action="FUL" disabled>
					<i class="fa fa-ban"></i> FUL - Not available in EBICS 3.0
				</button><br>
			`;
		} else {
			// EBICS 2.5 or older - Use FUL for uploads
			uploadButtons = `
				<button class="btn btn-sm btn-primary mb-2" data-dev-action="FUL_CCT">
					<i class="fa fa-upload"></i> Upload Credit Transfer (FUL/pain.001)
				</button><br>
				<button class="btn btn-sm btn-primary mb-2" data-dev-action="FUL_CDD">
					<i class="fa fa-upload"></i> Upload Direct Debit (FUL/pain.008)
				</button><br>
				<button class="btn btn-sm btn-info mb-2" data-dev-action="FUL">
					<i class="fa fa-file"></i> FUL - Generic File Upload
				</button><br>
			`;
		}
		
		dev_area.html(`
			<div class="developer-tools-content">
				<h4>EBICS Developer Tools</h4>
				
				<!-- Version Info Box -->
				<div class="alert alert-info mb-3">
					<strong>EBICS Configuration Detected:</strong><br>
					<i class="fa fa-server"></i> Protocol: <strong>${versionInfo.protocol}</strong> | 
					<i class="fa fa-code-branch"></i> Version: <strong>${versionInfo.version}</strong> | 
					<i class="fa fa-bank"></i> Bank: <strong>${versionInfo.bank}</strong><br>
					<small class="text-muted">${versionInfo.description}</small>
				</div>
				
				<div class="row mt-4">
					<div class="col-md-6">
						<h5>Download Orders</h5>
						<div class="dev-actions" data-category="download">
							<button class="btn btn-sm btn-default mb-2" data-dev-action="Z53">Z53 - Statement (camt.053)</button><br>
							<button class="btn btn-sm btn-default mb-2" data-dev-action="Z54">Z54 - Intraday (camt.052)</button><br>
							<button class="btn btn-sm btn-default mb-2" data-dev-action="FDL">FDL - File Download</button><br>
							<button class="btn btn-sm btn-default mb-2" data-dev-action="HAA">HAA - Available Order Types</button><br>
							<button class="btn btn-sm btn-default mb-2" data-dev-action="HTD">HTD - Transaction Details</button><br>
							<button class="btn btn-sm btn-default mb-2" data-dev-action="PTK">PTK - Transaction Status</button>
						</div>
					</div>
					<div class="col-md-6">
						<h5>Upload Orders</h5>
						<div class="upload-test-area mb-3">
							<label>Upload Test XML:</label>
							<textarea id="upload-xml-content" class="form-control" rows="4" placeholder="Paste your pain.001 (CCT) or pain.008 (CDD) XML content here..."></textarea>
							<div class="mt-2">
								<button class="btn btn-xs btn-info" onclick="frappe.ebics_control_panel.load_sample_xml('cct')">Load Sample CCT</button>
								<button class="btn btn-xs btn-info" onclick="frappe.ebics_control_panel.load_sample_xml('cdd')">Load Sample CDD</button>
							</div>
						</div>
						<div class="dev-actions" data-category="upload">
							${uploadButtons}
							<button class="btn btn-sm btn-warning mb-2" id="test-params-btn">TEST PARAMS</button>
						</div>
						<!-- Admin Functions not supported in node-ebics-client
						<h5 class="mt-3">Admin Functions</h5>
						<div class="dev-actions" data-category="admin">
							<button class="btn btn-sm btn-default mb-2" data-dev-action="HVE">HVE - VEU Overview</button><br>
							<button class="btn btn-sm btn-default mb-2" data-dev-action="HVU">HVU - VEU Details</button><br>
							<button class="btn btn-sm btn-default mb-2" data-dev-action="HKD">HKD - Customer Info</button>
						</div>
						-->
					</div>
				</div>
				<div class="row mt-4">
					<div class="col-md-12">
						<h5>Test Parameters</h5>
						<div class="test-params">
							<div class="row">
								<div class="col-md-4">
									<label>Date From</label>
									<input type="date" class="form-control" id="test-date-from" value="${sevenDaysAgoStr}">
								</div>
								<div class="col-md-4">
									<label>Date To</label>
									<input type="date" class="form-control" id="test-date-to" value="${todayStr}">
								</div>
								<div class="col-md-4">
									<label>Format</label>
									<select class="form-control" id="test-format">
										<option value="">Auto</option>
										<option value="camt.053">camt.053</option>
										<option value="camt.052">camt.052</option>
										<option value="camt.054">camt.054</option>
										<option value="pain.001">pain.001</option>
										<option value="pain.008">pain.008</option>
									</select>
								</div>
							</div>
						</div>
					</div>
				</div>
				<div class="row mt-4">
					<div class="col-md-12">
						<h5>Results</h5>
						<div class="dev-results">
							<pre style="background: #f8f9fa; padding: 15px; border-radius: 4px; min-height: 200px; max-height: 400px; overflow-y: auto;" id="dev-results-content">
No results yet. Click a button above to test an EBICS function.
							</pre>
						</div>
					</div>
				</div>
			</div>
		`);
		
		// Bind developer tool events
		dev_area.on('click', 'button[data-dev-action]', (e) => {
			const action = $(e.currentTarget).data('dev-action');
			this.execute_dev_action(action);
		});
		
		// Test button for debugging
		dev_area.on('click', '#test-params-btn', () => {
			const xmlContent = $('#upload-xml-content').val();
			console.log('Test button clicked');
			console.log('XML Content length:', xmlContent ? xmlContent.length : 0);
			
			// First test: send params as Frappe normally does
			frappe.call({
				method: 'erpnextswiss.erpnextswiss.ebics_manager.test_params_debug',
				args: {
					action: 'CCT',
					params: {
						xml_content: xmlContent,
						test: 'value'
					}
				},
				callback: (r) => {
					console.log('Test response:', r);
					frappe.show_alert({
						message: `Test result: ${JSON.stringify(r.message)}`,
						indicator: r.message && r.message.success ? 'green' : 'red'
					});
					
					// Now check the Error Log
					if (r.message && !r.message.has_xml) {
						frappe.show_alert({
							message: 'Check Error Log for "Test Params" entries',
							indicator: 'blue'
						});
					}
				}
			});
		});
	}
	
	execute_dev_action(action) {
		if (!this.connection) {
			frappe.show_alert({
				message: __('Please select a connection first'),
				indicator: 'orange'
			});
			return;
		}
		
		// Get test parameters
		const dateFrom = $('#test-date-from').val();
		const dateTo = $('#test-date-to').val();
		const format = $('#test-format').val();
		
		// Prepare params
		let params = {
			dateFrom: dateFrom,
			dateTo: dateTo,
			format: format
		};
		
		// Handle FUL_CCT and FUL_CDD for EBICS 2.5
		let actualAction = action;
		if (action === 'FUL_CCT' || action === 'FUL_CDD') {
			// For EBICS 2.5, use FUL with appropriate XML type
			actualAction = 'FUL';
			params.upload_type = action === 'FUL_CCT' ? 'pain.001' : 'pain.008';
			
			// Auto-load sample if no XML content
			const xmlContent = $('#upload-xml-content').val();
			if (!xmlContent) {
				const sampleType = action === 'FUL_CCT' ? 'cct' : 'cdd';
				this.load_sample_xml(sampleType);
				frappe.show_alert({
					message: `Loading sample ${sampleType.toUpperCase()} XML for EBICS 2.5`,
					indicator: 'blue'
				});
			}
		}
		
		// For upload actions, include XML content
		if (['CCT', 'CDD', 'FUL', 'FUL_CCT', 'FUL_CDD'].includes(action)) {
			// Debug: Check if textarea exists
			const textarea = $('#upload-xml-content');
			
			// Show debug alert
			frappe.show_alert({
				message: `Textarea found: ${textarea.length > 0}, Content length: ${textarea.val() ? textarea.val().length : 0}`,
				indicator: 'blue'
			});
			
			const xmlContent = textarea.val();
			
			if (!xmlContent || xmlContent.trim() === '') {
				// More detailed error message
				frappe.show_alert({
					message: __(`No XML content found. Textarea exists: ${textarea.length > 0}, Value: "${xmlContent}"`),
					indicator: 'orange'
				});
				return;
			}
			params.xml_content = xmlContent;
		}
		
		// Show loading
		$('#dev-results-content').text('Loading...');
		
		frappe.call({
			method: 'erpnextswiss.erpnextswiss.ebics_manager.execute_ebics_order',
			args: {
				connection: this.connection.name,
				action: actualAction,
				params: params
			},
			freeze: true,
			freeze_message: __(`Executing ${actualAction}...`),
			callback: (r) => {
				if (r.message) {
					// Format and display results
					let results = JSON.stringify(r.message, null, 2);
					$('#dev-results-content').text(results);
					
					// Show alert based on success
					if (r.message.success) {
						frappe.show_alert({
							message: __(`${action} executed successfully`),
							indicator: 'green'
						});
					} else {
						frappe.show_alert({
							message: r.message.error || __(`${action} failed`),
							indicator: 'red'
						});
					}
				}
			},
			error: (r) => {
				$('#dev-results-content').text('Error: ' + (r.message || 'Unknown error'));
				frappe.show_alert({
					message: __('Error executing action'),
					indicator: 'red'
				});
			}
		});
	}
	
	load_sample_xml(type) {
		const samples = {
			'cct': `<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.03">
  <CstmrCdtTrfInitn>
    <GrpHdr>
      <MsgId>TEST-CCT-${new Date().getTime()}</MsgId>
      <CreDtTm>${new Date().toISOString()}</CreDtTm>
      <NbOfTxs>1</NbOfTxs>
      <CtrlSum>100.00</CtrlSum>
      <InitgPty><Nm>Test Company</Nm></InitgPty>
    </GrpHdr>
    <PmtInf>
      <PmtInfId>PMT-TEST-001</PmtInfId>
      <PmtMtd>TRF</PmtMtd>
      <ReqdExctnDt>${new Date(Date.now() + 86400000).toISOString().split('T')[0]}</ReqdExctnDt>
      <Dbtr><Nm>Test Debtor</Nm></Dbtr>
      <DbtrAcct><Id><IBAN>CH9300762011623852957</IBAN></Id></DbtrAcct>
      <DbtrAgt><FinInstnId><BIC>CRESCHZZ80A</BIC></FinInstnId></DbtrAgt>
      <CdtTrfTxInf>
        <PmtId>
          <InstrId>INSTR-001</InstrId>
          <EndToEndId>E2E-TEST</EndToEndId>
        </PmtId>
        <Amt><InstdAmt Ccy="CHF">100.00</InstdAmt></Amt>
        <Cdtr><Nm>Test Creditor</Nm></Cdtr>
        <CdtrAcct><Id><IBAN>CH9309000000250097798</IBAN></Id></CdtrAcct>
      </CdtTrfTxInf>
    </PmtInf>
  </CstmrCdtTrfInitn>
</Document>`,
			'cdd': `<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.008.001.02">
  <CstmrDrctDbtInitn>
    <GrpHdr>
      <MsgId>TEST-CDD-${new Date().getTime()}</MsgId>
      <CreDtTm>${new Date().toISOString()}</CreDtTm>
      <NbOfTxs>1</NbOfTxs>
      <CtrlSum>50.00</CtrlSum>
      <InitgPty><Nm>Test Company</Nm></InitgPty>
    </GrpHdr>
    <PmtInf>
      <PmtInfId>DD-TEST-001</PmtInfId>
      <PmtMtd>DD</PmtMtd>
      <ReqdColltnDt>${new Date(Date.now() + 432000000).toISOString().split('T')[0]}</ReqdColltnDt>
      <Cdtr><Nm>Test Creditor</Nm></Cdtr>
      <CdtrAcct><Id><IBAN>CH9300762011623852957</IBAN></Id></CdtrAcct>
      <CdtrAgt><FinInstnId><BIC>CRESCHZZ80A</BIC></FinInstnId></CdtrAgt>
      <DrctDbtTxInf>
        <PmtId>
          <InstrId>DD-INSTR-001</InstrId>
          <EndToEndId>E2E-DD-001</EndToEndId>
        </PmtId>
        <InstdAmt Ccy="CHF">50.00</InstdAmt>
        <DrctDbtTx>
          <MndtRltdInf>
            <MndtId>MANDATE-TEST-001</MndtId>
            <DtOfSgntr>2025-01-01</DtOfSgntr>
          </MndtRltdInf>
        </DrctDbtTx>
        <Dbtr><Nm>Test Debtor</Nm></Dbtr>
        <DbtrAcct><Id><IBAN>CH9309000000250097798</IBAN></Id></DbtrAcct>
      </DrctDbtTxInf>
    </PmtInf>
  </CstmrDrctDbtInitn>
</Document>`
		};
		
		if (samples[type]) {
			$('#upload-xml-content').val(samples[type]);
			frappe.show_alert({
				message: __(`Sample ${type.toUpperCase()} loaded`),
				indicator: 'success'
			});
		}
	}
}