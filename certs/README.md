# SSL 证书

[English](README_EN.md) | 简体中文

只有在你希望 Python API 自己处理 HTTPS/WSS 时，才需要把证书和私钥放到这里。

公网部署时，更推荐让 Python API 保持本机或内网 HTTP/WS，然后用 Nginx、Caddy、宝塔、frp HTTPS 隧道、Cloudflare Tunnel 或其他前置代理负责 HTTPS/WSS。这样证书续期、域名绑定和浏览器兼容性通常更稳定，也可以避免 Python 程序直接管理私钥。

推荐文件名：

```text
certs/fullchain.pem
certs/privkey.pem
```

使用 SSL 启动：

```cmd
start_monitor.cmd --ssl-certfile certs\fullchain.pem --ssl-keyfile certs\privkey.pem
```

或者：

```cmd
python server_monitor_api.py --ssl-certfile certs\fullchain.pem --ssl-keyfile certs\privkey.pem
```

不要把真实私钥提交到公开仓库。`.gitignore` 已经默认忽略 `certs/*.pem`、`certs/*.key` 和 `certs/*.crt`。

