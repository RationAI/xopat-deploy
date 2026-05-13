import os
from pathlib import Path
from .process import start_process, stop_process

XOPAT_PORT = 9001
XOPAT_READY_URL = f"http://127.0.0.1:{XOPAT_PORT}"


class XOpat:
    def __init__(self, proc, base_url):
        self.proc = proc
        self.base_url = base_url

    def stop(self):
        stop_process(self.proc, "xOpat")


def start_xopat(binary):
    binary = Path(binary)
    env = os.environ.copy()
    env["XOPAT_CACHE_DIR"] = str(binary.parent / "cache")
    env["XOPAT_NODE_PORT"] = str(XOPAT_PORT)
    env["XOPAT_CROSS_SITE_COOKIES"] = "true"

    proc = start_process(binary, XOPAT_READY_URL, "xOpat", env=env)

    prefix = os.environ.get("JUPYTERHUB_SERVICE_PREFIX", "").rstrip("/")
    base_url = f"{prefix}/proxy/{XOPAT_PORT}" if prefix else f"http://127.0.0.1:{XOPAT_PORT}"

    return XOpat(proc, base_url)