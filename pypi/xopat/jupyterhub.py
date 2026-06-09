"""JupyterHub integration for xOpat."""

import json
import os

from ._post import (
    attr as _attr,
    iframe_style as _iframe_style,
    reload_toolbar as _reload_toolbar,
    session_form_inputs as _session_form_inputs,
)
from .download import get_binaries_dir
from .wsi import WSI_PORT
from .xopat import XOPAT_PORT


def is_jupyterhub():
    """Detect if running on JupyterHub."""
    return bool(os.environ.get("JUPYTERHUB_SERVICE_PREFIX"))


def setup_jupyterhub(jupyterhub_host):
    """
    Configure xOpat for JupyterHub environment.
    Call this before run_server() when running on JupyterHub.

    Requires `jupyter-server-proxy` to be installed in the JupyterHub
    single-user server environment (not the notebook kernel — by then
    it's too late). This package registers the `/proxy/<port>/...`
    routes the generated xopat config relies on. Without it the
    iframe will 404. Install it on the user-server image ahead of
    time; pip-installing it from a notebook cell does not work.

    Args:
        jupyterhub_host: Full URL of JupyterHub, e.g. 'https://hub.example.com'
    """
    host = jupyterhub_host.rstrip("/")
    prefix = os.environ.get("JUPYTERHUB_SERVICE_PREFIX", "").rstrip("/")
    if not prefix:
        raise RuntimeError("JUPYTERHUB_SERVICE_PREFIX not set - are you on JupyterHub?")

    wsi_path = f"{prefix}/proxy/{WSI_PORT}/"
    xopat_path = f"{prefix}/proxy/{XOPAT_PORT}/"

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
                            "url": f"`{wsi_path}v3/slides/info?slide_id=${{data}}`",
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
                    "pluginSelectionMode": False,
                    "notificationsPosition": "top"
                }
            },
            "setup": {
                "locale": "en",
                "theme": "auto",
                "disablePluginsUi": True,
                "scrollRequiresCtrl": True,
                "bypassCloseConfirmation": True,
                "notificationsPosition": "top",
                "ui": {
                    "scaleBar": True,
                    "toolBar": False,
                    "statusBar": True,
                    "mainMenu": True,
                    "navigator": True,
                    "appBar": True,
                    "globalMenu": False
                },
            },
        },
        "plugins": {
            "slide-info": {"permaLoad": True},
            "extra-tutorials": {"enabled": "true"}
        },
        "modules": {
            "rationai-wsi-tile-source": {"permaLoad": True},
            "geotiff": {"permaLoad": True},
        },
    }

    env_path = get_binaries_dir() / "xopat_env.json"
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text(json.dumps(config, indent=2))
    # XOPAT_ENV doubles as the "user called setup_jupyterhub" sentinel
    # for run_server's JupyterHub guard. Keep it the last side effect.
    os.environ["XOPAT_ENV"] = str(env_path)
    print(f"Configured for JupyterHub: {host}{xopat_path}")


def display_jupyterhub(url, slide, width, height, cap_height):
    """Display a slide on JupyterHub with retry-on-500 and recovery toolbar."""
    import uuid
    from IPython.display import HTML, display as _ipy_display

    uid = uuid.uuid4().hex[:8]
    style = _iframe_style(width, height, cap_height) + "visibility:hidden;"
    _ipy_display(HTML(f"""
<div id="loading-{uid}" style="font-family:sans-serif;font-size:13px;
     color:#6b7280;margin:4px 0;">Loading...</div>
<iframe
    id="xopat-frame-{uid}"
    src="{url}"
    style="{style}">
</iframe>
<script>
(function() {{
    const iframe = document.getElementById('xopat-frame-{uid}');
    const status = document.getElementById('loading-{uid}');
    const maxRetries = 15;
    let attempt = 0;
    function isErrorPage() {{
        try {{
            const body = iframe.contentDocument?.body?.innerText || '';
            return body.includes('500') || body.includes('Internal server error');
        }} catch(e) {{
            return false;
        }}
    }}
    function retry() {{
        if (attempt >= maxRetries) {{
            status.textContent = 'Failed to load slide after 15 retries.';
            iframe.style.visibility = 'visible';
            return;
        }}
        attempt++;
        status.textContent = 'Retrying... attempt ' + attempt + '/15';
        setTimeout(() => {{
            iframe.contentWindow.location.reload();
        }}, 2000);
    }}
    iframe.onload = function() {{
        if (isErrorPage()) {{
            retry();
        }} else {{
            status.textContent = 'Ready.';
            iframe.style.visibility = 'visible';
        }}
    }};
}})();
</script>
""" + _reload_toolbar(uid, open_url=url, reload_mode="src")))


def display_jupyterhub_post(xopat_url, session, width, height, cap_height):
    """Display a full session on JupyterHub via POST-into-iframe.

    The proxied xopat URL is same-origin with the notebook, so a
    standard form-target POST loads the response into the iframe with
    xopat's URL as the document base.

    TODO(jupyterhub): this path is fragile on hubs that sit behind an
    ingress which URL-decodes request bodies (nginx/traefik) — the
    session arrives at the client still 1x percent-encoded and xopat
    surfaces a `JSON Error: Unexpected token '%', "%7B%22para"...`
    failure. See `_post.py`'s module docstring for the full chain
    analysis and proposed fixes (the preferred one is to switch this
    function to a `fetch`-based `application/json` POST with the HTML
    response injected via iframe `srcdoc` + `<base href>`)."""
    import uuid
    from IPython.display import HTML, display as _ipy_display

    uid = uuid.uuid4().hex[:8]
    action = xopat_url.rstrip("/") + "/"
    inputs = _session_form_inputs(session)
    style = _iframe_style(width, height, cap_height)
    _ipy_display(HTML(f"""
<iframe name="xopat-frame-{uid}" id="xopat-frame-{uid}"
        style="{style}"></iframe>
<form id="xopat-form-{uid}" method="POST"
      action="{_attr(action)}"
      target="xopat-frame-{uid}" style="display:none">
{inputs}
</form>
<script>document.getElementById("xopat-form-{uid}").submit();</script>
""" + _reload_toolbar(uid, open_url=None, reload_mode="form")))

