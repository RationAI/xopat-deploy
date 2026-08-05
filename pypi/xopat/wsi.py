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


def resolve_data_dir(data_dir):
    """
    Absolutize data_dir against the *caller's* working directory.

    WSI-Service resolves a relative WS_DATA_DIR against its own CWD, and
    `process.start_process` pins that CWD to the binary's directory (it has
    to: the service reads a relative `env_file=".env"`, so it only finds its
    config when launched from there). Left alone, `data_dir="slides"` would
    therefore mean `~/.xopat/wsi/<version>/<platform>/slides` rather than the
    `slides` folder the caller is looking at. Resolving here, in the caller's
    process, makes a relative path mean what it looks like it means.

    Forward slashes because the service normalizes to them anyway, and an
    unquoted `.env` value with backslashes is asking for escaping trouble.
    """
    return os.path.abspath(os.path.expanduser(str(data_dir))).replace(os.sep, "/")


def _apply_data_dir(content, data_dir):
    """Replace the template's WS_DATA_DIR line rather than appending a second one."""
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("WS_DATA_DIR="):
            lines[i] = f"WS_DATA_DIR={data_dir}"
            break
    else:
        lines.append(f"WS_DATA_DIR={data_dir}")
    return "\n".join(lines) + "\n"


def start_wsi_service(binary, data_dir=None):
    binary = Path(binary)
    env_file = binary.parent / ".env"
    content = ENV_TEMPLATE.read_text()

    env = None
    if data_dir is not None:
        data_dir = resolve_data_dir(data_dir)
        content = _apply_data_dir(content, data_dir)
        # Also pass it through the environment: env vars outrank dotenv in
        # pydantic-settings, so this both avoids any .env quoting question and
        # stops a stale WS_DATA_DIR exported in the caller's shell from
        # silently winning over the value written here. The .env keeps the same
        # value so it stays useful for debugging.
        env = os.environ.copy()
        env["WS_DATA_DIR"] = data_dir

    env_file.write_text(content)

    proc = start_process(binary, WSI_READY_URL, "WSI-Service", env=env)
    return WsiService(proc)