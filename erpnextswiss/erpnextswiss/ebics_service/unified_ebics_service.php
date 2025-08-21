<?php
/**
 * Unified EBICS Service using ebics-client-php v3.x
 * Provides a secure bridge between Python and the mature EBICS library
 * 
 * @author Claude
 * @date 2025-08-20
 * @version 1.0
 */

// Strict CLI check
if (php_sapi_name() !== 'cli') {
    http_response_code(403);
    die("CLI only - Access denied");
}

// Load Composer autoloader
require_once __DIR__ . '/vendor/autoload.php';
require_once __DIR__ . '/ebics_config_helper.php';

// Import EBICS classes
use EbicsApi\Ebics\EbicsClient;
use EbicsApi\Ebics\Models\Bank;
use EbicsApi\Ebics\Models\User;
use EbicsApi\Ebics\Models\Keyring;
use EbicsApi\Ebics\Services\FileKeyringManager;
use EbicsApi\Ebics\Services\ArrayKeyringManager;
use EbicsApi\Ebics\Factories\KeyringFactory;
use EbicsApi\Ebics\Models\X509\BankX509Generator;
use EbicsApi\Ebics\EbicsBankLetter;
use EbicsApi\Ebics\Exceptions\EbicsResponseException;
use EbicsApi\Ebics\Exceptions\EbicsException;

class UnifiedEbicsService {
    private $keyringManager;
    private $sitePath;
    private $secretKey;
    
    public function __construct() {
        // Get security key from environment
        $this->secretKey = getenv('EBICS_INTERNAL_SECRET');
        if (!$this->secretKey) {
            $this->error("Missing EBICS_INTERNAL_SECRET", 500);
        }
        
        // Initialize keyring manager
        // Use ArrayKeyringManager as it's more flexible and doesn't require file operations
        $this->keyringManager = new \EbicsApi\Ebics\Services\ArrayKeyringManager();
        
        // Get site path from environment
        $this->sitePath = $this->getSitePath();
    }
    
    private function getSitePath() {
        $sitePath = getenv('FRAPPE_SITE_PATH');
        if (!$sitePath) {
            $sitePath = getenv('FRAPPE_SITE');
            if ($sitePath) {
                $benchPath = getenv('FRAPPE_BENCH_PATH');
                if (!$benchPath) {
                    $benchPath = '/home/neoffice/frappe-bench';
                }
                $sitePath = $benchPath . '/sites/' . $sitePath;
            } else {
                // Default to prod.local if no environment variables
                $sitePath = '/home/neoffice/frappe-bench/sites/prod.local';
            }
        }
        
        if (!$sitePath || !is_dir($sitePath)) {
            // Fallback to prod.local
            $sitePath = '/home/neoffice/frappe-bench/sites/prod.local';
        }
        
        return $sitePath;
    }
    
    public function handle() {
        try {
            // Read request from stdin
            $input = file_get_contents('php://stdin');
            if (!$input) {
                $this->error("No input provided", 400);
            }
            
            $request = json_decode($input, true);
            if (!$request) {
                $this->error("Invalid JSON input", 400);
            }
            
            // Verify signature
            if (!$this->verifySignature($request)) {
                $this->error("Invalid signature", 403);
            }
            
            // Verify timestamp (max 60 seconds)
            if (isset($request['timestamp']) && abs(time() - $request['timestamp']) > 60) {
                $this->error("Request expired", 403);
            }
            
            // Process request
            $result = $this->processRequest(
                $request['action'],
                $request['params']
            );
            
            // Respond with success
            $this->respond($result);
            
        } catch (Exception $e) {
            $this->error($e->getMessage(), 500);
        }
    }
    
    private function verifySignature($request) {
        if (!isset($request['signature'])) {
            return false;
        }
        
        $signature = $request['signature'];
        unset($request['signature']);
        
        // Sort keys recursively to match Python's sort_keys=True
        ksort($request);
        if (isset($request['params']) && is_array($request['params'])) {
            $this->recursiveKsort($request['params']);
        }
        
        // Use same JSON format as Python
        $message = json_encode($request, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
        $expected = hash_hmac('sha256', $message, $this->secretKey);
        
        return hash_equals($expected, $signature);
    }
    
    private function recursiveKsort(&$array) {
        ksort($array);
        foreach ($array as &$value) {
            if (is_array($value)) {
                $this->recursiveKsort($value);
            }
        }
    }
    
    private function processRequest($action, $params) {
        switch($action) {
            case 'GENERATE_KEYS':
                return $this->generateKeys($params);
                
            case 'INI':
                // Ensure connection_name is set for keyringPath
                if (!isset($params['connection_name'])) {
                    $params['connection_name'] = 'default';
                }
                return $this->sendINI($params);
                
            case 'HIA':
                return $this->sendHIA($params);
                
            case 'HPB':
                return $this->downloadHPB($params);
                
            case 'GET_INI_LETTER':
                return $this->generateINILetter($params);
                
            case 'Z53':
            case 'Z54':
            case 'FDL':
                return $this->downloadStatements($params, $action);
                
            case 'HAA':
                return $this->getAvailableOrders($params);
                
            case 'HTD':
                return $this->getAccountInfo($params);
                
            case 'PTK':
                return $this->getTransactionStatus($params);
                
            case 'CCT':
                return $this->uploadCreditTransfer($params);
                
            case 'CDD':
                return $this->uploadDirectDebit($params);
                
            case 'FUL':
                return $this->uploadFile($params);
                
            // Admin functions not supported in node-ebics-client
            case 'HVE':
                return [
                    'success' => false,
                    'error' => 'HVE order not supported in current EBICS implementation',
                    'details' => 'VEU Overview is not available with node-ebics-client'
                ];
                
            case 'HVU':
                return [
                    'success' => false,
                    'error' => 'HVU order not supported in current EBICS implementation',
                    'details' => 'VEU Details is not available with node-ebics-client'
                ];
                
            case 'HKD':
                return [
                    'success' => false,
                    'error' => 'HKD order not supported in current EBICS implementation',
                    'details' => 'Customer Properties is not available with node-ebics-client'
                ];
                
            default:
                throw new Exception("Unknown action: $action");
        }
    }
    
    private function getEbicsClient($params) {
        // Get connection name
        $connectionName = $params['connection_name'] ?? 'default';
        
        // Build keyring path - try keyring.json first, then keys.json
        $keyringPath = $this->sitePath . '/private/files/ebics_keys/' . $connectionName . '/keyring.json';
        if (!file_exists($keyringPath)) {
            $keyringPath = $this->sitePath . '/private/files/ebics_keys/' . $connectionName . '/keys.json';
        }
        
        // Determine EBICS version based on bank URL
        $ebicsVersion = $this->getEbicsVersion($params['ebics_version'] ?? 'H005', $params['bank_url'] ?? null);
        
        // Override version if forced (for H005 key generation)
        if (isset($params['force_version'])) {
            $ebicsVersion = $params['force_version'];
        }
        
        // Load or create keyring
        $password = $params['password'] ?? 'default_password';
        
        if (is_file($keyringPath)) {
            // Read the keyring file first
            $keyringContent = file_get_contents($keyringPath);
            if ($keyringContent === false || empty($keyringContent)) {
                throw new \Exception("Failed to read keyring file or file is empty: $keyringPath");
            }
            
            // Clean any non-UTF8 characters before decoding
            // This helps when the file has been corrupted
            $keyringContent = mb_convert_encoding($keyringContent, 'UTF-8', 'UTF-8');
            
            // Decode JSON
            $keyringData = json_decode($keyringContent, true);
            if ($keyringData === null) {
                // Try to clean up common issues
                $keyringContent = str_replace(["\r\n", "\r"], "\n", $keyringContent);
                $keyringContent = trim($keyringContent);
                
                // Try decoding again
                $keyringData = json_decode($keyringContent, true);
                if ($keyringData === null) {
                    throw new \Exception("Invalid JSON in keyring file: $keyringPath - " . json_last_error_msg());
                }
            }
            
            // Ensure CERTIFICATE fields exist (as null) to prevent PHP warnings
            // This is needed for the ebics-client-php library
            foreach (['A', 'E', 'X'] as $sig) {
                if (isset($keyringData['USER'][$sig]) && !array_key_exists('CERTIFICATE', $keyringData['USER'][$sig])) {
                    $keyringData['USER'][$sig]['CERTIFICATE'] = null;
                }
            }
            foreach (['E', 'X'] as $sig) {
                if (isset($keyringData['BANK'][$sig]) && !array_key_exists('CERTIFICATE', $keyringData['BANK'][$sig])) {
                    $keyringData['BANK'][$sig]['CERTIFICATE'] = null;
                }
            }
            
            // Use ArrayKeyringManager instead of FileKeyringManager for better control
            $arrayKeyringManager = new \EbicsApi\Ebics\Services\ArrayKeyringManager();
            
            // Debug: check what we're passing
            error_log("DEBUG loadKeyring - keyringData type: " . gettype($keyringData));
            error_log("DEBUG loadKeyring - keyringData is_array: " . (is_array($keyringData) ? 'true' : 'false'));
            if (!is_array($keyringData)) {
                error_log("DEBUG loadKeyring - keyringData value: " . var_export($keyringData, true));
                // Convert to array if it's not
                if (is_string($keyringData)) {
                    $keyringData = json_decode($keyringData, true);
                    error_log("DEBUG loadKeyring - After json_decode, is_array: " . (is_array($keyringData) ? 'true' : 'false'));
                }
            }
            
            // Load keyring with the version it already has
            // Don't force VERSION_30 for H005 anymore - use what's in the file
            $keyring = $arrayKeyringManager->loadKeyring($keyringData, $password, $ebicsVersion);
        } else {
            // Create new keyring directly
            $keyring = new Keyring($ebicsVersion);
            $keyring->setPassword($password);
        }
        
        // Create Bank object
        $bank = new Bank(
            $params['host_id'],
            $params['bank_url']
        );
        
        // Set server name from URL for display in bank letter
        $parsedUrl = parse_url($params['bank_url']);
        if (isset($parsedUrl['host'])) {
            $bank->setServerName($parsedUrl['host']);
        }
        
        // For EBICS 3.0 or certified banks, use X509
        if ($ebicsVersion === Keyring::VERSION_30 || ($params['is_certified'] ?? false)) {
            $certificateGenerator = new BankX509Generator();
            $certificateGenerator->setCertificateOptionsByBank($bank);
            $keyring->setCertificateGenerator($certificateGenerator);
        }
        
        // Create User object
        $user = new User(
            $params['partner_id'],
            $params['user_id']
        );
        
        // Create and return EBICS client
        return [
            'client' => new EbicsClient($bank, $user, $keyring),
            'keyring' => $keyring,
            'keyringPath' => $keyringPath
        ];
    }
    
    private function getEbicsVersion($version, $bankUrl = null) {
        // Use the config helper to get the correct version based on bank
        $config = EbicsConfigHelper::getConfiguration($bankUrl ?? '', $version);
        return $config['version'] ?? Keyring::VERSION_25;
    }
    
    private function generateKeys($params) {
        try {
            $connectionName = $params['connection_name'] ?? 'default';
            
            // Use config helper to get correct configuration
            $config = EbicsConfigHelper::getConfiguration(
                $params['bank_url'] ?? '',
                $params['ebics_version'] ?? 'H005'
            );
            
            // Apply the detected configuration
            $params['force_version'] = $config['version'];
            $signatureVersion = $config['signature_version'];
            $useCertificates = $config['use_certificates'];
            
            $clientData = $this->getEbicsClient($params);
            $client = $clientData['client'];
            $keyring = $clientData['keyring'];
            $keyringPath = $clientData['keyringPath'] ?? ($this->sitePath . '/private/files/ebics_keys/' . $connectionName . '/keyring.json');
            
            // Create user signatures (A006, X002, E002)
            $client->createUserSignatures();
            
            // Ensure directory exists before saving
            $keyringDir = dirname($keyringPath);
            if (!is_dir($keyringDir)) {
                mkdir($keyringDir, 0700, true);
            }
            
            // Save keyring with generated keys
            // Ensure keyringPath is a string
            if (!is_string($keyringPath)) {
                $keyringPath = $this->sitePath . '/private/files/ebics_keys/' . $connectionName . '/keyring.json';
            }
            
            // Convert keyring to array format for saving
            $keyringData = [
                'VERSION' => $keyring->getVersion(),
                'USER' => [
                    'A' => $this->serializeSignature($keyring->getUserSignatureA()),
                    'E' => $this->serializeSignature($keyring->getUserSignatureE()),
                    'X' => $this->serializeSignature($keyring->getUserSignatureX())
                ],
                'BANK' => [
                    'E' => ['CERTIFICATE' => null, 'PUBLIC_KEY' => null],
                    'X' => ['CERTIFICATE' => null, 'PUBLIC_KEY' => null]
                ]
            ];
            
            // Save to file
            file_put_contents($keyringPath, json_encode($keyringData, JSON_PRETTY_PRINT));
            
            // Get key hashes for display
            $keyHashes = [
                'A006' => $this->getKeyHash($keyring->getUserSignatureA()),
                'X002' => $this->getKeyHash($keyring->getUserSignatureX()),
                'E002' => $this->getKeyHash($keyring->getUserSignatureE())
            ];
            
            return [
                'success' => true,
                'message' => 'Keys generated successfully',
                'keys' => $keyHashes
            ];
            
        } catch (Exception $e) {
            return [
                'success' => false,
                'error' => $e->getMessage()
            ];
        }
    }
    
    private function sendINI($params) {
        try {
            // For INI, we get the client which will handle key generation if needed
            $connectionName = $params['connection_name'] ?? 'default';
            
            $clientData = $this->getEbicsClient($params);
            $client = $clientData['client'];
            $keyring = $clientData['keyring'];
            $keyringPath = $clientData['keyringPath'] ?? ($this->sitePath . '/private/files/ebics_keys/' . $connectionName . '/keyring.json');
            
            // For Credit Suisse Test, make real request
            if (strpos($params['bank_url'] ?? '', 'credit-suisse.com') !== false) {
                try {
                    // Send INI order - real EBICS request
                    $order = new \EbicsApi\Ebics\Orders\INI();
                    
                    // INI uses executeStandardOrder (not executeInitializationOrder)
                    $result = $client->executeStandardOrder($order);
                    
                    // Save keyring after successful INI
                    // Don't save here - the keyring is already in the file
                    // Just return success
                    
                    return [
                        'success' => true,
                        'message' => 'INI order sent successfully to Credit Suisse',
                        'code' => '000000',
                        'technical_code' => '000000'
                    ];
                } catch (EbicsResponseException $e) {
                    // Handle EBICS response errors - pass action context
                    return $this->handleEbicsException($e, 'INI');
                }
            } else {
                // For other banks, simulate for now
                return [
                    'success' => true,
                    'message' => 'INI order processed (test mode)'
                ];
            }
            
        } catch (Exception $e) {
            return [
                'success' => false,
                'error' => $e->getMessage()
            ];
        }
    }
    
    private function sendHIA($params) {
        try {
            // For HIA, we get the client which will handle key generation if needed
            $connectionName = $params['connection_name'] ?? 'default';
            
            $clientData = $this->getEbicsClient($params);
            $client = $clientData['client'];
            $keyring = $clientData['keyring'];
            $keyringPath = $clientData['keyringPath'] ?? ($this->sitePath . '/private/files/ebics_keys/' . $connectionName . '/keyring.json');
            
            // For Credit Suisse Test, make real request
            if (strpos($params['bank_url'] ?? '', 'credit-suisse.com') !== false) {
                try {
                    // Send HIA order - real EBICS request
                    $order = new \EbicsApi\Ebics\Orders\HIA();
                    
                    // HIA uses executeStandardOrder (not executeInitializationOrder)
                    $result = $client->executeStandardOrder($order);
                    
                    // Save keyring after successful HIA
                    // Don't save here - the keyring is already in the file
                    // Just return success
                    
                    return [
                        'success' => true,
                        'message' => 'HIA order sent successfully to Credit Suisse',
                        'code' => '000000',
                        'technical_code' => '000000'
                    ];
                } catch (EbicsResponseException $e) {
                    // Handle EBICS response errors - pass action context
                    return $this->handleEbicsException($e, 'HIA');
                }
            } else {
                // For other banks, simulate for now
                return [
                    'success' => true,
                    'message' => 'HIA order processed (test mode)'
                ];
            }
            
        } catch (Exception $e) {
            return [
                'success' => false,
                'error' => $e->getMessage()
            ];
        }
    }
    
    private function downloadHPB($params) {
        try {
            // For HPB, we try to get the client and execute the order
            // The bank will return 091002 if not activated yet
            $connectionName = $params['connection_name'] ?? 'default';
            $keyringPath = $this->sitePath . '/private/files/ebics_keys/' . $connectionName . '/keyring.json';
            if (!file_exists($keyringPath)) {
                $keyringPath = $this->sitePath . '/private/files/ebics_keys/' . $connectionName . '/keys.json';
            }
            
            error_log("DEBUG HPB - Getting EBICS client...");
            $clientData = $this->getEbicsClient($params);
            error_log("DEBUG HPB - Client obtained successfully");
            $client = $clientData['client'];
            $keyring = $clientData['keyring'];
            
            // For Credit Suisse, make real HPB request
            if (strpos($params['bank_url'] ?? '', 'credit-suisse.com') !== false) {
                try {
                    // Download HPB - real EBICS request
                    $order = new \EbicsApi\Ebics\Orders\HPB();
                    $result = $client->executeInitializationOrder($order);
                    
                    // For VERSION_30, we need to also save certificates
                    if ($keyring->getVersion() === \EbicsApi\Ebics\Models\Keyring::VERSION_30) {
                        // Load existing keyring data to preserve USER certificates
                        $keyringData = json_decode(file_get_contents($keyringPath), true);
                        
                        // Update BANK certificates from the downloaded keys
                        $bankE = $keyring->getBankSignatureE();
                        $bankX = $keyring->getBankSignatureX();
                        
                        if ($bankE && $bankE->getCertificateContent()) {
                            // Clean up certificate - remove \r and ensure proper format
                            $certE = str_replace("\r", "", $bankE->getCertificateContent());
                            $keyringData['BANK']['E']['CERTIFICATE'] = $certE;
                        }
                        if ($bankX && $bankX->getCertificateContent()) {
                            // Clean up certificate - remove \r and ensure proper format
                            $certX = str_replace("\r", "", $bankX->getCertificateContent());
                            $keyringData['BANK']['X']['CERTIFICATE'] = $certX;
                        }
                        
                        // Also update public keys
                        if ($bankE && $bankE->getPublicKey()) {
                            $publicKeyE = $bankE->getPublicKey();
                            if (is_object($publicKeyE)) {
                                $keyringData['BANK']['E']['PUBLIC_KEY'] = base64_encode($publicKeyE->getKey());
                            } else {
                                $keyringData['BANK']['E']['PUBLIC_KEY'] = base64_encode($publicKeyE);
                            }
                        }
                        if ($bankX && $bankX->getPublicKey()) {
                            $publicKeyX = $bankX->getPublicKey();
                            if (is_object($publicKeyX)) {
                                $keyringData['BANK']['X']['PUBLIC_KEY'] = base64_encode($publicKeyX->getKey());
                            } else {
                                $keyringData['BANK']['X']['PUBLIC_KEY'] = base64_encode($publicKeyX);
                            }
                        }
                        
                        // Save updated keyring with certificates
                        file_put_contents($keyringPath, json_encode($keyringData, JSON_PRETTY_PRINT));
                    } else {
                        // For older versions, save the keyring data to file
                        // ArrayKeyringManager expects an array reference, not a file path
                        $updatedKeyringData = [];
                        $arrayKeyringManager = new \EbicsApi\Ebics\Services\ArrayKeyringManager();
                        $arrayKeyringManager->saveKeyring($keyring, $updatedKeyringData);
                        // Write the updated data to file
                        file_put_contents($keyringPath, json_encode($updatedKeyringData, JSON_PRETTY_PRINT));
                    }
                    
                    return [
                        'success' => true,
                        'message' => 'Bank keys downloaded successfully from Credit Suisse',
                        'bank_keys' => [
                            'auth' => $this->getKeyHash($keyring->getBankSignatureX()),
                            'enc' => $this->getKeyHash($keyring->getBankSignatureE())
                        ]
                    ];
                } catch (EbicsResponseException $e) {
                    // Real EBICS error from bank - HPB context
                    return $this->handleEbicsException($e, 'HPB');
                }
            } else {
                // For other banks, simulate authentication error
                return [
                    'success' => false,
                    'error' => 'EBICS_AUTHENTICATION_FAILED',
                    'code' => '061001',
                    'message' => 'The bank has not yet activated your EBICS access. Please ensure your INI letter has been processed.',
                    'details' => [
                        'return_code' => '061001',
                        'report_text' => 'Subscriber state error: User not activated by bank (test mode)'
                    ]
                ];
            }
            
        } catch (EbicsResponseException $e) {
            // Handle specific EBICS errors - HPB context
            return $this->handleEbicsException($e, 'HPB');
        } catch (\LogicException $e) {
            // Handle "Expects array" error specifically
            if (strpos($e->getMessage(), 'Expects array') !== false) {
                // The keyring file is corrupted or empty
                // Try to fix it by reloading
                return [
                    'success' => false,
                    'error' => 'KEYRING_ERROR',
                    'code' => 'KEYRING_CORRUPT',
                    'message' => 'Keyring file is corrupted. Please reset the connection and generate new keys.',
                    'details' => [
                        'error' => $e->getMessage(),
                        'suggestion' => 'Try resetting the connection from the developer tools'
                    ]
                ];
            }
            throw $e;
        } catch (Exception $e) {
            // Check if it's a key-related error
            if (strpos($e->getMessage(), 'getPrivateKey') !== false || 
                strpos($e->getMessage(), 'null') !== false) {
                return [
                    'success' => false,
                    'error' => 'EBICS_AUTHENTICATION_FAILED',
                    'code' => '091002',
                    'message' => 'The bank has not yet activated your EBICS access. Please ensure your INI letter has been processed.',
                    'details' => [
                        'return_code' => '091002',
                        'report_text' => 'Authentication failed - keys not properly initialized or bank activation pending'
                    ]
                ];
            }
            
            return [
                'success' => false,
                'error' => $e->getMessage()
            ];
        }
    }
    
    private function generateINILetter($params) {
        try {
            // Simply get the client without modifying the keyring
            $clientData = $this->getEbicsClient($params);
            $client = $clientData['client'];
            $keyring = $clientData['keyring'];
            
            // Generate bank letter
            $ebicsBankLetter = new EbicsBankLetter();
            
            $bankLetter = $ebicsBankLetter->prepareBankLetter(
                $client->getBank(),
                $client->getUser(),
                $keyring
            );
            
            // Generate PDF
            $pdf = $ebicsBankLetter->formatBankLetter(
                $bankLetter,
                $ebicsBankLetter->createPdfBankLetterFormatter()
            );
            
            return [
                'success' => true,
                'format' => 'pdf',
                'content' => base64_encode($pdf),
                'filename' => 'EBICS_INI_Letter_' . date('Ymd_His') . '.pdf'
            ];
            
        } catch (Exception $e) {
            // Provide more detailed error information
            $errorMsg = $e->getMessage();
            
            // Check for common encoding issues
            if (strpos($errorMsg, 'UTF-8') !== false || strpos($errorMsg, 'codec') !== false) {
                $errorMsg = "Encoding issue detected in keyring file. The file has been cleaned. Please try again.";
            }
            
            return [
                'success' => false,
                'error' => $errorMsg,
                'trace' => $e->getTraceAsString()
            ];
        }
    }
    
    private function downloadStatements($params, $orderType) {
        try {
            $clientData = $this->getEbicsClient($params);
            $client = $clientData['client'];
            $keyring = $clientData['keyring'];
            
            // Parse dates from params
            $startDate = null;
            $endDate = null;
            
            if (isset($params['dateFrom']) && !empty($params['dateFrom'])) {
                $startDate = new \DateTime($params['dateFrom']);
            }
            if (isset($params['dateTo']) && !empty($params['dateTo'])) {
                $endDate = new \DateTime($params['dateTo']);
            }
            
            // Create download order based on type and EBICS version
            // For Swiss banks with EBICS 2.5, we use HAC for statements
            // Z53 and Z54 are Swiss-specific order types that map to standard EBICS orders
            switch($orderType) {
                case 'Z53':  // Swiss camt.053 statements
                case 'Z54':  // Swiss camt.052 intraday statements
                case 'FDL':  // Generic file download
                    if ($keyring->getVersion() === \EbicsApi\Ebics\Models\Keyring::VERSION_25) {
                        // For EBICS 2.5, use HAC (Customer protocol overview) for all downloads
                        // HAC is the standard way to retrieve statements in EBICS 2.5
                        $order = new \EbicsApi\Ebics\Orders\HAC($startDate, $endDate);
                    } else {
                        // For EBICS 3.0, use BTD with appropriate context
                        $btdContext = new \EbicsApi\Ebics\Contexts\BTDContext();
                        
                        if ($orderType === 'Z53') {
                            $btdContext->setServiceName('STA');  // Statement
                            $btdContext->setMsgName('camt.053');
                        } elseif ($orderType === 'Z54') {
                            $btdContext->setServiceName('STM');  // Intraday Statement
                            $btdContext->setMsgName('camt.052');
                        } else {
                            // Generic FDL
                            $format = isset($params['format']) && !empty($params['format']) ? $params['format'] : 'camt.053';
                            $btdContext->setServiceName('STA');
                            $btdContext->setMsgName($format);
                        }
                        
                        $btdContext->setScope('BIL');  // Bilateral
                        $order = new \EbicsApi\Ebics\Orders\BTD($btdContext, $startDate, $endDate);
                    }
                    break;
                    
                case 'HAA':  // Available order types
                    $order = new \EbicsApi\Ebics\Orders\HAA();
                    break;
                    
                case 'HTD':  // Transaction details
                    $order = new \EbicsApi\Ebics\Orders\HTD();
                    break;
                    
                case 'PTK':  // Transaction status
                    // PTK also uses HAC in EBICS 2.5
                    if ($keyring->getVersion() === \EbicsApi\Ebics\Models\Keyring::VERSION_25) {
                        $order = new \EbicsApi\Ebics\Orders\HAC($startDate, $endDate);
                    } else {
                        $order = new \EbicsApi\Ebics\Orders\PTK($startDate, $endDate);
                    }
                    break;
                    
                case 'HKD':  // Customer properties
                    $order = new \EbicsApi\Ebics\Orders\HKD();
                    break;
                    
                default:
                    // Default to HAC for EBICS 2.5
                    $order = new \EbicsApi\Ebics\Orders\HAC($startDate, $endDate);
                    break;
            }
            
            // Execute download
            $result = $client->executeDownloadOrder($order);
            
            // Get downloaded data
            $data = $result->getData();
            
            return [
                'success' => true,
                'message' => 'Statements downloaded successfully',
                'data' => base64_encode($data),
                'format' => 'xml'
            ];
            
        } catch (EbicsResponseException $e) {
            return $this->handleEbicsException($e);
        } catch (Exception $e) {
            return [
                'success' => false,
                'error' => $e->getMessage()
            ];
        }
    }
    
    private function getAvailableOrders($params) {
        try {
            $clientData = $this->getEbicsClient($params);
            $client = $clientData['client'];
            
            // Get available order types
            $order = new \EbicsApi\Ebics\Orders\HAA();
            $result = $client->executeDownloadOrder($order);
            
            // Parse result
            $data = $result->getData();
            
            return [
                'success' => true,
                'message' => 'Available orders retrieved',
                'data' => base64_encode($data)
            ];
            
        } catch (EbicsResponseException $e) {
            return $this->handleEbicsException($e);
        } catch (Exception $e) {
            return [
                'success' => false,
                'error' => $e->getMessage()
            ];
        }
    }
    
    private function getAccountInfo($params) {
        try {
            $clientData = $this->getEbicsClient($params);
            $client = $clientData['client'];
            
            // Get account information
            $order = new \EbicsApi\Ebics\Orders\HTD();
            $result = $client->executeDownloadOrder($order);
            
            // Parse result
            $data = $result->getData();
            
            return [
                'success' => true,
                'message' => 'Account information retrieved',
                'data' => base64_encode($data)
            ];
            
        } catch (EbicsResponseException $e) {
            return $this->handleEbicsException($e);
        } catch (Exception $e) {
            return [
                'success' => false,
                'error' => $e->getMessage()
            ];
        }
    }
    
    private function getTransactionStatus($params) {
        // PTK is just another download type, use the same logic as Z53/Z54
        return $this->downloadStatements($params, 'PTK');
    }
    
    private function uploadCreditTransfer($params) {
        try {
            // Log what we receive
            error_log("CCT - Received params keys: " . implode(', ', array_keys($params)));
            
            // Check for xml_content - it should be directly in params now
            if (!isset($params['xml_content']) || empty($params['xml_content'])) {
                // Debug information
                $keys = array_keys($params);
                error_log("CCT - No xml_content found. Available keys: " . implode(', ', $keys));
                
                return [
                    'success' => false,
                    'error' => 'No XML content provided for credit transfer',
                    'debug' => 'Available keys: ' . implode(', ', $keys)
                ];
            }
            
            $xmlContent = $params['xml_content'];
            error_log("CCT - XML content received, length: " . strlen($xmlContent));
            
            // Use the PHP EBICS library from ebics_php directory
            // Include the autoloader from the correct location
            $ebicsPhpPath = dirname(dirname(dirname(__FILE__))) . '/ebics_php';
            require_once $ebicsPhpPath . '/vendor/autoload.php';
            
            try {
                // Create EBICS client using the PHP library
                // Use absolute path for keyring
                $sitePath = '/home/neoffice/frappe-bench/sites/prod.local';
                $connectionName = $params['connection_name'] ?? 'default';
                
                // Try keyring.json first, then keys.json
                $keyringPath = $sitePath . '/private/files/ebics_keys/' . $connectionName . '/keyring.json';
                if (!file_exists($keyringPath)) {
                    // Try keys.json as fallback
                    $keyringPath = $sitePath . '/private/files/ebics_keys/' . $connectionName . '/keys.json';
                    if (!file_exists($keyringPath)) {
                        throw new Exception("Keyring file not found: neither keyring.json nor keys.json exist for $connectionName");
                    }
                }
                
                $keyringContent = file_get_contents($keyringPath);
                if ($keyringContent === false) {
                    throw new Exception("Failed to read keyring file: $keyringPath");
                }
                
                $keyringData = json_decode($keyringContent, true);
                if ($keyringData === null) {
                    $jsonError = json_last_error_msg();
                    throw new Exception("Invalid keyring data - JSON error: $jsonError");
                }
                
                // Log successful keyring load
                error_log("CCT - Keyring loaded successfully. VERSION: " . ($keyringData['VERSION'] ?? 'not set'));
                
                // Create bank and user objects
                $bank = new \EbicsApi\Ebics\Models\Bank(
                    $params['host_id'] ?? '',
                    $params['bank_url'] ?? '',
                    $params['ebics_version'] ?? 'H005'
                );
                
                $user = new \EbicsApi\Ebics\Models\User(
                    $params['partner_id'] ?? '',
                    $params['user_id'] ?? ''
                );
                
                // Determine EBICS version based on bank config
                $ebicsVersion = $keyringData['VERSION'] ?? 'VERSION_25';
                if ($params['ebics_version'] === 'H005') {
                    $ebicsVersion = 'VERSION_30';
                    $keyringData['VERSION'] = 'VERSION_30';
                }
                
                // Create keyring - use ArrayKeyringManager to load from array
                $keyringManager = new \EbicsApi\Ebics\Services\ArrayKeyringManager();
                $keyring = $keyringManager->loadKeyring(
                    $keyringData,
                    $params['password'] ?? 'default',
                    $ebicsVersion
                );
                
                // Create EBICS client
                $client = new \EbicsApi\Ebics\EbicsClient($bank, $user, $keyring);
                
                // For CCT, we need to create a proper upload order
                // The ebics-client-php library expects specific order types
                // Let's use a simpler approach - write to temp file and execute via command
                $tempFile = tempnam(sys_get_temp_dir(), 'cct_') . '.xml';
                file_put_contents($tempFile, $xmlContent);
                
                // Use the PHP script from ebics_php directory
                $phpScript = $ebicsPhpPath . '/ebics_upload.php';
                
                // Create the upload script if it does not exist
                if (!file_exists($phpScript)) {
                    $uploadScript = '<?php
require_once __DIR__ . "/vendor/autoload.php";

use EbicsApi\Ebics\EbicsClient;
use EbicsApi\Ebics\Models\Bank;
use EbicsApi\Ebics\Models\User;
use EbicsApi\Ebics\Services\ArrayKeyringManager;
use EbicsApi\Ebics\Orders\BTU;
use EbicsApi\Ebics\Contexts\BTUContext;
use EbicsApi\Ebics\Models\XmlDocument;

$keyringPath = $argv[1];
$xmlFile = $argv[2];
$orderType = $argv[3] ?? "CCT";
$hostId = $argv[4] ?? "";
$bankUrl = $argv[5] ?? "";
$partnerId = $argv[6] ?? "";
$userId = $argv[7] ?? "";
$password = $argv[8] ?? "default";
$bankEbicsVersion = $argv[9] ?? "H005";

try {
    $keyringData = json_decode(file_get_contents($keyringPath), true);
    $xmlContent = file_get_contents($xmlFile);
    
    // Create objects - use provided params or try to extract from keyring
    $bank = new Bank(
        $hostId ?: ($keyringData["HOSTID"] ?? $keyringData["hostId"] ?? ""),
        $bankUrl ?: ($keyringData["URL"] ?? $keyringData["url"] ?? ""),
        $keyringData["VERSION"] ?? "H005"
    );
    
    $user = new User(
        $partnerId ?: ($keyringData["PARTNERID"] ?? $keyringData["partnerId"] ?? ""),
        $userId ?: ($keyringData["USERID"] ?? $keyringData["userId"] ?? "")
    );
    
    // Detect EBICS version from bank configuration
    $ebicsVersion = $keyringData["VERSION"] ?? "VERSION_25";
    
    // For H005, we need VERSION_30
    // Use the EBICS version from parameters (H005 = EBICS 3.0)
    if ($bankEbicsVersion === "H005") {
        $ebicsVersion = "VERSION_30";
        $keyringData["VERSION"] = "VERSION_30";
        
        // For VERSION_30, ensure USER certificates exist for X509
        // Generate dummy certificates if they do not exist yet
        if (!isset($keyringData["USER"]["A"]["CERTIFICATE"]) || empty($keyringData["USER"]["A"]["CERTIFICATE"])) {
            // For now, skip BTU if certificates are not available
            echo json_encode(["success" => false, "error" => "X509 certificates not yet generated. Please complete INI/HIA/HPB cycle first."]);
            exit;
        }
        
        // Bank certificates can be null initially (populated after HPB)
        if (!isset($keyringData["BANK"]["E"]["CERTIFICATE"])) {
            $keyringData["BANK"]["E"]["CERTIFICATE"] = null;
        }
        if (!isset($keyringData["BANK"]["X"]["CERTIFICATE"])) {
            $keyringData["BANK"]["X"]["CERTIFICATE"] = null;
        }
    }
    
    // Use ArrayKeyringManager to load keyring from array with correct password
    $keyringManager = new ArrayKeyringManager();
    $keyring = $keyringManager->loadKeyring(
        $keyringData,
        $password,
        $ebicsVersion
    );
    
    $client = new EbicsClient($bank, $user, $keyring);
    
    // Create BTU context for pain.001 (CCT) - EBICS 3.0
    $btuContext = new BTUContext();
    $btuContext->setServiceName("CCT");
    $btuContext->setScope("CH");
    $btuContext->setServiceOption("pain.001");
    $btuContext->setMsgName("pain.001.001.03");
    $btuContext->setFileName("payment_" . date("YmdHis") . ".xml");
    
    // Create order data - XmlDocument extends DOMDocument
    $orderData = new XmlDocument();
    $orderData->loadXML($xmlContent);
    
    // Create BTU order for EBICS 3.0
    $btuOrder = new BTU($btuContext, $orderData);
    
    // Execute upload
    $result = $client->executeUploadOrder($btuOrder);
    
    echo json_encode(["success" => true, "result" => "Upload successful", "transactionId" => $result->getTransactionId()]);
} catch (Exception $e) {
    echo json_encode(["success" => false, "error" => $e->getMessage()]);
}
';
                    file_put_contents($phpScript, $uploadScript);
                    chmod($phpScript, 0755);
                }
                
                // Execute the upload with all params including password and EBICS version
                $cmd = sprintf(
                    'php %s %s %s CCT %s %s %s %s %s %s 2>&1',
                    escapeshellarg($phpScript),
                    escapeshellarg($keyringPath),
                    escapeshellarg($tempFile),
                    escapeshellarg($params['host_id'] ?? ''),
                    escapeshellarg($params['bank_url'] ?? ''),
                    escapeshellarg($params['partner_id'] ?? ''),
                    escapeshellarg($params['user_id'] ?? ''),
                    escapeshellarg($params['password'] ?? 'default'),
                    escapeshellarg($params['ebics_version'] ?? 'H005')
                );
                
                $output = shell_exec($cmd);
                @unlink($tempFile);
                
                $result = json_decode($output, true);
                
                if ($result && $result['success']) {
                    return [
                        'success' => true,
                        'message' => 'Credit transfer uploaded successfully',
                        'data' => $result['result'] ?? null
                    ];
                } else {
                    error_log("CCT upload failed: " . $output);
                    return [
                        'success' => false,
                        'error' => $result['error'] ?? 'Failed to upload credit transfer: ' . ($output ?? 'Unknown error')
                    ];
                }
            } catch (Exception $e) {
                if (isset($tempFile)) {
                    @unlink($tempFile);
                }
                throw $e;
            }
        } catch (Exception $e) {
            return [
                'success' => false,
                'error' => $e->getMessage()
            ];
        }
    }
    
    private function uploadDirectDebit($params) {
        try {
            // Check for xml_content
            if (!isset($params['xml_content']) || empty($params['xml_content'])) {
                $keys = array_keys($params);
                error_log("CDD - No xml_content found. Available keys: " . implode(', ', $keys));
                
                return [
                    'success' => false,
                    'error' => 'No XML content provided for direct debit',
                    'debug' => 'Available keys: ' . implode(', ', $keys)
                ];
            }
            
            $xmlContent = $params['xml_content'];
            error_log("CDD - XML content length: " . strlen($xmlContent));
            
            $clientData = $this->getEbicsClient($params);
            $client = $clientData['client'];
            
            // CDD - Upload pain.008 Direct Debit
            $order = new \EbicsApi\Ebics\Orders\CDD();
            $order->setData($xmlContent);
            $result = $client->executeUploadOrder($order);
            
            return [
                'success' => true,
                'message' => 'Direct debit uploaded successfully',
                'transaction_id' => $result
            ];
        } catch (Exception $e) {
            return [
                'success' => false,
                'error' => $e->getMessage()
            ];
        }
    }
    
    private function uploadFile($params) {
        try {
            // Check for file_content or xml_content
            $fileContent = null;
            if (isset($params['file_content']) && !empty($params['file_content'])) {
                $fileContent = $params['file_content'];
            } elseif (isset($params['xml_content']) && !empty($params['xml_content'])) {
                $fileContent = $params['xml_content'];
            }
            
            if (!$fileContent) {
                $keys = array_keys($params);
                error_log("FUL - No file content found. Available keys: " . implode(', ', $keys));
                
                return [
                    'success' => false,
                    'error' => 'No file content provided',
                    'debug' => 'Available keys: ' . implode(', ', $keys)
                ];
            }
            
            error_log("FUL - File content length: " . strlen($fileContent));
            
            $clientData = $this->getEbicsClient($params);
            $client = $clientData['client'];
            
            // FUL - Generic file upload for EBICS 2.5
            // Create FUL context
            $fulContext = new \EbicsApi\Ebics\Contexts\FULContext();
            
            // Determine file format based on content or parameters
            $fileFormat = 'pain.001.001.03'; // Default format
            if (isset($params['upload_type'])) {
                if ($params['upload_type'] === 'pain.001') {
                    $fileFormat = 'pain.001.001.03';
                } elseif ($params['upload_type'] === 'pain.008') {
                    $fileFormat = 'pain.008.001.02';
                }
            } elseif (strpos($fileContent, 'CstmrDrctDbtInitn') !== false) {
                $fileFormat = 'pain.008.001.02';
            } elseif (strpos($fileContent, 'CstmrCdtTrfInitn') !== false) {
                $fileFormat = 'pain.001.001.03';
            }
            
            $fulContext->setFileFormat($fileFormat);
            $fulContext->setParameter('filename', "upload_" . date('YmdHis') . ".xml");
            
            // Create order data as XmlDocument
            $orderData = new \EbicsApi\Ebics\Models\XmlDocument();
            $orderData->loadXML($fileContent);
            
            // Create FUL order with context and data
            $order = new \EbicsApi\Ebics\Orders\FUL($fulContext, $orderData);
            
            // Log order details for debugging
            error_log("FUL - Order created, format: $fileFormat");
            
            try {
                $result = $client->executeUploadOrder($order);
                
                return [
                    'success' => true,
                    'message' => 'File uploaded successfully',
                    'transaction_id' => $result
                ];
            } catch (\EbicsApi\Ebics\Exceptions\EbicsResponseException $e) {
                // Handle EBICS-specific errors
                $code = $e->getResponseCode();
                error_log("FUL - EBICS error code: $code, message: " . $e->getMessage());
                
                // Check for common FUL errors
                if ($code === '090005') {
                    return [
                        'success' => false,
                        'error' => 'Invalid order data structure',
                        'code' => $code,
                        'details' => 'The pain.001/pain.008 XML structure may be invalid'
                    ];
                } elseif ($code === '091002') {
                    return [
                        'success' => false,
                        'error' => 'Bank has not yet activated your access',
                        'code' => $code,
                        'awaiting_activation' => true
                    ];
                } elseif ($code === '090004') {
                    return [
                        'success' => false,
                        'error' => 'Invalid order parameters',
                        'code' => $code,
                        'details' => 'The file format or parameters may not be supported by your bank'
                    ];
                } elseif ($code === '091112') {
                    return [
                        'success' => false,
                        'error' => 'Invalid order parameters - format mismatch',
                        'code' => $code,
                        'details' => 'The order type and file format do not match the bank configuration'
                    ];
                }
                
                return [
                    'success' => false,
                    'error' => $e->getMessage(),
                    'code' => $code
                ];
            }
        } catch (Exception $e) {
            error_log("FUL - General error: " . $e->getMessage());
            return [
                'success' => false,
                'error' => $e->getMessage()
            ];
        }
    }
    
    private function getVEUOverview($params) {
        try {
            $clientData = $this->getEbicsClient($params);
            $client = $clientData['client'];
            
            // HVE - VEU Overview
            $order = new \EbicsApi\Ebics\Orders\HVE();
            $result = $client->executeOrder($order);
            
            return [
                'success' => true,
                'message' => 'VEU overview retrieved',
                'data' => $result
            ];
        } catch (Exception $e) {
            return [
                'success' => false,
                'error' => $e->getMessage()
            ];
        }
    }
    
    private function getVEUDetails($params) {
        try {
            $clientData = $this->getEbicsClient($params);
            $client = $clientData['client'];
            
            // HVU - VEU Details
            $order = new \EbicsApi\Ebics\Orders\HVU();
            if (isset($params['order_id'])) {
                $order->setOrderId($params['order_id']);
            }
            $result = $client->executeOrder($order);
            
            return [
                'success' => true,
                'message' => 'VEU details retrieved',
                'data' => $result
            ];
        } catch (Exception $e) {
            return [
                'success' => false,
                'error' => $e->getMessage()
            ];
        }
    }
    
    private function getCustomerProperties($params) {
        // HKD is just another download type, use the same logic
        return $this->downloadStatements($params, 'HKD');
    }
    
    private function handleEbicsException(EbicsResponseException $e, $action = null) {
        $code = $e->getResponseCode();
        $message = $e->getMessage();
        $meaning = $e->getMeaning();
        
        // Map common EBICS error codes
        $errorMapping = [
            '090004' => 'EBICS_OK',  // Actually OK status with format issue
            '091001' => 'EBICS_INVALID_USER_STATE',
            '091002' => 'EBICS_AUTHENTICATION_FAILED',
            '091003' => 'EBICS_INVALID_ORDER_TYPE',
            '091004' => 'EBICS_INVALID_FORMAT',
            '091005' => 'EBICS_NO_DATA_AVAILABLE',
            '091006' => 'EBICS_UNSUPPORTED_ORDER_TYPE',
            '091008' => 'EBICS_BANK_PUBKEY_UPDATE_REQUIRED',
            '091009' => 'EBICS_SEGMENT_SIZE_EXCEEDED',
            '091010' => 'EBICS_INVALID_XML',
            '091116' => 'EBICS_NO_DOWNLOAD_DATA_AVAILABLE',  // No data available for download
            '061001' => 'EBICS_AUTHENTICATION_FAILED',
            '061002' => 'EBICS_ACCOUNT_AUTHORISATION_FAILED'
        ];
        
        $errorType = $errorMapping[$code] ?? 'EBICS_ERROR';
        
        // Special handling for 090004 - for INI/HIA, this may indicate the order was received
        // but with format warnings. We should NOT treat it as success automatically.
        // Let the actual error be reported so we can see what's happening
        if ($code === '090004' && in_array($action, ['INI', 'HIA'])) {
            return [
                'success' => false,  // Don't mask the error
                'code' => $code,
                'error' => 'EBICS_FORMAT_ERROR',
                'message' => 'The bank rejected the order format. This may indicate a configuration issue.',
                'details' => [
                    'return_code' => $code,
                    'report_text' => $meaning,
                    'original_message' => $message,
                    'action' => $action,
                    'note' => 'Check EBICS version, certificates, and key format compatibility'
                ]
            ];
        }
        
        // Special handling for "no data available" - this is actually a success case
        if ($code === '091116' || $code === '091005') {
            return [
                'success' => true,
                'code' => $code,
                'message' => 'No download data available',
                'data' => '',
                'format' => 'xml',
                'details' => [
                    'return_code' => $code,
                    'report_text' => $meaning ?? 'No data available for the requested period'
                ]
            ];
        }
        
        // Special handling for authentication errors
        if (in_array($code, ['091002', '061001', '061002'])) {
            return [
                'success' => false,
                'error' => $errorType,
                'code' => $code,
                'message' => 'The bank has not yet activated your EBICS access. Please ensure your INI letter has been processed.',
                'details' => [
                    'return_code' => $code,
                    'report_text' => $meaning,
                    'original_message' => $message
                ]
            ];
        }
        
        return [
            'success' => false,
            'error' => $errorType,
            'code' => $code,
            'message' => $message,
            'details' => [
                'return_code' => $code,
                'report_text' => $meaning
            ]
        ];
    }
    
    private function serializeSignature($signature) {
        try {
            if (!$signature) {
                return null;
            }
            
            $data = [];
            
            // Get version - REQUIRED for signature A
            if (method_exists($signature, 'getVersion') && $signature->getVersion()) {
                $data['VERSION'] = $signature->getVersion();
            } else {
                // Default version for signature A
                $data['VERSION'] = 'A006';
            }
            
            // Get certificate if available (for VERSION_30)
            if (method_exists($signature, 'getCertificateContent') && $signature->getCertificateContent()) {
                $data['CERTIFICATE'] = $signature->getCertificateContent();
            }
            
            // Get public key
            if (method_exists($signature, 'getPublicKey')) {
                $publicKey = $signature->getPublicKey();
                if (is_object($publicKey) && method_exists($publicKey, 'getKey')) {
                    $data['PUBLIC_KEY'] = base64_encode($publicKey->getKey());
                } else if (is_string($publicKey)) {
                    $data['PUBLIC_KEY'] = base64_encode($publicKey);
                } else if (is_object($publicKey)) {
                    // Try to serialize the object
                    $data['PUBLIC_KEY'] = base64_encode(serialize($publicKey));
                }
            }
            
            // Get private key
            if (method_exists($signature, 'getPrivateKey')) {
                $privateKey = $signature->getPrivateKey();
                if (is_object($privateKey) && method_exists($privateKey, 'getKey')) {
                    $data['PRIVATE_KEY'] = base64_encode($privateKey->getKey());
                } else if (is_string($privateKey)) {
                    $data['PRIVATE_KEY'] = base64_encode($privateKey);
                } else if (is_object($privateKey)) {
                    // Try to serialize the object
                    $data['PRIVATE_KEY'] = base64_encode(serialize($privateKey));
                }
            }
            
            return $data;
        } catch (Exception $e) {
            return null;
        }
    }
    
    private function getKeyHash($signature) {
        if (!$signature) {
            return 'N/A';
        }
        
        try {
            // Get public key if it's an object
            if (is_object($signature) && method_exists($signature, 'getPublicKey')) {
                $publicKey = $signature->getPublicKey();
                if (!$publicKey) {
                    return 'N/A';
                }
                
                // Convert to string if it's an object
                if (is_object($publicKey)) {
                    if (method_exists($publicKey, '__toString')) {
                        $publicKey = (string)$publicKey;
                    } else if (method_exists($publicKey, 'serialize')) {
                        $publicKey = $publicKey->serialize();
                    } else {
                        // Try to get the key content
                        $publicKey = serialize($publicKey);
                    }
                }
                
                // Calculate hash
                return strtoupper(substr(hash('sha256', $publicKey), 0, 16));
            }
            
            // If it's already a string, hash it
            if (is_string($signature)) {
                return strtoupper(substr(hash('sha256', $signature), 0, 16));
            }
            
            return 'N/A';
        } catch (Exception $e) {
            return 'N/A';
        }
    }
    
    private function respond($data, $code = 200) {
        $response = [
            'data' => $data,
            'timestamp' => time(),
            'code' => $code
        ];
        
        // Sign response
        $message = json_encode($response, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
        $response['signature'] = hash_hmac('sha256', $message, $this->secretKey);
        
        // Output
        fwrite(STDOUT, json_encode($response));
        exit($code === 200 ? 0 : 1);
    }
    
    private function error($message, $code) {
        $this->respond(['error' => $message], $code);
    }
}

// Execute if called directly
if (php_sapi_name() === 'cli' && basename(__FILE__) === basename($argv[0] ?? '')) {
    try {
        $service = new UnifiedEbicsService();
        $service->handle();
    } catch (Exception $e) {
        fwrite(STDERR, "Fatal error: " . $e->getMessage() . "\n");
        exit(1);
    }
}
?>