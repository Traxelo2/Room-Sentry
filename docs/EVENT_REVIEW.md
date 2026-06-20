# Event Review/Search

RoomSentry v1.8 adds a proper local event review workflow to the dashboard.

Open the dashboard:

```text
http://127.0.0.1:8765
```

Scroll to **Event Review/Search**.

## What you can do

- Search event messages and review notes.
- Filter by event type.
- Filter by date.
- Show only important events.
- Show only false positives.
- Show events with snapshots or clips.
- Mark events as important.
- Mark events as false positives.
- Add short review notes.
- Export the currently visible events as JSON.
- Delete selected event rows.
- Optionally delete selected event media too.
- Generate a daily summary for the selected date.

## Local database migration

The dashboard automatically upgrades older local SQLite event databases by adding:

```text
important
false_positive
review_note
reviewed_at
```

This is local-only and does not upload any data.

## Delete safety

There are two delete buttons:

```text
Delete selected rows
Delete selected + media
```

The first removes only database rows. The second also deletes linked snapshot/clip files from the local RoomSentry folder.

## Recommended workflow

1. Let RoomSentry run for a while.
2. Open Event Review/Search.
3. Filter for today.
4. Mark wrong detections as false positives.
5. Mark useful detections as important.
6. Export visible events if you want a local report.
7. Delete junk events when you are happy.

False-positive marking is currently for review only. A future release can use these marks to tune sensitivity and suggest ignore zones.
