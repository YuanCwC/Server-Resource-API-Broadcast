# Server Resource API Broadcast

[English](README_EN.md) | [Русский](README_RU.md) | [日本語](README_JA.md) | 简体中文

一个专门面向 Windows 的服务器状态监控 API。它会每 5 秒采集一次 CPU、内存、网络、GPU、磁盘 IO、所有已挂载磁盘容量、任务管理器常见计数，并通过 HTTP API 与 WebSocket 广播出去，方便后续嵌入网页显示。

## 项目特点

- **实时监控**：每 5 秒自动采集系统资源数据
- **多协议支持**：提供 HTTP REST API 和 WebSocket 实时广播
- **全面监控**：涵盖 CPU、内存、网络、GPU、磁盘等所有关键指标
- **灵活配置**：支持命令行参数、环境变量、配置文件多种配置方式
- **安全认证**：内置 API Key 认证机制，支持 HTTPS/WSS
- **跨域友好**：默认允许浏览器跨域访问，便于前端集成
- **自动检测**：启动时自动检测各项硬件信息的可读性

## 一键脚本

第一次使用先运行环境检查脚本：

```cmd
check_env.cmd
```

该脚本会：
1. 检查是否安装 Python 3.10+
2. 创建 `.venv` 虚拟环境
3. 安装 `requirements.txt` 中的依赖包
4. 如果没有 Python，会尝试通过 `winget` 安装 Python 3.12
5. 如果电脑没有 `winget`，需要手动安装 Python

启动服务：

```cmd
start_monitor.cmd
```

程序会直接启动并显示启动自检结果。能读取的项目会显示绿色 `[True]`，不能读取的项目会显示红色 `[False]` 并给出原因：

```text
CPU[True] total=8.2%, logical=12
Memory[True] total=15.16GB, available=5.34GB
MemoryModules[False] Physical memory module details are unavailable. Windows denied CIM/WMI access or no module data was returned.
```

### 命令行参数

也可以在启动命令里直接传密钥：

```cmd
start_monitor.cmd --api-key "你的密钥"
```

指定端口和检测间隔：

```cmd
start_monitor.cmd --port 8765 --interval 5 --api-key "你的密钥"
```

使用自己的 HTTPS 证书启动：

```cmd
start_monitor.cmd --ssl-certfile certs\fullchain.pem --ssl-keyfile certs\privkey.pem --api-key "你的密钥"
```

指定配置文件：

```cmd
start_monitor.cmd --config monitor_config.local.json
```

### 环境变量

也可以用环境变量配置：

```cmd
set MONITOR_API_KEY=你的密钥
set MONITOR_PORT=8765
set MONITOR_INTERVAL_SECONDS=5
set MONITOR_SSL_CERTFILE=certs\fullchain.pem
set MONITOR_SSL_KEYFILE=certs\privkey.pem
start_monitor.cmd
```

`start_monitor.cmd` 会直接启动服务。如果发现 `.venv` 或依赖不存在，会自动先调用 `check_env.cmd`。

**安全提醒**：不要把真实 API Key、证书私钥或已填写生产密钥的配置文件提交到公开仓库。公开示例里请保留占位符；真实部署建议使用环境变量，或使用已被 `.gitignore` 忽略的 `monitor_config.local.json`。

## 配置文件

根目录有一个 `monitor_config.json`，建议公开仓库里保持空密钥、空证书路径：

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

真实部署时可以使用环境变量、启动参数，或新建一个不提交到 Git 的 `monitor_config.local.json`：

```json
{
  "host": "0.0.0.0",
  "port": 8765,
  "interval_seconds": 5,
  "api_key": "换成你自己的强密钥",
  "ssl_certfile": "",
  "ssl_keyfile": ""
}
```

然后直接启动即可：

```cmd
start_monitor.cmd
```

### 配置优先级

```text
命令行参数 > 环境变量 > monitor_config.json > 默认值
```

如果不想使用 SSL，把 `ssl_certfile` 和 `ssl_keyfile` 改成空字符串：

```json
{
  "ssl_certfile": "",
  "ssl_keyfile": ""
}
```

如果你想指定另一个配置文件：

```cmd
start_monitor.cmd --config monitor_config.local.json
```

## HTTPS / SSL 部署建议

程序可以直接适配 HTTPS/WSS：启动时传 `--ssl-certfile` 和 `--ssl-keyfile` 后，服务会从 HTTP/WS 切换为 HTTPS/WSS。

```cmd
start_monitor.cmd --ssl-certfile certs\fullchain.pem --ssl-keyfile certs\privkey.pem
```

对应地址会变成：

- `https://你的域名:8765/api/metrics`
- `https://你的域名:8765/api/hardware`
- `wss://你的域名:8765/ws/metrics`

不过更推荐的公网部署方式是：Python API 只监听本机或内网的 HTTP/WS，然后由 Nginx、Caddy、宝塔、frp HTTPS 隧道、Cloudflare Tunnel 等前置服务负责 SSL。这样证书续期、域名绑定、HTTPS 兼容性通常更稳定，Python 程序也不用直接管理私钥。

浏览器有一个硬性限制：如果你的网页是 HTTPS，API 广播端也必须是 HTTPS/WSS，不能从 HTTPS 页面连接普通的 `http://` 或 `ws://`。如果网页只是本地 Live Server 的 HTTP 页面，API 才可以继续使用 HTTP/WS。

需要让 Python 直接启用 SSL 时，把自己的证书放到：

```text
certs\fullchain.pem
certs\privkey.pem
```

## 手动安装

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 手动启动

```powershell
python .\server_monitor_api.py
```

带密钥：

```powershell
python .\server_monitor_api.py --api-key "你的密钥"
```

带 SSL：

```powershell
python .\server_monitor_api.py --ssl-certfile certs\fullchain.pem --ssl-keyfile certs\privkey.pem --api-key "你的密钥"
```

启动后终端会输出这些链接：

- `http://127.0.0.1:8765/api/metrics`
- `http://127.0.0.1:8765/api/hardware`
- `ws://局域网 IP:8765/ws/metrics`
- `http://127.0.0.1:8765/demo`
- `http://127.0.0.1:8765/docs`

如果设置了密钥，请求时使用请求头：

```powershell
Invoke-RestMethod "http://127.0.0.1:8765/api/metrics" -Headers @{"X-API-Key"="你的密钥"}
```

## 接口文档

HTTP API 默认允许浏览器跨域 `GET/OPTIONS` 请求，并允许 `X-API-Key` 请求头，方便把数据嵌入到独立网页里。公网部署时仍建议使用 API Key、后端代理或同源反代来控制访问。

### 获取当前快照

```http
GET /api/metrics
```

返回实时监控数据，并包含 `hardware` 硬件名称信息。

### 获取硬件名称

```http
GET /api/hardware
```

返回 CPU、内存、GPU、磁盘设备的名称/型号信息。这个接口适合网页初始化时请求一次，因为硬件名称通常不会频繁变化。

### 实时广播

```text
ws://127.0.0.1:8765/ws/metrics
```

服务端会按照配置的间隔自动广播 JSON 数据。

### 测试页面

```http
GET /demo
```

这是一个极简网页，用来验证 WebSocket 实时数据是否正常。

### API 文档

```http
GET /docs
```

Swagger/OpenAPI 格式的交互式 API 文档。

## 当前采集内容

### 系统信息 (`system`)
- 正常运行时间
- 开机时间
- 进程数
- 线程数
- 句柄数

### 硬件信息 (`hardware`)
- CPU 名称
- 内存条信息（容量、DDR 代数、频率）
- GPU 名称
- 磁盘设备名称

程序会自己检测主机内存容量、DDR 代数和频率，并在 `hardware.memory.name` / `hardware.memory.display_name` 合成整机内存显示句，例如 `32GB DDR5 4800MHz (2 x 16GB)`；每根内存条也会在 `modules[].name` / `modules[].display_name` 返回例如 `16GB DDR5 4800MHz`。

### CPU (`cpu`)
- 总 CPU 占用
- 物理核心数
- 逻辑核心数
- 当前频率
- 每个物理处理器包
- 每个逻辑处理器占用

### 内存 (`memory`)
- 总内存
- 已用内存
- 可用内存
- 空闲内存
- 内存占用百分比

### 网络 (`network`)
- 总上行/下行速度
- 总发送/接收流量
- 每个网络接口的上下行速度
- IP 地址
- 连接状态
- 网卡速率

### 磁盘 IO (`disk.io`)
- 所有磁盘设备的读写速度
- 忙碌百分比

### 磁盘卷 (`disk.drives`)
- 自动扫描到的所有已挂载盘符/卷容量
- 不再固定 C 盘和 D 盘

### GPU (`gpu`)
- 多张 NVIDIA GPU 会全部列出
- 没有 NVIDIA 时会尝试读取 Windows GPU 性能计数器

## API Key 与前端安全

本仓库不内置完整 `web` 前端目录，下面只提供 HTML / JavaScript 嵌入示例。浏览器端的 HTML、JS、Network 请求、报错截图和访问日志都可能暴露 URL 或源码；如果把密钥写进前端代码，别人打开开发者工具就能看到。

### 推荐做法

1. **HTTP API 请求**：使用 `X-API-Key` 请求头，不推荐把密钥放进 `?api_key=`
2. **WebSocket 连接**：浏览器原生 WebSocket 不能自定义 `X-API-Key` 请求头。为了让纯前端示例能直接连上，WebSocket 可使用 `?api_key=`；公网生产环境仍推荐使用自己的后端代理或同源反代，让密钥只保存在服务端
3. **使用场景**：`?api_key=` 适合本机测试、临时排查或完全受控的内网。公网网页可以用，但要知道它会暴露在浏览器地址、代理日志或截图中
4. **服务端代码**：PHP、Node、Java 等服务端代码可以保存 API Key，但不要把包含真实密钥的源码、日志或配置文件提交到公开仓库
5. **风险提示**：如果必须临时用 `?api_key=`，要注意浏览器历史、代理日志、服务器访问日志和截图都可能留下密钥

## HTML 嵌入示例

把 `SERVER_HOST` 换成服务器 IP 或域名。这个纯浏览器示例可以在未启用 API Key 时直接使用；如果启用了 API Key，填写 `API_KEY` 后 WebSocket 会通过 `?api_key=` 连接。公网生产环境更推荐后端代理或同源反代。

```html
<!doctype html>
<html lang="zh-CN">
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
  <h1>服务器状态</h1>
  <div class="grid">
    <div class="card">CPU<div id="cpu" class="value">-</div></div>
    <div class="card">内存<div id="memory" class="value">-</div></div>
    <div class="card">进程<div id="processes" class="value">-</div></div>
    <div class="card">线程<div id="threads" class="value">-</div></div>
    <div class="card">句柄<div id="handles" class="value">-</div></div>
    <div class="card">运行时间<div id="uptime" class="value">-</div></div>
    <div class="card">GPU<div id="gpu" class="value">-</div></div>
    <div class="card">网络下行<div id="netIn" class="value">-</div></div>
    <div class="card">网络上行<div id="netOut" class="value">-</div></div>
    <div class="card">磁盘读取<div id="diskRead" class="value">-</div></div>
    <div class="card">磁盘写入<div id="diskWrite" class="value">-</div></div>
  </div>
  <h2>所有磁盘卷</h2>
  <pre id="drives">-</pre>
  <h2>所有磁盘设备</h2>
  <pre id="diskNames">-</pre>
  <h2>所有网络接口</h2>
  <pre id="interfaces">-</pre>
  <h2>所有 GPU</h2>
  <pre id="gpus">-</pre>
  <h2>内存硬件</h2>
  <pre id="memoryHardware">-</pre>
  <h2>所有物理处理器</h2>
  <pre id="cpuPackages">-</pre>
  <h2>所有逻辑处理器</h2>
  <pre id="processors">-</pre>

  <script>
    const SERVER_HOST = "127.0.0.1:8765";
    const API_KEY = ""; // 启用密钥时填写；公开网页不建议写真实密钥
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

## JavaScript 请求示例

适合在已有前端项目里用。HTTP 请求可以用 `X-API-Key` 请求头；浏览器原生 WebSocket 不能设置自定义请求头，所以启用 API Key 且不使用后端代理时，WebSocket 需要使用 `?api_key=`。

```js
const apiBase = "http://127.0.0.1:8765";
const apiKey = ""; // 不要把生产 API Key 写进公开前端代码

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

`?api_key=` 可用于浏览器 WebSocket 鉴权，尤其是没有后端代理的纯前端页面。注意：不要在公开仓库、截图、日志或第三方代理里暴露真实 API Key。

## PHP 请求示例

PHP 适合作为后端代理或服务端渲染时读取当前快照。真实 API Key 只应该留在服务端，不要输出到 HTML 或 JS 里。WebSocket 实时展示如果需要鉴权，建议让 PHP/反代提供同源代理。

```php
<?php
$url = 'http://127.0.0.1:8765/api/metrics';
$apiKey = '你的密钥';

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
<html lang="zh-CN">
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

## 日志

每一次 HTTP 请求都会输出到控制台，并写入：

```text
server_monitor.log
```

WebSocket 的连接、断开和鉴权失败也会记录。

## GPU 说明

脚本会优先使用 `nvidia-smi` 获取 NVIDIA GPU 的占用、显存和温度。如果没有 NVIDIA GPU，会尝试读取 Windows 的 GPU Engine 性能计数器。不同显卡和驱动暴露的数据不完全一致，所以非 NVIDIA 显卡可能只能拿到 GPU 使用率，显存和温度可能为 `null`。

## 常见问题

### 为什么内存模块信息显示不可用？
Windows 对 CIM/WMI 的访问有限制，可能需要管理员权限或组策略调整。

### 如何查看详细的错误日志？
查看 `server_monitor.log` 文件，里面包含了所有 HTTP 请求和 WebSocket 连接的详细日志。

### 可以在 Linux 上使用吗？
当前版本仅支持 Windows，因为使用了 Windows 特定的性能计数器和 WMI 接口。

### 如何修改数据采集间隔？
通过 `--interval` 参数或 `MONITOR_INTERVAL_SECONDS` 环境变量设置，单位为秒。

## 技术栈

- Python 3.10+
- aiohttp (异步 HTTP 服务器)
- psutil (系统监控)
- asyncio (异步编程)

## 许可证

本项目采用 MIT 许可证。
