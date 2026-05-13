import os
from pathlib import Path
from .process import start_process, stop_process

ENV_TEMPLATE = Path(__file__).parent / "wsi_service.env"

WSI_PORT = 8050
WSI_READY_URL = f"http://127.0.0.1:{WSI_PORT}/docs"


class WsiService:
    def __init__(self, proc):
        self.proc = proc
        self.base_url = f"http://127.0.0.1:{WSI_PORT}"

    def stop(self):
        stop_process(self.proc, "WSI-Service")


def start_wsi_service(binary, data_dir=None):
    binary = Path(binary)
    env_file = binary.parent / ".env"
    content = ENV_TEMPLATE.read_text()
    if data_dir is not None:
        content += f"\nWS_DATA_DIR={data_dir}\n"
    env_file.write_text(content)

    proc = start_process(binary, WSI_READY_URL, "WSI-Service")
    return WsiService(proc)