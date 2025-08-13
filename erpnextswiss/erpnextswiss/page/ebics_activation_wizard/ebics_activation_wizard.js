frappe.pages['ebics-activation-wizard'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('EBICS Activation Wizard'),
		single_column: true
	});

	// Create the wizard instance
	new EBICSActivationWizard(page);
};

class EBICSActivationWizard {
	constructor(page) {
		this.page = page;
		this.current_step = 1;
		this.total_steps = 7;
		this.connection = null;
		this.wizard_data = {};
		
		this.steps = [
			{
				id: 1,
				name: __('Connection Setup'),
				icon: 'fa fa-plug',
				description: __('Configure your EBICS connection parameters')
			},
			{
				id: 2,
				name: __('Generate Keys'),
				icon: 'fa fa-key',
				description: __('Create RSA key pairs for secure communication')
			},
			{
				id: 3,
				name: __('Send INI'),
				icon: 'fa fa-send',
				description: __('Send electronic signature to the bank')
			},
			{
				id: 4,
				name: __('Send HIA'),
				icon: 'fa fa-shield',
				description: __('Send authentication and encryption keys')
			},
			{
				id: 5,
				name: __('INI Letter'),
				icon: 'fa fa-file-text',
				description: __('Generate and send initialization letter')
			},
			{
				id: 6,
				name: __('Download Bank Keys'),
				icon: 'fa fa-download',
				description: __('Retrieve bank public keys (HPB)')
			},
			{
				id: 7,
				name: __('Activation'),
				icon: 'fa fa-check-circle',
				description: __('Complete activation and test connection')
			}
		];
		
		this.init();
	}
	
	init() {
		// Add custom CSS with Neoffice style
		this.addStyles();
		
		// Create main container
		this.createMainContainer();
		
		// Load connections or start new
		this.loadConnectionsList();
		
		// Set up event handlers
		this.setupEventHandlers();
		
		// Auto-save every 30 seconds
		setInterval(() => this.autoSave(), 30000);
	}
	
	addStyles() {
		if (!document.getElementById('ebics-wizard-styles')) {
			const style = document.createElement('style');
			style.id = 'ebics-wizard-styles';
			style.textContent = `
				/* Modern Neoffice-inspired Design */
				.ebics-wizard-container {
					padding: 0;
					background: #f8f9fa;
					min-height: calc(100vh - 120px);
				}
				
				/* Header Section */
				.wizard-header {
					background: white;
					padding: 24px 32px;
					border-bottom: 1px solid #e9ecef;
					margin-bottom: 0;
				}
				
				.wizard-header h2 {
					margin: 0;
					font-size: 20px;
					font-weight: 500;
					color: #212529;
					display: flex;
					align-items: center;
					gap: 12px;
				}
				
				.wizard-header h2 i {
					color: #FFA500;
					font-size: 18px;
				}
				
				.wizard-header p {
					margin: 8px 0 0 0;
					color: #6c757d;
					font-size: 13px;
				}
				
				/* Progress Steps */
				.step-indicator-wrapper {
					background: white;
					padding: 24px 32px;
					border-bottom: 1px solid #e9ecef;
					display: flex;
					justify-content: center;
				}
				
				.step-indicator {
					display: flex;
					justify-content: space-between;
					margin: 0;
					position: relative;
					max-width: 900px;
					width: 100%;
				}
				
				.step-indicator::before {
					content: '';
					position: absolute;
					top: 20px;
					left: 50px;
					right: 50px;
					height: 2px;
					background: #e9ecef;
					z-index: 0;
				}
				
				.step-item {
					flex: 1;
					text-align: center;
					position: relative;
					z-index: 1;
				}
				
				.step-circle {
					width: 40px;
					height: 40px;
					border-radius: 50%;
					background: white;
					border: 2px solid #e9ecef;
					margin: 0 auto 8px;
					display: flex;
					align-items: center;
					justify-content: center;
					font-size: 14px;
					color: #adb5bd;
					transition: all 0.2s ease;
					cursor: pointer;
				}
				
				.step-item.active .step-circle {
					background: #FFA500;
					border-color: #FFA500;
					color: white;
					transform: scale(1.05);
				}
				
				.step-item.completed .step-circle {
					background: #28a745;
					border-color: #28a745;
					color: white;
				}
				
				.step-label {
					font-size: 11px;
					color: #6c757d;
					font-weight: 400;
				}
				
				.step-item.active .step-label {
					color: #212529;
					font-weight: 500;
				}
				
				.step-item.completed .step-label {
					color: #28a745;
				}
				
				/* Main Content Area */
				.wizard-main-content {
					display: flex;
					gap: 24px;
					padding: 24px 32px;
					max-width: 1400px;
					margin: 0 auto;
				}
				
				/* Connection Selector */
				.connection-selector {
					background: white;
					border-radius: 8px;
					padding: 24px;
					box-shadow: 0 1px 3px rgba(0,0,0,0.05);
					flex: 0 0 350px;
				}
				
				.connection-selector h4 {
					margin: 0 0 16px 0;
					font-size: 14px;
					font-weight: 500;
					color: #212529;
				}
				
				.connection-list {
					margin: 0 0 16px 0;
				}
				
				.connection-card {
					background: white;
					border: 1px solid #e9ecef;
					border-radius: 6px;
					padding: 12px;
					margin-bottom: 8px;
					cursor: pointer;
					transition: all 0.2s ease;
				}
				
				.connection-card:hover {
					border-color: #FFA500;
					background: #fff9f0;
				}
				
				.connection-card.selected {
					border-color: #FFA500;
					background: #fff9f0;
				}
				
				.connection-card h5 {
					margin: 0 0 4px 0;
					font-size: 13px;
					font-weight: 500;
					color: #212529;
				}
				
				.connection-card p {
					margin: 0;
					font-size: 11px;
					color: #6c757d;
				}
				
				.connection-status {
					display: inline-flex;
					align-items: center;
					gap: 4px;
					padding: 2px 6px;
					border-radius: 3px;
					font-size: 10px;
					font-weight: 500;
					margin-top: 6px;
				}
				
				.connection-status.active {
					background: #d4edda;
					color: #155724;
				}
				
				.connection-status.pending {
					background: #fff3cd;
					color: #856404;
				}
				
				.connection-status.inactive {
					background: #f8d7da;
					color: #721c24;
				}
				
				/* Wizard Content */
				.wizard-content {
					flex: 1;
					background: white;
					border-radius: 8px;
					box-shadow: 0 1px 3px rgba(0,0,0,0.05);
					overflow: hidden;
				}
				
				.step-content {
					padding: 32px;
				}
				
				.step-header {
					margin-bottom: 32px;
				}
				
				.step-header h3 {
					margin: 0 0 8px 0;
					font-size: 18px;
					font-weight: 500;
					color: #212529;
					display: flex;
					align-items: center;
					gap: 10px;
				}
				
				.step-header h3 i {
					color: #FFA500;
					font-size: 16px;
				}
				
				.step-header p {
					margin: 0;
					color: #6c757d;
					font-size: 13px;
				}
				
				/* Forms */
				.form-section {
					margin-bottom: 24px;
				}
				
				.form-section h4 {
					font-size: 13px;
					font-weight: 500;
					color: #495057;
					margin-bottom: 16px;
					text-transform: uppercase;
					letter-spacing: 0.5px;
				}
				
				.form-group {
					margin-bottom: 16px;
				}
				
				.form-group label {
					display: block;
					margin-bottom: 6px;
					font-size: 12px;
					font-weight: 500;
					color: #495057;
				}
				
				.form-control {
					width: 100%;
					padding: 8px 12px;
					border: 1px solid #dee2e6;
					border-radius: 4px;
					font-size: 13px;
					transition: all 0.2s ease;
					background: white;
				}
				
				.form-control:focus {
					border-color: #FFA500;
					outline: none;
					box-shadow: 0 0 0 3px rgba(255, 165, 0, 0.1);
				}
				
				.form-text {
					margin-top: 4px;
					font-size: 11px;
					color: #6c757d;
				}
				
				/* Info Cards */
				.info-card {
					background: #f8f9fa;
					border-left: 4px solid #FFA500;
					padding: 16px;
					border-radius: 4px;
					margin: 24px 0;
					display: flex;
					align-items: center;
				}
				
				.info-card i {
					color: #FFA500;
					margin-right: 8px;
				}
				
				.info-card p {
					margin: 0;
					font-size: 13px;
					color: #495057;
					line-height: 1.6;
				}
				
				/* Status Cards */
				.status-card {
					border: 1px solid #e9ecef;
					border-radius: 6px;
					padding: 16px;
					margin-bottom: 16px;
					display: flex;
					align-items: center;
					gap: 16px;
					transition: all 0.2s ease;
				}
				
				.status-card.completed {
					background: #d4edda;
					border-color: #c3e6cb;
				}
				
				.status-card.pending {
					background: #fff3cd;
					border-color: #ffeeba;
				}
				
				.status-card.error {
					background: #f8d7da;
					border-color: #f5c6cb;
				}
				
				.status-icon {
					width: 32px;
					height: 32px;
					border-radius: 50%;
					display: flex;
					align-items: center;
					justify-content: center;
					font-size: 14px;
					flex-shrink: 0;
				}
				
				.status-card.completed .status-icon {
					background: #28a745;
					color: white;
				}
				
				.status-card.pending .status-icon {
					background: #ffc107;
					color: white;
				}
				
				.status-card.error .status-icon {
					background: #dc3545;
					color: white;
				}
				
				.status-content {
					flex: 1;
				}
				
				.status-title {
					font-size: 13px;
					font-weight: 500;
					color: #212529;
					margin-bottom: 2px;
				}
				
				.status-description {
					font-size: 12px;
					color: #6c757d;
					margin: 0;
				}
				
				/* Buttons */
				.btn {
					padding: 8px 16px;
					border-radius: 4px;
					border: none;
					font-size: 13px;
					font-weight: 500;
					cursor: pointer;
					transition: all 0.2s ease;
					display: inline-flex;
					align-items: center;
					gap: 6px;
				}
				
				.btn-primary {
					background: #FFA500;
					color: white;
				}
				
				.btn-primary:hover {
					background: #ff9800;
				}
				
				.btn-secondary {
					background: white;
					color: #495057;
					border: 1px solid #dee2e6;
				}
				
				.btn-secondary:hover {
					background: #f8f9fa;
				}
				
				.btn-success {
					background: #28a745;
					color: white;
				}
				
				.btn-success:hover {
					background: #218838;
				}
				
				.btn:disabled {
					opacity: 0.5;
					cursor: not-allowed;
				}
				
				.btn-icon {
					width: 32px;
					height: 32px;
					padding: 0;
					border-radius: 50%;
					display: inline-flex;
					align-items: center;
					justify-content: center;
				}
				
				/* Action Buttons */
				.action-area {
					text-align: center;
					padding: 32px 0;
				}
				
				.action-button {
					background: #FFA500;
					color: white;
					border: none;
					padding: 12px 24px;
					border-radius: 4px;
					font-size: 14px;
					font-weight: 500;
					cursor: pointer;
					transition: all 0.2s ease;
					display: inline-flex;
					align-items: center;
					gap: 8px;
				}
				
				.action-button:hover {
					background: #ff9800;
					transform: translateY(-1px);
					box-shadow: 0 4px 12px rgba(255, 165, 0, 0.2);
				}
				
				.action-button:disabled {
					opacity: 0.5;
					cursor: not-allowed;
					transform: none;
				}
				
				.action-button.success {
					background: #28a745;
				}
				
				.action-button.success:hover {
					background: #218838;
				}
				
				/* Footer Navigation */
				.wizard-footer {
					background: #f8f9fa;
					padding: 16px 32px;
					border-top: 1px solid #e9ecef;
					display: flex;
					justify-content: space-between;
					align-items: center;
				}
				
				.wizard-footer-group {
					display: flex;
					gap: 12px;
				}
				
				/* Result Messages */
				.result-message {
					padding: 12px 16px;
					border-radius: 4px;
					margin: 16px 0;
					font-size: 13px;
					display: flex;
					align-items: center;
					gap: 8px;
				}
				
				.result-message.success {
					background: #d4edda;
					color: #155724;
					border: 1px solid #c3e6cb;
				}
				
				.result-message.error {
					background: #f8d7da;
					color: #721c24;
					border: 1px solid #f5c6cb;
				}
				
				.result-message.info {
					background: #d1ecf1;
					color: #0c5460;
					border: 1px solid #bee5eb;
				}
				
				/* Loading Spinner */
				.spinner {
					display: inline-block;
					width: 14px;
					height: 14px;
					border: 2px solid rgba(255,255,255,0.3);
					border-radius: 50%;
					border-top-color: white;
					animation: spin 0.8s linear infinite;
				}
				
				@keyframes spin {
					to { transform: rotate(360deg); }
				}
				
				/* Responsive */
				@media (max-width: 992px) {
					.wizard-main-content {
						flex-direction: column;
					}
					
					.connection-selector {
						flex: 1;
					}
				}
				
				/* Empty State */
				.empty-state {
					text-align: center;
					padding: 48px;
					color: #6c757d;
				}
				
				.empty-state i {
					font-size: 48px;
					color: #dee2e6;
					margin-bottom: 16px;
				}
				
				.empty-state p {
					margin: 0;
					font-size: 14px;
				}
				
				/* Progress Bar */
				.progress {
					height: 6px;
					background: #e9ecef;
					border-radius: 3px;
					overflow: hidden;
					margin: 16px 0;
				}
				
				.progress-bar {
					height: 100%;
					background: #FFA500;
					transition: width 0.3s ease;
				}
				
				/* Grid Layout */
				.grid-2 {
					display: grid;
					grid-template-columns: 1fr 1fr;
					gap: 16px;
				}
				
				@media (max-width: 768px) {
					.grid-2 {
						grid-template-columns: 1fr;
					}
				}
			`;
			document.head.appendChild(style);
		}
	}
	
	createMainContainer() {
		this.$container = $(`
			<div class="ebics-wizard-container">
				<!-- Header -->
				<div class="wizard-header">
					<h2><i class="fa fa-plug"></i> ${__('EBICS Activation Wizard')}</h2>
					<p>${__('Configure and activate your EBICS banking connection step by step')}</p>
				</div>
				
				<!-- Progress Steps -->
				<div class="step-indicator-wrapper">
					<div class="step-indicator"></div>
				</div>
				
				<!-- Main Content Area -->
				<div class="wizard-main-content">
					<!-- Connection Selector -->
					<div class="connection-selector">
						<h4>${__('Connections')}</h4>
						<div class="connection-list" id="connection-list">
							<!-- Will be populated dynamically -->
						</div>
						<button class="btn btn-primary" id="create-new-connection" style="width: 100%;">
							<i class="fa fa-plus"></i> ${__('New Connection')}
						</button>
					</div>
					
					<!-- Wizard Content -->
					<div class="wizard-content" style="display: none;">
						<div class="step-content">
							<!-- Step content will be inserted here -->
						</div>
						<div class="wizard-footer">
							<div class="wizard-footer-group">
								<button class="btn btn-secondary" id="btn-previous">
									<i class="fa fa-arrow-left"></i> ${__('Previous')}
								</button>
							</div>
							<div class="wizard-footer-group">
								<button class="btn btn-secondary" id="btn-save">
									<i class="fa fa-save"></i> ${__('Save')}
								</button>
								<button class="btn btn-primary" id="btn-next">
									${__('Next')} <i class="fa fa-arrow-right"></i>
								</button>
							</div>
						</div>
					</div>
				</div>
			</div>
		`);
		
		this.page.body.html(this.$container);
		this.createStepIndicator();
	}
	
	createStepIndicator() {
		const indicatorHtml = this.steps.map(step => `
			<div class="step-item ${step.id === 1 ? 'active' : ''}" data-step="${step.id}">
				<div class="step-circle">
					<i class="${step.icon}"></i>
				</div>
				<div class="step-label">${step.name}</div>
			</div>
		`).join('');
		
		this.$container.find('.step-indicator').html(indicatorHtml);
	}
	
	loadConnectionsList() {
		frappe.call({
			method: 'frappe.client.get_list',
			args: {
				doctype: 'ebics Connection',
				fields: ['name', 'title', 'host_id', 'activated', 'ini_sent', 'hia_sent', 'hpb_downloaded'],
				limit: 100
			},
			callback: (r) => {
				if (r.message && r.message.length > 0) {
					this.renderConnectionCards(r.message);
				} else {
					this.renderNoConnections();
				}
			}
		});
	}
	
	renderConnectionCards(connections) {
		const cardsHtml = connections.map(conn => {
			let status = 'inactive';
			let statusText = __('Not Started');
			let statusIcon = 'fa-circle';
			
			if (conn.activated) {
				status = 'active';
				statusText = __('Active');
				statusIcon = 'fa-check-circle';
			} else if (conn.hpb_downloaded) {
				status = 'pending';
				statusText = __('Pending Activation');
				statusIcon = 'fa-clock';
			} else if (conn.ini_sent || conn.hia_sent) {
				status = 'pending';
				statusText = __('In Progress');
				statusIcon = 'fa-spinner';
			}
			
			return `
				<div class="connection-card" data-connection="${conn.name}">
					<h5>${conn.title || conn.name}</h5>
					<p>${conn.host_id || __('Not configured')}</p>
					<div class="connection-status ${status}">
						<i class="fa ${statusIcon}"></i> ${statusText}
					</div>
				</div>
			`;
		}).join('');
		
		this.$container.find('#connection-list').html(cardsHtml);
	}
	
	renderNoConnections() {
		this.$container.find('#connection-list').html(`
			<div class="empty-state">
				<i class="fa fa-plug"></i>
				<p>${__('No connections yet')}</p>
			</div>
		`);
	}
	
	setupEventHandlers() {
		const self = this;
		
		// Connection card selection
		this.$container.on('click', '.connection-card', function() {
			$('.connection-card').removeClass('selected');
			$(this).addClass('selected');
			const connectionName = $(this).data('connection');
			self.loadConnection(connectionName);
		});
		
		// Create new connection button
		this.$container.on('click', '#create-new-connection', function() {
			self.showNewConnectionDialog();
		});
		
		// Step navigation
		this.$container.on('click', '.step-item', function() {
			const step = parseInt($(this).data('step'));
			if (self.canNavigateToStep(step)) {
				self.goToStep(step);
			}
		});
		
		// Navigation buttons
		this.$container.on('click', '#btn-previous', function() {
			if (self.current_step > 1) {
				self.goToStep(self.current_step - 1);
			}
		});
		
		this.$container.on('click', '#btn-next', function() {
			if (self.validateCurrentStep()) {
				if (self.current_step < self.total_steps) {
					self.goToStep(self.current_step + 1);
				}
			}
		});
		
		this.$container.on('click', '#btn-save', function() {
			self.saveCurrentStep();
		});
	}
	
	showNewConnectionDialog() {
		const dialog = new frappe.ui.Dialog({
			title: __('Create New EBICS Connection'),
			fields: [
				{
					label: __('Connection Name'),
					fieldname: 'title',
					fieldtype: 'Data',
					reqd: 1,
					description: __('A descriptive name for this connection')
				},
				{
					label: __('Bank'),
					fieldname: 'bank',
					fieldtype: 'Select',
					options: '\nRaiffeisen\nUBS\nCredit Suisse\nPostFinance\nZKB\nOther',
					reqd: 1
				},
				{
					label: __('Company'),
					fieldname: 'company',
					fieldtype: 'Link',
					options: 'Company',
					reqd: 1,
					default: frappe.defaults.get_default('company')
				}
			],
			primary_action_label: __('Create'),
			primary_action: (values) => {
				frappe.call({
					method: 'frappe.client.insert',
					args: {
						doc: {
							doctype: 'ebics Connection',
							title: values.title,
							company: values.company,
							bank_config: values.bank !== 'Other' ? values.bank : null
						}
					},
					callback: (r) => {
						if (r.message) {
							dialog.hide();
							frappe.show_alert({
								message: __('Connection created successfully'),
								indicator: 'green'
							});
							this.loadConnection(r.message.name);
						}
					}
				});
			}
		});
		dialog.show();
	}
	
	loadConnection(connectionName) {
		frappe.call({
			method: 'frappe.client.get',
			args: {
				doctype: 'ebics Connection',
				name: connectionName
			},
			callback: (r) => {
				if (r.message) {
					this.connection = r.message;
					this.analyzeConnectionStatus();
					this.$container.find('.wizard-content').show();
					this.renderCurrentStep();
				}
			}
		});
	}
	
	analyzeConnectionStatus() {
		// Determine which step we should be on based on connection status
		if (!this.connection.host_id || !this.connection.url || !this.connection.partner_id || !this.connection.user_id) {
			this.current_step = 1;
		} else if (!this.connection.keys_created) {
			this.current_step = 2;
		} else if (!this.connection.ini_sent) {
			this.current_step = 3;
		} else if (!this.connection.hia_sent) {
			this.current_step = 4;
		} else if (!this.connection.ini_letter_created) {
			this.current_step = 5;
		} else if (!this.connection.hpb_downloaded) {
			this.current_step = 6;
		} else if (!this.connection.activated) {
			this.current_step = 7;
		} else {
			this.current_step = 7; // Show final status
		}
		
		// Update step indicators
		this.updateStepIndicators();
	}
	
	updateStepIndicators() {
		this.$container.find('.step-item').each((_, element) => {
			const $step = $(element);
			const stepNum = parseInt($step.data('step'));
			
			$step.removeClass('active completed error');
			
			if (stepNum < this.current_step) {
				$step.addClass('completed');
				$step.find('.step-circle').html('<i class="fa fa-check"></i>');
			} else if (stepNum === this.current_step) {
				$step.addClass('active');
			}
		});
	}
	
	canNavigateToStep(step) {
		// Check if user can navigate to this step
		// For now, allow navigation to any completed or current step
		return step <= this.current_step;
	}
	
	goToStep(step) {
		this.current_step = step;
		this.updateStepIndicators();
		this.renderCurrentStep();
	}
	
	renderCurrentStep() {
		const stepContent = this.getStepContent(this.current_step);
		this.$container.find('.step-content').html(stepContent);
		this.initializeStepHandlers(this.current_step);
		
		// Update navigation buttons
		$('#btn-previous').prop('disabled', this.current_step === 1);
		$('#btn-next').toggle(this.current_step < this.total_steps);
	}
	
	getStepContent(step) {
		const currentStepData = this.steps[step - 1];
		let content = '';
		
		// Step header
		content = `
			<div class="step-header">
				<h3><i class="${currentStepData.icon}"></i> ${currentStepData.name}</h3>
				<p>${currentStepData.description}</p>
			</div>
		`;
		
		switch(step) {
			case 1:
				content += this.getStep1Content();
				break;
			case 2:
				content += this.getStep2Content();
				break;
			case 3:
				content += this.getStep3Content();
				break;
			case 4:
				content += this.getStep4Content();
				break;
			case 5:
				content += this.getStep5Content();
				break;
			case 6:
				content += this.getStep6Content();
				break;
			case 7:
				content += this.getStep7Content();
				break;
		}
		
		return content;
	}
	
	getStep1Content() {
		const conn = this.connection || {};
		return `
			<div class="info-card">
				<i class="fa fa-info-circle"></i>
				<p>${__('Enter the EBICS connection parameters provided by your bank.')}</p>
			</div>
			
			<div class="form-section">
				<h4>${__('Connection Details')}</h4>
				<div class="grid-2">
					<div class="form-group">
						<label>${__('Host ID')} <span class="text-danger">*</span></label>
						<input type="text" class="form-control" id="host_id" value="${conn.host_id || ''}" 
							placeholder="${__('e.g., RAIFCH22XXX')}">
						<small class="form-text">${__('Bank\'s EBICS host identifier')}</small>
					</div>
					<div class="form-group">
						<label>${__('EBICS URL')} <span class="text-danger">*</span></label>
						<input type="text" class="form-control" id="url" value="${conn.url || ''}" 
							placeholder="${__('https://ebics.bank.com/ebics')}">
						<small class="form-text">${__('Bank\'s EBICS server URL')}</small>
					</div>
				</div>
				
				<div class="grid-2">
					<div class="form-group">
						<label>${__('Partner ID')} <span class="text-danger">*</span></label>
						<input type="text" class="form-control" id="partner_id" value="${conn.partner_id || ''}" 
							placeholder="${__('Your partner ID')}">
						<small class="form-text">${__('Company\'s partner identifier')}</small>
					</div>
					<div class="form-group">
						<label>${__('User ID')} <span class="text-danger">*</span></label>
						<input type="text" class="form-control" id="user_id" value="${conn.user_id || ''}" 
							placeholder="${__('Your user ID')}">
						<small class="form-text">${__('Personal EBICS user ID')}</small>
					</div>
				</div>
			</div>
			
			<div class="form-section">
				<h4>${__('Security')}</h4>
				<div class="grid-2">
					<div class="form-group">
						<label>${__('Key Password')} <span class="text-danger">*</span></label>
						<input type="password" class="form-control" id="key_password" value="${conn.key_password || ''}" 
							placeholder="${__('Strong password')}">
						<small class="form-text">${__('For key encryption')}</small>
					</div>
					<div class="form-group">
						<label>${__('EBICS Version')}</label>
						<select class="form-control" id="ebics_version">
							<option value="H004" ${conn.ebics_version === 'H004' ? 'selected' : ''}>H004 (2.5)</option>
							<option value="H005" ${conn.ebics_version === 'H005' ? 'selected' : ''}>H005 (3.0)</option>
						</select>
						<small class="form-text">${__('Protocol version')}</small>
					</div>
				</div>
			</div>
			
			<div class="action-area">
				<button class="btn btn-primary" id="test-connectivity">
					<i class="fa fa-plug"></i> ${__('Test Connection')}
				</button>
			</div>
			
			<div id="connection-test-result"></div>
		`;
	}
	
	getStep2Content() {
		const conn = this.connection || {};
		const keysGenerated = conn.keys_created || false;
		
		return `
			<div class="info-card">
				<i class="fa fa-info-circle"></i>
				<p>${__('Generate RSA key pairs for secure communication (A006, X002, E002).')}</p>
			</div>
			
			<div class="status-card ${keysGenerated ? 'completed' : 'pending'}">
				<div class="status-icon">
					<i class="fa ${keysGenerated ? 'fa-check' : 'fa-key'}"></i>
				</div>
				<div class="status-content">
					<div class="status-title">${__('RSA Key Generation')}</div>
					<div class="status-description">
						${keysGenerated 
							? __('Keys generated successfully') 
							: __('Click below to generate your keys')}
					</div>
				</div>
			</div>
			
			<div class="action-area">
				<button class="action-button ${keysGenerated ? 'success' : ''}" id="generate-keys-btn" ${keysGenerated ? 'disabled' : ''}>
					<i class="fa ${keysGenerated ? 'fa-check' : 'fa-key'}"></i>
					${keysGenerated ? __('Keys Generated') : __('Generate Keys')}
				</button>
			</div>
			
			<div id="key-generation-result"></div>
		`;
	}
	
	getStep3Content() {
		const conn = this.connection || {};
		const iniSent = conn.ini_sent || false;
		
		return `
			<div class="info-card">
				<i class="fa fa-info-circle"></i>
				<p>${__('Send the INI order to transmit your electronic signature public key.')}</p>
			</div>
			
			<div class="status-card ${iniSent ? 'completed' : 'pending'}">
				<div class="status-icon">
					<i class="fa ${iniSent ? 'fa-check' : 'fa-send'}"></i>
				</div>
				<div class="status-content">
					<div class="status-title">${__('INI Order')}</div>
					<div class="status-description">
						${iniSent 
							? __('Signature key sent to bank') 
							: __('Send your A006 public key')}
					</div>
				</div>
			</div>
			
			<div class="action-area">
				<button class="action-button ${iniSent ? 'success' : ''}" id="send-ini-btn" ${iniSent ? 'disabled' : ''}>
					<i class="fa ${iniSent ? 'fa-check' : 'fa-send'}"></i>
					${iniSent ? __('INI Sent') : __('Send INI')}
				</button>
			</div>
			
			<div id="ini-send-result"></div>
		`;
	}
	
	getStep4Content() {
		const conn = this.connection || {};
		const hiaSent = conn.hia_sent || false;
		
		return `
			<div class="info-card">
				<i class="fa fa-info-circle"></i>
				<p>${__('Send the HIA order with authentication and encryption keys.')}</p>
			</div>
			
			<div class="status-card ${hiaSent ? 'completed' : 'pending'}">
				<div class="status-icon">
					<i class="fa ${hiaSent ? 'fa-check' : 'fa-shield'}"></i>
				</div>
				<div class="status-content">
					<div class="status-title">${__('HIA Order')}</div>
					<div class="status-description">
						${hiaSent 
							? __('Auth & encryption keys sent') 
							: __('Send X002 and E002 keys')}
					</div>
				</div>
			</div>
			
			<div class="action-area">
				<button class="action-button ${hiaSent ? 'success' : ''}" id="send-hia-btn" ${hiaSent ? 'disabled' : ''}>
					<i class="fa ${hiaSent ? 'fa-check' : 'fa-shield'}"></i>
					${hiaSent ? __('HIA Sent') : __('Send HIA')}
				</button>
			</div>
			
			<div id="hia-send-result"></div>
		`;
	}
	
	getStep5Content() {
		const conn = this.connection || {};
		const letterCreated = conn.ini_letter_created || false;
		
		return `
			<div class="info-card">
				<i class="fa fa-info-circle"></i>
				<p>${__('Generate the initialization letter for bank verification.')}</p>
			</div>
			
			<div class="status-card ${letterCreated ? 'completed' : 'pending'}">
				<div class="status-icon">
					<i class="fa ${letterCreated ? 'fa-check' : 'fa-file-text'}"></i>
				</div>
				<div class="status-content">
					<div class="status-title">${__('INI Letter')}</div>
					<div class="status-description">
						${letterCreated 
							? __('Letter generated - print and send to bank') 
							: __('Generate PDF with key signatures')}
					</div>
				</div>
			</div>
			
			<div class="action-area">
				<button class="action-button" id="generate-letter-btn">
					<i class="fa fa-file-text"></i>
					${letterCreated ? __('Regenerate Letter') : __('Generate Letter')}
				</button>
			</div>
			
			<div id="letter-generation-result"></div>
			
			${letterCreated ? `
				<div class="info-card" style="background: #fff3cd; border-color: #ffc107;">
					<i class="fa fa-exclamation-triangle" style="color: #856404;"></i>
					<p>
						<strong>${__('Next steps:')}</strong><br>
						1. ${__('Print the letter')}<br>
						2. ${__('Sign it (authorized signatory)')}<br>
						3. ${__('Send to your bank')}<br>
						4. ${__('Wait 1-2 business days')}
					</p>
				</div>
			` : ''}
		`;
	}
	
	getStep6Content() {
		const conn = this.connection || {};
		const hpbDownloaded = conn.hpb_downloaded || false;
		
		return `
			<div class="info-card">
				<i class="fa fa-info-circle"></i>
				<p>${__('Download bank public keys after they validate your letter.')}</p>
			</div>
			
			<div class="status-card ${hpbDownloaded ? 'completed' : 'pending'}">
				<div class="status-icon">
					<i class="fa ${hpbDownloaded ? 'fa-check' : 'fa-download'}"></i>
				</div>
				<div class="status-content">
					<div class="status-title">${__('HPB Order')}</div>
					<div class="status-description">
						${hpbDownloaded 
							? __('Bank keys downloaded') 
							: __('Retrieve bank public keys')}
					</div>
				</div>
			</div>
			
			<div class="action-area">
				<button class="action-button ${hpbDownloaded ? 'success' : ''}" id="download-hpb-btn">
					<i class="fa ${hpbDownloaded ? 'fa-check' : 'fa-download'}"></i>
					${hpbDownloaded ? __('HPB Downloaded') : __('Download HPB')}
				</button>
			</div>
			
			<div id="hpb-download-result"></div>
		`;
	}
	
	getStep7Content() {
		const conn = this.connection || {};
		const isActivated = conn.activated || false;
		
		return `
			<div class="info-card">
				<i class="fa fa-info-circle"></i>
				<p>${__('Complete activation and test your connection.')}</p>
			</div>
			
			<div class="status-card ${isActivated ? 'completed' : 'pending'}">
				<div class="status-icon">
					<i class="fa ${isActivated ? 'fa-check' : 'fa-rocket'}"></i>
				</div>
				<div class="status-content">
					<div class="status-title">${__('Connection Status')}</div>
					<div class="status-description">
						${isActivated 
							? __('Connection active and ready') 
							: __('Activate and test connection')}
					</div>
				</div>
			</div>
			
			<div class="action-area">
				<button class="action-button ${isActivated ? 'success' : ''}" id="activate-connection-btn">
					<i class="fa ${isActivated ? 'fa-check' : 'fa-rocket'}"></i>
					${isActivated ? __('Active') : __('Activate')}
				</button>
				
				<button class="action-button" id="test-download-btn">
					<i class="fa fa-download"></i> ${__('Test Download')}
				</button>
			</div>
			
			<div id="activation-result"></div>
			
			${isActivated ? `
				<div class="info-card" style="background: #d4edda; border-color: #28a745;">
					<i class="fa fa-check-circle" style="color: #28a745;"></i>
					<p>
						<strong>${__('Congratulations!')}</strong><br>
						${__('Your EBICS connection is ready for:')}
						<br>• ${__('Automatic statement downloads')}
						<br>• ${__('Payment file uploads')}
						<br>• ${__('Real-time synchronization')}
					</p>
				</div>
			` : ''}
		`;
	}
	
	initializeStepHandlers(step) {
		const self = this;
		
		switch(step) {
			case 1:
				$('#test-connectivity').click(() => self.testConnectivity());
				$('#host_id, #url, #partner_id, #user_id, #key_password').on('blur', function() {
					self.validateField($(this));
				});
				break;
			case 2:
				$('#generate-keys-btn').click(() => self.generateKeys());
				break;
			case 3:
				$('#send-ini-btn').click(() => self.sendINI());
				break;
			case 4:
				$('#send-hia-btn').click(() => self.sendHIA());
				break;
			case 5:
				$('#generate-letter-btn').click(() => self.generateINILetter());
				break;
			case 6:
				$('#download-hpb-btn').click(() => self.downloadHPB());
				break;
			case 7:
				$('#activate-connection-btn').click(() => self.activateConnection());
				$('#test-download-btn').click(() => self.testDownload());
				break;
		}
	}
	
	validateField($field) {
		const value = $field.val();
		let isValid = true;
		
		if ($field.attr('id') === 'url' && value) {
			isValid = value.startsWith('http://') || value.startsWith('https://');
		} else if ($field.attr('id') === 'key_password' && value) {
			isValid = value.length >= 8;
		} else {
			isValid = !!value;
		}
		
		$field.toggleClass('is-invalid', !isValid);
		return isValid;
	}
	
	validateCurrentStep() {
		if (this.current_step === 1) {
			let isValid = true;
			$('#host_id, #url, #partner_id, #user_id, #key_password').each(function() {
				if (!$(this).val()) {
					isValid = false;
					$(this).addClass('is-invalid');
				}
			});
			
			if (!isValid) {
				frappe.msgprint(__('Please fill all required fields'));
				return false;
			}
			
			this.saveStep1Data();
		}
		return true;
	}
	
	saveStep1Data() {
		const data = {
			host_id: $('#host_id').val(),
			url: $('#url').val(),
			partner_id: $('#partner_id').val(),
			user_id: $('#user_id').val(),
			key_password: $('#key_password').val(),
			ebics_version: $('#ebics_version').val()
		};
		
		frappe.call({
			method: 'frappe.client.set_value',
			args: {
				doctype: 'ebics Connection',
				name: this.connection.name,
				fieldname: data
			},
			callback: (r) => {
				if (r.message) {
					Object.assign(this.connection, data);
					frappe.show_alert({
						message: __('Configuration saved'),
						indicator: 'green'
					});
				}
			}
		});
	}
	
	testConnectivity() {
		const $btn = $('#test-connectivity');
		const originalText = $btn.html();
		$btn.html('<span class="spinner"></span> Testing...').prop('disabled', true);
		
		this.saveStep1Data();
		
		setTimeout(() => {
			frappe.call({
				method: 'erpnextswiss.erpnextswiss.doctype.ebics_connection.ebics_connection.test_connection',
				args: {
					connection_name: this.connection.name
				},
				callback: (r) => {
					$btn.html(originalText).prop('disabled', false);
					
					const $result = $('#connection-test-result');
					if (r.message && r.message.includes('✅')) {
						$result.html(`<div class="result-message success">
							<i class="fa fa-check-circle"></i> ${__('Connection test successful')}
						</div>`);
					} else {
						$result.html(`<div class="result-message error">
							<i class="fa fa-times-circle"></i> ${__('Connection test failed')}
						</div>`);
					}
				}
			});
		}, 500);
	}
	
	generateKeys() {
		const $btn = $('#generate-keys-btn');
		const originalText = $btn.html();
		$btn.html('<span class="spinner"></span> Generating...').prop('disabled', true);
		
		frappe.call({
			method: 'erpnextswiss.erpnextswiss.page.ebics_test_center.ebics_test_center.generate_keys',
			args: {
				connection: this.connection.name
			},
			callback: (r) => {
				if (r.message && r.message.success) {
					$btn.html('<i class="fa fa-check"></i> Keys Generated')
						.addClass('success').prop('disabled', true);
					$('#key-generation-result').html(`<div class="result-message success">
						<i class="fa fa-check-circle"></i> ${__('Keys generated successfully')}
					</div>`);
					this.connection.keys_created = true;
					setTimeout(() => this.renderCurrentStep(), 1000);
				} else {
					$btn.html(originalText).prop('disabled', false);
					$('#key-generation-result').html(`<div class="result-message error">
						<i class="fa fa-times-circle"></i> ${__('Key generation failed')}
					</div>`);
				}
			}
		});
	}
	
	sendINI() {
		const $btn = $('#send-ini-btn');
		const originalText = $btn.html();
		$btn.html('<span class="spinner"></span> Sending...').prop('disabled', true);
		
		frappe.call({
			method: 'erpnextswiss.erpnextswiss.page.ebics_test_center.ebics_test_center.send_ini',
			args: {
				connection: this.connection.name
			},
			callback: (r) => {
				if (r.message && r.message.success) {
					$btn.html('<i class="fa fa-check"></i> INI Sent')
						.addClass('success').prop('disabled', true);
					$('#ini-send-result').html(`<div class="result-message success">
						<i class="fa fa-check-circle"></i> ${__('INI sent successfully')}
					</div>`);
					this.connection.ini_sent = true;
				} else {
					$btn.html(originalText).prop('disabled', false);
					$('#ini-send-result').html(`<div class="result-message error">
						<i class="fa fa-times-circle"></i> ${__('Failed to send INI')}
					</div>`);
				}
			}
		});
	}
	
	sendHIA() {
		const $btn = $('#send-hia-btn');
		const originalText = $btn.html();
		$btn.html('<span class="spinner"></span> Sending...').prop('disabled', true);
		
		frappe.call({
			method: 'erpnextswiss.erpnextswiss.page.ebics_test_center.ebics_test_center.send_hia',
			args: {
				connection: this.connection.name
			},
			callback: (r) => {
				if (r.message && r.message.success) {
					$btn.html('<i class="fa fa-check"></i> HIA Sent')
						.addClass('success').prop('disabled', true);
					$('#hia-send-result').html(`<div class="result-message success">
						<i class="fa fa-check-circle"></i> ${__('HIA sent successfully')}
					</div>`);
					this.connection.hia_sent = true;
				} else {
					$btn.html(originalText).prop('disabled', false);
					$('#hia-send-result').html(`<div class="result-message error">
						<i class="fa fa-times-circle"></i> ${__('Failed to send HIA')}
					</div>`);
				}
			}
		});
	}
	
	generateINILetter() {
		const $btn = $('#generate-letter-btn');
		const originalText = $btn.html();
		$btn.html('<span class="spinner"></span> Generating...').prop('disabled', true);
		
		frappe.call({
			method: 'erpnextswiss.erpnextswiss.page.ebics_test_center.ebics_test_center.create_bank_letter',
			args: {
				connection: this.connection.name
			},
			callback: (r) => {
				$btn.html(originalText).prop('disabled', false);
				
				if (r.message && r.message.success && r.message.pdf_base64) {
					const pdfData = atob(r.message.pdf_base64);
					const pdfArray = new Uint8Array(pdfData.length);
					for (let i = 0; i < pdfData.length; i++) {
						pdfArray[i] = pdfData.charCodeAt(i);
					}
					const pdfBlob = new Blob([pdfArray], { type: 'application/pdf' });
					const pdfUrl = URL.createObjectURL(pdfBlob);
					window.open(pdfUrl, '_blank');
					
					$('#letter-generation-result').html(`<div class="result-message success">
						<i class="fa fa-check-circle"></i> ${__('Letter generated successfully')}
					</div>`);
					this.connection.ini_letter_created = true;
					setTimeout(() => this.renderCurrentStep(), 1000);
				} else {
					$('#letter-generation-result').html(`<div class="result-message error">
						<i class="fa fa-times-circle"></i> ${__('Failed to generate letter')}
					</div>`);
				}
			}
		});
	}
	
	downloadHPB() {
		const $btn = $('#download-hpb-btn');
		const originalText = $btn.html();
		$btn.html('<span class="spinner"></span> Downloading...').prop('disabled', true);
		
		frappe.call({
			method: 'erpnextswiss.erpnextswiss.page.ebics_test_center.ebics_test_center.download_hpb',
			args: {
				connection: this.connection.name
			},
			callback: (r) => {
				if (r.message && r.message.success) {
					$btn.html('<i class="fa fa-check"></i> HPB Downloaded')
						.addClass('success').prop('disabled', true);
					$('#hpb-download-result').html(`<div class="result-message success">
						<i class="fa fa-check-circle"></i> ${__('Bank keys downloaded')}
					</div>`);
					this.connection.hpb_downloaded = true;
					setTimeout(() => this.activateConnection(), 1000);
				} else {
					$btn.html(originalText).prop('disabled', false);
					$('#hpb-download-result').html(`<div class="result-message error">
						<i class="fa fa-times-circle"></i> ${__('Failed to download keys')}
					</div>`);
				}
			}
		});
	}
	
	activateConnection() {
		const $btn = $('#activate-connection-btn');
		const originalText = $btn.html();
		$btn.html('<span class="spinner"></span> Activating...').prop('disabled', true);
		
		frappe.call({
			method: 'frappe.client.set_value',
			args: {
				doctype: 'ebics Connection',
				name: this.connection.name,
				fieldname: {
					activated: 1
				}
			},
			callback: (r) => {
				if (r.message) {
					$btn.html('<i class="fa fa-check"></i> Active')
						.addClass('success').prop('disabled', true);
					$('#activation-result').html(`<div class="result-message success">
						<i class="fa fa-check-circle"></i> ${__('Connection activated')}
					</div>`);
					this.connection.activated = true;
					setTimeout(() => this.renderCurrentStep(), 1000);
				}
			}
		});
	}
	
	testDownload() {
		const $btn = $('#test-download-btn');
		const originalText = $btn.html();
		$btn.html('<span class="spinner"></span> Testing...').prop('disabled', true);
		
		const yesterday = new Date();
		yesterday.setDate(yesterday.getDate() - 1);
		const fromDate = yesterday.toISOString().split('T')[0];
		const toDate = new Date().toISOString().split('T')[0];
		
		frappe.call({
			method: 'erpnextswiss.erpnextswiss.page.ebics_test_center.ebics_test_center.test_download_statements',
			args: {
				connection: this.connection.name,
				from_date: fromDate,
				to_date: toDate,
				order_type: 'z53'
			},
			callback: (r) => {
				$btn.html(originalText).prop('disabled', false);
				
				if (r.message && r.message.success) {
					$('#activation-result').html(`<div class="result-message success">
						<i class="fa fa-check-circle"></i> ${__('Test successful')}
					</div>`);
				} else {
					$('#activation-result').html(`<div class="result-message info">
						<i class="fa fa-info-circle"></i> ${__('No data available')}
					</div>`);
				}
			}
		});
	}
	
	saveCurrentStep() {
		frappe.show_alert({
			message: __('Progress saved'),
			indicator: 'green'
		});
	}
	
	autoSave() {
		if (this.connection && this.current_step === 1) {
			const hasData = $('#host_id').val() && $('#url').val();
			if (hasData) {
				this.saveStep1Data();
			}
		}
	}
}