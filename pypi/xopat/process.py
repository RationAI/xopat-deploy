import subprocess
import signal
import os
import socket
import threading
import time
import urllib.request
from collections import deque
from .download import is_windows


_PR_SET_PDEATHSIG = 1


def _linux_die_with_parent():
    """preexec_fn for Linux: ask the kernel to SIGTERM this child when the
    parent process exits. Prevents wsi/xopat binaries from being orphaned
    onto PID 1 and continuing to hold their ports after a Colab "Restart
    session" — which then breaks the next run_server() invocation."""
    import ctypes
    libc = ctypes.CDLL("libc.so.6", use_errno=True)
    libc.prctl(_PR_SET_PDEATHSIG, signal.SIGTERM, 0, 0, 0)


def _port_in_use(port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            return s.connect_ex(("127.0.0.1", port)) == 0
    except Exception:
        return False


def _kill_process_on_port(port):
    """Best-effort: kill any process listening on `port` (Linux/macOS only).

    Used to recover from orphaned xopat/wsi binaries left behind by a prior
    Colab kernel that did not clean up before being restarted. No-op on
    Windows; no-op if `lsof` is unavailable."""
    if is_windows():
        return
    try:
        out = subprocess.run(
            ["lsof", "-ti", f"tcp:{port}", "-sTCP:LISTEN"],
            capture_output=True, text=True, timeout=3,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return
    for pid_str in out.stdout.split():
        try:
            pid = int(pid_str)
        except ValueError:
            continue
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.kill(pid, sig)
            except ProcessLookupError:
                break
            except Exception:
                pass
            for _ in range(10):
                if not _port_in_use(port):
                    break
                time.sleep(0.1)
            if not _port_in_use(port):
                break


def free_port(port, name):
    """Ensure `port` has no listener. Kills any orphan first."""
    if not _port_in_use(port):
        return
    print(f"Port {port} in use by an orphan process (likely {name} from a previous session); freeing it...")
    _kill_process_on_port(port)
    if _port_in_use(port):
        raise RuntimeError(
            f"Port {port} still in use after cleanup attempt; cannot start {name}. "
            f"Restart the notebook runtime (Runtime → Disconnect and delete runtime)."
        )


_READY_TIMEOUT_SECONDS = 30
_OUTPUT_TAIL_LINES = 200


def start_process(binary, ready_url, name, env=None, cwd=None):
    """
    Start a subprocess and wait until it responds on ready_url.

    On Linux, `LD_LIBRARY_PATH` is reset to `<binary>/_internal` and any
    `LD_PRELOAD` is dropped from the spawn env. The PyInstaller bundle
    is self-contained, and hosts that pollute these vars with
    ABI-incompatible libs (Linuxbrew, leaked conda envs) otherwise win
    the dynamic-loader race against the bundled libs and abort the
    binary on import. Real case: brew's libtiff.so.6 was linked against
    a libjpeg with renamed symbols, so openslide died with
    `undefined symbol: jpeg12_write_raw_data` before port 8050 was ever
    bound, leaving the user with a "did not start" with no log.

    stdout and stderr are captured into a bounded ring buffer (last
    ~200 lines) so that when the binary does fail, the actual error is
    surfaced in the raised `RuntimeError` instead of being silently
    discarded. The drain runs in a daemon thread to prevent the child
    from blocking on a full pipe.

    Args:
        binary:    Path to the executable.
        ready_url: URL to poll until the process is ready.
        name:      Human-readable name for log messages.
        env:       Optional environment variables dict.
        cwd:       Working directory (defaults to binary's parent).

    Returns:
        subprocess.Popen instance.

    Raises:
        RuntimeError: If the process does not respond within the
                      readiness window, or exits before becoming ready.
                      The message includes the binary's last captured
                      output and exit code (or "still running, terminated").
    """
    cwd = cwd or str(binary.parent)

    print(f"Starting {name}...")
    popen_kwargs = dict(
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    if is_windows():
        proc = subprocess.Popen(
            [str(binary)],
            env=env,
            **popen_kwargs,
        )
    else:
        spawn_env = dict(env) if env is not None else os.environ.copy()
        spawn_env["LD_LIBRARY_PATH"] = str(binary.parent / "_internal")
        spawn_env.pop("LD_PRELOAD", None)
        proc = subprocess.Popen(
            [str(binary)],
            env=spawn_env,
            preexec_fn=_linux_die_with_parent,
            **popen_kwargs,
        )

    captured = deque(maxlen=_OUTPUT_TAIL_LINES)

    def _drain():
        try:
            for line in proc.stdout:
                captured.append(line)
        except Exception:
            pass

    threading.Thread(target=_drain, daemon=True).start()

    deadline = time.monotonic() + _READY_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        # Bail out immediately if the binary already died — typical for
        # missing-lib failures, which abort in <1 s. Without this we'd
        # wait the full window before raising.
        if proc.poll() is not None:
            break
        try:
            urllib.request.urlopen(ready_url, timeout=0.5)
            print(f"{name} is running.")
            return proc
        except Exception:
            time.sleep(0.2)

    if proc.poll() is None:
        proc.terminate()
        exit_status = "still running, terminated"
    else:
        exit_status = str(proc.returncode)
    # Give the drain thread a moment to flush remaining lines after the
    # binary's stdout closes on terminate / natural exit.
    time.sleep(0.2)
    tail = "".join(list(captured))
    raise RuntimeError(
        f"{name} did not start on {ready_url}\n"
        f"Exit code: {exit_status}\n"
        f"Last output from the binary:\n{tail}"
    )


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
            os.kill(proc.pid, signal.SIGTERM)
    except Exception:
        pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.kill(proc.pid, signal.SIGKILL)
        except Exception:
            pass
        proc.wait()
    print(f"{name} stopped.")