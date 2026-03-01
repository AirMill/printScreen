import tkinter as tk
from tkinter import filedialog, messagebox
import pyautogui
import os
import re
import json
import time
from datetime import datetime
import subprocess
import sys

# ----------------------------
# Helpers
# ----------------------------

CONFIG_NAME = "screenshot_app_config.json"


def sanitize_filename(name: str, max_len: int = 120) -> str:
    """Make filename safe across Windows/macOS/Linux."""
    name = name.strip()
    # Replace forbidden characters (Windows especially)
    name = re.sub(r'[<>:"/\\|?*\n\r\t]', "_", name)
    # Collapse whitespace
    name = re.sub(r"\s+", " ", name)
    # Avoid trailing dot/space (Windows)
    name = name.rstrip(". ")
    if not name:
        name = "screenshot"
    return name[:max_len]


def next_available_path(folder: str, base: str, ext: str) -> str:
    """Return a path that doesn't exist, adding _001, _002, ... if needed."""
    folder = os.path.abspath(folder)
    os.makedirs(folder, exist_ok=True)

    candidate = os.path.join(folder, f"{base}{ext}")
    if not os.path.exists(candidate):
        return candidate

    for i in range(1, 10000):
        candidate = os.path.join(folder, f"{base}_{i:03d}{ext}")
        if not os.path.exists(candidate):
            return candidate

    raise RuntimeError("Too many files with the same base name in the folder.")


def open_folder(path: str):
    path = os.path.abspath(path)
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
    except Exception:
        pass


def get_active_window_title() -> str:
    """
    Best-effort active window title.
    - Windows: works if pygetwindow is installed.
    - macOS/Linux: returns empty unless you extend it.
    """
    try:
        if sys.platform.startswith("win"):
            import pygetwindow as gw  # pip install pygetwindow

            title = gw.getActiveWindowTitle()
            return title or ""
    except Exception:
        return ""
    return ""


# ----------------------------
# App
# ----------------------------

class ScreenshotApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Screenshot")
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(True)
        self.root.attributes("-alpha", 0.85)
        self.root.geometry("130x210+120+120")

        # Drag state
        self._drag_start_x = 0
        self._drag_start_y = 0

        # Defaults
        self.save_folder = os.getcwd()
        self.prefix = "screenshot"
        self.use_timestamp = True
        self.timestamp_format = "%Y-%m-%d_%H-%M-%S"
        self.include_window_title = False
        self.image_format = "PNG"  # PNG or JPG
        self.jpg_quality = 90

        self._load_config()

        # UI
        container = tk.Frame(root, bd=1, relief="solid")
        container.pack(fill="both", expand=True)

        self.exit_btn = tk.Button(container, text="Exit", bg="#2b6cb0", fg="white",
                                  width=12, height=2, command=self.exit_app)
        self.exit_btn.pack(pady=(6, 4))

        self.capture_btn = tk.Button(container, text="Capture", bg="#e53e3e", fg="white",
                                     width=12, height=4, command=self.capture_screen)
        self.capture_btn.pack(pady=4)

        self.settings_btn = tk.Button(container, text="Settings", bg="#ecc94b",
                                      width=12, height=2, command=self.open_settings)
        self.settings_btn.pack(pady=(4, 2))

        self.folder_btn = tk.Button(container, text="Open Folder", bg="#48bb78", fg="white",
                                    width=12, height=2, command=lambda: open_folder(self.save_folder))
        self.folder_btn.pack(pady=(2, 6))

        self.status_var = tk.StringVar(value="")
        self.status_lbl = tk.Label(container, textvariable=self.status_var, font=("Segoe UI", 8))
        self.status_lbl.pack(pady=(0, 4))

        # Drag anywhere on widget
        self.root.bind("<ButtonPress-1>", self._start_drag)
        self.root.bind("<B1-Motion>", self._drag_window)

    # ----------------------------
    # Dragging
    # ----------------------------
    def _start_drag(self, event):
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def _drag_window(self, event):
        x = self.root.winfo_pointerx() - self._drag_start_x
        y = self.root.winfo_pointery() - self._drag_start_y
        self.root.geometry(f"+{x}+{y}")

    # ----------------------------
    # Config
    # ----------------------------
    def _config_path(self) -> str:
        # Save config near script if possible, else cwd
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        except Exception:
            base_dir = os.getcwd()
        return os.path.join(base_dir, CONFIG_NAME)

    def _load_config(self):
        path = self._config_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.save_folder = data.get("save_folder", self.save_folder)
            self.prefix = data.get("prefix", self.prefix)
            self.use_timestamp = bool(data.get("use_timestamp", self.use_timestamp))
            self.timestamp_format = data.get("timestamp_format", self.timestamp_format)
            self.include_window_title = bool(data.get("include_window_title", self.include_window_title))
            self.image_format = data.get("image_format", self.image_format)
            self.jpg_quality = int(data.get("jpg_quality", self.jpg_quality))
        except Exception:
            # If config is corrupt, ignore it.
            pass

    def _save_config(self):
        data = {
            "save_folder": self.save_folder,
            "prefix": self.prefix,
            "use_timestamp": self.use_timestamp,
            "timestamp_format": self.timestamp_format,
            "include_window_title": self.include_window_title,
            "image_format": self.image_format,
            "jpg_quality": self.jpg_quality,
        }
        try:
            with open(self._config_path(), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    # ----------------------------
    # Naming
    # ----------------------------
    def _build_base_filename(self) -> str:
        prefix = sanitize_filename(self.prefix)

        parts = [prefix]

        if self.include_window_title:
            title = sanitize_filename(get_active_window_title())
            if title:
                parts.append(title)

        if self.use_timestamp:
            try:
                ts = datetime.now().strftime(self.timestamp_format)
            except Exception:
                ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            parts.append(ts)

        base = "_".join([p for p in parts if p])
        return sanitize_filename(base)

    # ----------------------------
    # Actions
    # ----------------------------
    def open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Settings")
        win.attributes("-topmost", True)
        win.resizable(False, False)
        win.geometry("+160+160")

        frm = tk.Frame(win, padx=10, pady=10)
        frm.pack()

        # Folder
        tk.Label(frm, text="Save folder:").grid(row=0, column=0, sticky="w")
        folder_var = tk.StringVar(value=self.save_folder)
        folder_entry = tk.Entry(frm, textvariable=folder_var, width=40)
        folder_entry.grid(row=1, column=0, columnspan=2, sticky="we", pady=(0, 4))

        def browse():
            folder = filedialog.askdirectory(initialdir=folder_var.get() or os.getcwd())
            if folder:
                folder_var.set(folder)

        tk.Button(frm, text="Browse...", command=browse).grid(row=1, column=2, padx=(6, 0))

        # Prefix
        tk.Label(frm, text="Filename prefix:").grid(row=2, column=0, sticky="w", pady=(8, 0))
        prefix_var = tk.StringVar(value=self.prefix)
        tk.Entry(frm, textvariable=prefix_var, width=25).grid(row=3, column=0, sticky="w")

        # Timestamp
        ts_var = tk.BooleanVar(value=self.use_timestamp)
        tk.Checkbutton(frm, text="Add timestamp", variable=ts_var).grid(row=3, column=1, sticky="w")

        tk.Label(frm, text="Timestamp format:").grid(row=4, column=0, sticky="w", pady=(8, 0))
        tsfmt_var = tk.StringVar(value=self.timestamp_format)
        tk.Entry(frm, textvariable=tsfmt_var, width=25).grid(row=5, column=0, sticky="w")

        tk.Label(frm, text="Example: %Y-%m-%d_%H-%M-%S").grid(row=5, column=1, columnspan=2, sticky="w")

        # Window title
        win_title_var = tk.BooleanVar(value=self.include_window_title)
        tk.Checkbutton(frm, text="Include active window title (Windows best)", variable=win_title_var)\
            .grid(row=6, column=0, columnspan=3, sticky="w", pady=(8, 0))

        # Format
        tk.Label(frm, text="Image format:").grid(row=7, column=0, sticky="w", pady=(10, 0))
        fmt_var = tk.StringVar(value=self.image_format)
        fmt_menu = tk.OptionMenu(frm, fmt_var, "PNG", "JPG")
        fmt_menu.config(width=8)
        fmt_menu.grid(row=8, column=0, sticky="w")

        tk.Label(frm, text="JPG quality (1-95):").grid(row=8, column=1, sticky="w")
        quality_var = tk.IntVar(value=self.jpg_quality)
        quality_spin = tk.Spinbox(frm, from_=1, to=95, textvariable=quality_var, width=6)
        quality_spin.grid(row=8, column=2, sticky="w")

        # Preview
        preview_var = tk.StringVar(value="")
        tk.Label(frm, text="Preview:").grid(row=9, column=0, sticky="w", pady=(12, 0))
        preview_lbl = tk.Label(frm, textvariable=preview_var, wraplength=420, justify="left")
        preview_lbl.grid(row=10, column=0, columnspan=3, sticky="w")

        def refresh_preview(*_):
            temp_prefix = prefix_var.get().strip() or "screenshot"
            temp_use_ts = ts_var.get()
            temp_fmt = tsfmt_var.get().strip() or "%Y-%m-%d_%H-%M-%S"
            temp_title = win_title_var.get()

            parts = [sanitize_filename(temp_prefix)]
            if temp_title:
                t = sanitize_filename(get_active_window_title())
                if t:
                    parts.append(t)
            if temp_use_ts:
                try:
                    parts.append(datetime.now().strftime(temp_fmt))
                except Exception:
                    parts.append(datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))

            base = sanitize_filename("_".join([p for p in parts if p]))
            ext = ".png" if fmt_var.get() == "PNG" else ".jpg"
            preview_var.set(os.path.join(folder_var.get() or "<folder>", f"{base}{ext}"))

        for var in (folder_var, prefix_var, ts_var, tsfmt_var, win_title_var, fmt_var, quality_var):
            try:
                var.trace_add("write", refresh_preview)
            except Exception:
                pass
        refresh_preview()

        # Buttons
        btns = tk.Frame(frm)
        btns.grid(row=11, column=0, columnspan=3, pady=(14, 0), sticky="e")

        def save():
            folder = folder_var.get().strip() or os.getcwd()
            if not os.path.isdir(folder):
                try:
                    os.makedirs(folder, exist_ok=True)
                except Exception:
                    messagebox.showerror("Error", "Cannot create that folder.")
                    return

            self.save_folder = folder
            self.prefix = prefix_var.get().strip() or "screenshot"
            self.use_timestamp = bool(ts_var.get())
            self.timestamp_format = tsfmt_var.get().strip() or "%Y-%m-%d_%H-%M-%S"
            self.include_window_title = bool(win_title_var.get())
            self.image_format = fmt_var.get()
            self.jpg_quality = int(quality_var.get())

            self._save_config()
            win.destroy()

        tk.Button(btns, text="Cancel", command=win.destroy).pack(side="right", padx=(6, 0))
        tk.Button(btns, text="Save", command=save).pack(side="right")

    def capture_screen(self):
        # Briefly hide widget so it doesn't show in screenshot
        self.root.withdraw()
        self.root.update_idletasks()

        time.sleep(0.12)  # tiny delay to ensure it's hidden

        base = self._build_base_filename()
        ext = ".png" if self.image_format == "PNG" else ".jpg"
        filepath = next_available_path(self.save_folder, base, ext)

        try:
            screenshot = pyautogui.screenshot()

            if self.image_format == "PNG":
                screenshot.save(filepath, "PNG")
            else:
                screenshot = screenshot.convert("RGB")
                # Pillow expects quality up to 95 in practice
                q = max(1, min(95, int(self.jpg_quality)))
                screenshot.save(filepath, "JPEG", quality=q)

            self.status_var.set("Saved ✓")
            print(f"Screenshot saved to {filepath}")

        except Exception as e:
            self.status_var.set("Error!")
            messagebox.showerror("Capture failed", str(e))

        finally:
            self.root.deiconify()
            self.root.update_idletasks()

    def exit_app(self):
        self._save_config()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ScreenshotApp(root)
    root.mainloop()