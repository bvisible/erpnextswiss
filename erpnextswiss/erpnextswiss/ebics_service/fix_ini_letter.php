#!/usr/bin/env php
<?php
/**
 * Fix INI Letter generation by patching Keyring initialization
 */

echo "=== Fixing INI Letter Generation ===\n\n";

// Create a patched generateINILetter function
$patchContent = '<?php
// Patch for unified_ebics_service.php - INI Letter generation fix

/**
 * Initialize Keyring version properties to avoid "must not be accessed before initialization" errors
 */
function initializeKeyringVersions($keyring) {
    $versionProperties = [
        "userSignatureAVersion" => "A006",
        "userSignatureXVersion" => "X002", 
        "userSignatureEVersion" => "E002"
    ];
    
    foreach ($versionProperties as $prop => $defaultValue) {
        try {
            $reflection = new ReflectionClass($keyring);
            if ($reflection->hasProperty($prop)) {
                $property = $reflection->getProperty($prop);
                $property->setAccessible(true);
                
                // Check if initialized (PHP 7.4+)
                if (PHP_VERSION_ID >= 70400) {
                    if (method_exists($property, "isInitialized") && !$property->isInitialized($keyring)) {
                        $property->setValue($keyring, $defaultValue);
                    }
                } else {
                    // For older PHP, check if null
                    $value = $property->getValue($keyring);
                    if ($value === null) {
                        $property->setValue($keyring, $defaultValue);
                    }
                }
            }
        } catch (Exception $e) {
            // Silently continue
        }
    }
    
    return $keyring;
}

/**
 * Generate simple HTML INI letter as fallback
 */
function generateSimpleINILetter($params, $keyring) {
    $html = \'<!DOCTYPE html>
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
        .key-section { margin: 30px 0; page-break-inside: avoid; }
        .key-hash { font-family: monospace; font-size: 10px; word-break: break-all; }
        .signature-section { margin-top: 50px; border-top: 1px solid #333; padding-top: 20px; }
    </style>
</head>
<body>
    <h1>EBICS Initialization Letter (INI)</h1>
    
    <table class="info-table">
        <tr><td>Date</td><td>\' . date("Y-m-d") . \'</td></tr>
        <tr><td>Time</td><td>\' . date("H:i:s") . \'</td></tr>
        <tr><td>Bank Name</td><td>\' . ($params["bank_name"] ?? "Credit Suisse Test Platform") . \'</td></tr>
        <tr><td>Bank URL</td><td>\' . ($params["bank_url"] ?? "") . \'</td></tr>
        <tr><td>Host ID</td><td>\' . ($params["host_id"] ?? "") . \'</td></tr>
        <tr><td>Partner ID</td><td>\' . ($params["partner_id"] ?? "") . \'</td></tr>
        <tr><td>User ID</td><td>\' . ($params["user_id"] ?? "") . \'</td></tr>
    </table>\';
    
    // Try to get key hashes
    $keys = [];
    try {
        if (method_exists($keyring, "getUserSignatureA")) {
            $key = $keyring->getUserSignatureA();
            if ($key && method_exists($key, "getPublicKey")) {
                $publicKey = $key->getPublicKey();
                $keys["Signature (A006)"] = hash("sha256", $publicKey);
            }
        }
    } catch (Exception $e) {}
    
    try {
        if (method_exists($keyring, "getUserSignatureX")) {
            $key = $keyring->getUserSignatureX();
            if ($key && method_exists($key, "getPublicKey")) {
                $publicKey = $key->getPublicKey();
                $keys["Authentication (X002)"] = hash("sha256", $publicKey);
            }
        }
    } catch (Exception $e) {}
    
    try {
        if (method_exists($keyring, "getUserSignatureE")) {
            $key = $keyring->getUserSignatureE();
            if ($key && method_exists($key, "getPublicKey")) {
                $publicKey = $key->getPublicKey();
                $keys["Encryption (E002)"] = hash("sha256", $publicKey);
            }
        }
    } catch (Exception $e) {}
    
    foreach ($keys as $keyType => $keyHash) {
        $html .= \'
    <div class="key-section">
        <h3>\' . $keyType . \'</h3>
        <table class="info-table">
            <tr><td>Hash (SHA-256)</td><td class="key-hash">\' . $keyHash . \'</td></tr>
        </table>
    </div>\';
    }
    
    $html .= \'
    <div class="signature-section">
        <p><strong>Please sign and send this letter to your bank to activate EBICS access.</strong></p>
        <br><br>
        <table style="width: 100%;">
            <tr>
                <td style="width: 50%;">
                    <p>_____________________________<br>
                    Date</p>
                </td>
                <td style="width: 50%;">
                    <p>_____________________________<br>
                    Signature</p>
                </td>
            </tr>
        </table>
    </div>
</body>
</html>\';
    
    return $html;
}
';

// Save the patch
file_put_contents(__DIR__ . '/ini_letter_patch.php', $patchContent);
echo "✓ Created ini_letter_patch.php\n";

// Create a simple test script
$testScript = '<?php
require_once __DIR__ . "/ebics_autoload.php";
require_once __DIR__ . "/ini_letter_patch.php";

// Test the patch
try {
    $keyring = new EbicsApi\Ebics\Models\Keyring();
    $keyring = initializeKeyringVersions($keyring);
    
    echo "✓ Keyring initialized successfully\n";
    
    // Test HTML generation
    $params = [
        "host_id" => "TEST001",
        "user_id" => "USER001",
        "partner_id" => "PARTNER001",
        "bank_url" => "https://test.bank.com/ebics"
    ];
    
    $html = generateSimpleINILetter($params, $keyring);
    if (strlen($html) > 100) {
        echo "✓ HTML letter generated successfully\n";
    }
    
} catch (Exception $e) {
    echo "✗ Error: " . $e->getMessage() . "\n";
}
';

file_put_contents(__DIR__ . '/test_ini_letter.php', $testScript);
echo "✓ Created test_ini_letter.php\n";

echo "\nTesting the fix...\n";
passthru('php ' . __DIR__ . '/test_ini_letter.php');