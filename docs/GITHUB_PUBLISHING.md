# Publishing to GitHub

## 1. Create the repository

Create a new GitHub repository named something like:

```text
roomsentry
```

Recommended settings:

- Public repository
- Do not initialise with README, license, or `.gitignore` because this package already includes them
- Enable Issues
- Enable Discussions if you want community ideas/support
- Enable GitHub Security Advisories

## 2. Push the code

From this folder:

```bash
git init
git add .
git commit -m "Initial open-source RoomSentry release"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/roomsentry.git
git push -u origin main
```

## 3. Check before publishing

Run:

```bash
git status
git ls-files | grep -E "config.json|snapshots|clips|logs|events|runtime|\.pt|\.mp4|\.jpg|\.png"
```

The second command should not show private runtime data. It may show docs images in the future, which is fine if they are intentionally public.

## 4. Add repository settings

Suggested About section:

```text
Local-first webcam room watcher with person detection, alerts, and a private dashboard.
```

Suggested topics:

```text
python opencv yolo webcam security-camera local-first privacy dashboard home-automation
```

## 5. First release

Create a GitHub release:

- Tag: `v1.4.0`
- Title: `RoomSentry v1.4.0 - Local Dashboard Alpha`
- Mention this is alpha software
- Mention that users should use it only with permission and keep the dashboard local/private
- Attach the clean source zip if wanted
