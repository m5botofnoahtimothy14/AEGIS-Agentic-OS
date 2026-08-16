#!/usr/bin/env python3
"""
SATURDAY Unified Boot - the single entry point for the whole system.

Pipeline: preflight checks -> device optimization -> launch core
(optionally gateway, telemetry, realtime bridge) -> supervise/health.

Commands:
  python saturday_boot.py                  boot everything (default)
  python saturday_boot.py --status         show running instance status
  python saturday_boot.py --stop           stop the running instance
  python saturday_boot.py --check          choke test (compile + import + device probe)
"""

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
RUN_DIR = BASE_DIR / "run"
LOG_DIR = BASE_DIR / "logs"
PID_FILE = RUN_DIR / "saturday.pid"
INFO_FILE = RUN_DIR / "saturday.json"
ENV_FILE = BASE_DIR / "prod.env"

PYTHON = sys.executable


def log(msg: str):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_DIR / "boot.log", "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        pass


def load_env():
    from dotenv import load_dotenv
    load_dotenv(ENV_FILE)


def port_free(host: str, port: int) -> bool:
    bind_host = host if host not in ("0.0.0.0", "::") else "127.0.0.1"
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        try:
            return sock.connect_ex((bind_host, port)) != 0
        finally:
            sock.close()
    except Exception:
        return True


def preflight(core_port: int) -> list:
    issues = []
    if not (BASE_DIR / ".venv").exists() and not (BASE_DIR / "saturday_env.py").exists():
        issues.append("No .venv found - run setup first (setup.ps1).")
    for name in ("core", "data", "logs"):
        (BASE_DIR / name).mkdir(exist_ok=True)
    if not port_free("0.0.0.0", core_port):
        issues.append(f"Core port {core_port} is already in use.")
    return issues


def device_optimize() -> dict:
    sys.path.insert(0, str(BASE_DIR))
    from core.processor import optimize_for_device
    try:
        profile = optimize_for_device(BASE_DIR / "data").to_dict()
        log(f"Device optimization: tier={profile['tier']}, backend={profile['backend']}, "
            f"threads={profile['thread_pool_workers']}, ram={profile['ram_total_gb']}GB")
        return profile
    except Exception as e:
        log(f"Device optimization skipped: {e}")
        return {}


def choke_check() -> int:
    import compileall
    log("Running choke test over project source...")
    errors = 0
    for root_dir, label in ((BASE_DIR / "core", "core"), (BASE_DIR, "root"), (BASE_DIR / "SATURDAY_SYSTEM", "saturday_system")):
        py_files = [p for p in root_dir.rglob("*.py")
                    if any(part.startswith(".") for part in p.parts) is False]
        for py_file in py_files:
            if any(part in {"node_modules", ".venv", "build", "dist", "__pycache__", "pip_packages"} for part in py_file.parts):
                continue
            try:
                compile(py_file.read_bytes(), str(py_file), "exec")
            except SyntaxError as e:
                errors += 1
                log(f"SYNTAX ERROR [{label}] {py_file}: {e}")
    log(f"Choke check finished. Errors: {errors}")
    return errors


def write_runtime(pid: int, port: int, started: float, extra: dict):
    RUN_DIR.mkdir(exist_ok=True)
    PID_FILE.write_text(str(pid), encoding="utf-8")
    info = {
        "pid": pid,
        "port": port,
        "started": started,
        "python": PYTHON,
        "root": str(BASE_DIR),
    }
    info.update(extra or {})
    INFO_FILE.write_text(json.dumps(info, indent=2), encoding="utf-8")


def read_runtime() -> dict:
    try:
        data = json.loads(INFO_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not data:
        return {}
    pid = data.get("pid")
    if pid and not _pid_alive(pid):
        return {}
    return data


def _pid_alive(pid: int) -> bool:
    try:
        import psutil
        if not psutil.pid_exists(pid):
            return False
        return psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False
    except Exception:
        return False


def show_status():
    info = read_runtime()
    if not info:
        log("SATURDAY is not running (no live PID record).")
        return 1
    port = info.get("port", 8000)
    alive = port_free("0.0.0.0", port) is False
    log(f"SATURDAY PID {info.get('pid')} on port {port} - {'UP' if alive else 'DOWN (record stale)'}")
    return 0


def stop_instance() -> int:
    info = read_runtime()
    if not info:
        log("No running SATURDAY instance found.")
        return 0
    pids = {int(p) for p in (info.get("pid"), info.get("supervisor_pid")) if p}
    for pid in pids:
        log(f"Stopping SATURDAY (PID {pid})...")
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
    deadline = time.time() + 12
    while time.time() < deadline and any(_pid_alive(p) for p in pids):
        time.sleep(0.5)
    for pid in pids:
        if _pid_alive(pid):
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
    for p in (PID_FILE, INFO_FILE):
        try:
            p.unlink(missing_ok=True)
        except Exception:
            pass
    log("SATURDAY stopped.")
    return 0


def spawn_child(args: list, watch: bool, port: int, started: float, extra: dict):
    log(f"Launching: {' '.join(args)}")
    while True:
        proc = subprocess.Popen(args, cwd=str(BASE_DIR))
        log(f"Core server started with PID {proc.pid}")
        write_runtime(proc.pid, port, started, extra)
        try:
            proc.wait()
        except KeyboardInterrupt:
            proc.terminate()
            proc.wait(timeout=10)
            raise
        code = proc.returncode
        log(f"Core server exited with code {code}")
        if not watch:
            return code
        log("Supervisor restarting core in 3s...")
        time.sleep(3)


def boot(args) -> int:
    RUN_DIR.mkdir(exist_ok=True)
    LOG_DIR.mkdir(exist_ok=True)
    core_port = int(args.port)
    load_env()

    issues = preflight(core_port)
    for issue in issues:
        log(f"PREFLIGHT ISSUE: {issue}")
    if issues and args.fail_fast:
        return 1

    profile = device_optimize()

    child = [PYTHON, str(BASE_DIR / "run_production.py"), "--mode", "standalone"]
    child_env = dict(os.environ)
    child_env.setdefault("PORT", str(core_port))
    child_env.setdefault("HOST", "0.0.0.0")

    extra = {"profile": profile, "gateway": args.gateway, "telemetry": args.telemetry, "realtime": args.realtime, "supervisor_pid": os.getpid()}
    started = time.time()
    write_runtime(os.getpid(), core_port, started, extra)
    log(f"SATURDAY booting core on 0.0.0.0:{core_port} (watch={args.watch})")
    if args.gateway:
        gateway_port = int(args.gateway_port)
        if not port_free("0.0.0.0", gateway_port):
            log(f"Gateway port {gateway_port} is busy - skipping gateway.")
        else:
            log(f"Launching secure API gateway on port {gateway_port}")
            subprocess.Popen(
                [PYTHON, str(BASE_DIR / "api_gateway.py")],
                cwd=str(BASE_DIR),
                env=dict(os.environ, SATURDAY_API_PORT=str(gateway_port)),
                stdout=open(LOG_DIR / "gateway.log", "a", encoding="utf-8"),
                stderr=subprocess.STDOUT,
            )

    if args.telemetry:
        log("Launching telemetry sync loop (requires Firebase credentials)")
        subprocess.Popen(
            [PYTHON, str(BASE_DIR / "telemetry_sync.py"),
             "--node-id", os.getenv("SATURDAY_NODE_ID", "saturday-node-1"),
             "--interval", "2.0"],
            cwd=str(BASE_DIR),
            stdout=open(LOG_DIR / "telemetry.log", "a", encoding="utf-8"),
            stderr=subprocess.STDOUT,
        )

    if args.realtime:
        log("Launching Firebase Realtime bridge (requires RTDB credentials)")
        subprocess.Popen(
            [PYTHON, str(BASE_DIR / "SATURDAY_SYSTEM" / "main.py"), "--firebase-realtime"],
            cwd=str(BASE_DIR),
            stdout=open(LOG_DIR / "realtime.log", "a", encoding="utf-8"),
            stderr=subprocess.STDOUT,
        )

    def _signal_handler(signum=None, frame=None):
        log(f"Received signal {signum} - shutting down.")
        stop_instance()
        sys.exit(0)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    code = spawn_child(child, watch=args.watch, port=core_port, started=started, extra=extra)
    log(f"SATURDAY exited with code {code}.")
    return code


def main():
    parser = argparse.ArgumentParser(description="SATURDAY Unified Boot")
    parser.add_argument("--port", default=int(os.getenv("PORT", "8000")), help="Core port (default 8000)")
    parser.add_argument("--gateway", action="store_true", help="Also launch secure API gateway")
    parser.add_argument("--gateway-port", default=int(os.getenv("SATURDAY_API_PORT", "8443")), help="Gateway port (default 8443)")
    parser.add_argument("--telemetry", action="store_true", help="Start Firestore telemetry loop")
    parser.add_argument("--realtime", action="store_true", help="Start Firebase Realtime bridge")
    parser.add_argument("--watch", action="store_true", help="Auto-restart the core if it exits")
    parser.add_argument("--fail-fast", action="store_true", help="Abort boot if preflight issues are found")
    parser.add_argument("--status", action="store_true", help="Show running instance status")
    parser.add_argument("--stop", action="store_true", help="Stop the running instance")
    parser.add_argument("--check", action="store_true", help="Run choke test (compile all project .py files)")
    args = parser.parse_args()

    if args.check:
        return choke_check()
    if args.status:
        return show_status()
    if args.stop:
        return stop_instance()
    return boot(args)


if __name__ == "__main__":
    sys.exit(main())
