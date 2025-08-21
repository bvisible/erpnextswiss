<?php
// Add this function to UnifiedEbicsService class

private function generateINILetter($params) {
    try {
        // Load keyring
        $keyringPath = $this->getKeyringPath($params['connection_name']);
        
        if (!file_exists($keyringPath)) {
            return [
                'success' => false,
                'error' => 'Keys not found. Please generate keys first.'
            ];
        }
        
        // Initialize keyring with version
        $keyringVersion = $params['ebics_version'] ?? 'H005';
        $keyring = $this->keyringManager->loadKeyring($keyringPath, $params['password'] ?? '', $keyringVersion);
        
        // Initialize version properties
        if (function_exists('initializeKeyringVersions')) {
            $keyring = initializeKeyringVersions($keyring);
        }
        
        // Generate simple HTML letter
        $html = generateSimpleINILetter($params, $keyring);
        
        // Return as HTML (PDF conversion could be added later)
        return [
            'success' => true,
            'format' => 'html',
            'content' => base64_encode($html),
            'filename' => 'EBICS_INI_Letter_' . date('Ymd_His') . '.html'
        ];
        
    } catch (Exception $e) {
        return [
            'success' => false,
            'error' => 'Failed to generate INI letter: ' . $e->getMessage()
        ];
    }
}