# Visual Zone Editor

RoomSentry v1.6 adds a browser-based zone editor to the local dashboard.

Open the dashboard at:

```text
http://127.0.0.1:8765
```

Then use **Visual Zone Editor** under the camera preview.

## Zone types

### Ignore zone

Ignore zones stop detections from counting when the centre point of a detected person box is inside the zone.

Good uses:

- TV reflections
- windows
- posters
- moving curtains
- an area outside the room that the camera can see

### Privacy zone

Privacy zones hide sensitive areas before frames are shown or stored.

Privacy zones are applied to:

- dashboard preview
- saved snapshots
- saved clips

Modes:

- `blur` — soft blur over the selected area
- `blackout` — fully black rectangle over the selected area

Good uses:

- bed area
- monitor/screen
- mirror
- shared-space area
- personal documents

## How to draw a zone

1. Start RoomSentry and the dashboard.
2. Wait for the latest camera preview to appear.
3. Choose `Ignore zone` or `Privacy zone`.
4. Enter a name such as `window`, `bed`, `monitor`, or `door`.
5. Drag a rectangle on the preview.
6. Click **Save Zones**.

RoomSentry writes the zones to `config.json`, creates a timestamped config backup, and queues a config reload.

## Storage format

Coordinates are normalized from `0.0` to `1.0`, so they still work if the camera resolution changes.

Example:

```json
"privacy_zones": [
  {
    "name": "monitor",
    "x1": 0.55,
    "y1": 0.12,
    "x2": 0.95,
    "y2": 0.62,
    "mode": "blackout"
  }
]
```

## Safety note

Do not rely on zones to make secret monitoring acceptable. Only run cameras where you have the right to do so. Privacy zones are a safety layer, not a legal bypass.
