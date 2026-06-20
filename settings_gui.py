import json
import os
import platform
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"

HELP_TEXT = """
Useful ignore_zones example:
[
  {"name": "window", "x1": 0.70, "y1": 0.00, "x2": 1.00, "y2": 0.45}
]

x/y can be 0-1 ratios, so it works on any camera resolution.
""".strip()


def load_config():
    if not CONFIG_PATH.exists():
        messagebox.showerror("Error", f"{CONFIG_PATH} not found.")
        return {}
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config):
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
    messagebox.showinfo("Success", "Settings saved successfully!")


def open_folder(path: Path):
    path.mkdir(parents=True, exist_ok=True)
    system = platform.system().lower()
    if system == "windows":
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif system == "darwin":
        subprocess.run(["open", str(path)], check=False)
    else:
        subprocess.run(["xdg-open", str(path)], check=False)


def run_script(script_name):
    result = subprocess.run(
        [sys.executable, str(BASE_DIR / script_name)],
        cwd=str(BASE_DIR),
        text=True,
        capture_output=True,
        check=False,
    )
    output = (result.stdout + result.stderr).strip()
    if result.returncode == 0:
        messagebox.showinfo(script_name, output or "Done.")
    else:
        messagebox.showerror(f"{script_name} failed", output or "Unknown error.")


def create_gui():
    config = load_config()
    if not config:
        return

    root = tk.Tk()
    root.title("RoomSentry Settings")
    root.geometry("760x820")

    top = tk.Frame(root)
    top.pack(fill="x", padx=10, pady=8)
    tk.Label(top, text="RoomSentry Settings", font=("Arial", 16, "bold")).pack(side="left")
    tk.Button(top, text="Help", command=lambda: messagebox.showinfo("RoomSentry Help", HELP_TEXT)).pack(side="right")

    canvas = tk.Canvas(root)
    scrollbar = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas)
    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    variables = {}
    original_types = {}
    widgets = {}

    row = 0
    for key, value in config.items():
        original_types[key] = type(value)
        label = tk.Label(scrollable_frame, text=key.replace("_", " ").title(), font=("Arial", 10, "bold"))
        label.grid(row=row, column=0, sticky="nw", padx=10, pady=5)

        if isinstance(value, bool):
            var = tk.BooleanVar(value=value)
            widget = tk.Checkbutton(scrollable_frame, variable=var)
            widget.grid(row=row, column=1, sticky="w", padx=10, pady=5)
            variables[key] = var
        elif isinstance(value, int) and not isinstance(value, bool):
            var = tk.IntVar(value=value)
            widget = tk.Entry(scrollable_frame, textvariable=var, width=34)
            widget.grid(row=row, column=1, sticky="w", padx=10, pady=5)
            variables[key] = var
        elif isinstance(value, float):
            var = tk.DoubleVar(value=value)
            widget = tk.Entry(scrollable_frame, textvariable=var, width=34)
            widget.grid(row=row, column=1, sticky="w", padx=10, pady=5)
            variables[key] = var
        elif isinstance(value, (list, dict)):
            text = tk.Text(scrollable_frame, width=58, height=5)
            text.insert("1.0", json.dumps(value, indent=2))
            text.grid(row=row, column=1, sticky="w", padx=10, pady=5)
            variables[key] = text
            widget = text
        else:
            var = tk.StringVar(value=str(value))
            widget = tk.Entry(scrollable_frame, textvariable=var, width=58)
            widget.grid(row=row, column=1, sticky="w", padx=10, pady=5)
            variables[key] = var

        widgets[key] = widget
        row += 1

    def on_save():
        new_config = {}
        for key, var in variables.items():
            try:
                original_type = original_types.get(key, str)
                if isinstance(var, tk.Text):
                    raw = var.get("1.0", "end").strip()
                    new_config[key] = json.loads(raw) if raw else ([] if original_type is list else {})
                else:
                    new_config[key] = var.get()
            except Exception as e:
                messagebox.showerror("Type Error", f"Invalid input for {key}: {e}")
                return
        save_config(new_config)
        root.destroy()

    def folder_from_var(name, default):
        value = variables.get(name).get() if name in variables and not isinstance(variables[name], tk.Text) else default
        folder = Path(value)
        return folder if folder.is_absolute() else BASE_DIR / folder

    btn_frame = tk.Frame(root)
    btn_frame.pack(side="bottom", fill="x", pady=10, padx=10)

    save_btn = tk.Button(btn_frame, text="Save & Close", command=on_save, bg="#4CAF50", fg="white", font=("Arial", 12, "bold"))
    save_btn.pack(side="top", fill="x", pady=5)

    row1 = tk.Frame(btn_frame)
    row1.pack(fill="x")
    tk.Button(row1, text="Test Alerts", command=lambda: run_script("test_alerts.py"), font=("Arial", 10)).pack(side="left", expand=True, fill="x", padx=2)
    tk.Button(row1, text="Open Dashboard", command=lambda: run_script("open_dashboard.py"), font=("Arial", 10)).pack(side="left", expand=True, fill="x", padx=2)
    tk.Button(row1, text="Open Snapshots", command=lambda: open_folder(folder_from_var("snapshots_dir", "snapshots")), font=("Arial", 10)).pack(side="left", expand=True, fill="x", padx=2)
    tk.Button(row1, text="Open Logs", command=lambda: open_folder(folder_from_var("logs_dir", "logs")), font=("Arial", 10)).pack(side="left", expand=True, fill="x", padx=2)

    row2 = tk.Frame(btn_frame)
    row2.pack(fill="x", pady=(4, 0))
    tk.Button(row2, text="Open Clips", command=lambda: open_folder(folder_from_var("clips_dir", "clips")), font=("Arial", 10)).pack(side="left", expand=True, fill="x", padx=2)
    tk.Button(row2, text="Open Events", command=lambda: open_folder(folder_from_var("events_dir", "events")), font=("Arial", 10)).pack(side="left", expand=True, fill="x", padx=2)

    root.mainloop()


if __name__ == "__main__":
    create_gui()
