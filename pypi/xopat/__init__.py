import hashlib
import json
import os
import time

from IPython.display import HTML, IFrame, display as _ipy_display

from .download import get_wsi_binary, get_xopat_binary
from .wsi import start_wsi_service
from .xopat import start_xopat

def configure(jupyterhub_host):
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

    wsi_path = f"{prefix}/proxy/8080"
    xopat_path = f"{prefix}/proxy/9000"

    config = {
        "core": {
            "gateway": "/",
            "active_client": "jupyter",
            "client": {
                "jupyter": {
                    "domain": host,
                    "path": xopat_path,
                    "image_group_server": host,
                    "image_group_protocol": f"`{wsi_path}/v3/slides/info?slide_id=${{data}}`",
                    "image_group_preview": f"`{wsi_path}/v3/slides/thumbnail/max_size/250/250?slide_id=${{data}}`",
                    "data_group_server": host,
                    "data_group_protocol": f"`{wsi_path}/v3/files/info?paths=${{data.join(\",\")}}`",
                    "headers": {},
                    "js_cookie_expire": 365,
                    "js_cookie_path": "/",
                    "js_cookie_same_site": "",
                    "js_cookie_secure": "",
                    "secureMode": False
                }
            },
            "setup": {"locale": "en", "theme": "auto"}
        },
        "plugins": {
            "slide-info": {"permaLoad": True},
            "file-browser": {"permaLoad": True}
        },
        "modules": {
            "empaia-wsi-tile-source": {"permaLoad": True},
            "mlflow": {"enabled": False}
        }
    }

    xopat_binary = get_xopat_binary()
    env_path = xopat_binary.parent / "xopat_env.json"
    env_path.write_text(json.dumps(config, indent=2))
    os.environ["XOPAT_ENV"] = str(env_path)
    print(f"Configured for JupyterHub: {host}{xopat_path}")

class Server:
    """Running xOpat + WSI-Service instance returned by run_server()."""

    def __init__(self, wsi, xopat):
        self._wsi = wsi
        self._xopat = xopat
        self.wsi_url = wsi.base_url
        self.xopat_url = xopat.base_url

    def stop(self):
        """Stop both xOpat and WSI-Service processes."""
        try:
            self._xopat.stop()
        finally:
            self._wsi.stop()

def run_server(data_dir=None):
    """
    Download (if needed) and start WSI-Service and xOpat.
    Args:
        data_dir: Path to the directory containing slide files. Defaults to the current working directory.
    Returns:
        Server instance with wsi_url and xopat_url attributes.
    """
    data_dir = data_dir or os.getcwd()
    wsi_binary = get_wsi_binary()
    xopat_binary = get_xopat_binary()
    wsi = start_wsi_service(wsi_binary, data_dir=data_dir)
    try:
        xopat = start_xopat(xopat_binary)
    except Exception:
        wsi.stop()
        raise
    return Server(wsi, xopat)

def display(server, slide, width="100%", height=800):
    """
    Display a slide in a Jupyter notebook iframe.
    Args:
        server: Server instance returned by run_server().
        slide:  Slide identifier (path or URL) passed to xOpat.
        width:  iframe width (CSS value, default "100%").
        height: iframe height in pixels (default 800).
    """
    slide_q = slide.replace(">", "%3E")
    url = server.xopat_url + "/?slides=" + slide_q
    
    prefix = os.environ.get("JUPYTERHUB_SERVICE_PREFIX", "")
    
    if not prefix:
        # localhost
        _ipy_display(IFrame(url, width=width, height=height))
        return
    
    # JupyterHub - reload fallback
    uid = hashlib.md5(f"{slide}{time.time()}".encode()).hexdigest()[:8]
    print(f"Loading slide: {slide}")
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