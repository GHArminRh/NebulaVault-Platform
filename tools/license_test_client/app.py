"""Small desktop smoke-test client for Nebula Vault's Django licensing API.

This is a development/testing utility, not the production Nebula Vault client.
Uses only Python's standard library (Tkinter + urllib).
"""
from __future__ import annotations

import json
import os
import platform
import threading
import uuid
import urllib.error
import urllib.request
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

APP_VERSION = "0.1.0"
API_PATHS = {
    "activate": "/api/licensing/activate/",
    "validate": "/api/licensing/validate/",
    "deactivate": "/api/licensing/deactivate/",
}


def state_dir() -> Path:
    root = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    base = Path(root) if root else Path.home() / ".config"
    path = base / "NebulaVaultLicenseTest"
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_fingerprint() -> str:
    path = state_dir() / "device-id.txt"
    try:
        value = path.read_text(encoding="utf-8").strip()
        if len(value) >= 8:
            return value
    except OSError:
        pass
    value = str(uuid.uuid4())
    path.write_text(value, encoding="utf-8")
    return value


class LicenseTester(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Nebula Vault · License Test Client")
        self.geometry("790x700")
        self.minsize(700, 620)
        self.configure(bg="#0b1220")
        self.fingerprint = load_fingerprint()
        self._build_ui()

    def _build_ui(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background="#0b1220")
        style.configure("Panel.TFrame", background="#111c2f")
        style.configure("TLabel", background="#0b1220", foreground="#e7edf7", font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background="#111c2f", foreground="#9aaac2", font=("Segoe UI", 9))
        style.configure("Heading.TLabel", background="#0b1220", foreground="#f3f7ff", font=("Segoe UI", 19, "bold"))
        style.configure("Sub.TLabel", background="#0b1220", foreground="#9aaac2", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10), padding=(12, 8))
        style.configure("Accent.TButton", background="#2c7a67", foreground="#ffffff")
        style.map("Accent.TButton", background=[("active", "#36947c"), ("disabled", "#354457")])
        style.configure("TEntry", padding=8)
        style.configure("TLabelframe", background="#111c2f", foreground="#dbe7f7")
        style.configure("TLabelframe.Label", background="#111c2f", foreground="#dbe7f7", font=("Segoe UI", 10, "bold"))

        outer = ttk.Frame(self, padding=22)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="License Test Client", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(
            outer,
            text="A lightweight desktop utility for testing the Django licensing API",
            style="Sub.TLabel",
        ).pack(anchor="w", pady=(4, 18))

        config = ttk.Frame(outer, style="Panel.TFrame", padding=16)
        config.pack(fill="x", pady=(0, 12))
        ttk.Label(config, text="Server base URL").grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.url_var = tk.StringVar(value="http://127.0.0.1:8000")
        ttk.Entry(config, textvariable=self.url_var).grid(row=1, column=0, sticky="ew", padx=(0, 12))
        ttk.Label(config, text="Example: http://127.0.0.1:8000", style="Muted.TLabel").grid(
            row=2, column=0, sticky="w", pady=(4, 0)
        )
        config.columnconfigure(0, weight=1)

        key_frame = ttk.Frame(outer, style="Panel.TFrame", padding=16)
        key_frame.pack(fill="x", pady=(0, 12))
        ttk.Label(key_frame, text="License key").grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.key_var = tk.StringVar()
        self.key_entry = ttk.Entry(key_frame, textvariable=self.key_var)
        self.key_entry.grid(row=1, column=0, sticky="ew", padx=(0, 12))
        ttk.Button(key_frame, text="Paste", command=self._paste_key).grid(row=1, column=1, sticky="ew")
        key_frame.columnconfigure(0, weight=1)

        device = ttk.Frame(outer, style="Panel.TFrame", padding=16)
        device.pack(fill="x", pady=(0, 12))
        ttk.Label(device, text="Device fingerprint", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(device, text=self.fingerprint, background="#111c2f", foreground="#dbe7f7").grid(
            row=1, column=0, sticky="w", pady=(5, 8)
        )
        ttk.Label(
            device,
            text=f"Device name: {platform.node() or 'Unknown'}    •    Client version: {APP_VERSION}",
            style="Muted.TLabel",
        ).grid(row=2, column=0, sticky="w")
        ttk.Label(
            device,
            text="The fingerprint is stable between runs and is stored locally; it is not a real hardware ID.",
            style="Muted.TLabel",
        ).grid(row=3, column=0, sticky="w", pady=(5, 0))

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(0, 12))
        self.buttons = []
        for label, action, accent in [
            ("Activate device", "activate", True),
            ("Validate license", "validate", False),
            ("Deactivate device", "deactivate", False),
        ]:
            btn = ttk.Button(actions, text=label, command=lambda a=action: self._request(a),
                             style="Accent.TButton" if accent else "TButton")
            btn.pack(side="left", padx=(0, 8))
            self.buttons.append(btn)

        self.status_var = tk.StringVar(value="Ready · Enter a license key to begin.")
        status = ttk.Label(outer, textvariable=self.status_var, style="Sub.TLabel")
        status.pack(anchor="w", pady=(0, 8))

        result_frame = ttk.LabelFrame(outer, text="API response", padding=10)
        result_frame.pack(fill="both", expand=True)
        self.output = tk.Text(
            result_frame, height=10, wrap="word", bg="#080e19", fg="#c9d8eb",
            insertbackground="#ffffff", relief="flat", borderwidth=0,
            font=("Consolas", 10), padx=10, pady=10,
        )
        scrollbar = ttk.Scrollbar(result_frame, orient="vertical", command=self.output.yview)
        self.output.configure(yscrollcommand=scrollbar.set)
        self.output.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._show_json({"info": "Choose Activate, Validate, or Deactivate to call the API."})

        footer = ttk.Label(
            outer,
            text="TEST TOOL ONLY — do not use as a production licensing client.",
            style="Sub.TLabel",
        )
        footer.pack(anchor="w", pady=(10, 0))

    def _paste_key(self) -> None:
        try:
            self.key_var.set(self.clipboard_get().strip())
        except tk.TclError:
            messagebox.showinfo("Clipboard", "No text is available on the clipboard.")

    def _show_json(self, data: dict) -> None:
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", json.dumps(data, indent=2, ensure_ascii=False))
        self.output.configure(state="disabled")

    def _request(self, action: str) -> None:
        base = self.url_var.get().strip().rstrip("/")
        key = self.key_var.get().strip()
        if not base.startswith(("http://", "https://")):
            messagebox.showerror("Invalid URL", "Enter a base URL beginning with http:// or https://.")
            return
        if not key:
            messagebox.showwarning("License key required", "Enter a license key issued from the admin panel.")
            self.key_entry.focus_set()
            return

        payload = {
            "license_key": key,
            "device_fingerprint": self.fingerprint,
            "device_name": platform.node() or "Desktop test device",
            "app_version": APP_VERSION,
        }
        self.status_var.set(f"Sending {action} request…")
        for button in self.buttons:
            button.configure(state="disabled")
        threading.Thread(target=self._worker, args=(action, base, payload), daemon=True).start()

    def _worker(self, action: str, base: str, payload: dict) -> None:
        url = base + API_PATHS[action]
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        status_code = None
        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                status_code = response.status
                raw = response.read(1024 * 1024).decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            status_code = exc.code
            raw = exc.read(1024 * 1024).decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            self.after(0, self._finish, action, None, {
                "ok": False, "code": "connection_error",
                "message": f"Could not reach the server: {exc}",
            })
            return

        try:
            data = json.loads(raw)
            if not isinstance(data, dict):
                data = {"raw_response": data}
        except json.JSONDecodeError:
            data = {"raw_response": raw}
        data["_http_status"] = status_code
        self.after(0, self._finish, action, status_code, data)

    def _finish(self, action: str, status_code: int | None, data: dict) -> None:
        for button in self.buttons:
            button.configure(state="normal")
        self._show_json(data)
        if data.get("ok"):
            self.status_var.set(f"Success · {action} completed (HTTP {status_code}).")
        else:
            self.status_var.set(f"Request rejected or failed · {data.get('code', 'unknown')} (HTTP {status_code or '—'}).")


if __name__ == "__main__":
    LicenseTester().mainloop()
