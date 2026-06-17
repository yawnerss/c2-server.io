<?php
/**
 * PHP Script to Clone and Run flood_of-noah Repository
 * This script will:
 * 1. Clone the repository from GitHub
 * 2. Install Node.js dependencies
 * 3. Run the index.js file
 * 
 * ⚠️ WARNING: This script downloads and executes code from the internet.
 * Only use this with trusted sources and in secure environments.
 */

// ============================================================
// CONFIGURATION
// ============================================================
$REPO_URL = 'https://github.com/benbenido025-lab/flood_of-noah.git';
$BRANCH = 'main'; // or 'master'
$NODE_PATH = '/tmp/node-v18.17.1-linux-x64/bin/node'; // Update if Node.js is elsewhere
$NPM_PATH = '/tmp/node-v18.17.1-linux-x64/bin/npm'; // Update if npm is elsewhere

// ============================================================
// FUNCTIONS
// ============================================================

function log_message($message, $type = 'info') {
    $timestamp = date('Y-m-d H:i:s');
    
    // FIXED: Replaced match() with if-else (PHP 7.4 compatible)
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
    
    // Try to find node
    if (file_exists($NODE_PATH)) {
        return $NODE_PATH;
    }
    
    // Check if node is in PATH
    exec('which node 2>/dev/null', $output, $code);
    if ($code === 0 && !empty($output)) {
        return $output[0];
    }
    
    // Check common locations
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

log_message("Starting flood_of-noah deployment", 'info');
log_message("Repository: $REPO_URL", 'info');

// Check Node.js
$node = check_node_available();
if (!$node) {
    log_message("Node.js not found. Please install Node.js first.", 'error');
    log_message("Try: export PATH=/tmp/node-v18.17.1-linux-x64/bin:\$PATH", 'info');
    exit(1);
}
log_message("Node.js found at: $node", 'success');

// Check git
exec('which git 2>/dev/null', $git_output, $git_code);
if ($git_code !== 0) {
    log_message("Git is not installed or not in PATH", 'error');
    exit(1);
}
log_message("Git found at: " . $git_output[0], 'success');

// Create working directory
$WORK_DIR = __DIR__ . '/flood_of-noah';
if (is_dir($WORK_DIR)) {
    log_message("Removing existing directory: $WORK_DIR", 'warning');
    run_command("rm -rf $WORK_DIR");
}

// Clone repository
log_message("Cloning repository...", 'info');
if (!run_command("git clone $REPO_URL $WORK_DIR")) {
    log_message("Failed to clone repository", 'error');
    exit(1);
}
log_message("Repository cloned successfully!", 'success');

// Change to repository directory
chdir($WORK_DIR);
log_message("Changed to: " . getcwd(), 'info');

// Install dependencies
log_message("Installing Node.js dependencies...", 'info');
if (!run_command("$NPM_PATH install")) {
    log_message("Failed to install dependencies", 'error');
    exit(1);
}
log_message("Dependencies installed successfully!", 'success');

// Create .env file if needed (sometimes required)
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

// Run with node
$command = "$node index.js";
passthru($command);
