# certbot-uyuni

Certbot installer plugin for [Uyuni](https://www.uyuni-project.org/).

Deploys certificates as podman secrets and restarts the Uyuni server via `mgradm`.

## Installation

```bash
pip install certbot-uyuni
```

## Usage

```bash
certbot install --installer uyuni -d uyuni.example.com
```

### Options

- `--uyuni-restart-timeout` — Seconds to wait for the server to become healthy after restart (default: 300).

## Requirements

- `podman` and `mgradm` must be on PATH
- The `uyuni-server` container must be running

## License

Apache-2.0
