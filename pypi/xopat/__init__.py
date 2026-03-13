from IPython.display import IFrame, display as _ipy_display

from .download import get_wsi_binary, get_xopat_binary
from .wsi import start_wsi_service
from .xopat import start_xopat


class Server:
    def __init__(self, wsi, xopat):
        self._wsi = wsi
        self._xopat = xopat
        self.wsi_url = wsi.base_url
        self.xopat_url = xopat.base_url

    def stop(self):
        try:
            self._xopat.stop()
        finally:
            self._wsi.stop()


def run_server(data_dir=None):
    """
    Downloads binaries if needed, then starts WSI-Service and xOpat.

    Args:
        data_dir: path to the folder with WSI slides (sets WS_DATA_DIR)

    Returns:
        Server handle with .stop() method
    """
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
    Displays a WSI slide in Jupyter via xOpat.

    Args:
        server: Server handle from run_server()
        slide:  slide path or identifier
        width:  IFrame width (default "100%")
        height: IFrame height in pixels (default 800)
    """
    slide_q = slide.replace(">", "%3E")
    url = server.xopat_url + "/?slides=" + slide_q
    _ipy_display(IFrame(url, width=width, height=height))