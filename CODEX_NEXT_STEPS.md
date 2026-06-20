# Codex Prompt: Install and harden RoomSentry Local

You are Codex working on my local machine. Set up this project safely.

Goal:
Create and run a local webcam person-detection alert system called RoomSentry Local.

Constraints:
- Keep camera processing local.
- Do not upload footage anywhere except Discord if I explicitly set a webhook in config.json.
- Do not add cloud services.
- Do not add face recognition.
- Do not identify people by name.
- Do not run anything hidden or persistent without telling me.
- Do not bypass OS permissions.
- Keep all secrets out of git.

Tasks:
1. Inspect the project files.
2. Create a Python virtual environment.
3. Install requirements.
4. Copy config.example.json to config.json if missing.
5. Confirm camera_index works; if not, try 1 and 2.
6. Run room_sentry.py.
7. Verify:
   - Webcam opens.
   - Person detection boxes appear.
   - Pressing q quits.
   - Snapshots save to snapshots/.
   - Logs save to logs/.
8. Optional:
   - If Ollama is installed, set use_ollama true and test with llama3.1:8b or qwen2.5:3b.
   - If Discord webhook is added, send one test alert.

Safety:
- Never expose the Discord webhook.
- Never commit config.json if it contains a webhook.
- Never add facial recognition.
- Never make legal/safety claims beyond “local alert system”.
- Add clear comments for any changes.

When done, report:
- What command I should use to run it.
- Whether camera worked.
- Whether YOLO downloaded.
- Whether alerts/logs/snapshots worked.
