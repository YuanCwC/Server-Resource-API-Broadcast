# Server Resource API Broadcast

[English](README_EN.md) | [Русский](README_RU.md) | [日本語](README_JA.md) | 简体中文

A Windows-focused server resource monitoring API. It collects CPU, memory, network, GPU, disk I/O, mounted drive capacity, and common Task Manager counters every 5 seconds, then exposes the data through HTTP APIs and WebSocket broadcasts for web dashboards or integrations.

## Project Features

- **Real-time Monitoring**: Automatically collects system resource data every 5 seconds
- **Multi-protocol Support**: Provides HTTP REST API and WebSocket real-time broadcasting
- **Comprehensive Monitoring**: Covers all key metrics including CPU, memory, network, GPU, and disk
- **Flexible Configuration**: Supports command-line arguments, environment variables, and configuration files
- **Secure Authentication**: Built-in API Key authentication mechanism with HTTPS/WSS support
- **CORS Friendly**: Allows browser cross-origin access by default for easy frontend integration
- **Auto Detection**: Automatically detects hardware information readability at startup

## Quick Start Scripts

Run the environment check script first:

```cmd
check_env.cmd
```

This script will:
1. Check if Python 3.10+ is installed
2. Create a `.venv` virtual environment
3. Install dependencies from `requirements.txt`
4. If Python is not found, try to install Python 3.12 via `winget`
5. If `winget` is unavailable, install Python manually

Start the service:

```cmd
start_monitor.cmd
```

The program starts directly and displays startup self-check results. Available features are shown in green as `[True]`; unavailable features are shown in red as `[False]` with a reason:

```text
CPU[True] total=8.2%, logical=12
Memory[True] total=15.16GB, available=5.34GB
MemoryModules[False] Physical memory module details are unavailable. Windows denied CIM/WMI access or no module data was returned.
```

### Command-line Arguments

You can also pass the API key directly:

```cmd
start_monitor.cmd --api-key "your_secret"
```

Set the port and sampling interval:

```cmd
start_monitor.cmd --port 8765 --interval 5 --api-key "your_secret"
```

Start with your own HTTPS certificate:

```cmd
start_monitor.cmd --ssl-certfile certs\fullchain.pem --ssl-keyfile certs\privkey.pem --api-key "your_secret"
```

Specify a configuration file:

```cmd
start_monitor.cmd --config monitor_config.local.json
```

### Environment Variables

You can also configure using environment variables:

```cmd
set MONITOR_API_KEY=your_secret
set MONITOR_PORT=8765
set MONITOR_INTERVAL_SECONDS=5
set MONITOR_SSL_CERTFILE=certs\fullchain.pem
set MONITOR_SSL_KEYFILE=certs\privkey.pem
start_monitor.cmd
```

`start_monitor.cmd` starts the service directly. If `.venv` or required packages are missing, it automatically runs `check_env.cmd` first.

**Security Reminder**: Do not commit real API keys, private keys, or production config files to a public repository. Keep public examples as placeholders. For real deployments, prefer environment variables or a local config file such as `monitor_config.local.json`, which is ignored by `.gitignore`.

## Configuration File

The root directory contains `monitor_config.json`. Keep public repository defaults empty:

```json
{
  "host": "0.0.0.0",
  "port": 8765,
  "interval_seconds": 5,
  "api_key": "",
  "ssl_certfile": "",
  "ssl_keyfile": ""
}
```

For real deployments, use environment variables, command-line arguments, or create a local config file that is not committed to Git:

```json
{
  "host": "0.0.0.0",
  "port": 8765,
  "interval_seconds": 5,
  "api_key": "replace_with_your_strong_secret",
  "ssl_certfile": "",
  "ssl_keyfile": ""
}
```

Then start the server:

```cmd
start_monitor.cmd
```

### Configuration Priority

```text
command-line arguments > environment variables > monitor_config.json > defaults
```

To disable SSL, leave `ssl_certfile` and `ssl_keyfile` empty:

```json
{
  "ssl_certfile": "",
  "ssl_keyfile": ""
}
```

To use another config file:

```cmd
start_monitor.cmd --config monitor_config.local.json
```

## HTTPS / SSL Deployment Recommendation

The Python server can serve HTTPS/WSS directly. When both `--ssl-certfile` and `--ssl-keyfile` are provided, the service switches from HTTP/WS to HTTPS/WSS:

```cmd
start_monitor.cmd --ssl-certfile certs\fullchain.pem --ssl-keyfile certs\privkey.pem
```

The URLs become:

- `https://your-domain:8765/api/metrics`
- `https://your-domain:8765/api/hardware`
- `wss://your-domain:8765/ws/metrics`

For public deployments, the recommended setup is usually to keep the Python API on local HTTP/WS and terminate TLS in a front proxy or tunnel, such as Nginx, Caddy, BT Panel, an frp HTTPS tunnel, Cloudflare Tunnel, or another reverse proxy. This usually makes certificate renewal, domain binding, and browser compatibility easier, and avoids putting private keys directly into the Python process.

Browser rule: if your web page is loaded through HTTPS, the API broadcast endpoint must also use HTTPS/WSS. An HTTPS page cannot connect to plain `http://` or `ws://`. If you are using a local HTTP page, such as VS Code Live Server over HTTP, the API can use HTTP/WS.

If you need Python to terminate SSL directly, put your certificate files here:

```text
certs\fullchain.pem
certs\privkey.pem
```

## Manual Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Manual Start

```powershell
python .\server_monitor_api.py
```

With an API key:

```powershell
python .\server_monitor_api.py --api-key "your_secret"
```

With SSL:

```powershell
python .\server_monitor_api.py --ssl-certfile certs\fullchain.pem --ssl-keyfile certs\privkey.pem --api-key "your_secret"
```

After startup, the terminal prints links like:

- `http://127.0.0.1:8765/api/metrics`
- `http://127.0.0.1:8765/api/hardware`
- `ws://LAN-IP:8765/ws/metrics`
- `http://127.0.0.1:8765/demo`
- `http://127.0.0.1:8765/docs`

If an API key is enabled, send it with the request header:

```powershell
Invoke-RestMethod "http://127.0.0.1:8765/api/metrics" -Headers @{"X-API-Key"="your_secret"}
```

## API Endpoints

HTTP APIs allow browser cross-origin `GET/OPTIONS` requests and the `X-API-Key` header by default, which makes browser dashboards easier to build. For public deployments, still use an API key, a backend proxy, or a same-origin reverse proxy to control access.

### Current Metrics Snapshot

```http
GET /api/metrics
```

Returns live monitoring data, including hardware name information.

### Hardware Names

```http
GET /api/hardware
```

Returns CPU, memory module, GPU, and disk device names/models. This endpoint is useful during web page initialization because hardware names usually do not change often.

### Live Broadcast

```text
ws://127.0.0.1:8765/ws/metrics
```

The server broadcasts JSON data automatically at the configured interval.

### Demo Page

```http
GET /demo
```

A minimal page for checking whether WebSocket live data works.

### API Documentation

```http
GET /docs
```

Interactive API documentation in Swagger/OpenAPI format.

## Collected Data

### System Information (`system`)
- Uptime
- Boot time
- Process count
- Thread count
- Handle count

### Hardware Information (`hardware`)
- CPU name
- Memory module information (capacity, DDR generation, frequency)
- GPU names
- Disk device names

The program detects host memory capacity, DDR generation, and frequency, then builds `hardware.memory.name` / `hardware.memory.display_name` such as `32GB DDR5 4800MHz (2 x 16GB)`. Each module also includes `modules[].name` / `modules[].display_name` such as `16GB DDR5 4800MHz` when Windows exposes enough data.

### CPU (`cpu`)
- Total CPU usage
- Physical cores
- Logical cores
- Current frequency
- Physical processor packages
- Logical processor usage

### Memory (`memory`)
- Total memory
- Used memory
- Available memory
- Free memory
- Memory usage percentage

### Network (`network`)
- Total upload/download speed
- Total sent/received traffic
- Per-interface upload/download speed
- IP addresses
- Connection state
- NIC speed

### Disk IO (`disk.io`)
- Read/write speed for disk devices
- Busy percentage

### Disk Drives (`disk.drives`)
- Capacity of all mounted drive letters/volumes
- Not limited to C: and D:

### GPU (`gpu`)
- All NVIDIA GPUs are listed when available
- Without NVIDIA, tries to read Windows GPU Engine performance counters

## API Key And Frontend Safety

This repository does not include a complete `web` frontend directory. The following sections are embed examples only. Browser-side HTML, JavaScript, Network panels, error screenshots, and access logs can expose URLs or source code. If you put a secret in frontend code, visitors can see it in developer tools.

### Recommended Practices

1. **HTTP API Requests**: Use the `X-API-Key` header. Avoid putting secrets in `?api_key=`.
2. **WebSocket Connections**: Native browser WebSocket cannot set a custom `X-API-Key` header. To make browser-only examples work, WebSocket can use `?api_key=`. For public production deployments, a backend proxy or same-origin reverse proxy is still recommended so the key stays server-side.
3. **Use Cases**: `?api_key=` is suitable for local tests, troubleshooting, or controlled LAN environments. It can be used by public pages, but it may be exposed through browser URLs, proxy logs, or screenshots.
4. **Server-side Code**: Server-side code such as PHP, Node.js, or Java can keep the API key, but do not commit source code, logs, or config files containing real keys to a public repository.
5. **Risk Warning**: If you must temporarily use `?api_key=`, remember that browser history, proxy logs, server access logs, and screenshots may retain the key.

## HTML Embed Example

Replace `SERVER_HOST` with your server IP or domain. This browser-only example works directly when no API key is enabled. If an API key is enabled, fill `API_KEY` and the WebSocket will connect with `?api_key=`. For public production deployments, a backend proxy or same-origin reverse proxy is still recommended.

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Server Monitor</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; }
    .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
    .card { border: 1px solid #ddd; border-radius: 6px; padding: 12px; }
    .value { font-size: 28px; font-weight: 700; }
  </style>
</head>
<body>
  <h1>Server Status</h1>
  <div class="grid">
    <div class="card">CPU<div id="cpu" class="value">-</div></div>
    <div class="card">Memory<div id="memory" class="value">-</div></div>
    <div class="card">Processes<div id="processes" class="value">-</div></div>
    <div class="card">Threads<div id="threads" class="value">-</div></div>
    <div class="card">Handles<div id="handles" class="value">-</div></div>
    <div class="card">Uptime<div id="uptime" class="value">-</div></div>
    <div class="card">GPU<div id="gpu" class="value">-</div></div>
    <div class="card">Network In<div id="netIn" class="value">-</div></div>
    <div class="card">Network Out<div id="netOut" class="value">-</div></div>
    <div class="card">Disk Read<div id="diskRead" class="value">-</div></div>
    <div class="card">Disk Write<div id="diskWrite" class="value">-</div></div>
  </div>
  <h2>All Disk Drives</h2>
  <pre id="drives">-</pre>
  <h2>All Disk Devices</h2>
  <pre id="diskNames">-</pre>
  <h2>All Network Interfaces</h2>
  <pre id="interfaces">-</pre>
  <h2>All GPUs</h2>
  <pre id="gpus">-</pre>
  <h2>Memory Hardware</h2>
  <pre id="memoryHardware">-</pre>
  <h2>All Physical Processors</h2>
  <pre id="cpuPackages">-</pre>
  <h2>All Logical Processors</h2>
  <pre id="processors">-</pre>

  <script>
    const SERVER_HOST = "127.0.0.1:8765";
    const API_KEY = ""; // Fill this only for trusted/local pages.
    const query = API_KEY ? `?api_key=${encodeURIComponent(API_KEY)}` : "";
    const ws = new WebSocket(`ws://${SERVER_HOST}/ws/metrics${query}`);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      document.getElementById("cpu").textContent = `${data.cpu.usage_percent}%`;
      document.getElementById("memory").textContent = `${data.memory.usage_percent}%`;
      document.getElementById("processes").textContent = data.system.process_count;
      document.getElementById("threads").textContent = data.system.thread_count;
      document.getElementById("handles").textContent = data.system.handle_count ?? "N/A";
      document.getElementById("uptime").textContent = data.system.uptime_human;
      document.getElementById("gpu").textContent = data.gpu.available
        ? `${data.gpu.average_utilization_percent}%`
        : "N/A";
      document.getElementById("netIn").textContent = `${data.network.received_mb_per_second} MB/s`;
      document.getElementById("netOut").textContent = `${data.network.sent_mb_per_second} MB/s`;
      document.getElementById("diskRead").textContent = `${data.disk.io.read_mb_per_second} MB/s`;
      document.getElementById("diskWrite").textContent = `${data.disk.io.write_mb_per_second} MB/s`;

      document.getElementById("drives").textContent = Object.entries(data.disk.drives)
        .map(([name, drive]) => `${name} ${drive.used_percent ?? "N/A"}% used, free ${drive.free_gb ?? "N/A"} GB`)
        .join("\n");
      document.getElementById("diskNames").textContent = data.hardware.disk.devices
        .map((disk) => `${disk.index}: ${disk.name}`)
        .join("\n") || "N/A";
      document.getElementById("interfaces").textContent = Object.entries(data.network.interfaces)
        .map(([name, nic]) => `${name}: down ${nic.received_mb_per_second} MB/s, up ${nic.sent_mb_per_second} MB/s, ${nic.is_up ? "up" : "down"}`)
        .join("\n");
      document.getElementById("gpus").textContent = data.hardware.gpu.devices
        .map((gpu) => `${gpu.index}: ${gpu.name}`)
        .join("\n") || "N/A";
      document.getElementById("memoryHardware").textContent = data.hardware.memory.module_details_available
        ? data.hardware.memory.modules.map((module) => `${module.index}: ${module.display_name ?? `${module.manufacturer ?? ""} ${module.part_number ?? ""} ${module.capacity_gb ?? "N/A"} GB`}`).join("\n")
        : `Total ${data.hardware.memory.total_gb} GB\n${data.hardware.memory.message ?? ""}`;
      document.getElementById("cpuPackages").textContent = data.cpu.processors
        .map((cpu) => `${cpu.device_id}: ${cpu.name}, load ${cpu.load_percent ?? "N/A"}%`)
        .join("\n") || "N/A";
      document.getElementById("processors").textContent = data.cpu.logical_processors
        .map((cpu) => `CPU ${cpu.index}: ${cpu.usage_percent}%`)
        .join("\n");
    };
  </script>
</body>
</html>
```

## JavaScript Request Example

Suitable for existing frontend projects. HTTP requests can use the `X-API-Key` header. Native browser WebSocket cannot set custom request headers, so when an API key is enabled and no backend proxy is used, WebSocket needs `?api_key=`.

```js
const apiBase = "http://127.0.0.1:8765";
const apiKey = ""; // Do not put a production API key in public frontend code.

async function fetchHardware() {
  const res = await fetch(`${apiBase}/api/hardware`, {
    headers: apiKey ? { "X-API-Key": apiKey } : {}
  });

  if (!res.ok) {
    throw new Error(`Monitor hardware API error: ${res.status}`);
  }

  return await res.json();
}

async function fetchMetrics() {
  const res = await fetch(`${apiBase}/api/metrics`, {
    headers: apiKey ? { "X-API-Key": apiKey } : {}
  });

  if (!res.ok) {
    throw new Error(`Monitor API error: ${res.status}`);
  }

  return await res.json();
}

function subscribeMetrics(onMetrics) {
  const wsBase = apiBase.replace(/^http/, "ws");
  const query = apiKey ? `?api_key=${encodeURIComponent(apiKey)}` : "";
  const ws = new WebSocket(`${wsBase}/ws/metrics${query}`);

  ws.onmessage = (event) => onMetrics(JSON.parse(event.data));
  ws.onerror = () => console.error("Monitor WebSocket error");
  ws.onclose = () => console.warn("Monitor WebSocket closed");

  return ws;
}

fetchHardware().then((hardware) => {
  console.log("CPU name:", hardware.cpu.name);
  console.log("Memory modules:", hardware.memory.modules);
  console.log("GPU names:", hardware.gpu.devices);
  console.log("Disk names:", hardware.disk.devices);
});

fetchMetrics().then(console.log);
subscribeMetrics((data) => {
  console.log("CPU:", data.cpu.usage_percent);
  console.log("CPU name:", data.hardware.cpu.name);
  console.log("Processes:", data.system.process_count);
  console.log("Network interfaces:", data.network.interfaces);
  console.log("Drives:", data.disk.drives);
  console.log("Disk IO:", data.disk.io.devices);
  console.log("GPUs:", data.gpu.devices);
  console.log("CPU packages:", data.cpu.processors);
  console.log("Logical processors:", data.cpu.logical_processors);
});
```

`?api_key=` can be used for browser WebSocket authentication, especially for browser-only pages without a backend proxy. Do not expose real API keys in public repositories, screenshots, logs, or third-party proxies.

## PHP Request Example

PHP is suitable as a backend proxy or server-side rendered snapshot reader. The real API key should stay on the server and should not be printed into HTML or JavaScript. If WebSocket live display needs authentication, provide a same-origin proxy or reverse proxy.

```php
<?php
$url = 'http://127.0.0.1:8765/api/metrics';
$apiKey = 'your_secret';

$headers = [];
if ($apiKey !== '') {
    $headers[] = 'X-API-Key: ' . $apiKey;
}

$ch = curl_init($url);
curl_setopt_array($ch, [
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HTTPHEADER => $headers,
    CURLOPT_TIMEOUT => 5,
]);

$body = curl_exec($ch);
$status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$error = curl_error($ch);
curl_close($ch);

if ($body === false || $status !== 200) {
    http_response_code(502);
    echo 'Monitor API request failed: ' . ($error ?: $status);
    exit;
}

$data = json_decode($body, true);
?>
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Server Monitor PHP</title>
</head>
<body>
  <p>CPU: <?= htmlspecialchars($data['cpu']['usage_percent']) ?>%</p>
  <p>CPU Name: <?= htmlspecialchars($data['hardware']['cpu']['name'] ?? 'N/A') ?></p>
  <p>Memory: <?= htmlspecialchars($data['memory']['usage_percent']) ?>%</p>
  <p>Processes: <?= htmlspecialchars($data['system']['process_count']) ?></p>
  <p>Threads: <?= htmlspecialchars($data['system']['thread_count']) ?></p>
  <p>Handles: <?= htmlspecialchars($data['system']['handle_count'] ?? 'N/A') ?></p>
  <p>Uptime: <?= htmlspecialchars($data['system']['uptime_human']) ?></p>

  <h2>Drives</h2>
  <ul>
    <?php foreach ($data['disk']['drives'] as $name => $drive): ?>
      <li>
        <?= htmlspecialchars($name) ?>:
        <?= htmlspecialchars($drive['used_percent'] ?? 'N/A') ?>% used,
        <?= htmlspecialchars($drive['free_gb'] ?? 'N/A') ?> GB free
      </li>
    <?php endforeach; ?>
  </ul>

  <h2>Disk Devices</h2>
  <ul>
    <?php foreach ($data['hardware']['disk']['devices'] as $disk): ?>
      <li><?= htmlspecialchars($disk['name'] ?? 'N/A') ?></li>
    <?php endforeach; ?>
  </ul>

  <h2>GPU Devices</h2>
  <ul>
    <?php foreach ($data['hardware']['gpu']['devices'] as $gpu): ?>
      <li><?= htmlspecialchars($gpu['name'] ?? 'N/A') ?></li>
    <?php endforeach; ?>
  </ul>

  <h2>Memory Hardware</h2>
  <?php if ($data['hardware']['memory']['module_details_available']): ?>
    <ul>
      <?php foreach ($data['hardware']['memory']['modules'] as $module): ?>
        <li>
          <?= htmlspecialchars($module['display_name'] ?? (($module['manufacturer'] ?? '') . ' ' . ($module['part_number'] ?? '') . ' ' . ($module['capacity_gb'] ?? 'N/A') . ' GB')) ?>
        </li>
      <?php endforeach; ?>
    </ul>
  <?php else: ?>
    <p>Total memory: <?= htmlspecialchars($data['hardware']['memory']['total_gb']) ?> GB</p>
  <?php endif; ?>

  <h2>Network Interfaces</h2>
  <ul>
    <?php foreach ($data['network']['interfaces'] as $name => $nic): ?>
      <li>
        <?= htmlspecialchars($name) ?>:
        down <?= htmlspecialchars($nic['received_mb_per_second']) ?> MB/s,
        up <?= htmlspecialchars($nic['sent_mb_per_second']) ?> MB/s
      </li>
    <?php endforeach; ?>
  </ul>
</body>
</html>
```

## Logs

Every HTTP request is printed to the console and written to:

```text
server_monitor.log
```

WebSocket connections, disconnections, and authentication failures are also logged.

## GPU Notes

The script prefers `nvidia-smi` for NVIDIA GPU usage, VRAM, and temperature. If no NVIDIA GPU is available, it tries to read Windows GPU Engine performance counters. Different GPUs and drivers expose different data, so non-NVIDIA GPUs may only provide usage percentage while memory and temperature may be `null`.

## Frequently Asked Questions

### Why is memory module information unavailable?
Windows has restrictions on CIM/WMI access, which may require administrator privileges or group policy adjustments.

### How do I view detailed error logs?
Check the `server_monitor.log` file, which contains detailed logs of all HTTP requests and WebSocket connections.

### Can I use this on Linux?
The current version only supports Windows because it uses Windows-specific performance counters and WMI interfaces.

### How do I change the data collection interval?
Set it via the `--interval` argument or the `MONITOR_INTERVAL_SECONDS` environment variable, in seconds.

## Technology Stack

- Python 3.10+
- aiohttp (Asynchronous HTTP Server)
- psutil (System Monitoring)
- asyncio (Asynchronous Programming)

## License

This project is licensed under the MIT License.
