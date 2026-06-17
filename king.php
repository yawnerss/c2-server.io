<?php
/**
 * PHP Script to Download and Run flood_of-noah Repository
 * This script will:
 * 1. Download the repository as a ZIP from GitHub
 * 2. Extract the ZIP file
 * 3. Install Node.js dependencies
 * 4. Run the index.js file
 *
 * ⚠️ WARNING: This script downloads and executes code from the internet.
 * Only use this with trusted sources and in secure environments.
 */

// ============================================================
// CONFIGURATION
// ============================================================
$REPO_URL = 'https://github.com/benbenido025-lab/flood_of-noah/archive/refs/heads/main.zip';
$EXTRACT_DIR = 'flood_of-noah';
$NODE_PATH = '/tmp/node-v18.17.1-linux-x64/bin/node'; // Update if Node.js is elsewhere
$NPM_PATH = '/tmp/node-v18.17.1-linux-x64/bin/npm'; // Update if npm is elsewhere

// ============================================================
// FUNCTIONS
// ============================================================

function log_message($message, $type = 'info') {
    $timestamp = date('Y-m-d H:i:s');
    $prefix = '•';
    if ($type === 'success') {
        $prefix = '✅';
    } elseif ($type === 'error') {
        $prefix = '❌';
    } elseif ($type === 'warning') {
        $prefix = '⚠️';
    } elseif ($type === 'info') {
        $prefix = 'ℹ️';
    }
    echo "[$timestamp] $prefix $message\n";
}

function run_command($command, &$output = null, &$return_code = null) {
    log_message("Executing: $command", 'info');
    exec($command . ' 2>&1', $output, $return_code);
    if ($return_code !== 0) {
        log_message("Command failed with code: $return_code", 'error');
        if ($output) {
            echo "Output:\n" . implode("\n", $output) . "\n";
        }
        return false;
    }
    if ($output) {
        echo implode("\n", $output) . "\n";
    }
    return true;
}

function check_node_available() {
    global $NODE_PATH;
    if (file_exists($NODE_PATH)) {
        return $NODE_PATH;
    }
    exec('which node 2>/dev/null', $output, $code);
    if ($code === 0 && !empty($output)) {
        return $output[0];
    }
    $common_paths = [
        '/usr/bin/node',
        '/usr/local/bin/node',
        '/opt/bitnami/node/bin/node',
        '/tmp/node-v18.17.1-linux-x64/bin/node'
    ];
    foreach ($common_paths as $path) {
        if (file_exists($path)) {
            return $path;
        }
    }
    return null;
}

// ============================================================
// MAIN EXECUTION
// ============================================================

log_message("Starting flood_of-noah deployment (ZIP method)", 'info');
log_message("Repository ZIP: $REPO_URL", 'info');

// Check Node.js
$node = check_node_available();
if (!$node) {
    log_message("Node.js not found. Please install Node.js first.", 'error');
    log_message("Try: export PATH=/tmp/node-v18.17.1-linux-x64/bin:\$PATH", 'info');
    exit(1);
}
log_message("Node.js found at: $node", 'success');

// Check for unzip
exec('which unzip 2>/dev/null', $unzip_output, $unzip_code);
if ($unzip_code !== 0) {
    log_message("unzip is not installed. Trying to use PHP's ZipArchive...", 'warning');
}

// Clean up old directory
$WORK_DIR = __DIR__ . '/' . $EXTRACT_DIR;
if (is_dir($WORK_DIR)) {
    log_message("Removing existing directory: $WORK_DIR", 'warning');
    run_command("rm -rf $WORK_DIR");
}

// Download ZIP file
log_message("Downloading repository ZIP...", 'info');
$zip_file = __DIR__ . '/repo.zip';
if (!run_command("wget -O $zip_file $REPO_URL")) {
    log_message("Failed to download ZIP file", 'error');
    exit(1);
}
log_message("ZIP file downloaded successfully!", 'success');

// Extract ZIP file
log_message("Extracting ZIP file...", 'info');
if (function_exists('zip_open')) {
    // Use PHP's ZipArchive if available
    $zip = new ZipArchive();
    if ($zip->open($zip_file) === true) {
        $zip->extractTo(__DIR__);
        $zip->close();
        log_message("Extracted using PHP ZipArchive", 'success');
    } else {
        log_message("PHP ZipArchive failed, trying system unzip", 'warning');
        run_command("unzip $zip_file -d .");
    }
} else {
    // Fallback to system unzip
    if (!run_command("unzip $zip_file -d .")) {
        log_message("Failed to extract ZIP file", 'error');
        exit(1);
    }
}

// Find the extracted directory (it will be flood_of-noah-main)
$extracted_dirs = glob('flood_of-noah-main*', GLOB_ONLYDIR);
if (empty($extracted_dirs)) {
    log_message("Could not find extracted directory", 'error');
    exit(1);
}
$extracted_dir = $extracted_dirs[0];
log_message("Extracted to: $extracted_dir", 'success');

// Rename to a standard name
if ($extracted_dir !== $EXTRACT_DIR) {
    run_command("mv $extracted_dir $EXTRACT_DIR");
}
chdir($EXTRACT_DIR);
log_message("Changed to: " . getcwd(), 'info');

// Install dependencies
log_message("Installing Node.js dependencies...", 'info');
if (!run_command("$NPM_PATH install")) {
    log_message("Failed to install dependencies", 'error');
    exit(1);
}
log_message("Dependencies installed successfully!", 'success');

// Create .env file if needed
if (!file_exists('.env')) {
    log_message("Creating .env file...", 'info');
    file_put_contents('.env', "PORT=8080\nNODE_ENV=production\n");
}

// Check if index.js exists
if (!file_exists('index.js')) {
    log_message("index.js not found in the repository!", 'error');
    log_message("Available files:", 'info');
    $files = scandir('.');
    foreach ($files as $file) {
        if ($file !== '.' && $file !== '..') {
            echo "  - $file\n";
        }
    }
    exit(1);
}

// Run index.js
log_message("Starting index.js...", 'info');
log_message("Press Ctrl+C to stop the server", 'warning');
log_message("===============================================", 'info');

$command = "$node index.js";
passthru($command);
