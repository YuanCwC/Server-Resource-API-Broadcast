# SSL certificates

Put your HTTPS certificate and private key here only when you want the Python API to terminate SSL by itself.

For public deployments, it is usually easier to keep the Python API on local HTTP/WS and let Nginx, Caddy, BT panel, frp HTTPS tunnel, or another front proxy handle HTTPS/WSS.

Recommended filenames:

```text
certs/fullchain.pem
certs/privkey.pem
```

Start with SSL:

```cmd
start_monitor.cmd --ssl-certfile certs\fullchain.pem --ssl-keyfile certs\privkey.pem
```

Or:

```cmd
python server_monitor_api.py --ssl-certfile certs\fullchain.pem --ssl-keyfile certs\privkey.pem
```

Do not commit real private keys to a public repository.
