import subprocess
import time
import urllib.request
from pathlib import Path


class XOpat:
    def __init__(self, proc):
        self.proc = proc
        self.base_url = "http://127.0.0.1:9000"

    def stop(self):
        self.proc.terminate()
        self.proc.wait()


def start_xopat(binary):
    binary = Path(binary)

    proc = subprocess.Popen(
        [str(binary)],
        cwd=str(binary.parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for _ in range(50):
        try:
            urllib.request.urlopen("http://127.0.0.1:9000", timeout=0.5)
            return XOpat(proc)
        except Exception:
            time.sleep(0.2)

    proc.terminate()
    raise RuntimeError("xOpat did not start on http://127.0.0.1:9000")