#!/usr/bin/env python3
"""
Contract Ghost — Master Launcher
Starts both backend (FastAPI) and frontend (Vite) in parallel.
Usage: python run.py
"""
import os
import sys
import subprocess
import threading
import signal
import time
from pathlib import Path

# ─── Config ───────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
BACKEND_PORT = 8000
FRONTEND_PORT = 5173

# ANSI colours
BLUE = "\033[94m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


def banner():
    print(f"""
{BOLD}╔══════════════════════════════════════╗
║        👻  Contract Ghost           ║
║  Ghost clause detection for legal   ║
║  documents. Not legal advice.       ║
╚══════════════════════════════════════╝{RESET}
""")


def log(prefix: str, color: str, msg: str):
    print(f"{color}[{prefix}]{RESET} {msg}", flush=True)


def kill_port(port: int):
    """Kill any process listening on the given port (cross-platform)."""
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                f'netstat -ano | findstr :{port}',
                shell=True, capture_output=True, text=True
            )
            for line in result.stdout.splitlines():
                parts = line.strip().split()
                if parts and parts[-1].isdigit():
                    subprocess.run(f"taskkill /PID {parts[-1]} /F", shell=True,
                                   capture_output=True)
        else:
            subprocess.run(
                f"lsof -ti:{port} | xargs kill -9 2>/dev/null || true",
                shell=True
            )
    except Exception:
        pass


def check_env():
    """Check system environment or .env file for a valid GEMINI_API_KEY."""
    
    # 1. First, check if it's already in the system environment variables (os)
    os_key = os.environ.get("GEMINI_API_KEY")
    if os_key and os_key != "your_key_here" and os_key.strip() != "":
        print(f"{GREEN}✓  GEMINI_API_KEY found in system environment variables{RESET}")
        return  # Key is valid, we can safely exit the check early!

    # 2. Fallback: If not in os, look for the .env file
    env_file = BACKEND_DIR / ".env"
    if not env_file.exists():
        print(f"{YELLOW}⚠  No .env file found at backend/.env and not found in system OS.{RESET}")
        print(f"   Creating template — please fill in your GEMINI_API_KEY:\n")
        env_file.write_text("GEMINI_API_KEY=your_key_here\n")
        print(f"   {BOLD}backend/.env created.{RESET}")
        print(f"   Edit it with your API key, or set it in your OS, then re-run.\n")
        sys.exit(1)

    # 3. If .env exists, check its content
    env_content = env_file.read_text()
    if "your_key_here" in env_content or "GEMINI_API_KEY=" not in env_content:
        print(f"{RED}✕  GEMINI_API_KEY is missing or invalid in both system OS and backend/.env{RESET}")
        print(f"   Get your key at: https://aistudio.google.com/app/apikey")
        sys.exit(1)

    print(f"{GREEN}✓  .env file found with GEMINI_API_KEY{RESET}")


def install_backend():
    log("BACKEND", BLUE, "Installing Python dependencies...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        log("BACKEND", RED, f"pip install failed:\n{result.stderr}")
        sys.exit(1)
    log("BACKEND", BLUE, "Dependencies ready.")


def install_frontend():
    node_modules = FRONTEND_DIR / "node_modules"
    if not node_modules.exists():
        log("FRONTEND", GREEN, "Installing npm dependencies...")
        result = subprocess.run(
            ["npm", "install"],
            cwd=FRONTEND_DIR,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            log("FRONTEND", RED, f"npm install failed:\n{result.stderr}")
            sys.exit(1)
        log("FRONTEND", GREEN, "npm dependencies ready.")


def stream_output(proc, prefix: str, color: str):
    """Stream subprocess output with colored prefix."""
    try:
        for line in iter(proc.stdout.readline, ""):
            if line:
                print(f"{color}[{prefix}]{RESET} {line.rstrip()}", flush=True)
    except (ValueError, OSError):
        pass


processes: list[subprocess.Popen] = []


def start_backend():
    log("BACKEND", BLUE, f"Starting FastAPI on http://localhost:{BACKEND_PORT}")
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--reload",
            "--port", str(BACKEND_PORT),
            "--host", "0.0.0.0",
            "--log-level", "warning",
        ],
        cwd=BACKEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    processes.append(proc)
    t = threading.Thread(target=stream_output, args=(proc, "BACKEND", BLUE), daemon=True)
    t.start()
    return proc


def start_frontend():
    log("FRONTEND", GREEN, f"Starting Vite on http://localhost:{FRONTEND_PORT}")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    proc = subprocess.Popen(
        [npm_cmd, "run", "dev", "--", "--port", str(FRONTEND_PORT)],
        cwd=FRONTEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    processes.append(proc)
    t = threading.Thread(target=stream_output, args=(proc, "FRONTEND", GREEN), daemon=True)
    t.start()
    return proc


def shutdown(signum=None, frame=None):
    print(f"\n{YELLOW}Shutting down...{RESET}")
    for proc in processes:
        try:
            proc.terminate()
        except Exception:
            pass
    time.sleep(0.5)
    for proc in processes:
        try:
            proc.kill()
        except Exception:
            pass
    sys.exit(0)


if __name__ == "__main__":
    banner()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    log("SETUP", YELLOW, f"Freeing ports {BACKEND_PORT} and {FRONTEND_PORT}...")
    kill_port(BACKEND_PORT)
    kill_port(FRONTEND_PORT)

    check_env()
    install_backend()
    install_frontend()

    backend_proc = start_backend()

    # Brief pause to let backend boot before frontend tries to proxy
    time.sleep(2)

    frontend_proc = start_frontend()

    log("LAUNCHER", YELLOW, f"""
  {BOLD}Contract Ghost is running!{RESET}
  Frontend → http://localhost:{FRONTEND_PORT}
  Backend  → http://localhost:{BACKEND_PORT}
  API Docs → http://localhost:{BACKEND_PORT}/docs

  Press {BOLD}Ctrl+C{RESET} to stop both servers.
""")

    # Keep alive — wait for either process to exit
    while True:
        if backend_proc.poll() is not None:
            log("BACKEND", RED, "Backend exited unexpectedly.")
            shutdown()
        if frontend_proc.poll() is not None:
            log("FRONTEND", RED, "Frontend exited unexpectedly.")
            shutdown()
        time.sleep(1)
