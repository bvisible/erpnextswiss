#!/usr/bin/env php
<?php

// Test script to identify available EBICS order classes and their requirements

require_once '/Users/jeremy/Downloads/ebics-client-php-3.x/vendor/autoload.php';

use EbicsApi\Ebics\Orders;
use EbicsApi\Ebics\Contexts;

echo "=== EBICS Order Classes Test ===\n\n";

// Test available order classes
$orderClasses = [
    'BTD' => 'Business Transaction Download (EBICS 3.0)',
    'BTU' => 'Business Transaction Upload (EBICS 3.0)',
    'FDL' => 'File Download',
    'FUL' => 'File Upload',
    'HAA' => 'Available order types',
    'HAC' => 'Customer protocol overview',
    'HCS' => 'Subscriber information',
    'HEV' => 'EBICS versions',
    'HIA' => 'Identification & Authentication signature',
    'HKD' => 'Customer properties and settings',
    'HPB' => 'Bank public keys',
    'HPD' => 'Bank parameters',
    'HTD' => 'Transaction details',
    'INI' => 'Initialization',
    'PTK' => 'Transaction status',
    'SPR' => 'Suspend order'
];

echo "Available Order Classes:\n";
echo "------------------------\n";

foreach ($orderClasses as $class => $description) {
    $fullClass = "\\EbicsApi\\Ebics\\Orders\\$class";
    if (class_exists($fullClass)) {
        echo "✓ $class - $description\n";
        
        // Check constructor requirements
        $reflection = new ReflectionClass($fullClass);
        $constructor = $reflection->getConstructor();
        if ($constructor) {
            $params = $constructor->getParameters();
            if (count($params) > 0) {
                echo "  Parameters:\n";
                foreach ($params as $param) {
                    $type = $param->getType();
                    $typeName = $type ? $type->getName() : 'mixed';
                    $default = $param->isDefaultValueAvailable() ? ' = ' . json_encode($param->getDefaultValue()) : '';
                    $optional = $param->isOptional() ? ' (optional)' : '';
                    echo "    - {$param->getName()}: $typeName$default$optional\n";
                }
            }
        }
    } else {
        echo "✗ $class - Class not found\n";
    }
}

echo "\n=== Testing Statement Download Orders ===\n\n";

// Test what works for statement downloads
$testDate = new DateTime('2024-01-01');
$endDate = new DateTime('2024-01-31');

// Test FDL with different contexts
echo "Testing FDL order:\n";
try {
    $fdlContext = new Contexts\FDLContext();
    $fdlContext->setFileFormat('camt.053');
    $fdlContext->setCountryCode('CH');
    
    $fdlOrder = new Orders\FDL($fdlContext, $testDate, $endDate);
    echo "✓ FDL order created successfully with FDLContext\n";
} catch (Exception $e) {
    echo "✗ FDL order failed: " . $e->getMessage() . "\n";
}

// Test HAC for statements (some banks use this)
echo "\nTesting HAC order:\n";
try {
    $hacOrder = new Orders\HAC($testDate, $endDate);
    echo "✓ HAC order created successfully\n";
} catch (Exception $e) {
    echo "✗ HAC order failed: " . $e->getMessage() . "\n";
}

// Test direct camt.053 download (Swiss specific)
echo "\nTesting Swiss-specific orders:\n";

// For Swiss banks, we might need to use specific order types
$swissOrderTypes = ['Z53', 'Z54', 'ZSR', 'Z01'];
foreach ($swissOrderTypes as $orderType) {
    $class = "\\EbicsApi\\Ebics\\Orders\\$orderType";
    if (class_exists($class)) {
        echo "✓ $orderType order class exists\n";
    } else {
        echo "✗ $orderType order class not found - might need custom implementation\n";
    }
}

echo "\n=== Context Classes Test ===\n\n";

// Test available context classes
$contextClasses = [
    'BTDContext' => 'BTD Context (EBICS 3.0)',
    'BTUContext' => 'BTU Context (EBICS 3.0)',
    'FDLContext' => 'FDL Context',
    'FULContext' => 'FUL Context',
    'HVDContext' => 'HVD Context',
    'HVEContext' => 'HVE Context',
    'HVTContext' => 'HVT Context',
    'HVUContext' => 'HVU Context',
    'HVZContext' => 'HVZ Context'
];

foreach ($contextClasses as $class => $description) {
    $fullClass = "\\EbicsApi\\Ebics\\Contexts\\$class";
    if (class_exists($fullClass)) {
        echo "✓ $class - $description\n";
    } else {
        echo "✗ $class - Not found\n";
    }
}

echo "\n=== Done ===\n";