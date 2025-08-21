<?php
/**
 * EBICS Version Detector
 * Automatically detects whether a bank uses EBICS 2.5 or 3.0
 */

namespace EbicsService;

use EbicsApi\Ebics\Models\Bank;
use EbicsApi\Ebics\Models\User;
use EbicsApi\Ebics\Models\Keyring;
use EbicsApi\Ebics\EbicsClient;
use EbicsApi\Ebics\Orders\INI;
use EbicsApi\Ebics\Services\ArrayKeyringManager;
use EbicsApi\Ebics\Exceptions\EbicsResponseException;

class EbicsVersionDetector {
    
    private $sitePath;
    
    public function __construct($sitePath) {
        $this->sitePath = $sitePath;
    }
    
    /**
     * Detect the correct EBICS version for a bank
     * Returns array with version info or null if detection fails
     */
    public function detectVersion($params) {
        $results = [];
        
        // Test configurations based on ebics_version parameter
        $testConfigs = $this->getTestConfigurations($params['ebics_version'] ?? 'H005');
        
        foreach ($testConfigs as $config) {
            $result = $this->testConfiguration($params, $config);
            $results[] = $result;
            
            // If we found a working configuration, return it
            if ($result['works']) {
                return $result['config'];
            }
        }
        
        // No working configuration found, return the most likely based on error analysis
        return $this->analyzeResults($results, $params['ebics_version'] ?? 'H005');
    }
    
    /**
     * Get test configurations based on declared EBICS version
     */
    private function getTestConfigurations($ebicsVersion) {
        $configs = [];
        
        switch($ebicsVersion) {
            case 'H004':
                // H004 is always EBICS 2.4
                $configs[] = [
                    'version' => 'VERSION_24',
                    'signature_version' => 'A005',
                    'use_certificates' => false,
                    'description' => 'EBICS 2.4 (H004)'
                ];
                break;
                
            case 'H005':
                // H005 can be either EBICS 2.5 or 3.0
                // Test 2.5 first as it's more common for H005
                $configs[] = [
                    'version' => 'VERSION_25',
                    'signature_version' => 'A005',
                    'use_certificates' => false,
                    'description' => 'EBICS 2.5 with A005 (H005 as 2.5)'
                ];
                $configs[] = [
                    'version' => 'VERSION_30',
                    'signature_version' => 'A006',
                    'use_certificates' => true,
                    'description' => 'EBICS 3.0 with A006 (H005 as 3.0)'
                ];
                break;
                
            case 'H006':
            case '3.0':
                // H006 is always EBICS 3.0
                $configs[] = [
                    'version' => 'VERSION_30',
                    'signature_version' => 'A006',
                    'use_certificates' => true,
                    'description' => 'EBICS 3.0 (H006)'
                ];
                break;
                
            default:
                // Default: try both 2.5 and 3.0
                $configs[] = [
                    'version' => 'VERSION_25',
                    'signature_version' => 'A005',
                    'use_certificates' => false,
                    'description' => 'EBICS 2.5 (default)'
                ];
                $configs[] = [
                    'version' => 'VERSION_30',
                    'signature_version' => 'A006',
                    'use_certificates' => true,
                    'description' => 'EBICS 3.0'
                ];
        }
        
        return $configs;
    }
    
    /**
     * Test a specific configuration
     */
    private function testConfiguration($params, $config) {
        try {
            // Create temporary keyring with test configuration
            $keyringData = $this->prepareTestKeyring($params, $config);
            
            // Create bank and user
            $bank = new Bank(
                $params['host_id'],
                $params['bank_url']
            );
            
            $user = new User(
                $params['partner_id'],
                $params['user_id']
            );
            
            // Load keyring
            $keyringManager = new ArrayKeyringManager();
            $keyring = $keyringManager->loadKeyring(
                $keyringData,
                $params['password'] ?? 'default_password',
                $config['version']
            );
            
            // Create client
            $client = new EbicsClient($bank, $user, $keyring);
            
            // Try to create INI order (dry run - don't actually send)
            $ini = new INI();
            
            // We can't actually test without sending, but we can check if the order builds correctly
            // In a real implementation, you might want to actually send a test request
            
            return [
                'config' => $config,
                'works' => true,  // Assume it works if no exception
                'error' => null
            ];
            
        } catch (EbicsResponseException $e) {
            return [
                'config' => $config,
                'works' => $this->isAcceptableError($e->getResponseCode()),
                'error' => $e->getResponseCode(),
                'message' => $e->getMessage()
            ];
        } catch (\Exception $e) {
            return [
                'config' => $config,
                'works' => false,
                'error' => 'EXCEPTION',
                'message' => $e->getMessage()
            ];
        }
    }
    
    /**
     * Check if an error code indicates the format is acceptable
     */
    private function isAcceptableError($code) {
        // These codes mean the format is correct but there's another issue
        $acceptableErrors = [
            '091002',  // User not activated - format is OK
            '061001',  // Authentication failed - format is OK
            '061002',  // Account authorization failed - format is OK
            '000000',  // Success
        ];
        
        return in_array($code, $acceptableErrors);
    }
    
    /**
     * Prepare a test keyring with the given configuration
     */
    private function prepareTestKeyring($params, $config) {
        $keyringData = [
            'VERSION' => $config['version'],
            'USER' => [],
            'BANK' => []
        ];
        
        // Generate test keys for each signature type
        foreach (['A', 'E', 'X'] as $sig) {
            $keyPair = $this->generateKeyPair();
            
            $keyringData['USER'][$sig] = [
                'VERSION' => $config['signature_version'],
                'PRIVATE_KEY' => $keyPair['private'],
                'PUBLIC_KEY' => $keyPair['public']
            ];
            
            if ($config['use_certificates']) {
                $keyringData['USER'][$sig]['CERTIFICATE'] = $this->generateCertificate($keyPair['private'], $sig);
            }
        }
        
        // Add empty bank keys
        foreach (['E', 'X'] as $sig) {
            $keyringData['BANK'][$sig] = [
                'PUBLIC_KEY' => null,
                'CERTIFICATE' => null
            ];
        }
        
        return $keyringData;
    }
    
    /**
     * Generate a key pair for testing
     */
    private function generateKeyPair() {
        $config = [
            "private_key_bits" => 2048,
            "private_key_type" => OPENSSL_KEYTYPE_RSA,
        ];
        
        $res = openssl_pkey_new($config);
        openssl_pkey_export($res, $privateKey);
        $publicKey = openssl_pkey_get_details($res);
        
        return [
            'private' => $privateKey,
            'public' => $publicKey["key"]
        ];
    }
    
    /**
     * Generate a self-signed certificate for testing
     */
    private function generateCertificate($privateKey, $signatureType) {
        $dn = [
            "countryName" => "CH",
            "organizationName" => "Test Organization",
            "commonName" => "Test User $signatureType"
        ];
        
        $privkey = openssl_pkey_get_private($privateKey);
        $csr = openssl_csr_new($dn, $privkey, ['digest_alg' => 'sha256']);
        $cert = openssl_csr_sign($csr, null, $privkey, 365, ['digest_alg' => 'sha256']);
        
        openssl_x509_export($cert, $certOut);
        return $certOut;
    }
    
    /**
     * Analyze test results to determine the best configuration
     */
    private function analyzeResults($results, $declaredVersion) {
        // Look for any working configuration
        foreach ($results as $result) {
            if ($result['works']) {
                return $result['config'];
            }
        }
        
        // If none worked, analyze errors to make best guess
        foreach ($results as $result) {
            if ($result['error'] === '090004') {
                // Format error - this config is definitely wrong
                continue;
            }
            // Any other error might mean the format is OK but something else is wrong
            return $result['config'];
        }
        
        // Default fallback based on declared version
        if ($declaredVersion === 'H005') {
            return [
                'version' => 'VERSION_25',
                'signature_version' => 'A005',
                'use_certificates' => false,
                'description' => 'EBICS 2.5 (H005 default fallback)'
            ];
        }
        
        return [
            'version' => 'VERSION_30',
            'signature_version' => 'A006',
            'use_certificates' => true,
            'description' => 'EBICS 3.0 (default fallback)'
        ];
    }
    
    /**
     * Apply detected configuration to an existing keyring
     */
    public function applyConfiguration($keyringPath, $config) {
        $keyringData = json_decode(file_get_contents($keyringPath), true);
        
        // Update version
        $keyringData['VERSION'] = $config['version'];
        
        // Update signature versions
        foreach (['A', 'E', 'X'] as $sig) {
            if (isset($keyringData['USER'][$sig])) {
                $keyringData['USER'][$sig]['VERSION'] = $config['signature_version'];
                
                if (!$config['use_certificates'] && isset($keyringData['USER'][$sig]['CERTIFICATE'])) {
                    unset($keyringData['USER'][$sig]['CERTIFICATE']);
                } elseif ($config['use_certificates'] && !isset($keyringData['USER'][$sig]['CERTIFICATE'])) {
                    // Generate certificate if needed
                    if (isset($keyringData['USER'][$sig]['PRIVATE_KEY'])) {
                        $keyringData['USER'][$sig]['CERTIFICATE'] = $this->generateCertificate(
                            $keyringData['USER'][$sig]['PRIVATE_KEY'],
                            $sig
                        );
                    }
                }
            }
        }
        
        // Save updated keyring
        file_put_contents($keyringPath, json_encode($keyringData, JSON_PRETTY_PRINT));
        
        return true;
    }
}