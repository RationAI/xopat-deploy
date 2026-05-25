"""Google Colab integration for xOpat.

Handles Colab-specific setup: proxy configuration, missing shared
libraries, and iframe display via the proxyPort JS API.
"""

import hashlib
import json
import os
import subprocess
import time

from IPython.display import HTML, display as _ipy_display

from .download import get_wsi_binary, get_xopat_binary
from .wsi import WSI_PORT
from .xopat import XOPAT_PORT


def is_colab():
    """Detect if running in Google Colab."""
    try:
        import google.colab
        return True
    except ImportError:
        return False


def setup_colab():
    """
    Configure xOpat for Google Colab environment.

    Colab assigns each port a unique subdomain (e.g. 8050-xxx.colab.dev,
    9001-xxx.colab.dev), which causes cross-origin errors when xOpat
    frontend tries to fetch tiles from WSI-Service on a different port.

    This is solved by routing all WSI-Service requests through xOpat's
    built-in proxy endpoint (/proxy/wsi/...), keeping everything on a
    single port.

    Also fixes missing shared libraries (libtiff5 -> libtiff6 symlink).
    """
    from google.colab.output import eval_js

    fix_colab_libs()

    xopat_proxy = eval_js(f"google.colab.kernel.proxyPort({XOPAT_PORT})")
    xopat_proxy = xopat_proxy.rstrip("/")

    config = {
          "core": {
              "gateway": "/",
              "active_client": "colab",
              "client": {
                  "colab": {
                    "domain": xopat_proxy,
                    "path": "/",
                    "slide_protocols": {
                        "wsi_service": {
                            "url": "`/v3/slides/info?slide_id=${data}`",
                            "proxy": "wsi"
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
              "server": {
                  "secure": {
                      "proxies": {
                          "wsi": {
                              "baseUrl": f"http://127.0.0.1:{WSI_PORT}",
                              "auth": {
                                  "enabled": False
                              }
                          }
                      }
                  }
              },
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
    os.environ["XOPAT_CROSS_SITE_COOKIES"] = "true"

    print("Configured for Google Colab.")


def display_colab(slide_q, width, height):
    """Display a slide in Google Colab using the proxyPort JS API."""
    path = f"/?slides={slide_q}"
    uid = hashlib.md5(f"{slide_q}{time.time()}".encode()).hexdigest()[:8]

    _ipy_display(HTML(f"""
<div id="xopat-status-{uid}" style="font-family: monospace; padding: 8px;">
    Loading xOpat viewer...
</div>
<div id="xopat-container-{uid}"></div>
<script>
(async function() {{
    const status = document.getElementById('xopat-status-{uid}');
    const container = document.getElementById('xopat-container-{uid}');
    try {{
        const proxyUrl = await google.colab.kernel.proxyPort({XOPAT_PORT});
        const url = proxyUrl + '{path}';
        const iframe = document.createElement('iframe');
        iframe.src = url;
        iframe.width = '{width}';
        iframe.height = '{height}';
        iframe.style.border = '1px solid #ccc';
        iframe.style.borderRadius = '4px';
        container.appendChild(iframe);
        iframe.onload = function() {{
            status.textContent = 'xOpat ready.';
        }};
        status.textContent = 'Connecting to xOpat...';
    }} catch(e) {{
        status.textContent = 'Error: ' + e.message;
    }}
}})();
</script>
"""))


def fix_colab_libs():
    """
    Fix missing shared libraries on Colab.
    Creates a symlink because Colab ships libtiff5 
    but the WSI-Service PyInstaller binary expects libtiff6
    """
    internal_dir = get_wsi_binary().parent / "_internal"
    libtiff6 = internal_dir / "libtiff.so.6"

    if libtiff6.exists():
        return

    result = subprocess.run(
        ["find", "/usr/lib", "-name", "libtiff.so.5*", "-type", "f"],
        capture_output=True, text=True,
    )
    for line in result.stdout.strip().split("\n"):
        if line:
            os.symlink(line.strip(), str(libtiff6))
            return

    print("Warning: libtiff.so.5 not found, WSI-Service may fail.")