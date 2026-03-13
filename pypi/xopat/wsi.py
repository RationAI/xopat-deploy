import subprocess
import time
import urllib.request
from pathlib import Path

_ENV_TEMPLATE = Path(__file__).parent / "wsi_service.env"


class WsiService:
    def __init__(self, proc):
        self.proc = proc
        self.base_url = "http://127.0.0.1:8080"

    def stop(self):
        self.proc.terminate()
        self.proc.wait()


def start_wsi_service(binary, data_dir=None):
    binary = Path(binary)

    # TODO ?
    env_file = binary.parent / ".env"
    content = _ENV_TEMPLATE.read_text()
    if data_dir is not None:
        content += f"\nWS_DATA_DIR={data_dir}\n"
    env_file.write_text(content)

    proc = subprocess.Popen(
        [str(binary)],
        cwd=str(binary.parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for _ in range(50):
        try:
            urllib.request.urlopen("http://127.0.0.1:8080/docs", timeout=0.5)
            return WsiService(proc)
        except Exception:
            time.sleep(0.2)

    proc.terminate()
    raise RuntimeError("WSI-Service did not start on http://127.0.0.1:8080")