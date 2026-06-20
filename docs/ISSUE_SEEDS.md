# Suggested Starter Issues

Create these issues after publishing the repo.

## 1. Add real dashboard screenshots

Labels: `docs`, `good first issue`

```markdown
Replace the placeholder SVGs with real privacy-safe screenshots.

Acceptance criteria:
- Dashboard screenshot added
- Timeline/gallery screenshot added
- Any faces/tokens/private room details are blurred or synthetic
- README image links updated if needed
```

## 2. Refactor alerts into an `alerts/` package

Labels: `enhancement`, `alerts`, `help wanted`

```markdown
Move Discord, Telegram, ntfy, webhook, and TTS alert logic out of `room_sentry.py` into a small `alerts/` package.

Acceptance criteria:
- Behaviour remains the same
- Each alert backend has a clear function/class
- Existing config keys keep working
- Compile checks pass
```

## 3. Improve camera diagnostics

Labels: `enhancement`, `windows`, `linux`, `good first issue`

```markdown
Make `doctor.py` more helpful when the camera cannot open.

Acceptance criteria:
- Shows available camera indexes when possible
- Gives Windows and Linux troubleshooting suggestions
- Does not require an actual camera in CI
```

## 4. Add dashboard API tests

Labels: `enhancement`, `dashboard`, `help wanted`

```markdown
Add simple tests for dashboard API endpoints.

Acceptance criteria:
- `/api/state` handles missing runtime files
- `/api/events` handles empty database/logs
- `/api/command` rejects invalid commands
```

## 5. Add a plugin interface proposal

Labels: `enhancement`, `architecture`, `discussion`

```markdown
Design a lightweight plugin interface for future detectors, alerts, and automations.

Acceptance criteria:
- Proposal added to `docs/ARCHITECTURE.md` or a new ADR
- Keeps local-first/privacy-first defaults
- Avoids breaking current config
```
