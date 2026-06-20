# Security Policy

## Supported versions

RoomSentry is currently alpha software. Security fixes should target the latest `main` branch until formal releases are created.

## Reporting a vulnerability

Please do not open a public issue for serious security problems involving remote access, token leakage, camera access, command execution, or dashboard bypasses.

Instead, report privately through GitHub Security Advisories if the repository has them enabled, or contact the maintainer using the security contact listed in the GitHub repository.

## Sensitive data

RoomSentry can be configured with webhooks, Telegram tokens, private camera URLs, and local footage. These should never be committed.

The repo ignores common runtime and secret files, including:

- `config.json`
- `.env`
- snapshots
- clips
- logs
- events database/logs
- runtime command/status files

## Dashboard exposure warning

The dashboard defaults to `127.0.0.1`. Keep it that way unless you are using a trusted private network.

Do not expose the dashboard directly to the public internet. Use Tailscale, WireGuard, SSH tunnel, or another private access layer.
