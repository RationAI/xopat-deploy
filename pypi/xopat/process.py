import subprocess
import signal
import os
import time
import urllib.request
from .download import is_windows


def start_process(binary, ready_url, name, env=None, cwd=None):
    """
    Start a subprocess and wait until it responds on ready_url.

    Args:
        binary:    Path to the executable.
        ready_url: URL to poll until the process is ready.
        name:      Human-readable name for log messages.
        env:       Optional environment variables dict.
        cwd:       Working directory (defaults to binary's parent).

    Returns:
        subprocess.Popen instance.

    Raises:
        RuntimeError: If the process does not respond within timeout.
    """
    cwd = cwd or str(binary.parent)

    print(f"Starting {name}...")
    if is_windows():
        proc = subprocess.Popen(
            [str(binary)],
            cwd=cwd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        proc = subprocess.Popen(
            [str(binary)],
            cwd=cwd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid,
        )

    for _ in range(50):
        try:
            urllib.request.urlopen(ready_url, timeout=0.5)
            print(f"{name} is running.")
            return proc
        except Exception:
            time.sleep(0.2)

    proc.terminate()
    raise RuntimeError(f"{name} did not start on {ready_url}")


def stop_process(proc, name):
    """
    Terminate a subprocess, falling back to SIGKILL if needed.

    Args:
        proc: subprocess.Popen instance.
        name: Human-readable name for log messages.
    """
    print(f"Stopping {name}...")
    try:
        if is_windows():
            proc.terminate()
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except Exception:
        pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            pass
        proc.wait()
    print(f"{name} stopped.")