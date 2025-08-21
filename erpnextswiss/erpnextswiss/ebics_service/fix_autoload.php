#!/usr/bin/env php
<?php
/**
 * Fix autoload for EBICS service
 */

echo "=== Fixing EBICS Autoload ===\n\n";

// Create a custom autoload file
$autoloadContent = '<?php
// Custom autoload for EBICS service

spl_autoload_register(function ($class) {
    // EBICS API classes
    if (strpos($class, "EbicsApi\\\\Ebics\\\\") === 0) {
        $path = str_replace("EbicsApi\\\\Ebics\\\\", "", $class);
        $path = str_replace("\\\\", "/", $path);
        $file = __DIR__ . "/src/" . $path . ".php";
        
        if (file_exists($file)) {
            require_once $file;
            return true;
        }
    }
    
    // Other vendor classes
    $vendorFile = __DIR__ . "/vendor/autoload.php";
    if (file_exists($vendorFile)) {
        require_once $vendorFile;
    }
    
    return false;
});

// Load phpseclib if available
$phpseclib = __DIR__ . "/vendor/phpseclib/phpseclib/phpseclib/autoload.php";
if (file_exists($phpseclib)) {
    require_once $phpseclib;
}
';

file_put_contents(__DIR__ . '/ebics_autoload.php', $autoloadContent);
echo "✓ Created ebics_autoload.php\n";

// Test the autoload
require_once __DIR__ . '/ebics_autoload.php';

$testClasses = [
    'EbicsApi\Ebics\Models\Bank',
    'EbicsApi\Ebics\Models\User',
    'EbicsApi\Ebics\Models\Keyring',
    'EbicsApi\Ebics\EbicsClient',
    'EbicsApi\Ebics\Orders\INI',
    'EbicsApi\Ebics\Orders\HIA',
    'EbicsApi\Ebics\Orders\HPB'
];

echo "\nTesting classes with new autoload:\n";
foreach ($testClasses as $class) {
    if (class_exists($class)) {
        echo "✓ $class loaded\n";
    } else {
        echo "✗ $class not found\n";
    }
}

echo "\n✓ Autoload fixed!\n";