# Windows Server Monitor API

A Windows-focused server resource monitoring API. It collects CPU, memory, network, GPU, disk I/O, mounted drive capacity, and common Task Manager counters every 5 seconds, then exposes the data through HTTP APIs and WebSocket broadcasts for web dashboards or integrations.

## Quick Start Scripts

Run this first:

```cmd
check_env.cmd
```

It checks for Python 3.10+, creates a `.venv` virtual environment, and installs the dependencies from `requirements.txt`. If Python is not found, it will try to install Python 3.12 through `winget`. If `winget` is unavailable, install Python manually.

Start the API server:

```cmd
start_monitor.cmd
```

On startup, the program asks:

```text
Set API key now? Press Enter to skip, or type a key:
```

Press Enter to run without an API key, or type a key to protect this run.

The program then prints startup feature checks. Available features are shown in green as `[True]`; unavailable features are shown in red as `[False]` with a reason, for example:

```text
CPU[True] total=8.2%, logical=12
Memory[True] total=15.16GB, available=5.34GB
MemoryModules[False] Physical memory module details are unavailable. Windows denied CIM/WMI access or no module data was returned.
```

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

Or use environment variables:

```cmd
set MONITOR_API_KEY=your_secret
set MONITOR_PORT=8765
set MONITOR_INTERVAL_SECONDS=5
set MONITOR_SSL_CERTFILE=certs\fullchain.pem
set MONITOR_SSL_KEYFILE=certs\privkey.pem
start_monitor.cmd
```

`start_monitor.cmd` starts the service directly. If `.venv` or required packages are missing, it automatically runs `check_env.cmd` first.

Security reminder: do not commit real API keys, private keys, or production config files to a public repository. Keep public examples as placeholders. For real deployments, prefer environment variables or a local config file such as `monitor_config.local.json`, which is ignored by `.gitignore`.

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

Configuration priority:

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

## Protocol Notes

This API uses TCP, not UDP.

- `/api/metrics` and `/api/hardware` are HTTP APIs. HTTP runs over TCP.
- `/ws/metrics` is a WebSocket endpoint. WebSocket starts with an HTTP Upgrade and also runs over TCP.
- This project does not use UDP broadcast.

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

## Collected Data

- `system`: uptime, boot time, process count, thread count, handle count.
- `hardware`: CPU name, memory module information, GPU names, disk device names.
- `cpu`: total CPU usage, physical cores, logical cores, current frequency, physical processor packages, logical processor usage.
- `memory`: total, used, available, free memory, and memory usage percentage.
- `network`: total upload/download speed, total sent/received traffic, per-interface upload/download speed, IP addresses, connection state, and NIC speed.
- `disk.io`: read/write speed and busy percentage for disk devices.
- `disk.drives`: capacity of all mounted drive letters/volumes. It is not limited to C: and D:.
- `gpu`: all NVIDIA GPUs are listed when available. Without NVIDIA, the script tries to read Windows GPU Engine performance counters.

## API Key And Frontend Safety

The examples in this README do not hard-code a production API key into browser code. Browser-side HTML, JavaScript, Network panels, error screenshots, and access logs can expose URLs or source code. If you put a secret in frontend code, visitors can see it in developer tools.

Recommended practices:

- Use the `X-API-Key` header for HTTP API requests. Avoid putting secrets in `?api_key=`.
- Native browser WebSocket cannot set a custom `X-API-Key` header. If you need API-key-protected WebSocket access on the public internet, use your own backend proxy or same-origin reverse proxy so the key stays server-side.
- `?api_key=` is still supported by the server for simple testing or fully controlled LAN environments. Do not use it in public web pages.
- Server-side code such as PHP, Node.js, or Java can keep the API key, but do not commit source code, logs, or config files containing real keys to a public repository.
- If you must temporarily use `?api_key=`, remember that browser history, proxy logs, server access logs, and screenshots may retain the key.

## HTML Embed Example

Replace `SERVER_HOST` with your server IP or domain. This browser-only example is suitable for trusted LAN use without an API key. For public deployments with an API key, use a backend proxy or same-origin reverse proxy instead of putting secrets in frontend code.

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
  </div>

  <script>
    const SERVER_HOST = "127.0.0.1:8765";
    const ws = new WebSocket(`ws://${SERVER_HOST}/ws/metrics`);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      document.getElementById("cpu").textContent = `${data.cpu.usage_percent}%`;
      document.getElementById("memory").textContent = `${data.memory.usage_percent}%`;
      document.getElementById("processes").textContent = data.system.process_count;
      document.getElementById("threads").textContent = data.system.thread_count;
      document.getElementById("handles").textContent = data.system.handle_count ?? "N/A";
      document.getElementById("uptime").textContent = data.system.uptime_human;
    };
  </script>
</body>
</html>
```

## JavaScript Request Example

Suitable for existing frontend projects. HTTP requests can use the `X-API-Key` header. Native browser WebSocket cannot set custom request headers, so do not put production API keys in frontend URLs. Use a backend proxy or same-origin reverse proxy when WebSocket authentication is needed.

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
  const ws = new WebSocket(`${wsBase}/ws/metrics`);

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
  console.log("Processes:", data.system.process_count);
  console.log("Network interfaces:", data.network.interfaces);
  console.log("Drives:", data.disk.drives);
});
```

`?api_key=` is still supported by the server, mainly for simple tests or fully controlled LAN environments. Do not expose real API keys in public pages, browser URLs, screenshots, logs, or third-party proxies.

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
