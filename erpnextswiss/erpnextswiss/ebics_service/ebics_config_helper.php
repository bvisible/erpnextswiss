<?php
/**
 * EBICS Configuration Helper
 * Helps determine the correct EBICS configuration based on bank and version
 */

class EbicsConfigHelper {
    
    private static $mappings = null;
    
    /**
     * Load bank mappings
     */
    private static function loadMappings() {
        if (self::$mappings === null) {
            $mappingFile = __DIR__ . '/bank_ebics_mapping.json';
            if (file_exists($mappingFile)) {
                self::$mappings = json_decode(file_get_contents($mappingFile), true);
            } else {
                self::$mappings = [
                    'bank_mappings' => [],
                    'default_mappings' => []
                ];
            }
        }
        return self::$mappings;
    }
    
    /**
     * Get EBICS configuration for a bank
     * 
     * @param string $bankUrl Bank URL
     * @param string $ebicsVersion Declared EBICS version (H004, H005, H006)
     * @return array Configuration array
     */
    public static function getConfiguration($bankUrl, $ebicsVersion) {
        $mappings = self::loadMappings();
        
        // Extract domain from bank URL
        $domain = self::extractDomain($bankUrl);
        
        // Check if we have a specific mapping for this bank
        foreach ($mappings['bank_mappings'] as $pattern => $bankConfig) {
            if (strpos($domain, $pattern) !== false) {
                if (isset($bankConfig[$ebicsVersion])) {
                    return $bankConfig[$ebicsVersion];
                }
            }
        }
        
        // Fall back to default mapping for the version
        if (isset($mappings['default_mappings'][$ebicsVersion])) {
            return $mappings['default_mappings'][$ebicsVersion];
        }
        
        // Ultimate fallback
        return [
            'version' => 'VERSION_25',
            'signature_version' => 'A005',
            'use_certificates' => false,
            'comment' => 'Default fallback configuration'
        ];
    }
    
    /**
     * Extract domain from URL
     */
    private static function extractDomain($url) {
        $parts = parse_url($url);
        return isset($parts['host']) ? $parts['host'] : $url;
    }
    
    /**
     * Apply configuration to keyring data
     */
    public static function applyToKeyring(&$keyringData, $config) {
        // Set main version
        $keyringData['VERSION'] = $config['version'];
        
        // Update user signatures
        foreach (['A', 'E', 'X'] as $sig) {
            if (isset($keyringData['USER'][$sig])) {
                $keyringData['USER'][$sig]['VERSION'] = $config['signature_version'];
                
                // Handle certificates
                if (!$config['use_certificates'] && isset($keyringData['USER'][$sig]['CERTIFICATE'])) {
                    unset($keyringData['USER'][$sig]['CERTIFICATE']);
                } elseif ($config['use_certificates'] && !isset($keyringData['USER'][$sig]['CERTIFICATE'])) {
                    // Certificate will be generated if needed
                    // This is just a placeholder
                }
            }
        }
        
        // Update bank signatures if they exist
        foreach (['E', 'X'] as $sig) {
            if (isset($keyringData['BANK'][$sig]) && isset($keyringData['BANK'][$sig]['VERSION'])) {
                $keyringData['BANK'][$sig]['VERSION'] = $config['signature_version'];
                
                if (!$config['use_certificates'] && isset($keyringData['BANK'][$sig]['CERTIFICATE'])) {
                    unset($keyringData['BANK'][$sig]['CERTIFICATE']);
                }
            }
        }
        
        return true;
    }
    
    /**
     * Check if configuration needs certificates
     */
    public static function needsCertificates($ebicsVersion, $bankUrl = null) {
        $config = self::getConfiguration($bankUrl ?? '', $ebicsVersion);
        return $config['use_certificates'] ?? false;
    }
    
    /**
     * Get the correct keyring version constant
     */
    public static function getKeyringVersion($ebicsVersion, $bankUrl = null) {
        $config = self::getConfiguration($bankUrl ?? '', $ebicsVersion);
        return $config['version'] ?? 'VERSION_25';
    }
    
    /**
     * Add or update a bank mapping
     */
    public static function addBankMapping($bankPattern, $ebicsVersion, $config) {
        $mappings = self::loadMappings();
        
        if (!isset($mappings['bank_mappings'][$bankPattern])) {
            $mappings['bank_mappings'][$bankPattern] = [];
        }
        
        $mappings['bank_mappings'][$bankPattern][$ebicsVersion] = $config;
        
        // Save updated mappings
        $mappingFile = __DIR__ . '/bank_ebics_mapping.json';
        file_put_contents($mappingFile, json_encode($mappings, JSON_PRETTY_PRINT));
        
        // Clear cache
        self::$mappings = null;
        
        return true;
    }
}