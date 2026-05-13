import os

from IPython.display import IFrame, display as _ipy_display

from .download import get_wsi_binary, get_xopat_binary
from .wsi import start_wsi_service, WSI_PORT
from .xopat import start_xopat, XOPAT_PORT
from .colab import is_colab, setup_colab, display_colab
from .jupyterhub import is_jupyterhub, setup_jupyterhub, display_jupyterhub

__all__ = ["setup_jupyterhub", "setup_colab", "run_server", "display", "Server"]


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

    if is_colab():
        setup_colab()

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
    Display a slide in a Jupyter notebook iframe.

    Args:
        server: Server instance returned by run_server().
        slide:  Slide identifier (path or URL) passed to xOpat.
        width:  iframe width (CSS value, default "100%").
        height: iframe height in pixels (default 800).
    """
    slide_q = slide.replace(">", "%3E")

    if is_colab():
        display_colab(slide_q, width, height)
    elif is_jupyterhub():
        url = server.xopat_url + "/?slides=" + slide_q
        display_jupyterhub(url, slide, width, height)
    else:
        url = server.xopat_url + "/?slides=" + slide_q
        _ipy_display(IFrame(url, width=width, height=height))