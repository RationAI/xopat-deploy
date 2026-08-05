"""Google Colab integration for xOpat.

Handles Colab-specific setup: proxy configuration, missing shared
libraries, and iframe display via the proxyPort JS API.
"""

import json
import os
import subprocess
import uuid
from urllib.parse import quote as _urlquote

from ._post import (
    attr as _attr,
    STALL_HINT_HTML as _STALL_HINT_HTML,
    ACCUMULATION_WARN_AT as _ACCUMULATION_WARN_AT,
)
from .download import get_binaries_dir, get_wsi_binary
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
            "extra-tutorials": {"enabled": True},
        },
        "modules": {
            "rationai-wsi-tile-source": {"permaLoad": True},
            "geotiff": {"permaLoad": True},
        },
    }


    env_path = get_binaries_dir() / "xopat_env.json"
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text(json.dumps(config, indent=2))
    os.environ["XOPAT_ENV"] = str(env_path)
    os.environ["XOPAT_CROSS_SITE_COOKIES"] = "true"
    print("Configured for Google Colab.")


def _warn_if_private_browsing():
    """Emit a one-time HTML notice in the cell output if the browser is
    in private/incognito mode. Colab's kernel-port proxy relies on
    storage that incognito strips, so the iframe document fetch 404s
    even though run_server() and everything else looks fine. We can't
    fix it from this side (no first-party context is reachable); the
    best we can do is tell the user clearly instead of leaving them
    with a silent broken iframe.

    Detection heuristic: navigator.storage.estimate().quota is much
    smaller in incognito (Chrome caps it around 120 MB) than in normal
    mode (typically multiple GB). False positives on storage-constrained
    devices are possible — the notice is worded as a heads-up, not a
    hard block."""
    from IPython.display import HTML, display as _ipy_display
    _ipy_display(HTML("""
<div id="xopat-incognito-warn" style="display:none;border:1px solid #d97706;
     background:#fef3c7;color:#78350f;padding:10px 14px;border-radius:6px;
     font-family:sans-serif;line-height:1.45;max-width:720px;margin:0 0 8px 0;">
  <strong>Private / Incognito browsing detected.</strong>
  Google Colab's kernel-port proxy needs storage that private/incognito
  windows strip, so the xopat viewer iframe will fail to load (proxy
  returns 404). Open this notebook in a regular browser window instead.
</div>
<script>
(async function() {
    try {
        if (!navigator.storage || !navigator.storage.estimate) return;
        const {quota} = await navigator.storage.estimate();
        if (typeof quota === 'number' && quota < 200 * 1024 * 1024) {
            const el = document.getElementById('xopat-incognito-warn');
            if (el) el.style.display = 'block';
        }
    } catch (e) { /* ignore */ }
})();
</script>
"""))


def _proxy_port_url():
    """Return the absolute *.googleusercontent.com proxy URL for XOPAT_PORT,
    or '' if the lookup fails. Used to build an "Open in new tab" escape
    hatch — a real tab bypasses Colab's parent-frame postMessage bridge
    entirely, which is where the input-routing wedge lives."""
    try:
        from google.colab.output import eval_js
        url = eval_js(f"google.colab.kernel.proxyPort({XOPAT_PORT})")
        return (url or "").rstrip("/")
    except Exception:
        return ""


def _render_recovery_toolbar(path):
    """Render a thin toolbar BELOW the just-mounted Colab kernel-port
    iframe. Carries two recovery affordances for the silent
    "iframe loads but input stops reaching it" freeze:

      * Reload viewer: locates the most recent iframe in this output cell
        whose src matches a Colab proxy host, then removes and reinserts
        it. Pure src= reassignment is not enough — Colab's parent bridge
        keys its postMessage routing off the old element identity; only a
        fresh node forces re-registration.
      * Open in new tab: opens the same proxyPort URL in a real tab where
        Colab's bridge is not in the path at all. Last-resort recovery
        when even reload doesn't unstick events.

    Also surfaces an accumulation warning once ACCUMULATION_WARN_AT proxy
    iframes are present in the document — stale iframes from prior cell
    runs are a frequent cause of "input swallowed" in Colab.

    No height clamp here: Colab renders cell outputs inside a sandboxed
    `outputframe.html`, so `vh` is relative to that frame (often a small
    auto-sized strip) rather than the browser viewport — applying
    `min(800px, 70vh)` collapses the viewer to ~100 px. The default
    `display(height=None)` therefore falls through to the literal pixel
    height in Colab; callers wanting a smaller embed pass an explicit
    `height=` value."""
    base = _proxy_port_url()
    abs_url = (base + path) if base else ""
    uid = uuid.uuid4().hex[:8]
    from IPython.display import HTML, display as _ipy_display
    _ipy_display(HTML(f"""
<div id="xopat-bar-{uid}" style="display:flex;align-items:center;gap:8px;
     margin:6px 0;font-family:sans-serif;font-size:13px;color:#374151;">
  <button id="xopat-reload-{uid}" type="button"
          style="padding:4px 10px;border:1px solid #d1d5db;background:#f9fafb;
                 border-radius:4px;cursor:pointer;">Reload viewer</button>
  <a id="xopat-open-{uid}" href="{_attr(abs_url)}" target="_blank" rel="noopener"
     style="padding:4px 10px;border:1px solid #d1d5db;background:#f9fafb;
            border-radius:4px;color:#374151;text-decoration:none;">Open in new tab</a>
  <span id="xopat-status-{uid}" style="margin-left:6px;color:#6b7280;">Loading…</span>
</div>
{_STALL_HINT_HTML}
<script>
(function() {{
    const script = document.currentScript;
    const status = document.getElementById('xopat-status-{uid}');
    const proxyHostSel = 'iframe[src*="googleusercontent.com"], iframe[src*="prod.colab.dev"]';

    function findOwnIframe() {{
        // Walk up from our script to find the nearest ancestor that
        // contains a Colab proxy iframe — scopes us to this output cell
        // rather than picking up iframes from sibling cells.
        let node = script;
        while (node) {{
            const parent = node.parentElement;
            if (!parent) break;
            const frames = parent.querySelectorAll(proxyHostSel);
            if (frames.length) return frames[frames.length - 1];
            node = parent;
        }}
        return null;
    }}

    function updateAccumulationWarning() {{
        const all = document.querySelectorAll(proxyHostSel);
        // Threshold, not `> 1`: the selector matches every proxy iframe in
        // the document, including stale outputs from prior runs that no
        // longer host a working viewer. Only warn on a real pile-up.
        if (all.length >= {_ACCUMULATION_WARN_AT}) {{
            status.textContent = all.length + ' viewer iframes in this notebook — '
                + 'older outputs may swallow input. Try Cell → Clear All Output.';
            status.style.color = '#a16207';
        }}
    }}

    const iframe = findOwnIframe();
    if (iframe) {{
        // iframes don't have a synchronous "loaded" flag (.complete is for
        // <img>); listen for load. If the iframe was already loaded before
        // our script ran (cached), the load event won't fire — fall back
        // to a short timer that flips the status optimistically.
        let settled = false;
        const markReady = () => {{
            if (settled) return;
            settled = true;
            status.textContent = 'Viewer ready.';
            updateAccumulationWarning();
        }};
        iframe.addEventListener('load', markReady, {{once: true}});
        setTimeout(markReady, 3000);
    }} else {{
        status.textContent = 'Could not locate viewer iframe.';
    }}
    updateAccumulationWarning();

    document.getElementById('xopat-reload-{uid}').addEventListener('click', function() {{
        const f = findOwnIframe();
        if (!f) {{ status.textContent = 'Could not find iframe to reload.'; return; }}
        status.textContent = 'Reloading…';
        status.style.color = '#6b7280';
        const parent = f.parentNode;
        const next = f.nextSibling;
        const src = f.src;
        parent.removeChild(f);
        // Build a fresh element rather than reassigning src on the old one.
        // Colab's parent postMessage bridge ties routing to the original
        // node; a brand-new node forces it to re-register the listener.
        const fresh = document.createElement('iframe');
        for (const a of f.attributes) fresh.setAttribute(a.name, a.value);
        fresh.src = src;
        fresh.addEventListener('load', function() {{
            status.textContent = 'Reloaded.';
            updateAccumulationWarning();
        }}, {{once: true}});
        parent.insertBefore(fresh, next);
    }});
}})();
</script>
"""))


def _display_colab_with_recovery(path, width, height):
    """Shared body of display_colab / display_colab_post.

    Order matters:
      1. clear_output(wait=True) — defends against the same cell stacking
         multiple iframes when display() is called more than once per cell.
         Cell re-runs already clear; this catches in-cell repeat calls.
      2. private-browsing warning — must come before the iframe so the
         user sees it even if the iframe then 404s.
      3. serve_kernel_port_as_iframe — Colab appends its iframe here.
      4. recovery toolbar — appended after, sits below the iframe."""
    from IPython.display import clear_output
    from google.colab.output import serve_kernel_port_as_iframe
    clear_output(wait=True)
    _warn_if_private_browsing()
    serve_kernel_port_as_iframe(
        XOPAT_PORT,
        path=path,
        width=str(width),
        height=str(height),
    )
    _render_recovery_toolbar(path)


def display_colab(slide_q, width, height, cap_height):
    """Display a slide in Google Colab via serve_kernel_port_as_iframe.

    Uses the Colab-supplied helper so the iframe wrapper runs same-origin
    to the notebook output. Raw proxyPort URLs are on
    *.googleusercontent.com, which is 3rd-party to colab.research.google.com
    — Safari (ITP) and Firefox (ETP) block the auth cookies for that
    context and the proxy returns 404. The wrapper sidesteps that.

    Incognito/private windows still fail the proxy auth even with the
    wrapper; _warn_if_private_browsing renders a notice in those cases.

    Known freeze mode: the iframe sometimes stops receiving mouse and
    keyboard input even though the page inside is still alive (status
    bar updates, animations keep running). Cause is browser-tab-scoped
    state in Colab's parent postMessage bridge that survives kernel
    restarts. The toolbar rendered alongside the iframe carries a
    "Reload viewer" button (re-creates the iframe element, which forces
    Colab to re-register its event routing) and an "Open in new tab"
    link (bypasses the bridge entirely). If neither works, closing and
    reopening the browser tab is the only known full recovery.

    `cap_height` is accepted for signature parity with the other display
    backends but ignored: Colab's outputframe.html sandbox makes `vh`
    units meaningless, so the default-height auto-cap collapses the
    viewer to a strip. Callers wanting a smaller embed pass an explicit
    pixel `height=` instead."""
    del cap_height
    _display_colab_with_recovery(f"/?slides={slide_q}", width, height)


def display_colab_post(session, width, height, cap_height):
    """Display a full session in Google Colab via URL-hash GET.

    Session is serialized to JSON and placed in the URL fragment, which
    is never sent to the network — xopat parses it client-side. Uses
    serve_kernel_port_as_iframe for the same Safari/Firefox reason as
    display_colab, and ships the same Reload/Open-in-new-tab recovery
    toolbar for the input-wedge case described there.

    `cap_height` is ignored on Colab — see display_colab for why."""
    del cap_height
    encoded = _urlquote(json.dumps(session), safe="")
    _display_colab_with_recovery(f"/#{encoded}", width, height)


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