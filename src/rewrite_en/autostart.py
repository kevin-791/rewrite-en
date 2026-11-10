"""Start rewrite-en at login.

Windows: a hidden-window .vbs launcher in the user's Startup folder (shell:startup).
macOS:   ~/Library/LaunchAgents/com.rewrite-en.plist with RunAtLoad, loaded with
         `launchctl bootstrap gui/$(id -u)`.
"""

from __future__ import annotations

import os
import plistlib
import subprocess
import sys
from pathlib import Path

from rewrite_en.config import log_dir

LABEL = "com.rewrite-en"


def _windows_startup_dir() -> Path:
    return Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def _windows_launcher() -> Path:
    return _windows_startup_dir() / "rewrite-en.vbs"


def _pythonw() -> Path:
    exe = Path(sys.executable)
    candidate = exe.with_name("pythonw.exe")
    return candidate if candidate.exists() else exe


def _mac_plist() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def _launchctl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["launchctl", *args], capture_output=True, text=True)


def install() -> str:
    if sys.platform == "win32":
        launcher = _windows_launcher()
        launcher.parent.mkdir(parents=True, exist_ok=True)
        cmd = f'""{_pythonw()}"" -m rewrite_en run'
        # Run with window style 0 (hidden), don't wait.
        launcher.write_text(
            f'CreateObject("WScript.Shell").Run "{cmd}", 0, False\r\n', encoding="utf-8"
        )
        return f"Installed {launcher}. rewrite-en will start at next login."

    if sys.platform == "darwin":
        plist = _mac_plist()
        logs = log_dir()
        logs.mkdir(parents=True, exist_ok=True)
        plist.parent.mkdir(parents=True, exist_ok=True)
        with plist.open("wb") as fh:
            plistlib.dump(
                {
                    "Label": LABEL,
                    "ProgramArguments": [sys.executable, "-m", "rewrite_en", "run"],
                    "RunAtLoad": True,
                    "KeepAlive": {"SuccessfulExit": False},
                    "ProcessType": "Interactive",
                    "StandardOutPath": str(logs / "launchd.out.log"),
                    "StandardErrorPath": str(logs / "launchd.err.log"),
                },
                fh,
            )
        domain = f"gui/{os.getuid()}"
        _launchctl("bootout", f"{domain}/{LABEL}")  # ignore "not loaded"
        res = _launchctl("bootstrap", domain, str(plist))
        if res.returncode != 0:
            raise RuntimeError(f"launchctl bootstrap failed: {res.stderr.strip()}")
        real = os.path.realpath(sys.executable)
        return (
            f"Installed and started {plist}.\n"
            "Grant Accessibility and Input Monitoring (System Settings > Privacy & Security) to:\n"
            f"  {real}\n"
            "then run `rewrite-en install-autostart` again (or log out and back in)."
        )

    raise RuntimeError(f"Autostart is not supported on {sys.platform}")


def uninstall() -> str:
    if sys.platform == "win32":
        launcher = _windows_launcher()
        if launcher.exists():
            launcher.unlink()
            return f"Removed {launcher}. (A running copy keeps running until logout.)"
        return "Autostart was not installed."

    if sys.platform == "darwin":
        plist = _mac_plist()
        _launchctl("bootout", f"gui/{os.getuid()}/{LABEL}")
        if plist.exists():
            plist.unlink()
            return f"Stopped and removed {plist}."
        return "Autostart was not installed."

    raise RuntimeError(f"Autostart is not supported on {sys.platform}")
