#!/usr/bin/env php
<?php
/**
 * Fix keys location and format for TEST_PHP connection
 */

$sitePath = '/home/neoffice/frappe-bench/sites/dmis.neoffice.me';
$connectionName = 'TEST_PHP';

// Old location (wrong)
$oldKeysDir = $sitePath . '/private/files/ebics_keys_' . $connectionName;

// New location (correct)
$newKeysDir = $sitePath . '/private/files/ebics_keys/' . $connectionName;

echo "=== EBICS Keys Location Fix ===\n";
echo "Old location: $oldKeysDir\n";
echo "New location: $newKeysDir\n\n";

// Check if old directory exists
if (!is_dir($oldKeysDir)) {
    die("Old keys directory not found: $oldKeysDir\n");
}

// Create new directory structure
$parentDir = dirname($newKeysDir);
if (!is_dir($parentDir)) {
    echo "Creating parent directory: $parentDir\n";
    mkdir($parentDir, 0700, true);
}

if (!is_dir($newKeysDir)) {
    echo "Creating keys directory: $newKeysDir\n";
    mkdir($newKeysDir, 0700, true);
}

// Move the PEM files
$pemFiles = glob($oldKeysDir . '/*.pem');
echo "\nFound " . count($pemFiles) . " PEM files to move:\n";

foreach ($pemFiles as $file) {
    $filename = basename($file);
    $newPath = $newKeysDir . '/' . $filename;
    
    if (copy($file, $newPath)) {
        echo "  ✓ Copied: $filename\n";
    } else {
        echo "  ✗ Failed to copy: $filename\n";
    }
}

echo "\n=== Creating keyring.json ===\n";

// Now we need to create a proper keyring.json
// Since we have the PEM files, we need to convert them to keyring format

// Include the EBICS library
$autoloadPath = '/home/neoffice/frappe-bench/apps/erpnextswiss/erpnextswiss/erpnextswiss/ebics_service/vendor/autoload.php';
if (!file_exists($autoloadPath)) {
    echo "Warning: autoload.php not found at $autoloadPath\n";
    echo "Will create a simple keyring structure instead.\n";
    
    // Create a simple keyring structure that references the PEM files
    $keyring = [
        'version' => 'H005',
        'keys' => [
            'A006' => [
                'private_key_file' => 'a006_private.pem',
                'public_key_file' => 'a006_public.pem',
                'certificate' => null
            ],
            'X002' => [
                'private_key_file' => 'x002_private.pem', 
                'public_key_file' => 'x002_public.pem',
                'certificate' => null
            ],
            'E002' => [
                'private_key_file' => 'e002_private.pem',
                'public_key_file' => 'e002_public.pem',
                'certificate' => null
            ]
        ],
        'bank_keys' => null,
        'created_at' => date('Y-m-d H:i:s')
    ];
    
    $keyringPath = $newKeysDir . '/keyring.json';
    if (file_put_contents($keyringPath, json_encode($keyring, JSON_PRETTY_PRINT))) {
        echo "Created keyring.json with PEM file references\n";
    } else {
        echo "Failed to create keyring.json\n";
    }
} else {
    echo "Using EBICS library to create proper keyring...\n";
    require_once $autoloadPath;
    
    use EbicsApi\Ebics\Services\FileKeyringManager;
    use EbicsApi\Ebics\Models\Keyring;
    
    try {
        // Create keyring manager
        $keyringManager = new FileKeyringManager();
        
        // We can't directly import PEM files into the keyring
        // The keyring needs to be generated fresh or we need the original serialized keyring
        
        echo "Note: Cannot directly convert PEM files to keyring format.\n";
        echo "The keys need to be regenerated or the original keyring restored.\n";
        
    } catch (Exception $e) {
        echo "Error: " . $e->getMessage() . "\n";
    }
}

// Clean up old directory
echo "\n=== Cleanup ===\n";
echo "Old directory still exists at: $oldKeysDir\n";
echo "You can manually delete it after verifying the keys work.\n";

echo "\n=== Done ===\n";
echo "Keys have been moved to the correct location.\n";
echo "However, due to error 061001, you may need to:\n";
echo "1. Reset the connection completely\n";
echo "2. Generate new keys\n";
echo "3. Send new INI/HIA to bank\n";
echo "4. Get bank to re-activate with new keys\n";