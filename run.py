#!/usr/bin/env python3
"""Starts FINN locally: the API on port 8000 and the web app on http://localhost:3000.

First run creates .venv and installs dependencies. Press Ctrl+C to stop both."""
import os
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
VENV = os.path.join(ROOT, ".venv")
WINDOWS = sys.platform.startswith("win")
PYTHON = os.path.join(VENV, "Scripts" if WINDOWS else "bin", "python.exe" if WINDOWS else "python")
NPM = shutil.which("npm.cmd" if WINDOWS else "npm")


def main():
    if sys.version_info < (3, 10):
        sys.exit("FINN needs Python 3.10 or newer. Try: python3.12 run.py")
    if not NPM:
        sys.exit("npm was not found. Install Node.js 18 or newer from https://nodejs.org")

    # A .venv copied from another computer has no working interpreter, so rebuild it
    if os.path.isdir(VENV) and not os.path.exists(PYTHON):
        shutil.rmtree(VENV)
    if not os.path.isdir(VENV):
        print("Creating .venv and installing backend packages...")
        subprocess.check_call([sys.executable, "-m", "venv", VENV])
        subprocess.check_call([PYTHON, "-m", "pip", "install", "-q", "-r", os.path.join(ROOT, "backend", "requirements.txt")])
    if not os.path.isdir(os.path.join(ROOT, "frontend", "node_modules")):
        print("Installing frontend packages...")
        subprocess.check_call([NPM, "install", "--no-audit", "--no-fund"], cwd=os.path.join(ROOT, "frontend"))
    if not os.path.exists(os.path.join(ROOT, ".env")):
        print("No .env file found, so AI features are off. Add GEMINI_API_KEY=... to .env to turn them on.")

    env = {**os.environ, "PYTHONPATH": os.path.join(ROOT, "backend")}
    procs = [
        subprocess.Popen([PYTHON, "-m", "uvicorn", "finn.main:app", "--port", "8000"], cwd=ROOT, env=env),
        subprocess.Popen([NPM, "run", "dev"], cwd=os.path.join(ROOT, "frontend")),
    ]
    try:
        # The backend can take a minute to load its libraries on a busy machine
        print("Starting the backend...")
        for _ in range(240):
            if any(p.poll() is not None for p in procs):
                break
            try:
                urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=2)
                print("\n  FINN is running at http://localhost:3000  (Ctrl+C to stop)\n")
                break
            except OSError:
                time.sleep(1)
        while all(p.poll() is None for p in procs):
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for p in procs:
            p.terminate()
        for p in procs:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
        print("Stopped.")


if __name__ == "__main__":
    main()
