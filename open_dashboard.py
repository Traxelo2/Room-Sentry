import json
import sqlite3
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"


def load_config():
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def app_path(value: str, default: str) -> Path:
    path = Path(str(value or default))
    return path if path.is_absolute() else BASE_DIR / path


def try_open_live_dashboard(config):
    host = config.get("dashboard_host", "127.0.0.1")
    port = int(config.get("dashboard_port", 8765))
    url = f"http://{host}:{port}/"
    try:
        with urlopen(url, timeout=1.5) as response:
            if response.status < 500:
                webbrowser.open(url)
                print(f"Opened live dashboard: {url}")
                return True
    except Exception:
        return False
    return False


def fetch_events(config, limit=100):
    db_path = app_path(config.get("events_db_path", "events/roomsentry_events.sqlite3"), "events/roomsentry_events.sqlite3")
    if not db_path.exists():
        return []
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,))]


def rel_link(value):
    if not value:
        return ""
    path = BASE_DIR / value
    if not path.exists():
        return str(value)
    return f'<a href="{path.as_uri()}" target="_blank">{Path(value).name}</a>'


def image_thumb(value):
    if not value:
        return ""
    path = BASE_DIR / value
    if not path.exists():
        return ""
    return f'<a href="{path.as_uri()}" target="_blank"><img src="{path.as_uri()}" loading="lazy" /></a>'


def open_static_dashboard(config):
    events = fetch_events(config)
    person_events = [e for e in events if e.get("event_type") == "person_detected"]
    latest = events[0]["created_at"] if events else "No events yet"
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    rows = []
    gallery = []
    for e in events:
        snapshot = e.get("snapshot_path")
        clip = e.get("clip_path")
        rows.append(
            "<tr>"
            f"<td>{e.get('created_at','')}</td>"
            f"<td><span class='badge'>{e.get('event_type','')}</span></td>"
            f"<td>{e.get('message','')}</td>"
            f"<td>{'' if e.get('confidence') is None else round(float(e.get('confidence')), 3)}</td>"
            f"<td>{'' if e.get('person_count') is None else e.get('person_count')}</td>"
            f"<td>{rel_link(snapshot)}</td>"
            f"<td>{rel_link(clip)}</td>"
            "</tr>"
        )
        if snapshot:
            gallery.append(f"<figure>{image_thumb(snapshot)}<figcaption>{e.get('created_at','')}</figcaption></figure>")

    html_text = f"""<!doctype html><html lang="en"><head><meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>RoomSentry Static Dashboard</title>
<style>
:root {{ color-scheme: dark; }} body {{ margin:0; font-family: Inter, Segoe UI, Arial, sans-serif; background:#080b0a; color:#e9fff3; }}
header {{ padding:28px; background:linear-gradient(135deg,#101a14,#07100b); border-bottom:1px solid #1e3b2b; }}
h1 {{ margin:0 0 6px; font-size:34px; letter-spacing:-1px; }} p {{ color:#a9c8b6; }}
.cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:14px; padding:20px 28px; }}
.card {{ background:#0f1712; border:1px solid #1e3b2b; border-radius:16px; padding:18px; }} .card strong {{ display:block; font-size:30px; margin-top:8px; color:#73ff9d; }}
section {{ padding:8px 28px 28px; }} .tablewrap {{ overflow:auto; border:1px solid #1e3b2b; border-radius:16px; }}
table {{ width:100%; border-collapse:collapse; min-width:980px; background:#0b110d; }} th,td {{ padding:12px; border-bottom:1px solid #17271d; text-align:left; vertical-align:top; }} th {{ background:#102016; color:#bfffd1; }}
a {{ color:#73ff9d; }} .badge {{ display:inline-block; padding:4px 8px; border:1px solid #2f6041; border-radius:999px; background:#0d1a12; color:#bfffd1; font-size:12px; }}
.gallery {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(170px,1fr)); gap:14px; }} figure {{ margin:0; background:#0f1712; border:1px solid #1e3b2b; border-radius:16px; overflow:hidden; }} img {{ width:100%; height:130px; object-fit:cover; display:block; }} figcaption {{ padding:9px; color:#a9c8b6; font-size:12px; }}
</style></head><body><header><h1>RoomSentry Static Dashboard</h1><p>Generated {generated}. Start dashboard_server.py for live controls.</p></header>
<div class="cards"><div class="card">Total events<strong>{len(events)}</strong></div><div class="card">Person alerts<strong>{len(person_events)}</strong></div><div class="card">Latest event<strong style="font-size:16px">{latest}</strong></div></div>
<section><h2>Snapshot gallery</h2><div class="gallery">{''.join(gallery) or '<p>No snapshots yet.</p>'}</div><h2>Event timeline</h2><div class="tablewrap"><table><thead><tr><th>Time</th><th>Type</th><th>Message</th><th>Conf</th><th>People</th><th>Snapshot</th><th>Clip</th></tr></thead><tbody>{''.join(rows) or '<tr><td colspan="7">No events yet.</td></tr>'}</tbody></table></div></section></body></html>"""
    out = BASE_DIR / "roomsentry_dashboard_static.html"
    out.write_text(html_text, encoding="utf-8")
    webbrowser.open(out.as_uri())
    print(f"Live dashboard was not running, so opened static dashboard: {out}")


def main():
    config = load_config()
    if not try_open_live_dashboard(config):
        open_static_dashboard(config)


if __name__ == "__main__":
    main()
