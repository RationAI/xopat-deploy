"""JupyterHub integration for xOpat."""

import json
import os

from ._post import attr as _attr, session_form_inputs as _session_form_inputs
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

    env_path = get_binaries_dir() / "xopat_env.json"
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text(json.dumps(config, indent=2))
    # XOPAT_ENV doubles as the "user called setup_jupyterhub" sentinel
    # for run_server's JupyterHub guard. Keep it the last side effect.
    os.environ["XOPAT_ENV"] = str(env_path)
    print(f"Configured for JupyterHub: {host}{xopat_path}")


def display_jupyterhub(url, slide, width, height):
    """Display a slide on JupyterHub with reload fallback."""
    import uuid
    from IPython.display import HTML, display as _ipy_display

    uid = uuid.uuid4().hex[:8]
    _ipy_display(HTML(f"""
<div id="status-{uid}">Loading...</div>
<iframe
    id="frame-{uid}"
    src="{url}"
    width="{width}"
    height="{height}"
    style="border:1px solid #ccc; visibility: hidden;">
</iframe>
<script>
(function() {{
    const iframe = document.getElementById('frame-{uid}');
    const status = document.getElementById('status-{uid}');
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
"""))


def display_jupyterhub_post(xopat_url, session, width, height):
    """Display a full session on JupyterHub via POST-into-iframe.

    The proxied xopat URL is same-origin with the notebook, so a
    standard form-target POST loads the response into the iframe with
    xopat's URL as the document base."""
    import uuid
    from IPython.display import HTML, display as _ipy_display

    uid = uuid.uuid4().hex[:8]
    action = xopat_url.rstrip("/") + "/"
    inputs = _session_form_inputs(session)
    _ipy_display(HTML(f"""
<iframe name="xopat-frame-{uid}" id="xopat-frame-{uid}"
        width="{_attr(width)}" height="{_attr(height)}"
        style="border:1px solid #ccc;"></iframe>
<form id="xopat-form-{uid}" method="POST"
      action="{_attr(action)}"
      target="xopat-frame-{uid}" style="display:none">
{inputs}
</form>
<script>document.getElementById("xopat-form-{uid}").submit();</script>
"""))

