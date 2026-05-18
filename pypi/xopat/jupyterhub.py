"""JupyterHub integration for xOpat."""

import json
import os

from .download import get_xopat_binary
from .wsi import WSI_PORT
from .xopat import XOPAT_PORT


def is_jupyterhub():
    """Detect if running on JupyterHub."""
    return bool(os.environ.get("JUPYTERHUB_SERVICE_PREFIX"))


def setup_jupyterhub(jupyterhub_host):
    """
    Configure xOpat for JupyterHub environment.
    Call this before run_server() when running on JupyterHub.

    Args:
        jupyterhub_host: Full URL of JupyterHub, e.g. 'https://hub.example.com'
    """
    host = jupyterhub_host.rstrip("/")
    prefix = os.environ.get("JUPYTERHUB_SERVICE_PREFIX", "").rstrip("/")
    if not prefix:
        raise RuntimeError("JUPYTERHUB_SERVICE_PREFIX not set - are you on JupyterHub?")

    wsi_path = f"{prefix}/proxy/{WSI_PORT}"
    xopat_path = f"{prefix}/proxy/{XOPAT_PORT}"

    config = {
        "core": {
            "gateway": "/",
            "active_client": "jupyter",
            "client": {
                "jupyter": {
                    "domain": host,
                    "path": xopat_path,
                    "slide_protocols": {
                        "wsi_service": {
                            "url": f"`{wsi_path}/v3/slides/info?slide_id=${{data}}`",
                        }
                    },
                    "default_background_protocol": "wsi_service",
                    "default_visualization_protocol": "wsi_service",
                    "headers": {},
                    "js_cookie_expire": 365,
                    "js_cookie_path": "/",
                    "js_cookie_same_site": "",
                    "js_cookie_secure": "",
                    "secureMode": False,
                }
            },
            "setup": {"locale": "en", "theme": "auto"},
        },
        "plugins": {
            "slide-info": {"permaLoad": True},
        },
        "modules": {
            "rationai-wsi-tile-source": {"permaLoad": True},
            "mlflow": {"enabled": False},
        },
    }

    xopat_binary = get_xopat_binary()
    env_path = xopat_binary.parent / "xopat_env.json"
    env_path.write_text(json.dumps(config, indent=2))
    os.environ["XOPAT_ENV"] = str(env_path)
    print(f"Configured for JupyterHub: {host}{xopat_path}")

