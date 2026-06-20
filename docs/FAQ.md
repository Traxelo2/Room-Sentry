# FAQ

## Is RoomSentry a security system?

No. It is an experimental local-first room watcher for personal projects and tinkering. Do not rely on it as your only safety/security system.

## Does it upload my camera feed?

No, not by default. The camera feed stays local unless you configure external alerts. Some alert integrations may send a snapshot if enabled.

## Does it use face recognition?

No. RoomSentry detects whether a person is present. It does not identify people.

## Can I use it in shared spaces?

Only with clear permission from the people affected and only where local law allows it.

## Why YOLOv8?

It is easy to install, widely used, and good enough for a simple alpha. Future versions may support other detector backends.

## Can an 8B local model run this?

The detector does not need an 8B language model. YOLO/OpenCV handles the vision part. A local LLM could be added later for event summaries, but it is optional and heavier.
