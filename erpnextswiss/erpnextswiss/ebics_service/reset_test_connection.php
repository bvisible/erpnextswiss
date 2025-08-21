<?php
/**
 * Reset the TEST_PHP connection and start fresh
 * This will delete the existing keys and allow regeneration
 */

$sitePath = '/home/neoffice/frappe-bench/sites/dmis.neoffice.me';
$connectionName = 'TEST_PHP';
$keysDir = $sitePath . '/private/files/ebics_keys/' . $connectionName;

echo "=== EBICS Connection Reset Script ===\n";
echo "Connection: $connectionName\n";
echo "Keys directory: $keysDir\n\n";

if (!is_dir($keysDir)) {
    echo "Keys directory does not exist. Nothing to reset.\n";
    exit(0);
}

echo "Current contents:\n";
$files = scandir($keysDir);
foreach ($files as $file) {
    if ($file != '.' && $file != '..') {
        $path = $keysDir . '/' . $file;
        $size = filesize($path);
        $mtime = date('Y-m-d H:i:s', filemtime($path));
        echo "  - $file ($size bytes, modified: $mtime)\n";
    }
}

echo "\n";
echo "WARNING: This will delete all keys for connection: $connectionName\n";
echo "You will need to:\n";
echo "1. Generate new keys\n";
echo "2. Send new INI/HIA to bank\n";
echo "3. Generate new INI letter\n";
echo "4. Have bank re-activate with new keys\n";
echo "\n";
echo "Type 'YES' to confirm deletion: ";

$confirm = trim(fgets(STDIN));

if ($confirm !== 'YES') {
    echo "Cancelled.\n";
    exit(0);
}

// Delete all files in the directory
foreach ($files as $file) {
    if ($file != '.' && $file != '..') {
        $path = $keysDir . '/' . $file;
        if (unlink($path)) {
            echo "Deleted: $file\n";
        } else {
            echo "Failed to delete: $file\n";
        }
    }
}

// Remove the directory itself
if (rmdir($keysDir)) {
    echo "Removed directory: $keysDir\n";
} else {
    echo "Failed to remove directory (might not be empty)\n";
}

echo "\n=== Reset Complete ===\n";
echo "The connection has been reset.\n";
echo "You can now generate new keys from the EBICS Control Panel.\n";