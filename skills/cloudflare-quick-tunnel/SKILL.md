---
name: cloudflare-quick-tunnel
description: Expose a local server on a public HTTPS URL with a Cloudflare quick tunnel (TryCloudflare), no account or DNS needed. Use when someone wants to share localhost, give a reviewer or phone a link to a dev server, receive a webhook or OAuth callback locally, or asks about cloudflared, trycloudflare.com, or an ngrok alternative.
metadata:
  skillforge:
    version: 1.2.0
---

# Cloudflare quick tunnel

`cloudflared` dials out to Cloudflare, gets a random `*.trycloudflare.com` hostname, and proxies
it to a port on this machine. No account, no signup, no inbound port. The hostname lives as long
as the process and cannot be reserved or reused.

Before starting one, confirm with the person: a quick tunnel puts whatever is on that port on the
public internet, unauthenticated, for anyone who has the URL.

## Install

| Platform | Command |
| --- | --- |
| macOS | `brew install cloudflared` |
| Debian, Ubuntu | see the repo commands below |
| RHEL, CentOS, Amazon Linux | `curl -fsSl https://pkg.cloudflare.com/cloudflared.repo \| sudo tee /etc/yum.repos.d/cloudflared.repo` then `sudo yum install cloudflared` |
| Docker | `docker run --rm cloudflare/cloudflared:latest tunnel --url http://host.docker.internal:8000` |
| Anywhere | download a binary from `https://github.com/cloudflare/cloudflared/releases/latest` |

```bash
sudo mkdir -p --mode=0755 /usr/share/keyrings
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main' | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt-get update && sudo apt-get install cloudflared
```

On Windows, take the `.msi` from the releases page. `winget install --id Cloudflare.cloudflared`
exists but is community-maintained and has shipped stale, unsigned builds; prefer the MSI.
Downloading the single static binary is always an option and needs no privileges.

## Run one

```bash
cloudflared tunnel --url http://localhost:8000
```

That is the whole product. The public hostname is printed in a box in the logs:

```
Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):
https://<random-words>.trycloudflare.com
```

Variants, all verified against `cloudflared tunnel --help` on 2026.9.1:

| Goal | Flag |
| --- | --- |
| Origin is HTTPS with a self-signed certificate | `--no-tls-verify` |
| Origin is a Unix socket, not a port | `--unix-socket /path/to.sock` (replaces `--url`) |
| Origin is name-based virtual hosted | `--http-host-header example.test` |
| Origin certificate has a different name | `--origin-server-name example.test` |
| Origin speaks HTTP/2 | `--http2-origin` |
| WSGI origin that mishandles chunked bodies | `--no-chunked-encoding` |
| Structured logs | `--output json` (needs 2025.6.1 or later) |
| Quieter or noisier logs | `--loglevel {debug,info,warn,error,fatal}` |
| Logs to a file | `--logfile ./tunnel.log` |
| Prometheus metrics endpoint | `--metrics localhost:20241` |
| Force IPv4 or IPv6 to the edge | `--edge-ip-version {4,6,auto}` |
| Slow origin startup | `--proxy-connect-timeout 60s` |
| Write the PID for later cleanup | `--pidfile ./tunnel.pid` |

`--url` defaults to `http://localhost:8080`, so a bare `cloudflared tunnel` is not a no-op. Always
pass the port explicitly. Every `--url`-style origin flag above is ignored if an ingress-rules
config file is in play, which is why a stray `~/.cloudflared/config.yaml` breaks quick tunnels;
rename it before debugging anything else.

`--protocol {auto,http2,quic}` is accepted and documented by Cloudflare but is hidden from
`--help`; quick tunnels pick `quic`. Reach for it only when QUIC is blocked on the network.

## Capture the URL

The hostname is generated at runtime, so anything automated has to read it back out. Start the
process in the background, then wait for the line rather than sleeping a fixed time:

```bash
cloudflared tunnel --url http://localhost:8000 --output json >tunnel.log 2>&1 &
until url=$(grep -om1 'https://[a-z0-9-]*\.trycloudflare\.com' tunnel.log); do sleep 1; done
echo "$url"
```

`--output json` changes the log format, not the shape of the result. Each line becomes
`{"level":"info","message":"...","time":"..."}` and the hostname arrives inside a `message`, still
wrapped in the ASCII box:

```json
{"level":"info","message":"|  https://gather-masters-wifi-boots.trycloudflare.com    |","time":"..."}
```

So parse for the hostname, not for a field. Match on `https://` too: the first line mentioning
`trycloudflare.com` is `Requesting new quick Tunnel on trycloudflare.com...`, which is not the URL.

Two things that bite in a shell: `cd ... && cloudflared ... &` backgrounds the whole `&&` list, so
the `cd` does not apply to the foreground poll and it watches for the log in the wrong directory;
and the URL answers a few seconds after it is printed, as the banner itself warns.

## Read the failure

The edge and the origin fail differently, and the code says which:

| Symptom | Meaning |
| --- | --- |
| Cloudflare error 1033 | No connector for that hostname: the process died, or the URL is from an earlier run. A hostname is never reissued, so an old link can only ever give this |
| HTTP 530 | The status the 1033 page is served with |
| Cloudflare error 1016 | The tunnel is up; nothing is listening on the port passed to `--url` |
| Plain 502 or 504 | The origin is listening but erroring or too slow |
| HTTP 429 | The 200 in-flight request cap |
| `curl` exit 6, status `000` | DNS has not caught up yet, seconds after the URL is printed |

The first and last are both normal right after starting: the hostname can be unresolvable, then
1033, then answer, within about ten seconds. Poll for a 200 before handing the link to anyone
rather than reporting the first failure.

## Stop it

`SIGINT` or `SIGTERM` the process. The hostname dies with it and there is nothing to clean up on
Cloudflare's side. A second signal skips the 30 second drain for in-flight requests.

## Know the limits

- **Testing and development only.** Cloudflare says so explicitly. Anything that needs to stay up
  wants a named tunnel on an account.
- **200 concurrent in-flight requests.** Past that the edge returns HTTP 429.
- **No Server-Sent Events.** Streaming endpoints that use SSE will not work; this rules out many
  LLM and live-log demos.
- **The URL is random and unrecoverable.** Restarting gives a different hostname, so anything that
  hardcodes a callback URL has to be updated on every restart.
- **Requires 2020.5.1 or later**, and Cloudflare supports only releases from the past year.

If any of these bite, the answer is a named tunnel with an account, not a workaround.
