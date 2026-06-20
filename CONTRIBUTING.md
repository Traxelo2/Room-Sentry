# Contributing to RoomSentry

Thanks for wanting to improve RoomSentry.

## Good first contributions

- Improve README setup steps
- Add screenshots/GIFs
- Test different webcams/IP cameras
- Improve Windows installer reliability
- Improve Linux launch scripts
- Add dashboard UI polish
- Add unit tests around config migration and event export
- Improve privacy/security defaults

## Development setup

```bash
git clone https://github.com/YOUR_USERNAME/roomsentry.git
cd roomsentry
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.example.json config.json
python doctor.py
```

On Windows, use PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item config.example.json config.json
python doctor.py
```

## Before opening a pull request

Run:

```bash
python -m py_compile room_sentry.py dashboard_server.py settings_gui.py doctor.py export_events.py migrate_config.py test_alerts.py test_discord.py open_dashboard.py
python migrate_config.py
python doctor.py
```

Do not commit:

- `config.json`
- webhook URLs
- API tokens
- snapshots/clips/logs
- camera footage
- `.venv` or `venv`

## Pull request checklist

- [ ] I tested the changed code locally
- [ ] I did not commit secrets or personal footage
- [ ] I updated docs if setup/features changed
- [ ] I kept the dashboard local-first/private by default
- [ ] I considered privacy and consent implications

## Code style

RoomSentry is currently intentionally simple and script-based. Prefer readable standard-library Python over adding heavy frameworks. Avoid adding cloud services as hard dependencies.
