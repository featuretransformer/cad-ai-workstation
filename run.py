#!/usr/bin/env python3
"""
AI-Native CAD-CAM Workstation — Unified Process Runner.
Launches the full stack (FastAPI Backend, Celery Worker, and Next.js Frontend)
with unified logging, health monitoring, and graceful multi-process termination.

Usage:
    python run.py
    python run.py --no-celery
    python run.py --no-browser
"""
import argparse
import os
import platform
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Fix Windows console encoding crashes (cp1252 / charmap)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"

IS_WINDOWS = platform.system() == "Windows"

# ANSI Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
RESET = "\033[0m"


def log(prefix: str, msg: str, color: str = RESET):
    try:
        sys.stdout.write(f"{color}{BOLD}[{prefix}]{RESET} {msg}\n")
        sys.stdout.flush()
    except UnicodeEncodeError:
        safe_msg = msg.encode("ascii", errors="replace").decode("ascii")
        sys.stdout.write(f"[{prefix}] {safe_msg}\n")
        sys.stdout.flush()


def find_python() -> str:
    """Finds best Python interpreter, prioritizing local backend virtualenv with CAD dependencies."""
    candidates = [
        BACKEND_DIR / (".venv" if not IS_WINDOWS else ".venv/Scripts/python.exe"),
        BACKEND_DIR / ".venv/bin/python",
        ROOT_DIR / (".venv" if not IS_WINDOWS else ".venv/Scripts/python.exe"),
        ROOT_DIR / ".venv/bin/python",
    ]
    for c in candidates:
        if c.exists() and os.access(str(c), os.X_OK if not IS_WINDOWS else os.F_OK):
            # Verify interpreter has core dependencies
            try:
                probe = subprocess.run(
                    [str(c), "-c", "import fastapi; print('ok')"],
                    capture_output=True,
                    text=True,
                    timeout=3,
                )
                if probe.returncode == 0:
                    return str(c)
            except Exception:
                continue

    return sys.executable


def find_npm() -> str:
    """Finds npm executable."""
    cmd = "npm.cmd" if IS_WINDOWS else "npm"
    found = shutil.which(cmd) or shutil.which("npm")
    if not found:
        log("ERROR", "Node.js / npm not found in system PATH. Please install Node.js.", RED)
        sys.exit(1)
    return found


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Checks if a network port is already occupied."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def kill_port(port: int):
    """Terminates any process currently bound to the given port to avoid address conflicts."""
    if not is_port_in_use(port):
        return
    log("CLEANUP", f"Port {port} is occupied by an older process. Freeing port...", YELLOW)
    try:
        if IS_WINDOWS:
            cmd = f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess"
            res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True)
            pids = set(res.stdout.strip().split())
            for pid in pids:
                if pid and pid.isdigit() and int(pid) > 0:
                    subprocess.run(["taskkill", "/F", "/T", "/PID", pid], capture_output=True)
        else:
            subprocess.run(["fuser", "-k", f"{port}/tcp"], capture_output=True)
        time.sleep(1)
    except Exception as e:
        log("WARN", f"Could not automatically clear port {port}: {e}", YELLOW)


def stream_output(proc: subprocess.Popen, prefix: str, color: str):
    """Streams stdout and stderr from child process with color prefix."""
    try:
        for line in iter(proc.stdout.readline, ""):
            if not line:
                break
            clean_line = line.rstrip()
            if clean_line:
                try:
                    sys.stdout.write(f"{color}[{prefix}]{RESET} {clean_line}\n")
                    sys.stdout.flush()
                except UnicodeEncodeError:
                    safe_line = clean_line.encode("ascii", errors="replace").decode("ascii")
                    sys.stdout.write(f"[{prefix}] {safe_line}\n")
                    sys.stdout.flush()
    except Exception:
        pass


def check_environment():
    """Validates configuration and files before launch."""
    env_root = ROOT_DIR / ".env"
    env_backend = BACKEND_DIR / ".env"
    env_example = ROOT_DIR / ".env.example"

    if not env_root.exists() and not env_backend.exists() and env_example.exists():
        log("SYSTEM", "Creating .env from .env.example...", YELLOW)
        shutil.copy(str(env_example), str(env_root))

    if not (FRONTEND_DIR / "node_modules").exists():
        log("SYSTEM", "Installing frontend node dependencies (npm install)...", YELLOW)
        npm = find_npm()
        subprocess.run([npm, "install"], cwd=str(FRONTEND_DIR), check=True)


def main():
    parser = argparse.ArgumentParser(description="Run CAD AI Workstation")
    parser.add_argument("--no-celery", action="store_true", help="Skip launching Celery worker")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open browser")
    parser.add_argument("--backend-port", type=int, default=8000, help="Backend port (default: 8000)")
    parser.add_argument("--frontend-port", type=int, default=3000, help="Frontend port (default: 3000)")
    args = parser.parse_args()

    print(f"""{CYAN}{BOLD}
+-------------------------------------------------------------------+
|               AI-NATIVE CAD-CAM WORKSTATION RUNNER                |
|     FastAPI Backend  *  Celery Worker  *  Next.js 14 Frontend    |
+-------------------------------------------------------------------+{RESET}
""")

    check_environment()

    # Free target ports from previous stale runs
    kill_port(args.backend_port)
    kill_port(args.frontend_port)

    py_bin = find_python()
    npm_bin = find_npm()
    log("SYSTEM", f"Using Python: {py_bin}", GREEN)
    log("SYSTEM", f"Using npm:    {npm_bin}", GREEN)

    # Check database and message broker availability
    pg_active = is_port_in_use(5432)
    redis_active = is_port_in_use(6379)

    log("STATUS", f"PostgreSQL (5432): {'CONNECTED [OK]' if pg_active else 'OFFLINE (Will use fallback)'}", GREEN if pg_active else YELLOW)
    log("STATUS", f"Redis (6379):      {'CONNECTED [OK]' if redis_active else 'OFFLINE (Will use in-process tasks)'}", GREEN if redis_active else YELLOW)

    procs = []

    def shutdown(sig=None, frame=None):
        print("\n")
        log("SYSTEM", "Shutting down all CAD Workstation processes...", YELLOW)
        for name, p in procs:
            if p.poll() is None:
                log("STOP", f"Terminating {name}...", RED)
                try:
                    if IS_WINDOWS:
                        subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
                    else:
                        p.terminate()
                except Exception:
                    pass
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    if not IS_WINDOWS:
        signal.signal(signal.SIGTERM, shutdown)

    # 1. Start FastAPI Backend
    log("START", f"Starting FastAPI backend on port {args.backend_port}...", BLUE)
    backend_env = os.environ.copy()
    backend_env["PYTHONPATH"] = str(BACKEND_DIR)

    backend_cmd = [
        py_bin, "-m", "uvicorn", "main:app",
        "--host", "0.0.0.0",
        "--port", str(args.backend_port),
        "--reload",
    ]
    p_backend = subprocess.Popen(
        backend_cmd,
        cwd=str(BACKEND_DIR),
        env=backend_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    procs.append(("Backend", p_backend))
    t_back = threading.Thread(target=stream_output, args=(p_backend, "BACKEND", BLUE), daemon=True)
    t_back.start()

    # 2. Start Celery Worker (if Redis is active and not disabled)
    start_celery = (not args.no_celery) and redis_active
    if start_celery:
        log("START", "Starting Celery worker (queues: cad_generation, celery)...", MAGENTA)
        celery_cmd = [
            py_bin, "-m", "celery",
            "-A", "tasks.celery_app", "worker",
            "--loglevel=info",
            "-Q", "cad_generation,celery",
        ]
        if IS_WINDOWS:
            celery_cmd.append("--pool=solo")

        p_celery = subprocess.Popen(
            celery_cmd,
            cwd=str(BACKEND_DIR),
            env=backend_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        procs.append(("Celery", p_celery))
        t_celery = threading.Thread(target=stream_output, args=(p_celery, "CELERY", MAGENTA), daemon=True)
        t_celery.start()
    else:
        log("NOTICE", "Running in standalone mode: FastAPI BackgroundTasks will handle pipelines directly.", YELLOW)

    # 3. Start Next.js Frontend
    log("START", f"Starting Next.js frontend on port {args.frontend_port}...", CYAN)
    p_frontend = subprocess.Popen(
        [npm_bin, "run", "dev"],
        cwd=str(FRONTEND_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    procs.append(("Frontend", p_frontend))
    t_front = threading.Thread(target=stream_output, args=(p_frontend, "FRONTEND", CYAN), daemon=True)
    t_front.start()

    # 4. Wait for services to become responsive
    log("WAIT", "Waiting for services to become available...", YELLOW)
    backend_ready = False
    frontend_ready = False

    for _ in range(60):
        if not backend_ready and is_port_in_use(args.backend_port):
            backend_ready = True
        if not frontend_ready and is_port_in_use(args.frontend_port):
            frontend_ready = True
        if backend_ready and frontend_ready:
            break
        time.sleep(0.5)

    print(f"""
{GREEN}{BOLD}===================================================================
[OK]  CAD AI WORKSTATION IS READY AND LIVE!
==================================================================={RESET}
  {BOLD}* Web Workstation UI:{RESET}  {CYAN}http://localhost:{args.frontend_port}{RESET}
  {BOLD}* API Documentation:{RESET}   {BLUE}http://localhost:{args.backend_port}/docs{RESET}
  {BOLD}* WebSocket Gateway:{RESET}    {MAGENTA}ws://localhost:{args.backend_port}/ws{RESET}
{GREEN}==================================================================={RESET}
  {YELLOW}Press Ctrl+C anytime to cleanly stop all services.{RESET}
""")

    if not args.no_browser:
        try:
            webbrowser.open(f"http://localhost:{args.frontend_port}")
        except Exception:
            pass

    # Keep main thread alive and monitor processes
    try:
        while True:
            for name, p in procs:
                ret = p.poll()
                if ret is not None:
                    log("EXIT", f"Process {name} exited unexpectedly with code {ret}", RED)
                    shutdown()
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
