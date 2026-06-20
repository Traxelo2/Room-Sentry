# Privacy Zones

Privacy zones hide sensitive parts of the camera frame before media is stored or displayed in the dashboard.

This is different from ignore zones:

- **Ignore zones** stop detections from counting in a region.
- **Privacy zones** blur or black out a region in previews, snapshots, and clips.

## Basic percentage zone

```json
"privacy_zones": [
  {
    "name": "bed area",
    "x1": 0.0,
    "y1": 0.0,
    "x2": 0.35,
    "y2": 1.0,
    "mode": "blur"
  }
]
```

Coordinates between `0.0` and `1.0` are treated as percentages of the frame.

## Pixel zone

```json
"privacy_zones": [
  {
    "name": "monitor",
    "x1": 100,
    "y1": 80,
    "x2": 420,
    "y2": 280,
    "mode": "blackout"
  }
]
```

Coordinates larger than `1.0` are treated as pixels.

## Modes

`blur` softly hides the region. `blackout` fully blacks it out. The older `black` value is still accepted for compatibility.

## Defaults

These are enabled by default:

```json
"apply_privacy_zones_to_preview": true,
"apply_privacy_zones_to_snapshots": true,
"apply_privacy_zones_to_clips": true
```

Leave them enabled if you plan to send snapshots to Discord, Telegram, or any webhook.
