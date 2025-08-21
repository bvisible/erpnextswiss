#!/usr/bin/env php
<?php
/**
 * Test and fix EBICS service issues
 */

// Test 1: Check if ebics-client-php is properly installed
echo "=== EBICS Service Test ===\n\n";

$baseDir = dirname(__FILE__);
$vendorAutoload = $baseDir . '/vendor/autoload.php';
$altAutoload = $baseDir . '/../ebics-client-php-3.x/vendor/autoload.php';

if (file_exists($vendorAutoload)) {
    echo "✓ Vendor autoload found at: $vendorAutoload\n";
    require_once $vendorAutoload;
} elseif (file_exists($altAutoload)) {
    echo "✓ Vendor autoload found at: $altAutoload\n";
    require_once $altAutoload;
} else {
    echo "✗ ERROR: Could not find vendor/autoload.php\n";
    echo "  Please run: composer install\n";
    exit(1);
}

// Test 2: Check if required classes exist
$requiredClasses = [
    'EbicsApi\Ebics\Client',
    'EbicsApi\Ebics\Models\Bank',
    'EbicsApi\Ebics\Models\User',
    'EbicsApi\Ebics\Models\Keyring',
    'EbicsApi\Ebics\Services\KeyringManager',
    'EbicsApi\Ebics\Builders\Request\OrderDetailsBuilder',
    'EbicsApi\Ebics\Orders\INI',
    'EbicsApi\Ebics\Orders\HIA',
    'EbicsApi\Ebics\Orders\HPB'
];

echo "\nChecking required classes:\n";
foreach ($requiredClasses as $class) {
    if (class_exists($class)) {
        echo "✓ $class\n";
    } else {
        echo "✗ $class not found\n";
    }
}

// Test 3: Test Keyring initialization
echo "\n=== Testing Keyring Initialization ===\n";

try {
    $keyringManager = new EbicsApi\Ebics\Services\KeyringManager();
    $keyring = new EbicsApi\Ebics\Models\Keyring();
    
    // Check if version properties exist
    $reflection = new ReflectionClass($keyring);
    $versionProps = ['userSignatureAVersion', 'userSignatureXVersion', 'userSignatureEVersion'];
    
    foreach ($versionProps as $prop) {
        if ($reflection->hasProperty($prop)) {
            echo "✓ Property $prop exists\n";
            
            $property = $reflection->getProperty($prop);
            $property->setAccessible(true);
            
            // Try to initialize if not set
            if (PHP_VERSION_ID >= 70400) {
                if (!$property->isInitialized($keyring)) {
                    echo "  → Property not initialized, setting default value\n";
                    $defaultValue = str_contains($prop, 'A') ? 'A006' : 
                                   (str_contains($prop, 'X') ? 'X002' : 'E002');
                    $property->setValue($keyring, $defaultValue);
                }
            }
        } else {
            echo "✗ Property $prop does not exist\n";
        }
    }
    
    echo "\n✓ Keyring can be instantiated\n";
    
} catch (Exception $e) {
    echo "✗ Error with Keyring: " . $e->getMessage() . "\n";
}

// Test 4: Check if we can generate keys
echo "\n=== Testing Key Generation ===\n";

try {
    $keyringManager = new EbicsApi\Ebics\Services\KeyringManager();
    $keyring = new EbicsApi\Ebics\Models\Keyring();
    
    // Generate keys
    $keyringManager->generateKeys($keyring);
    
    echo "✓ Keys generated successfully\n";
    
    // Check if keys are accessible
    if (method_exists($keyring, 'getUserSignatureA')) {
        $signKey = $keyring->getUserSignatureA();
        if ($signKey) {
            echo "✓ Signature key (A) is accessible\n";
        }
    }
    
    if (method_exists($keyring, 'getUserSignatureX')) {
        $authKey = $keyring->getUserSignatureX();
        if ($authKey) {
            echo "✓ Authentication key (X) is accessible\n";
        }
    }
    
    if (method_exists($keyring, 'getUserSignatureE')) {
        $encKey = $keyring->getUserSignatureE();
        if ($encKey) {
            echo "✓ Encryption key (E) is accessible\n";
        }
    }
    
} catch (Exception $e) {
    echo "✗ Error generating keys: " . $e->getMessage() . "\n";
}

echo "\n=== Test Complete ===\n";