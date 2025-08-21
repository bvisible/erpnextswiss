<?php
/**
 * Patch for unified_ebics_service.php
 * Fixes Keyring initialization issues
 */

// Add this function to the UnifiedEbicsService class:
function initializeKeyringVersions($keyring) {
    // Use reflection to set version properties if they're not initialized
    $versionProperties = [
        'userSignatureAVersion' => 'A006',
        'userSignatureXVersion' => 'X002',
        'userSignatureEVersion' => 'E002'
    ];
    
    foreach ($versionProperties as $prop => $defaultValue) {
        try {
            $reflection = new ReflectionClass($keyring);
            if ($reflection->hasProperty($prop)) {
                $property = $reflection->getProperty($prop);
                $property->setAccessible(true);
                
                // Check if property is initialized
                if (PHP_VERSION_ID >= 70400) {
                    if (!$property->isInitialized($keyring)) {
                        $property->setValue($keyring, $defaultValue);
                    }
                } else {
                    // For older PHP versions, just set the value
                    $currentValue = $property->getValue($keyring);
                    if ($currentValue === null) {
                        $property->setValue($keyring, $defaultValue);
                    }
                }
            }
        } catch (Exception $e) {
            // Log but don't fail
            error_log("Warning: Could not initialize property $prop: " . $e->getMessage());
        }
    }
    
    return $keyring;
}

// Modified generateINILetter function:
function generateINILetterFixed($params) {
    try {
        $clientData = $this->getEbicsClient($params);
        $client = $clientData['client'];
        $keyring = $clientData['keyring'];
        
        // Initialize keyring versions if needed
        $keyring = $this->initializeKeyringVersions($keyring);
        
        // Create simplified bank letter data
        $bankLetter = [
            'hostId' => $params['host_id'],
            'userId' => $params['user_id'],  
            'partnerId' => $params['partner_id'],
            'bankName' => 'Credit Suisse Test Platform',
            'bankUrl' => $params['bank_url'],
            'date' => date('Y-m-d'),
            'time' => date('H:i:s'),
            'keys' => []
        ];
        
        // Add key information with safe access
        try {
            // Signature key (A006)
            if (method_exists($keyring, 'getUserSignatureA')) {
                $signKey = $keyring->getUserSignatureA();
                if ($signKey && method_exists($signKey, 'getPublicKey')) {
                    $bankLetter['keys']['signature'] = [
                        'version' => 'A006',
                        'hash' => $this->getKeyHash($signKey),
                        'exponent' => $this->getKeyExponent($signKey),
                        'modulus' => $this->getKeyModulus($signKey)
                    ];
                }
            }
            
            // Authentication key (X002)
            if (method_exists($keyring, 'getUserSignatureX')) {
                $authKey = $keyring->getUserSignatureX();
                if ($authKey && method_exists($authKey, 'getPublicKey')) {
                    $bankLetter['keys']['authentication'] = [
                        'version' => 'X002',
                        'hash' => $this->getKeyHash($authKey),
                        'exponent' => $this->getKeyExponent($authKey),
                        'modulus' => $this->getKeyModulus($authKey)
                    ];
                }
            }
            
            // Encryption key (E002)
            if (method_exists($keyring, 'getUserSignatureE')) {
                $encKey = $keyring->getUserSignatureE();
                if ($encKey && method_exists($encKey, 'getPublicKey')) {
                    $bankLetter['keys']['encryption'] = [
                        'version' => 'E002',
                        'hash' => $this->getKeyHash($encKey),
                        'exponent' => $this->getKeyExponent($encKey),
                        'modulus' => $this->getKeyModulus($encKey)
                    ];
                }
            }
        } catch (Exception $e) {
            error_log("Warning: Could not extract all key information: " . $e->getMessage());
        }
        
        // Generate simple HTML letter if PDF generation fails
        $html = $this->generateSimpleINILetterHTML($bankLetter);
        
        // Try to generate PDF, fallback to HTML
        try {
            $ebicsBankLetter = new EbicsBankLetter();
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
        } catch (Exception $pdfError) {
            // Fallback to HTML
            return [
                'success' => true,
                'format' => 'html',
                'content' => base64_encode($html),
                'filename' => 'EBICS_INI_Letter_' . date('Ymd_His') . '.html',
                'message' => 'PDF generation failed, returning HTML format'
            ];
        }
        
    } catch (Exception $e) {
        return [
            'success' => false,
            'error' => $e->getMessage(),
            'trace' => $e->getTraceAsString()
        ];
    }
}

// Helper function to generate simple HTML letter
function generateSimpleINILetterHTML($bankLetter) {
    $html = '<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>EBICS INI Letter</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #333; }
        .info-table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        .info-table td { padding: 8px; border: 1px solid #ddd; }
        .info-table td:first-child { font-weight: bold; width: 30%; background: #f5f5f5; }
        .key-section { margin: 30px 0; }
        .key-hash { font-family: monospace; word-break: break-all; }
        .signature-section { margin-top: 50px; border-top: 1px solid #333; padding-top: 20px; }
    </style>
</head>
<body>
    <h1>EBICS Initialization Letter (INI)</h1>
    
    <table class="info-table">
        <tr><td>Date</td><td>' . $bankLetter['date'] . '</td></tr>
        <tr><td>Time</td><td>' . $bankLetter['time'] . '</td></tr>
        <tr><td>Bank Name</td><td>' . $bankLetter['bankName'] . '</td></tr>
        <tr><td>Bank URL</td><td>' . $bankLetter['bankUrl'] . '</td></tr>
        <tr><td>Host ID</td><td>' . $bankLetter['hostId'] . '</td></tr>
        <tr><td>Partner ID</td><td>' . $bankLetter['partnerId'] . '</td></tr>
        <tr><td>User ID</td><td>' . $bankLetter['userId'] . '</td></tr>
    </table>';
    
    foreach ($bankLetter['keys'] as $keyType => $keyInfo) {
        $html .= '
    <div class="key-section">
        <h2>' . ucfirst($keyType) . ' Key (' . $keyInfo['version'] . ')</h2>
        <table class="info-table">
            <tr><td>Version</td><td>' . $keyInfo['version'] . '</td></tr>
            <tr><td>Hash (SHA-256)</td><td class="key-hash">' . $keyInfo['hash'] . '</td></tr>
        </table>
    </div>';
    }
    
    $html .= '
    <div class="signature-section">
        <p><strong>Please sign and send this letter to your bank to activate EBICS access.</strong></p>
        <br><br>
        <p>_____________________________<br>
        Date and Signature</p>
    </div>
</body>
</html>';
    
    return $html;
}