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

    `domain` is set to the literal marker "__ORIGIN__" so xopat
    substitutes window.location.origin at boot. Colab exposes each
    kernel port under two aliases (*.googleusercontent.com and
    *.prod.colab.dev); serve_kernel_port_as_iframe picks one and
    google.colab.kernel.proxyPort returns the other. Pre-baking either
    causes xopat's wsi-proxy fetch to be cross-origin to the iframe,
    which preflights and fails with no Access-Control-Allow-Origin.
    Using __ORIGIN__ keeps the fetch same-origin regardless of which
    alias Colab chose. Requires xopat client support for the marker.

    Also fixes missing shared libraries (libtiff5 -> libtiff6 symlink).
    """
    fix_colab_libs()

    config = {
          "core": {
              "gateway": "/",
              "active_client": "colab",
              "client": {
                  "colab": {
                    "domain": "__ORIGIN__",
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
    """Display a slide in Google Colab via serve_kernel_port_as_iframe.

    Uses the Colab-supplied helper so the iframe wrapper runs same-origin
    to the notebook output. Raw proxyPort URLs are on
    *.googleusercontent.com, which is 3rd-party to colab.research.google.com
    — Safari (ITP) and Firefox (ETP) block the auth cookies for that
    context and the proxy returns 404. The wrapper sidesteps that."""
    from google.colab.output import serve_kernel_port_as_iframe
    serve_kernel_port_as_iframe(
        XOPAT_PORT,
        path=f"/?slides={slide_q}",
        width=str(width),
        height=str(height),
    )


def display_colab_post(session, width, height):
    """Display a full session in Google Colab via URL-hash GET.

    Session is serialized to JSON and placed in the URL fragment, which
    is never sent to the network — xopat parses it client-side. Uses
    serve_kernel_port_as_iframe for the same Safari/Firefox reason as
    display_colab."""
    from google.colab.output import serve_kernel_port_as_iframe
    encoded = _urlquote(json.dumps(session), safe="")
    serve_kernel_port_as_iframe(
        XOPAT_PORT,
        path=f"/#{encoded}",
        width=str(width),
        height=str(height),
    )


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