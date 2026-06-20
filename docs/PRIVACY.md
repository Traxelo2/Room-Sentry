# Privacy Guide

RoomSentry is designed to be local-first.

## What stays local by default

- Camera frames
- Detection results
- Event database
- Snapshots
- Clips
- Runtime status
- Dashboard commands

## What can leave your machine

Only if you configure it, RoomSentry may send alert text or snapshots to:

- Discord webhook
- Telegram bot/chat
- ntfy topic
- Generic webhook URL

## What RoomSentry does not do

- No face recognition
- No identity tracking
- No cloud account
- No cloud storage
- No analytics service
- No automatic upload of footage by default

## Safe use recommendations

- Use it only in your own room or workspace
- Tell people if a camera is monitoring an area they may enter
- Do not point it at shared/private spaces without permission
- Keep the dashboard on `127.0.0.1`
- Do not commit real `config.json`
- Auto-delete old snapshots/clips if you do not need them
- Blur saved snapshots if you want lower-risk saved evidence
