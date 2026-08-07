import os
import time
import uuid
import urllib.request
import urllib.error
from urllib.parse import quote as _urlquote

from IPython.display import HTML, display as _ipy_display

from ._post import (
    attr as _attr,
    iframe_style as _iframe_style,
    reload_toolbar as _reload_toolbar,
    session_form_inputs as _session_form_inputs,
)
from .download import clear_binary_cache, get_wsi_binary, get_xopat_binary
from .process import free_port
from .wsi import WSI_PORT, resolve_data_dir, start_wsi_service
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


def _probe(url, timeout=5):
    """GET `url`, returning (status, body) and capturing the body even on
    an HTTP error response. The xopat node server writes its exception text
    into the 500 body, so we must read error bodies rather than let
    urllib raise them away. Returns (None, "<reason>") if unreachable."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", "replace")
        except Exception:
            body = ""
        return e.code, body
    except Exception as e:
        return None, f"unreachable: {e!r}"


def _proc_health(proc):
    """Return a snapshot of a subprocess: pid, liveness, resident memory,
    open file descriptors, and the NOFILE limit. Memory/fd/limit are read
    from /proc (Linux/Colab); they come back None elsewhere. open_fds
    climbing toward nofile_soft points at EMFILE; rss_mb climbing toward the
    VM ceiling points at ENOMEM."""
    pid = proc.pid
    info = {
        "pid": pid,
        "running": proc.poll() is None,
        "returncode": proc.returncode,
        "rss_mb": None,
        "open_fds": None,
        "nofile_soft": None,
        "nofile_hard": None,
    }
    try:
        with open(f"/proc/{pid}/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    info["rss_mb"] = round(int(line.split()[1]) / 1024, 1)
                    break
    except Exception:
        pass
    try:
        info["open_fds"] = len(os.listdir(f"/proc/{pid}/fd"))
    except Exception:
        pass
    try:
        with open(f"/proc/{pid}/limits") as f:
            for line in f:
                if line.startswith("Max open files"):
                    parts = line.split()
                    info["nofile_soft"], info["nofile_hard"] = parts[3], parts[4]
                    break
    except Exception:
        pass
    return info


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

    def logs(self, name=None, n=50, full=False):
        """Print captured output from the running processes and return it
        as a dict.

        Prefers the persistent per-process log file (the complete history of
        this run) over the in-memory ring buffer, because under load the
        buffer is flooded by uvicorn access lines and a 500 traceback is
        evicted within milliseconds. The file keeps everything, so the
        traceback is still there when you look.

        Args:
            name: "xopat" or "wsi" to limit output; None prints both.
            n:    Number of trailing lines to show (ignored when full=True).
            full: Print the entire log file instead of the last `n` lines.
        """
        targets = {"xopat": self._xopat.proc, "wsi": self._wsi.proc}
        if name is not None:
            key = name.lower()
            if key not in targets:
                raise ValueError("name must be 'xopat', 'wsi', or None")
            targets = {key: targets[key]}

        out = {}
        for key, proc in targets.items():
            text = ""
            log_path = getattr(proc, "_logfile", None)
            if log_path:
                try:
                    with open(log_path, "r", errors="replace") as f:
                        lines = f.readlines()
                    text = "".join(lines if full else lines[-n:])
                except Exception:
                    text = ""
            if not text:
                # Fall back to the ring buffer (e.g. file open failed).
                captured = getattr(proc, "_captured", None)
                buf = list(captured)[-n:] if captured else []
                text = "".join(buf)
            out[key] = text
            src = log_path if log_path else "ring buffer"
            print(f"===== {key} ({src}) =====")
            print(text or "(no output captured)")
        return out

    def log_path(self, name="wsi"):
        """Return the filesystem path of a process's persistent log file
        (or None). Handy for shell access, e.g.:
            !grep -i -A40 traceback $(...)   /   !tail -f <path>
        """
        proc = {"xopat": self._xopat.proc, "wsi": self._wsi.proc}.get(name.lower())
        if proc is None:
            raise ValueError("name must be 'xopat' or 'wsi'")
        return getattr(proc, "_logfile", None)

    def diagnose(self, slide=None):
        """Probe both backends and print each status code + response body.

        Reproduces what the iframe does from the Python side so a 500 that
        shows up as a blank page becomes readable: both servers write the
        failing exception into the response body. Pass `slide` to also probe
        the real WSI request the viewer makes (`/v3/slides/info`) — that, not
        the index, is what fails when the viewer "can't connect".

        NOTE: WSI-Service `/alive` is deliberately NOT probed. In the
        PyInstaller binary it 500s on every boot because it calls
        importlib.metadata.version() for each plugin and the bundle ships no
        dist-info metadata (PackageNotFoundError) — a persistent health-route
        bug unrelated to the intermittent viewer failure. `/docs` is a
        metadata-free liveness check, and `/v3/slides/info` is the request
        that actually matters.

        Args:
            slide: optional slide id; if given, also probes the viewer at
                   `/?slides=<id>` and WSI `/v3/slides/info?slide_id=<id>`.
        """
        probes = [("xopat index", f"http://127.0.0.1:{XOPAT_PORT}/")]
        if slide is not None:
            slide_q = str(slide).replace(">", "%3E")
            slide_id = _urlquote(str(slide), safe="")
            probes.append(
                ("xopat slide", f"http://127.0.0.1:{XOPAT_PORT}/?slides={slide_q}")
            )
            probes.append(
                ("wsi slide info",
                 f"http://127.0.0.1:{WSI_PORT}/v3/slides/info?slide_id={slide_id}")
            )
        # Metadata-free WSI liveness (see note above re: /alive).
        probes.append(("wsi docs", f"http://127.0.0.1:{WSI_PORT}/docs"))

        results = {}
        for label, url in probes:
            status, body = _probe(url)
            results[label] = (status, body)
            print(f"===== {label}: {url} =====")
            print(f"status: {status}")
            snippet = body if len(body) <= 2000 else body[:2000] + "… [truncated]"
            print(snippet or "(empty body)")
        return results

    def health(self):
        """Print and return a resource snapshot of both processes: liveness,
        resident memory (MB), open file descriptors, and the open-file limit.

        Use this to tell the two failure hypotheses apart at a glance:
        open_fds approaching nofile_soft => heading for EMFILE; rss_mb
        ballooning => heading for ENOMEM. (Memory/fd require /proc, i.e.
        Linux/Colab.)"""
        out = {}
        for key, proc in (("xopat", self._xopat.proc), ("wsi", self._wsi.proc)):
            h = _proc_health(proc)
            out[key] = h
            print(
                f"{key:6} pid={h['pid']} running={h['running']} "
                f"rss={h['rss_mb']}MB fds={h['open_fds']} "
                f"nofile={h['nofile_soft']}/{h['nofile_hard']}"
            )
        return out

    def monitor(self, seconds=60, interval=2, slide=None, stop_on_error=True):
        """Poll the viewer (and optionally a real WSI slide request) while
        sampling each process's memory and fd count, printing one line per
        tick. Run this, then load 4+ viewers in the notebook, and watch which
        resource climbs and the exact moment a probe flips to 500 — that
        pins EMFILE vs ENOMEM with evidence instead of a guess.

        Args:
            seconds:       total wall-clock duration to sample.
            interval:      seconds between samples.
            slide:         if given, probes WSI `/v3/slides/info` each tick;
                           otherwise probes only the xopat index.
            stop_on_error: stop and dump the failing body on the first non-200.
        """
        if slide is not None:
            url = (f"http://127.0.0.1:{WSI_PORT}/v3/slides/info"
                   f"?slide_id={_urlquote(str(slide), safe='')}")
        else:
            url = f"http://127.0.0.1:{XOPAT_PORT}/"

        t0 = time.monotonic()
        deadline = t0 + seconds
        samples = []
        while time.monotonic() < deadline:
            status, body = _probe(url)
            h = _proc_health(self._xopat.proc)
            w = _proc_health(self._wsi.proc)
            elapsed = round(time.monotonic() - t0)
            print(
                f"[t+{elapsed:>4}s] probe={status} "
                f"xopat(rss={h['rss_mb']}MB fds={h['open_fds']}) "
                f"wsi(rss={w['rss_mb']}MB fds={w['open_fds']})"
            )
            samples.append((elapsed, status, h, w))
            if stop_on_error and status not in (200, None):
                print(f"---- {url} returned {status}; body: ----")
                print(body[:2000] if body else "(empty)")
                break
            time.sleep(interval)
        return samples


def run_server(data_dir=None):
    """
    Download (if needed) and start WSI-Service and xOpat.

    On Colab, automatically fixes missing shared libraries and
    configures the proxy-based environment.

    Args:
        data_dir: Path to the directory containing slide files. A relative
                  path is resolved against the current working directory and
                  `~` is expanded; the resolved absolute path is printed on
                  startup. Defaults to the current working directory (or
                  /content on Colab).
    Returns:
        Server instance with wsi_url and xopat_url attributes.
    """
    if Server.running is not None:
        Server.running.stop()

    if data_dir is None:
        data_dir = "/content" if is_colab() else os.getcwd()

    requested_dir = str(data_dir)
    data_dir = resolve_data_dir(data_dir)
    if not os.path.isdir(data_dir):
        print(f"Warning: slides folder does not exist: {data_dir}")
        if not os.path.isabs(os.path.expanduser(requested_dir)):
            print(f"  (you passed {requested_dir!r}; relative paths are "
                  f"resolved against the current working directory, "
                  f"{os.getcwd()})")
        print("  Tile requests will fail with HTTP 500 until it exists.")

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
""" + _reload_toolbar(uid, open_url=None, reload_mode="form", open_form=True)))
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