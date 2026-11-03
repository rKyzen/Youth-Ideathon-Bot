"""
Youth Ideathon Bot - Windows Installer
--------------------------------------
Checks the machine for all required dependencies and installs any that are
missing, then launches the application like a normal Windows app.

Dependency strategy:
  1. If a real system Python is available, verify/install the Python packages
     required to run from source (fastapi, uvicorn, jinja2, beautifulsoup4,
     playwright) and the Playwright Chromium runtime.
  2. Launch YouthIdeathonBot.exe (self-contained GUI build) when it is present
     next to this installer, otherwise fall back to running app.py with Python.
  3. Verify Google Chrome is available (the automation uses channel="chrome").
"""

import os
import shutil
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

APP_NAME = "Youth Ideathon Bot"
APP_VERSION = "2.1.0"
PYTHON_MIN_VERSION = (3, 10)

REQUIRED_PACKAGES = [
    # (pip package name, importable module name)
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn"),
    ("jinja2", "jinja2"),
    ("beautifulsoup4", "bs4"),
    ("playwright", "playwright"),
]


def base_dir() -> Path:
    """Folder the installer lives in (works frozen and from source)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


BASE_DIR = base_dir()


def banner(step: str):
    print()
    print(f"--- {step} ---")


def find_system_python():
    """Locate a real Python interpreter (never sys.executable when frozen)."""
    candidates = []

    if not getattr(sys, "frozen", False):
        candidates.append([sys.executable])

    # Windows Python launcher
    py_launcher = shutil.which("py")
    if py_launcher:
        for args in (["-3"], ["-3.12"], ["-3.11"], ["-3.10"]):
            candidates.append([py_launcher, *args])

    for name in ("python", "python3"):
        found = shutil.which(name)
        if found:
            candidates.append([found])

    # Validate each candidate; return the first real interpreter >= 3.10.
    for parts in candidates:
        try:
            probe = subprocess.run(
                [*parts, "-c", "import sys; print(sys.version_info[:2])"],
                capture_output=True, text=True, timeout=15
            )
            if probe.returncode != 0:
                continue
            text = probe.stdout.strip().strip("()")
            major, minor = [int(x) for x in text.split(",")]
            if (major, minor) >= PYTHON_MIN_VERSION:
                return parts
        except Exception:
            continue
    return None


def run_python(python_cmd, args, timeout=600):
    """Run a command using the detected Python interpreter."""
    return subprocess.run(
        [*python_cmd, *args],
        capture_output=True, text=True, timeout=timeout, cwd=str(BASE_DIR)
    )


def ensure_python_dependencies(python_cmd):
    """Install missing Python packages and Playwright browsers."""
    if not python_cmd:
        print("[i] No system Python found.")
        print("    This is OK if you are using the bundled YouthIdeathonBot.exe.")
        print("    Python is only required for running from source / CLI mode.")
        return False

    print(f"[+] Found Python: {' '.join(python_cmd)}")

    missing = []
    for pip_name, module_name in REQUIRED_PACKAGES:
        probe = run_python(
            python_cmd,
            ["-c", f"import importlib; importlib.import_module('{module_name}')"],
            timeout=60,
        )
        if probe.returncode != 0:
            missing.append(pip_name)
        else:
            print(f"    {pip_name}: already installed")

    if missing:
        print(f"[*] Installing missing packages: {', '.join(missing)}")
        result = run_python(
            python_cmd,
            ["-m", "pip", "install", "--upgrade", *missing]
        )
        if result.returncode == 0:
            print("[+] Python packages installed successfully.")
        else:
            print("[-] Package installation reported an error:")
            print((result.stderr or result.stdout or "")[:800])
            return False
    else:
        print("[+] All Python packages are already installed.")

    # Playwright Chromium (used by the portal automation)
    print("[*] Ensuring Playwright Chromium browser is installed...")
    result = run_python(python_cmd, ["-m", "playwright", "install", "chromium"], timeout=900)
    if result.returncode == 0:
        print("[+] Playwright Chromium ready.")
    else:
        print("[!] Playwright browser install warning (Chrome fallback will be used).")

    return True


def find_chrome():
    """Return the Chrome executable path if installed."""
    candidates = [
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
    ]
    for path in candidates:
        if path and path.exists():
            return path

    # Registry fallback
    try:
        import winreg
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                key = winreg.OpenKey(hive, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe")
                value, _ = winreg.QueryValueEx(key, "")
                if value and Path(value).exists():
                    return Path(value)
            except OSError:
                continue
    except Exception:
        pass
    return None


def ensure_chrome():
    """Warn (and offer the download page) when Chrome is missing."""
    chrome = find_chrome()
    if chrome:
        print(f"[+] Google Chrome found: {chrome}")
        return True

    print("[!] Google Chrome was not detected.")
    print("    The automation launches Chrome through Playwright. Install Chrome from:")
    print("    https://www.google.com/chrome/")
    try:
        answer = input("Open the Chrome download page now? [y/N]: ").strip().lower()
    except Exception:
        answer = "n"
    if answer.startswith("y"):
        webbrowser.open("https://www.google.com/chrome/")
    return False


def wait_for_dashboard(timeout=60):
    """Poll the local dashboard until it responds or the timeout expires."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                "http://127.0.0.1:8000/api/status", timeout=1.5
            ) as response:
                if response.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False


def launch_app():
    """Start the GUI application."""
    bundled_exe = BASE_DIR / "YouthIdeathonBot.exe"
    if bundled_exe.exists():
        print(f"[*] Starting {bundled_exe.name} ...")
        subprocess.Popen([str(bundled_exe)], cwd=str(BASE_DIR))
    else:
        python_cmd = find_system_python()
        app_py = BASE_DIR / "app.py"
        if python_cmd and app_py.exists():
            print("[*] Starting app.py with Python ...")
            subprocess.Popen([*python_cmd, str(app_py)], cwd=str(BASE_DIR))
        else:
            print("[-] Could not find YouthIdeathonBot.exe or a Python installation to run app.py.")
            print("    Place YouthIdeathonBot.exe next to this installer and run it again.")
            return False

    print("[*] Waiting for the dashboard to respond ...")
    if wait_for_dashboard():
        print("[+] Dashboard is running at http://localhost:8000")
        return True

    print("[!] The app was started but the dashboard did not respond within 60 seconds.")
    print("    Try running YouthIdeathonBot.exe manually to see the error.")
    return False


def main():
    print("=" * 64)
    print(f"  {APP_NAME} v{APP_VERSION} - Installer")
    print("=" * 64)
    print(f"Install location: {BASE_DIR}")

    banner("1/4  Checking system Python")
    python_cmd = find_system_python()
    if python_cmd:
        print(f"[+] Python detected: {' '.join(python_cmd)}")
    else:
        print("[i] Python not detected (not required for the bundled GUI app).")

    banner("2/4  Checking and installing dependencies")
    ensure_python_dependencies(python_cmd)

    banner("3/4  Checking Google Chrome")
    ensure_chrome()

    banner("4/4  Launching the application")
    ok = launch_app()

    print()
    print("=" * 64)
    print("  Installation / dependency check complete." if ok else "  Finished with warnings.")
    print("=" * 64)

    if not getattr(sys, "frozen", False):
        try:
            input("Press Enter to exit...")
        except Exception:
            pass


if __name__ == "__main__":
    main()