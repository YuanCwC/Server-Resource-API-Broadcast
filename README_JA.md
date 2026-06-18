# Server Resource API Broadcast

[English](README_EN.md) | [Русский](README_RU.md) | [日本語](README_JA.md) | 简体中文

Windows 向けのサーバーリソース監視 API です。CPU、メモリ、ネットワーク、GPU、ディスク I/O、マウント済みドライブの容量、タスクマネージャーの一般的なカウンターを 5 秒ごとに収集し、HTTP API と WebSocket ブロードキャストを通じてウェブダッシュボードや統合用にデータを公開します。

## プロジェクトの特徴

- **リアルタイム監視**: システムリソースデータを 5 秒ごとに自動収集
- **マルチプロトコル対応**: HTTP REST API と WebSocket リアルタイムブロードキャストを提供
- **包括的な監視**: CPU、メモリ、ネットワーク、GPU、ディスクなどすべての主要メトリクスをカバー
- **柔軟な設定**: コマンドライン引数、環境変数、設定ファイルをサポート
- **安全な認証**: API キー認証メカニズムを内蔵し、HTTPS/WSS をサポート
- **CORS フレンドリー**: ブラウザのクロスオリジンアクセスをデフォルトで許可し、フロントエンド統合を容易に
- **自動検出**: 起動時にハードウェア情報の読み取り可能性を自動検出

## クイックスタートスクリプト

まず環境チェックスクリプトを実行します：

```cmd
check_env.cmd
```

このスクリプトは以下のことを行います：
1. Python 3.10+ がインストールされているか確認
2. `.venv` 仮想環境を作成
3. `requirements.txt` から依存関係をインストール
4. Python が見つからない場合、`winget` を通じて Python 3.12 をインストールしようと試みる
5. `winget` が利用できない場合、手動で Python をインストールする必要があります

サービスの開始：

```cmd
start_monitor.cmd
```

プログラムは直接起動し、起動時の自己診断結果を表示します。利用可能な機能は緑色で `[True]` と表示され、利用できない機能は赤色で `[False]` と理由と共に表示されます：

```text
CPU[True] total=8.2%, logical=12
Memory[True] total=15.16GB, available=5.34GB
MemoryModules[False] Physical memory module details are unavailable. Windows denied CIM/WMI access or no module data was returned.
```

### コマンドライン引数

API キーを直接渡すこともできます：

```cmd
start_monitor.cmd --api-key "your_secret"
```

ポートとサンプリング間隔を設定：

```cmd
start_monitor.cmd --port 8765 --interval 5 --api-key "your_secret"
```

独自の HTTPS 証明書で起動：

```cmd
start_monitor.cmd --ssl-certfile certs\fullchain.pem --ssl-keyfile certs\privkey.pem --api-key "your_secret"
```

設定ファイルを指定：

```cmd
start_monitor.cmd --config monitor_config.local.json
```

### 環境変数

環境変数を使用して設定することもできます：

```cmd
set MONITOR_API_KEY=your_secret
set MONITOR_PORT=8765
set MONITOR_INTERVAL_SECONDS=5
set MONITOR_SSL_CERTFILE=certs\fullchain.pem
set MONITOR_SSL_KEYFILE=certs\privkey.pem
start_monitor.cmd
```

`start_monitor.cmd` はサービスを直接起動します。`.venv` または必要なパッケージが見つからない場合、自動的に `check_env.cmd` を最初に実行します。

**セキュリティのリマインダー**: 実際の API キー、秘密鍵、または本番環境の設定ファイルをパブリックリポジトリにコミットしないでください。パブリックな例ではプレースホルダーを保持してください。実際の本番展開では、環境変数または `.gitignore` で無視される `monitor_config.local.json` などのローカル設定ファイルを使用することを推奨します。

## 設定ファイル

ルートディレクトリには `monitor_config.json` があります。パブリックリポジトリではデフォルトを空に保ってください：

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

実際の本番展開では、環境変数、コマンドライン引数、または Git にコミットしないローカル設定ファイルを使用してください：

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

その後、サーバーを起動します：

```cmd
start_monitor.cmd
```

### 設定の優先順位

```text
コマンドライン引数 > 環境変数 > monitor_config.json > デフォルト値
```

SSL を無効にするには、`ssl_certfile` と `ssl_keyfile` を空にします：

```json
{
  "ssl_certfile": "",
  "ssl_keyfile": ""
}
```

別の設定ファイルを使用するには：

```cmd
start_monitor.cmd --config monitor_config.local.json
```

## HTTPS / SSL 展開の推奨事項

Python サーバーは直接 HTTPS/WSS を提供できます。`--ssl-certfile` と `--ssl-keyfile` の両方が提供されると、サービスは HTTP/WS から HTTPS/WSS に切り替わります：

```cmd
start_monitor.cmd --ssl-certfile certs\fullchain.pem --ssl-keyfile certs\privkey.pem
```

URL は次のようになります：

- `https://your-domain:8765/api/metrics`
- `https://your-domain:8765/api/hardware`
- `wss://your-domain:8765/ws/metrics`

パブリック展開の場合、推奨される設定は通常、Python API をローカル HTTP/WS で動作させ、Nginx、Caddy、BT Panel、frp HTTPS トンネル、Cloudflare Tunnel、または他のリバースプロキシなどのフロントプロキシまたはトンネルで TLS を終端することです。これにより、証明書の更新、ドメインバインディング、ブラウザの互換性が通常より簡単になり、秘密鍵を Python プロセスに直接配置する必要がなくなります。

ブラウザのルール：ウェブページが HTTPS でロードされる場合、API ブロードキャストエンドポイントも HTTPS/WSS を使用する必要があります。HTTPS ページは通常の `http://` または `ws://` に接続できません。VS Code Live Server over HTTP などのローカル HTTP ページを使用している場合、API は HTTP/WS を使用できます。

Python に直接 SSL を終端させる必要がある場合は、証明書ファイルをここに配置します：

```text
certs\fullchain.pem
certs\privkey.pem
```

## 手動インストール

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 手動起動

```powershell
python .\server_monitor_api.py
```

API キー付き：

```powershell
python .\server_monitor_api.py --api-key "your_secret"
```

SSL 付き：

```powershell
python .\server_monitor_api.py --ssl-certfile certs\fullchain.pem --ssl-keyfile certs\privkey.pem --api-key "your_secret"
```

起動後、ターミナルは次のようなリンクを出力します：

- `http://127.0.0.1:8765/api/metrics`
- `http://127.0.0.1:8765/api/hardware`
- `ws://LAN-IP:8765/ws/metrics`
- `http://127.0.0.1:8765/demo`
- `http://127.0.0.1:8765/docs`

API キーが有効な場合、リクエストヘッダーで送信します：

```powershell
Invoke-RestMethod "http://127.0.0.1:8765/api/metrics" -Headers @{"X-API-Key"="your_secret"}
```

## API エンドポイント

HTTP API はデフォルトでブラウザのクロスオリジン `GET/OPTIONS` リクエストと `X-API-Key` ヘッダーを許可しており、ブラウザダッシュボードの構築を容易にします。パブリック展開の場合は、アクセス制御のために API キー、バックエンドプロキシ、または同一生成元リバースプロキシを引き続き使用してください。

### 現在のメトリクスのスナップショット

```http
GET /api/metrics
```

ハードウェア名情報を含むライブ監視データを返します。

### ハードウェア名

```http
GET /api/hardware
```

CPU、メモリモジュール、GPU、およびディスクデバイスの名前/モデルを返します。このエンドポイントは、ハードウェア名が頻繁に変更されないため、ウェブページの初期化中に役立ちます。

### ライブブロードキャスト

```text
ws://127.0.0.1:8765/ws/metrics
```

サーバーは設定された間隔で JSON データを自動的にブロードキャストします。

### デモページ

```http
GET /demo
```

WebSocket ライブデータが機能するかどうかを確認するための最小限のページです。

### API ドキュメント

```http
GET /docs
```

Swagger/OpenAPI 形式のインタラクティブな API ドキュメント。

## 収集データ

### システム情報 (`system`)
- アップタイム
- ブート時間
- プロセス数
- スレッド数
- ハンドル数

### ハードウェア情報 (`hardware`)
- CPU 名
- メモリモジュール情報（容量、DDR 世代、周波数）
- GPU 名
- ディスクデバイス名

プログラムはホストメモリ容量、DDR 世代、および周波数を検出し、`hardware.memory.name` / `hardware.memory.display_name` を `32GB DDR5 4800MHz (2 x 16GB)` のように構築します。Windows が十分なデータを公開する場合、各モジュールには `modules[].name` / `modules[].display_name`（例：`16GB DDR5 4800MHz`）も含まれます。

### CPU (`cpu`)
- 総 CPU 使用率
- 物理コア
- 論理コア
- 現在の周波数
- 物理プロセッサパッケージ
- 論理プロセッサの使用率

### メモリ (`memory`)
- 総メモリ
- 使用済みメモリ
- 利用可能メモリ
- 空きメモリ
- メモリ使用率

### ネットワーク (`network`)
- 総アップロード/ダウンロード速度
- 総送信/受信トラフィック
- インターフェースごとのアップロード/ダウンロード速度
- IP アドレス
- 接続状態
- NIC 速度

### ディスク I/O (`disk.io`)
- ディスクデバイスの読み取り/書き込み速度
- ビジーパーセンテージ

### ディスクドライブ (`disk.drives`)
- マウント済みのすべてのドライブ文字/ボリュームの容量
- C: および D: に限定されません

### GPU (`gpu`)
- 利用可能な場合、すべての NVIDIA GPU がリストされます
- NVIDIA がない場合、Windows GPU Engine パフォーマンスカウンターを読み取ろうとします

## API キーとフロントエンドの安全性

このリポジトリには完全な `web` フロントエンドディレクトリは含まれていません。以下のセクションは埋め込み例のみです。ブラウザ側の HTML、JavaScript、ネットワークパネル、エラーのスクリーンショット、およびアクセスログは URL やソースコードを公開する可能性があります。シークレットをフロントエンドコードに記述すると、訪問者は開発者ツールでそれを見ることができます。

### 推奨プラクティス

1. **HTTP API リクエスト**: `X-API-Key` ヘッダーを使用します。`?api_key=` にシークレットを配置することは避けてください。
2. **WebSocket 接続**: ネイティブブラウザ WebSocket はカスタム `X-API-Key` ヘッダーを設定できません。ブラウザのみの例を機能させるために、WebSocket は `?api_key=` を使用できます。パブリックな本番展開の場合は、キーをサーバー側に保つために、バックエンドプロキシまたは同一生成元リバースプロキシを引き続き推奨します。
3. **ユースケース**: `?api_key=` はローカルテスト、トラブルシューティング、または制御された LAN 環境に適しています。パブリックページで使用できますが、ブラウザ URL、プロキシログ、またはスクリーンショットを通じて公開される可能性があることに注意してください。
4. **サーバー側コード**: PHP、Node.js、Java などのサーバー側コードは API キーを保持できますが、実際のキーを含むソースコード、ログ、または設定ファイルをパブリックリポジトリにコミットしないでください。
5. **リスク警告**: 一時的に `?api_key=` を使用する必要がある場合は、ブラウザの履歴、プロキシログ、サーバーアクセスログ、およびスクリーンショットがキーを保持する可能性があることを覚えておいてください。

## HTML 埋め込み例

`SERVER_HOST` をサーバーの IP またはドメインに置き換えます。このブラウザのみの例は、API キーが有効になっていない場合に直接使用できます。API キーが有効な場合は、`API_KEY` を入力すると、WebSocket は `?api_key=` で接続します。パブリックな本番展開の場合は、バックエンドプロキシまたは同一生成元リバースプロキシを引き続き推奨します。

```html
<!doctype html>
<html lang="ja">
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
  <h1>サーバー状態</h1>
  <div class="grid">
    <div class="card">CPU<div id="cpu" class="value">-</div></div>
    <div class="card">メモリ<div id="memory" class="value">-</div></div>
    <div class="card">プロセス<div id="processes" class="value">-</div></div>
    <div class="card">スレッド<div id="threads" class="value">-</div></div>
    <div class="card">ハンドル<div id="handles" class="value">-</div></div>
    <div class="card">稼働時間<div id="uptime" class="value">-</div></div>
    <div class="card">GPU<div id="gpu" class="value">-</div></div>
    <div class="card">ネットワーク受信<div id="netIn" class="value">-</div></div>
    <div class="card">ネットワーク送信<div id="netOut" class="value">-</div></div>
    <div class="card">ディスク読み取り<div id="diskRead" class="value">-</div></div>
    <div class="card">ディスク書き込み<div id="diskWrite" class="value">-</div></div>
  </div>
  <h2>すべてのディスクドライブ</h2>
  <pre id="drives">-</pre>
  <h2>すべてのディスクデバイス</h2>
  <pre id="diskNames">-</pre>
  <h2>すべてのネットワークインターフェース</h2>
  <pre id="interfaces">-</pre>
  <h2>すべての GPU</h2>
  <pre id="gpus">-</pre>
  <h2>メモリハードウェア</h2>
  <pre id="memoryHardware">-</pre>
  <h2>すべての物理プロセッサ</h2>
  <pre id="cpuPackages">-</pre>
  <h2>すべての論理プロセッサ</h2>
  <pre id="processors">-</pre>

  <script>
    const SERVER_HOST = "127.0.0.1:8765";
    const API_KEY = ""; // 信頼できる/ローカルページでのみ入力してください。
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

## JavaScript リクエスト例

既存のフロントエンドプロジェクトに適しています。HTTP リクエストは `X-API-Key` ヘッダーを使用できます。ネイティブブラウザ WebSocket はカスタムリクエストヘッダーを設定できないため、API キーが有効でバックエンドプロキシが使用されていない場合、WebSocket は `?api_key=` を必要とします。

```js
const apiBase = "http://127.0.0.1:8765";
const apiKey = ""; // 本番 API キーをパブリックなフロントエンドコードに記述しないでください。

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

`?api_key=` は、特にバックエンドプロキシのないブラウザのみのページの場合、ブラウザ WebSocket 認証に使用できます。パブリックリポジトリ、スクリーンショット、ログ、またはサードパーティプロキシに実際の API キーを公開しないでください。

## PHP リクエスト例

PHP はバックエンドプロキシまたはサーバー側レンダリングされたスナップショットリーダーとして適しています。実際の API キーはサーバー上に留める必要があり、HTML または JavaScript に出力しないでください。WebSocket ライブ表示に認証が必要な場合は、同一生成元プロキシまたはリバースプロキシを提供してください。

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
<html lang="ja">
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

## ログ

すべての HTTP リクエストはコンソールに出力され、次のファイルに書き込まれます：

```text
server_monitor.log
```

WebSocket 接続、切断、および認証失敗もログに記録されます。

## GPU の注意事項

スクリプトは NVIDIA GPU の使用率、VRAM、および温度を取得するために `nvidia-smi` を優先します。NVIDIA GPU が利用できない場合、Windows GPU Engine パフォーマンスカウンターを読み取ろうとします。異なる GPU とドライバーは異なるデータを公開するため、非 NVIDIA GPU は使用率パーセンテージのみを提供し、メモリと温度は `null` になる可能性があります。

## よくある質問

### なぜメモリモジュール情報が利用できないのですか？
Windows には CIM/WMI アクセスへの制限があり、管理者権限またはグループポリシーの調整が必要になる場合があります。

### 詳細なエラーログをどのように表示しますか？
すべての HTTP リクエストと WebSocket 接続の詳細なログを含む `server_monitor.log` ファイルを確認してください。

### Linux で使用できますか？
現在のバージョンは Windows 固有のパフォーマンスカウンターと WMI インターフェイスを使用するため、Windows のみをサポートしています。

### データ収集間隔を変更するにはどうすればよいですか？
`--interval` 引数または `MONITOR_INTERVAL_SECONDS` 環境変数で秒単位で設定します。

## テクノロジースタック

- Python 3.10+
- aiohttp（非同期 HTTP サーバー）
- psutil（システム監視）
- asyncio（非同期プログラミング）

## ライセンス

このプロジェクトは MIT ライセンスの下でライセンスされています。
