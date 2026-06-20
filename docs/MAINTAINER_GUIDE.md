# Maintainer Guide

## Before merging a PR

- Check the change keeps RoomSentry local-first by default.
- Check no secrets, real `config.json`, snapshots, clips, or logs were committed.
- Run compile checks:

```bash
python -m py_compile room_sentry.py dashboard_server.py settings_gui.py doctor.py export_events.py migrate_config.py test_alerts.py test_discord.py open_dashboard.py
```

- Run diagnostics if possible:

```bash
cp config.example.json config.json
python migrate_config.py
python doctor.py
```

## Labels

Recommended labels:

| Label | Use |
|---|---|
| `bug` | Broken behaviour |
| `enhancement` | New feature |
| `good first issue` | Safe starter task |
| `help wanted` | External contributors welcome |
| `privacy` | Privacy docs/defaults/data handling |
| `safety` | Permission, misuse prevention, warnings |
| `windows` | Windows scripts/UI/camera issues |
| `linux` | Linux scripts/camera issues |
| `dashboard` | Browser dashboard/API |
| `detector` | YOLO/OpenCV/motion detection |
| `alerts` | Discord/Telegram/ntfy/webhook/TTS |
| `docs` | Documentation only |
| `dependencies` | Dependency updates |
| `needs-triage` | Needs maintainer review |

## Release process

1. Update `CHANGELOG.md`.
2. Update version in `pyproject.toml`.
3. Run checks locally.
4. Build a zip:

```bash
python scripts/make_release_zip.py
```

5. Create a git tag:

```bash
git tag v1.4.0
git push origin v1.4.0
```

6. Confirm the Release ZIP workflow attached the clean zip.
7. Add screenshots and release notes.

## Security/privacy reports

For urgent vulnerabilities, use GitHub private security advisories. Do not ask reporters to post private camera URLs, images, or tokens in public issues.
