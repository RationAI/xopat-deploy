import os
import uuid

from IPython.display import HTML, display as _ipy_display

from ._post import (
    attr as _attr,
    iframe_style as _iframe_style,
    reload_toolbar as _reload_toolbar,
    session_form_inputs as _session_form_inputs,
)
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
    "display_link",
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


_DEFAULT_HEIGHT = 800


def display(server, slide, width="100%", height=None):
    """
    Display a slide or a full session in a Jupyter notebook iframe.

    Args:
        server: Server instance returned by run_server().
        slide:  Either a slide identifier (str) — opened via GET
                `?slides=<id>` — or a full session config (dict) with
                keys like ``data``, ``background``, ``visualizations``,
                ``params``, ``plugins`` — POSTed into the viewer.
        width:  iframe width (CSS value, default "100%").
        height: iframe height in pixels. Default (None) renders at 800 px
                but is capped at 70 % of the browser window so the viewer
                doesn't crowd out the notebook on short screens. Pass an
                explicit number (e.g. ``height=1200``) to opt out of the
                cap entirely.
    """
    cap_height = height is None
    height_value = _DEFAULT_HEIGHT if cap_height else height

    if isinstance(slide, str):
        slide_q = slide.replace(">", "%3E")
        if is_colab():
            display_colab(slide_q, width, height_value, cap_height)
        elif is_jupyterhub():
            url = server.xopat_url + "/?slides=" + slide_q
            display_jupyterhub(url, slide, width, height_value, cap_height)
        else:
            uid = uuid.uuid4().hex[:8]
            url = server.xopat_url + "/?slides=" + slide_q
            _ipy_display(HTML(
                f'<iframe id="xopat-frame-{uid}" src="{_attr(url)}" '
                f'style="{_iframe_style(width, height_value, cap_height)}"></iframe>'
                + _reload_toolbar(uid, url, reload_mode="src")
            ))
        return

    if isinstance(slide, dict):
        if is_colab():
            display_colab_post(slide, width, height_value, cap_height)
        elif is_jupyterhub():
            display_jupyterhub_post(
                server.xopat_url, slide, width, height_value, cap_height
            )
        else:
            uid = uuid.uuid4().hex[:8]
            inputs = _session_form_inputs(slide)
            _ipy_display(HTML(f"""
<iframe name="xopat-frame-{uid}" id="xopat-frame-{uid}"
        style="{_iframe_style(width, height_value, cap_height)}"></iframe>
<form id="xopat-form-{uid}" method="POST"
      action="{_attr(server.xopat_url.rstrip('/') + '/')}"
      target="xopat-frame-{uid}" style="display:none">
{inputs}
</form>
<script>document.getElementById("xopat-form-{uid}").submit();</script>
""" + _reload_toolbar(uid, open_url=None, reload_mode="form")))
        return

    raise TypeError(
        "display(): second argument must be a slide id (str) or a session config (dict)"
    )


def display_link(server, path, label=None):
    """Render a clickable button that opens the xopat viewer at `path`
    in a new browser tab.

    Args:
        server: Server instance returned by run_server().
        path:   URL path under the xopat root (leading slash optional).
                Example: "dev_setup".
        label:  Button text. Defaults to `path` with underscores/dashes
                turned into spaces and Title-Cased ("dev_setup" → "Dev Setup").

    The new tab is the user's best escape hatch in Colab when the
    in-notebook iframe wedges, and is the only viable surface for pages
    like dev_setup that aren't meant to be embedded next to a slide.
    """
    p = "/" + path.lstrip("/")

    if is_colab():
        # Colab: server.xopat_url is http://127.0.0.1:9001, unreachable
        # from the browser. The user-clickable URL lives behind Colab's
        # kernel-port proxy; same lookup the recovery toolbar uses.
        from .colab import _proxy_port_url
        base = _proxy_port_url()
        url = (base + p) if base else ""
    else:
        # JupyterHub: relative `/proxy/<port>` prefix — resolves against
        # the notebook origin. Local Jupyter: absolute 127.0.0.1 URL.
        # Both are directly usable as anchor hrefs.
        url = server.xopat_url.rstrip("/") + p

    if label is None:
        label = path.strip("/").replace("_", " ").replace("-", " ").title() or "Open"

    _ipy_display(HTML(
        f'<a href="{_attr(url)}" target="_blank" rel="noopener" '
        f'style="display:inline-block;padding:4px 10px;margin:4px 4px 4px 0;'
        f'border:1px solid #d1d5db;background:#f9fafb;border-radius:4px;'
        f'color:#374151;text-decoration:none;font-family:sans-serif;'
        f'font-size:13px;">{_attr(label)}</a>'
    ))