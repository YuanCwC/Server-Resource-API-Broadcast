# Server Resource API Broadcast

[English](README_EN.md) | [Русский](README_RU.md) | [日本語](README_JA.md) | 简体中文

API для мониторинга ресурсов сервера под Windows. Каждые 5 секунд собирает данные о загрузке CPU, памяти, сети, GPU, дискового ввода-вывода, ёмкости всех подключённых дисков и счётчики из Диспетчера задач, затем предоставляет их через HTTP API и WebSocket для встраивания в веб-панели.

## Особенности проекта

- **Мониторинг в реальном времени**: автоматический сбор данных о ресурсах системы каждые 5 секунд
- **Поддержка нескольких протоколов**: HTTP REST API и вещание через WebSocket
- **Комплексный мониторинг**: охватывает все ключевые метрики — CPU, память, сеть, GPU и диски
- **Гибкая настройка**: поддержка аргументов командной строки, переменных окружения и файлов конфигурации
- **Безопасная аутентификация**: встроенный механизм аутентификации по API-ключу с поддержкой HTTPS/WSS
- **Дружелюбность к CORS**: по умолчанию разрешает междоменные запросы из браузера для удобной интеграции с фронтендом
- **Автоопределение**: при запуске автоматически проверяет доступность информации об оборудовании

## Быстрый старт

Сначала запустите скрипт проверки окружения:

```cmd
check_env.cmd
```

Этот скрипт:
1. Проверяет наличие Python 3.10+
2. Создаёт виртуальное окружение `.venv`
3. Устанавливает зависимости из `requirements.txt`
4. Если Python не найден, пытается установить Python 3.12 через `winget`
5. Если `winget` недоступен, требуется ручная установка Python

Запуск сервиса:

```cmd
start_monitor.cmd
```

Программа запускается напрямую и отображает результаты самодиагностики. Доступные функции отображаются зелёным как `[True]`, недоступные — красным как `[False]` с указанием причины:

```text
CPU[True] total=8.2%, logical=12
Memory[True] total=15.16GB, available=5.34GB
MemoryModules[False] Physical memory module details are unavailable. Windows denied CIM/WMI access or no module data was returned.
```

### Аргументы командной строки

Можно передать API-ключ напрямую:

```cmd
start_monitor.cmd --api-key "ваш_секрет"
```

Указать порт и интервал опроса:

```cmd
start_monitor.cmd --port 8765 --interval 5 --api-key "ваш_секрет"
```

Запуск с собственным HTTPS-сертификатом:

```cmd
start_monitor.cmd --ssl-certfile certs\fullchain.pem --ssl-keyfile certs\privkey.pem --api-key "ваш_секрет"
```

Указать файл конфигурации:

```cmd
start_monitor.cmd --config monitor_config.local.json
```

### Переменные окружения

Также можно настроить через переменные окружения:

```cmd
set MONITOR_API_KEY=ваш_секрет
set MONITOR_PORT=8765
set MONITOR_INTERVAL_SECONDS=5
set MONITOR_SSL_CERTFILE=certs\fullchain.pem
set MONITOR_SSL_KEYFILE=certs\privkey.pem
start_monitor.cmd
```

`start_monitor.cmd` запускает сервис напрямую. Если `.venv` или необходимые пакеты отсутствуют, автоматически сначала запускается `check_env.cmd`.

**Напоминание о безопасности**: не коммитьте реальные API-ключи, закрытые ключи сертификатов или производственные конфигурационные файлы в публичный репозиторий. В публичных примерах оставляйте заполнители. Для реальных развёртываний используйте переменные окружения или локальный конфигурационный файл, например `monitor_config.local.json`, который игнорируется `.gitignore`.

## Файл конфигурации

В корневом каталоге находится `monitor_config.json`. В публичном репозитории держите ключи и пути к сертификатам пустыми:

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

Для реального развёртывания используйте переменные окружения, аргументы командной строки или создайте локальный конфигурационный файл, который не будет закоммичен в Git:

```json
{
  "host": "0.0.0.0",
  "port": 8765,
  "interval_seconds": 5,
  "api_key": "замените_на_ваш_надёжный_секрет",
  "ssl_certfile": "",
  "ssl_keyfile": ""
}
```

Затем запустите сервер:

```cmd
start_monitor.cmd
```

### Приоритет конфигурации

```text
аргументы командной строки > переменные окружения > monitor_config.json > значения по умолчанию
```

Чтобы отключить SSL, оставьте `ssl_certfile` и `ssl_keyfile` пустыми:

```json
{
  "ssl_certfile": "",
  "ssl_keyfile": ""
}
```

Чтобы использовать другой файл конфигурации:

```cmd
start_monitor.cmd --config monitor_config.local.json
```

## Рекомендации по развёртыванию HTTPS / SSL

Python-сервер может обслуживать HTTPS/WSS напрямую. При указании обоих `--ssl-certfile` и `--ssl-keyfile` сервис переключается с HTTP/WS на HTTPS/WSS:

```cmd
start_monitor.cmd --ssl-certfile certs\fullchain.pem --ssl-keyfile certs\privkey.pem
```

URL-адреса становятся:

- `https://ваш-домен:8765/api/metrics`
- `https://ваш-домен:8765/api/hardware`
- `wss://ваш-домен:8765/ws/metrics`

Для публичных развёртываний рекомендуется держать Python API на локальном HTTP/WS и завершать TLS во фронт-прокси или туннеле, таком как Nginx, Caddy, BT Panel, frp HTTPS tunnel, Cloudflare Tunnel или другом обратном прокси. Это обычно упрощает продление сертификатов, привязку доменов и совместимость с браузерами, а также позволяет не помещать закрытые ключи напрямую в процесс Python.

Правило браузера: если ваша веб-страница загружается через HTTPS, конечная точка API также должна использовать HTTPS/WSS. Страница HTTPS не может подключаться к обычному `http://` или `ws://`. Если вы используете локальную HTTP-страницу, например VS Code Live Server через HTTP, API может использовать HTTP/WS.

Если вам нужно, чтобы Python напрямую завершал SSL, поместите файлы сертификатов сюда:

```text
certs\fullchain.pem
certs\privkey.pem
```

## Ручная установка

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Ручной запуск

```powershell
python .\server_monitor_api.py
```

С API-ключом:

```powershell
python .\server_monitor_api.py --api-key "ваш_секрет"
```

С SSL:

```powershell
python .\server_monitor_api.py --ssl-certfile certs\fullchain.pem --ssl-keyfile certs\privkey.pem --api-key "ваш_секрет"
```

После запуска терминал выводит ссылки:

- `http://127.0.0.1:8765/api/metrics`
- `http://127.0.0.1:8765/api/hardware`
- `ws://LAN-IP:8765/ws/metrics`
- `http://127.0.0.1:8765/demo`
- `http://127.0.0.1:8765/docs`

Если включён API-ключ, отправляйте его в заголовке запроса:

```powershell
Invoke-RestMethod "http://127.0.0.1:8765/api/metrics" -Headers @{"X-API-Key"="ваш_секрет"}
```

## Конечные точки API

HTTP API по умолчанию разрешают браузерные междоменные запросы `GET/OPTIONS` и заголовок `X-API-Key`, что упрощает создание панелей в браузере. Для публичных развёртываний всё равно используйте API-ключ, бэкенд-прокси или однодоменный обратный прокси для контроля доступа.

### Снимок текущих метрик

```http
GET /api/metrics
```

Возвращает данные мониторинга в реальном времени, включая информацию об именах оборудования.

### Имена оборудования

```http
GET /api/hardware
```

Возвращает имена/модели CPU, модулей памяти, GPU и дисковых устройств. Эта конечная точка полезна при инициализации веб-страницы, поскольку имена оборудования обычно не меняются часто.

### Вещание в реальном времени

```text
ws://127.0.0.1:8765/ws/metrics
```

Сервер автоматически вещает JSON-данные с настроенным интервалом.

### Демо-страница

```http
GET /demo
```

Минимальная страница для проверки работы WebSocket в реальном времени.

### Документация API

```http
GET /docs
```

Интерактивная документация API в формате Swagger/OpenAPI.

## Собираемые данные

### Системная информация (`system`)
- Время безотказной работы
- Время загрузки
- Количество процессов
- Количество потоков
- Количество дескрипторов

### Информация об оборудовании (`hardware`)
- Имя CPU
- Информация о модулях памяти (ёмкость, поколение DDR, частота)
- Имена GPU
- Имена дисковых устройств

Программа определяет ёмкость памяти хоста, поколение DDR и частоту, затем формирует `hardware.memory.name` / `hardware.memory.display_name`, например `32GB DDR5 4800MHz (2 x 16GB)`. Каждый модуль также включает `modules[].name` / `modules[].display_name`, например `16GB DDR5 4800MHz`, когда Windows предоставляет достаточно данных.

### CPU (`cpu`)
- Общая загрузка CPU
- Физические ядра
- Логические ядра
- Текущая частота
- Пакеты физических процессоров
- Загрузка логических процессоров

### Память (`memory`)
- Общая память
- Использованная память
- Доступная память
- Свободная память
- Процент использования памяти

### Сеть (`network`)
- Общая скорость загрузки/выгрузки
- Общий отправленный/полученный трафик
- Скорость загрузки/выгрузки для каждого интерфейса
- IP-адреса
- Состояние подключения
- Скорость сетевого адаптера

### Дисковый ввод-вывод (`disk.io`)
- Скорость чтения/записи для дисковых устройств
- Процент занятости

### Дисковые тома (`disk.drives`)
- Ёмкость всех подключённых букв дисков/томов
- Не ограничивается C: и D:

### GPU (`gpu`)
- Все GPU NVIDIA перечисляются при наличии
- Без NVIDIA пытается считать счётчики производительности Windows GPU Engine

## API-ключ и безопасность фронтенда

Этот репозиторий не включает полный каталог фронтенда `web`. Следующие разделы — только примеры встраивания. Браузерный HTML, JavaScript, панели Network, скриншоты ошибок и журналы доступа могут раскрыть URL-адреса или исходный код. Если вы поместите секрет в код фронтенда, посетители смогут увидеть его в инструментах разработчика.

### Рекомендуемые практики

1. **Запросы HTTP API**: используйте заголовок `X-API-Key`. Избегайте помещения секретов в `?api_key=`.
2. **WebSocket-соединения**: нативный браузерный WebSocket не может установить пользовательский заголовок `X-API-Key`. Чтобы примеры только для браузера работали, WebSocket может использовать `?api_key=`. Для публичных производственных развёртываний всё равно рекомендуется бэкенд-прокси или однодоменный обратный прокси, чтобы ключ оставался на стороне сервера.
3. **Варианты использования**: `?api_key=` подходит для локальных тестов, устранения неполадок или контролируемых LAN-сред. Его можно использовать на публичных страницах, но он может быть раскрыт через URL-адреса браузера, журналы прокси или скриншоты.
4. **Серверный код**: серверный код, такой как PHP, Node.js или Java, может хранить API-ключ, но не коммитьте исходный код, журналы или конфигурационные файлы, содержащие реальные ключи, в публичный репозиторий.
5. **Предупреждение о рисках**: если вы временно используете `?api_key=`, помните, что история браузера, журналы прокси, журналы доступа сервера и скриншоты могут сохранить ключ.

## Пример встраивания HTML

Замените `SERVER_HOST` на IP-адрес или домен вашего сервера. Этот пример только для браузера работает напрямую, когда API-ключ не включён. Если API-ключ включён, заполните `API_KEY`, и WebSocket подключится с `?api_key=`. Для публичных производственных развёртываний всё равно рекомендуется бэкенд-прокси или однодоменный обратный прокси.

```html
<!doctype html>
<html lang="ru">
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
  <h1>Статус сервера</h1>
  <div class="grid">
    <div class="card">CPU<div id="cpu" class="value">-</div></div>
    <div class="card">Память<div id="memory" class="value">-</div></div>
    <div class="card">Процессы<div id="processes" class="value">-</div></div>
    <div class="card">Потоки<div id="threads" class="value">-</div></div>
    <div class="card">Дескрипторы<div id="handles" class="value">-</div></div>
    <div class="card">Время работы<div id="uptime" class="value">-</div></div>
    <div class="card">GPU<div id="gpu" class="value">-</div></div>
    <div class="card">Входящий трафик<div id="netIn" class="value">-</div></div>
    <div class="card">Исходящий трафик<div id="netOut" class="value">-</div></div>
    <div class="card">Чтение диска<div id="diskRead" class="value">-</div></div>
    <div class="card">Запись диска<div id="diskWrite" class="value">-</div></div>
  </div>
  <h2>Все дисковые тома</h2>
  <pre id="drives">-</pre>
  <h2>Все дисковые устройства</h2>
  <pre id="diskNames">-</pre>
  <h2>Все сетевые интерфейсы</h2>
  <pre id="interfaces">-</pre>
  <h2>Все GPU</h2>
  <pre id="gpus">-</pre>
  <h2>Аппаратная память</h2>
  <pre id="memoryHardware">-</pre>
  <h2>Все физические процессоры</h2>
  <pre id="cpuPackages">-</pre>
  <h2>Все логические процессоры</h2>
  <pre id="processors">-</pre>

  <script>
    const SERVER_HOST = "127.0.0.1:8765";
    const API_KEY = ""; // Заполняйте только для доверенных/локальных страниц.
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

## Пример запроса JavaScript

Подходит для существующих фронтенд-проектов. HTTP-запросы могут использовать заголовок `X-API-Key`. Нативный браузерный WebSocket не может устанавливать пользовательские заголовки запроса, поэтому при включённом API-ключе и отсутствии бэкенд-прокси WebSocket нуждается в `?api_key=`.

```js
const apiBase = "http://127.0.0.1:8765";
const apiKey = ""; // Не помещайте производственный API-ключ в публичный фронтенд-код.

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

`?api_key=` можно использовать для аутентификации браузерного WebSocket, особенно для страниц только на браузере без бэкенд-прокси. Не раскрывайте реальные API-ключи в публичных репозиториях, скриншотах, журналах или сторонних прокси.

## Пример запроса PHP

PHP подходит как бэкенд-прокси или считыватель снимков на стороне сервера. Реальный API-ключ должен оставаться на сервере и не должен выводиться в HTML или JavaScript. Если живому отображению WebSocket нужна аутентификация, предоставьте однодоменный прокси или обратный прокси.

```php
<?php
$url = 'http://127.0.0.1:8765/api/metrics';
$apiKey = 'ваш_секрет';

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
<html lang="ru">
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

## Журналы

Каждый HTTP-запрос выводится в консоль и записывается в:

```text
server_monitor.log
```

Также логируются подключения WebSocket, отключения и сбои аутентификации.

## Примечания о GPU

Скрипт предпочитает `nvidia-smi` для получения загрузки, видеопамяти и температуры GPU NVIDIA. Если GPU NVIDIA нет, он пытается считать счётчики производительности Windows GPU Engine. Разные GPU и драйверы предоставляют разные данные, поэтому не-NVIDIA GPU могут предоставлять только процент загрузки, а память и температура могут быть `null`.

## Часто задаваемые вопросы

### Почему информация о модулях памяти недоступна?
Windows имеет ограничения на доступ к CIM/WMI, которые могут требовать прав администратора или корректировок групповой политики.

### Как просмотреть подробные журналы ошибок?
Проверьте файл `server_monitor.log`, который содержит подробные журналы всех HTTP-запросов и WebSocket-соединений.

### Можно ли использовать это на Linux?
Текущая версия поддерживает только Windows, поскольку использует специфичные для Windows счётчики производительности и интерфейсы WMI.

### Как изменить интервал сбора данных?
Установите через аргумент `--interval` или переменную окружения `MONITOR_INTERVAL_SECONDS` в секундах.

## Технологический стек

- Python 3.10+
- aiohttp (асинхронный HTTP-сервер)
- psutil (мониторинг системы)
- asyncio (асинхронное программирование)

## Лицензия

Этот проект лицензирован под лицензией MIT.
