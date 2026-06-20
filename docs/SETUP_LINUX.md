# Linux Setup

## 1. Install Python and venv support

Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
```

## 2. Install RoomSentry dependencies

```bash
chmod +x install_linux.sh run_linux.sh run_dashboard_linux.sh run_all_linux.sh
./install_linux.sh
```

## 3. Create your local config

```bash
cp config.example.json config.json
```

## 4. Run diagnostics

```bash
source .venv/bin/activate
python doctor.py
```

## 5. Start RoomSentry and dashboard

```bash
./run_all_linux.sh
```

Dashboard:

```text
http://127.0.0.1:8765
```
