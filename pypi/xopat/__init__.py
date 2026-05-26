import os
import uuid

from IPython.display import HTML, IFrame, display as _ipy_display

from ._post import attr as _attr, session_form_inputs as _session_form_inputs
from .download import clear_binary_cache, get_wsi_binary, get_xopat_binary
from .process import free_port
from .wsi import WSI_PORT, start_wsi_service
from .xopat import XOPAT_PORT, start_xopat
from .colab import is_colab, setup_colab, display_colab, display_colab_post
from .jupyterhub import (
    setup_jupyterhub,
    is_jupyterhub,
    display_jupyterhub,
    display_jupyterhub_post,
)

__all__ = [
    "setup_jupyterhub",
    "setup_colab",
    "run_server",
    "display",
    "Server",
    "clear_binary_cache",
]


class Server:
    """Running xOpat + WSI-Service instance returned by run_server()."""

    running = None

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
        if Server.running is self:
            Server.running = None


def run_server(data_dir=None):
    """
    Download (if needed) and start WSI-Service and xOpat.

    On Colab, automatically fixes missing shared libraries and
    configures the proxy-based environment.

    Args:
        data_dir: Path to the directory containing slide files.
                  Defaults to current working directory (or /content on Colab).
    Returns:
        Server instance with wsi_url and xopat_url attributes.
    """
    if Server.running is not None:
        Server.running.stop()

    if data_dir is None:
        data_dir = "/content" if is_colab() else os.getcwd()

    free_port(WSI_PORT, "WSI-Service")
    free_port(XOPAT_PORT, "xOpat")

    if is_colab():
        setup_colab()
    elif is_jupyterhub() and not os.environ.get("XOPAT_ENV"):
        # setup_jupyterhub() sets XOPAT_ENV as its last side effect; if
        # we're on a hub and that var is missing, the user skipped the
        # setup call. Without it the xopat binary boots its built-in
        # "localhost" client config and every asset URL resolves to
        # http://localhost:9001 — unreachable through the hub proxy and
        # confusing to debug. Fail loud instead.
        raise RuntimeError(
            "Detected JupyterHub but xopat is not configured. Call "
            "setup_jupyterhub('https://your-hub-host') before "
            "run_server() — without it, the xopat binary uses a "
            "built-in localhost client config and every asset URL "
            "resolves to http://localhost:9001, which is not "
            "reachable through the hub proxy."
        )

    wsi_binary = get_wsi_binary()
    xopat_binary = get_xopat_binary()

    wsi = start_wsi_service(wsi_binary, data_dir=data_dir)
    try:
        xopat = start_xopat(xopat_binary)
    except Exception:
        wsi.stop()
        raise

    print(f"Servers running. Slides folder: {data_dir}")
    Server.running = Server(wsi, xopat)
    return Server.running


def display(server, slide, width="100%", height=800):
    """
    Display a slide or a full session in a Jupyter notebook iframe.

    Args:
        server: Server instance returned by run_server().
        slide:  Either a slide identifier (str) — opened via GET
                `?slides=<id>` — or a full session config (dict) with
                keys like ``data``, ``background``, ``visualizations``,
                ``params``, ``plugins`` — POSTed into the viewer.
        width:  iframe width (CSS value, default "100%").
        height: iframe height in pixels (default 800).
    """
    if isinstance(slide, str):
        slide_q = slide.replace(">", "%3E")
        if is_colab():
            display_colab(slide_q, width, height)
        elif is_jupyterhub():
            url = server.xopat_url + "/?slides=" + slide_q
            display_jupyterhub(url, slide, width, height)
        else:
            url = server.xopat_url + "/?slides=" + slide_q
            _ipy_display(IFrame(url, width=width, height=height))
        return

    if isinstance(slide, dict):
        if is_colab():
            display_colab_post(slide, width, height)
        elif is_jupyterhub():
            display_jupyterhub_post(server.xopat_url, slide, width, height)
        else:
            uid = uuid.uuid4().hex[:8]
            inputs = _session_form_inputs(slide)
            _ipy_display(HTML(f"""
<iframe name="xopat-frame-{uid}" id="xopat-frame-{uid}"
        width="{_attr(width)}" height="{_attr(height)}"
        style="border:1px solid #ccc;"></iframe>
<form id="xopat-form-{uid}" method="POST"
      action="{_attr(server.xopat_url.rstrip('/') + '/')}"
      target="xopat-frame-{uid}" style="display:none">
{inputs}
</form>
<script>document.getElementById("xopat-form-{uid}").submit();</script>
"""))
        return

    raise TypeError(
        "display(): second argument must be a slide id (str) or a session config (dict)"
    )