# Open Source Launch Pack

## Repo name

`roomsentry`

## Description

Local-first webcam room watcher with person detection, alerts, and a private dashboard.

## Topics

```text
python opencv yolo webcam security-camera local-first privacy dashboard home-automation
```

## First GitHub release title

`RoomSentry v1.4.0 — first open-source alpha`

## Release notes

```markdown
RoomSentry is now open source.

This first alpha includes local YOLO person detection, armed/disarmed mode, event history, snapshots/clips, optional alerts, a localhost dashboard, config migration, diagnostics, and Windows/Linux launch scripts.

Privacy-first defaults:
- camera feed stays local unless an external alert is configured
- dashboard binds to 127.0.0.1 by default
- real config, logs, snapshots, clips, and runtime files are ignored by Git

This is alpha software. Expect rough edges, especially around camera/device compatibility.
```

## Launch post

```markdown
I open-sourced RoomSentry — a local-first webcam room watcher built with Python, OpenCV, and YOLO.

It detects when a person enters your own room/workspace, logs local events, can save snapshots/clips, and has optional Discord/Telegram/ntfy/webhook alerts. The dashboard runs locally at 127.0.0.1 by default.

No face recognition. No cloud feed by default. Built for permission-based personal monitoring and tinkering.

Looking for contributors/testers for Windows/Linux camera compatibility, dashboard improvements, alert plugins, docs, and privacy-first feature ideas.
```

## First pinned issue

Title: `Welcome: roadmap and first contributor tasks`

Body:

```markdown
Thanks for checking out RoomSentry.

This project is an alpha local-first webcam room watcher. The goal is a useful, privacy-respecting tool for monitoring your own room/workspace with permission.

Good first areas:
- test Windows camera setup
- test Linux camera setup
- improve dashboard styling
- add screenshot docs
- add alert plugin tests
- improve config validation
- refactor detector/alerts into modules

Please read `docs/PRIVACY.md`, `CONTRIBUTING.md`, and `SECURITY.md` before contributing.
```
