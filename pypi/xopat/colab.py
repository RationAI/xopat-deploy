"""Google Colab integration for xOpat.

Handles Colab-specific setup: proxy configuration, missing shared
libraries, and iframe display via the proxyPort JS API.
"""

import json
import os
import subprocess
from urllib.parse import quote as _urlquote

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

    `domain` is captured via google.colab.kernel.proxyPort so xopat's
    own URL composition matches the Colab proxy alias the iframe is
    loaded from. xopat fails CORE initialization with an empty domain
    (it cannot compose absolute URLs for proxied wsi-service calls).

    Also fixes missing shared libraries (libtiff5 -> libtiff6 symlink).
    """
    from google.colab.output import eval_js

    fix_colab_libs()

    xopat_proxy = eval_js(
        f"google.colab.kernel.proxyPort({XOPAT_PORT}, {{cache: true}})"
    ).rstrip("/")

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


def _colab_proxy_url():
    """Resolve the Colab proxy URL for the xopat port. Reuses the cached
    URL from setup_colab if available — kernel.proxyPort with cache:true
    returns the same alias on repeat calls within a kernel session."""
    from google.colab.output import eval_js
    return eval_js(
        f"google.colab.kernel.proxyPort({XOPAT_PORT}, {{cache: true}})"
    ).rstrip("/")


def display_colab(slide_q, width, height):
    """Display a slide in Google Colab via a plain IFrame.

    Uses google.colab.kernel.proxyPort to resolve the proxy URL, then
    renders an IPython.display.IFrame. serve_kernel_port_as_iframe was
    tried but corrupts the Colab notebook runtime token (kernel-execute
    returns 500 afterwards). The trade-off is that the iframe loads
    from *.googleusercontent.com which is 3rd-party to colab.research.google.com:
    Safari (ITP) and Firefox (ETP) block the auth cookies for that
    context and the proxy returns 404. Chrome works."""
    from IPython.display import IFrame, display as _ipy_display
    url = f"{_colab_proxy_url()}/?slides={slide_q}"
    _ipy_display(IFrame(url, width=width, height=height))


def display_colab_post(session, width, height):
    """Display a full session in Google Colab via URL-hash GET.

    Session is serialized to JSON and placed in the URL fragment, which
    is never sent to the network — xopat parses it client-side. Same
    iframe trade-off as display_colab regarding Safari/Firefox."""
    from IPython.display import IFrame, display as _ipy_display
    encoded = _urlquote(json.dumps(session), safe="")
    url = f"{_colab_proxy_url()}/#{encoded}"
    _ipy_display(IFrame(url, width=width, height=height))


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