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

    `domain` uses the `<% DOMAIN %>` placeholder so xopat resolves it
    against the iframe's actual origin at runtime. Colab serves the
    same kernel port on two aliases (*.googleusercontent.com and
    *.prod.colab.dev) and may pick either one for the iframe — pre-
    capturing one alias and writing it into the config breaks the other.

    Also fixes missing shared libraries (libtiff5 -> libtiff6 symlink).
    """
    fix_colab_libs()

    config = {
          "core": {
              "gateway": "/",
              "active_client": "colab",
              "client": {
                  "colab": {
                    "domain": "<% DOMAIN %>",
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


_UNSUPPORTED_BROWSER_HTML = """
<div style="border:1px solid #d97706;background:#fef3c7;color:#78350f;
            padding:12px 16px;border-radius:6px;font-family:sans-serif;
            line-height:1.5;max-width:720px;">
  <strong>Browser not supported on Google Colab</strong><br>
  Viewing slides via <code>xopat</code> on Google Colab currently requires a
  Chromium-based browser (Chrome, Edge, Brave, etc.). On Safari and Firefox,
  Colab's third-party iframe proxy can corrupt this notebook's runtime token
  and leave the notebook unable to execute further cells (HTTP 500 errors).
  <br><br>
  Please open this notebook in Chrome. If this notebook is already in the
  broken state, recover by either switching to Chrome, switching Colab
  accounts, or making a copy (File &rarr; Save a copy in Drive) to get a
  fresh runtime.
</div>
"""


def _is_unsupported_colab_browser():
    """Return True for Safari and Firefox on Colab; False otherwise.

    Loading xopat's iframe via serve_kernel_port_as_iframe on Safari/Firefox
    has been observed to corrupt the Colab notebook's runtime auth state,
    breaking subsequent cell execution (kernel-execute calls return 500).
    Avoid creating the iframe at all on those browsers until the root cause
    is identified."""
    try:
        from google.colab.output import eval_js
    except ImportError:
        return False
    try:
        ua = eval_js("navigator.userAgent")
    except Exception:
        return False
    if not isinstance(ua, str):
        return False
    is_firefox = "Firefox" in ua
    is_safari = "Safari" in ua and "Chrome" not in ua and "Chromium" not in ua
    return is_firefox or is_safari


def _render_unsupported_browser_notice():
    from IPython.display import HTML, display as _ipy_display
    _ipy_display(HTML(_UNSUPPORTED_BROWSER_HTML))


def display_colab(slide_q, width, height):
    """Display a slide in Google Colab via serve_kernel_port_as_iframe.

    Uses the Colab-supplied helper rather than raw kernel.proxyPort()
    so the iframe wrapper runs same-origin to the notebook output. Raw
    proxyPort URLs are on *.googleusercontent.com, which is 3rd-party
    to colab.research.google.com — Safari (ITP) blocks the auth cookies
    for that context and the proxy then returns 404.

    On Safari and Firefox the helper itself is unsafe (it can break the
    notebook's runtime auth), so we render a notice instead of loading
    the iframe."""
    if _is_unsupported_colab_browser():
        _render_unsupported_browser_notice()
        return
    from google.colab.output import serve_kernel_port_as_iframe
    serve_kernel_port_as_iframe(
        XOPAT_PORT,
        path=f"/?slides={slide_q}",
        width=str(width),
        height=str(height),
        cache_in_notebook=True,
    )


def display_colab_post(session, width, height):
    """Display a full session in Google Colab via URL-hash GET.

    Session is serialized to JSON and placed in the URL fragment, which
    is never sent to the network — xopat parses it client-side. Uses
    serve_kernel_port_as_iframe so the load also works in Safari (see
    display_colab for the cookie/ITP rationale).

    On Safari and Firefox the helper is unsafe; see display_colab."""
    if _is_unsupported_colab_browser():
        _render_unsupported_browser_notice()
        return
    from google.colab.output import serve_kernel_port_as_iframe
    encoded = _urlquote(json.dumps(session), safe="")
    serve_kernel_port_as_iframe(
        XOPAT_PORT,
        path=f"/#{encoded}",
        width=str(width),
        height=str(height),
        cache_in_notebook=True,
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