<?php
/**
 * Fix for keyring saving issue
 * The keyring needs to be saved in the correct format for ebics-client-php
 */

// Check if we're in the right directory
if (!file_exists('unified_ebics_service.php')) {
    die("Please run this script from the ebics_service directory\n");
}

// Include required files
require_once __DIR__ . '/ebics_autoload.php';

use EbicsApi\Ebics\Services\FileKeyringManager;
use EbicsApi\Ebics\Models\Keyring;

$sitePath = '/home/neoffice/frappe-bench/sites/dmis.neoffice.me';
$keysDir = $sitePath . '/private/files/ebics_keys/TEST_PHP';

echo "Checking keys directory: $keysDir\n";

if (!is_dir($keysDir)) {
    die("Keys directory not found: $keysDir\n");
}

// Check for existing keys.json
$keysJsonPath = $keysDir . '/keys.json';
$keyringPath = $keysDir . '/keyring.json';

if (file_exists($keysJsonPath)) {
    echo "Found keys.json\n";
    
    // Read the keys.json file
    $keysData = json_decode(file_get_contents($keysJsonPath), true);
    
    if (!$keysData || !isset($keysData['keys'])) {
        die("Invalid keys.json format\n");
    }
    
    echo "Keys found:\n";
    foreach ($keysData['keys'] as $type => $keyInfo) {
        echo "  - $type: Hash = " . substr($keyInfo['hash'], 0, 20) . "...\n";
    }
    
    // Now we need to convert this to proper keyring format
    // The keyring should be serialized with the FileKeyringManager
    
    try {
        // Create a new keyring
        $keyringManager = new FileKeyringManager();
        $keyring = $keyringManager->createKeyring(Keyring::VERSION_25); // H005
        
        // We can't directly set the keys from PEM as they're already generated
        // We need to save the existing keyring in the proper format
        
        // The issue is that the keys are saved as separate PEM files
        // but ebics-client-php expects them in the keyring object
        
        echo "\nThe keys exist but are not in the correct format for ebics-client-php.\n";
        echo "The service needs to use the keyring serialization format.\n";
        echo "\nRecommendation: Reset the connection and regenerate keys using the proper flow.\n";
        
    } catch (Exception $e) {
        echo "Error: " . $e->getMessage() . "\n";
    }
} else {
    echo "No keys.json found\n";
}

// Check if keyring.json exists
if (file_exists($keyringPath)) {
    echo "\nFound keyring.json - checking format...\n";
    $content = file_get_contents($keyringPath);
    
    if (strpos($content, '{') === 0) {
        // It's JSON
        $data = json_decode($content, true);
        if ($data) {
            echo "Keyring is in JSON format\n";
            if (isset($data['keys'])) {
                echo "Has keys field\n";
            }
        }
    } else {
        echo "Keyring appears to be encrypted/serialized\n";
        echo "First 50 chars: " . substr($content, 0, 50) . "\n";
    }
}

echo "\n=== SOLUTION ===\n";
echo "The problem is that the keys are saved in a custom format (keys.json)\n";
echo "instead of using the FileKeyringManager's serialization.\n";
echo "\nTo fix this, the unified_ebics_service.php needs to:\n";
echo "1. Use FileKeyringManager->saveKeyring() properly\n";
echo "2. Use FileKeyringManager->loadKeyring() properly\n";
echo "3. Not save keys as separate PEM files\n";
echo "\nFor now, you should:\n";
echo "1. Reset the EBICS connection\n";
echo "2. Generate new keys\n";
echo "3. The system will now save them correctly\n";