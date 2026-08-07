"""Shared helpers for POST-iframe session opening.

xopat's POST entry point parses the urlencoded request body into a
key-value map, then JSON-parses each value. It looks up the session
under a single top-level `visualization` key. We therefore emit a
single form field named `visualization` whose value is the
JSON-stringified session, URL-encoded once (the browser adds the
second encoding layer on submit, matching the server's decode).

TODO(jupyterhub): the 2-encode / 2-decode chain is brittle.
xopat's Node entrypoint (external/xopat/server/node/index.js around
the `application/x-www-form-urlencoded` case) does
`decodeURIComponent(rawBody)` AND `querystring.parse(...)` — two decode
layers, so it requires the wire body to be 2x percent-encoded. That
holds for direct loopback (local Jupyter) and Colab's
`serve_kernel_port_as_iframe` (no intermediate decoder), but on
JupyterHub deployments with an extra hop in front of the single-user
server (CHP, or more commonly an nginx/traefik ingress) the body
arrives at Node 1x-decoded already. Node's two decodes then over-
strip, the value reaches `JSON.parse` still 1x-encoded, and the
client surfaces:

    "JSON Error: SyntaxError: Unexpected token '%', "%7B%22para"...
     is not valid JSON"

(`%7B%22` = `{"`.) jupyter-server-proxy itself is NOT the culprit —
its handler forwards `self.request.body` as raw bytes — so the fix
can't live there. Options when this becomes worth fixing:

  1. (preferred) Stop using a form POST for the JupyterHub path.
     Emit a small `<script>` that `fetch()`-POSTs the session as
     `application/json` to the proxied xopat URL, then load the
     HTML response into the iframe via `srcdoc` with an injected
     `<base href="…">` so relative asset URLs still resolve through
     the proxy. That hits Node's `application/json` branch
     (plain `JSON.parse(rawBody)`), which is invariant under
     however many decode layers sit between browser and Node.
     Only `display_jupyterhub_post` needs to change; the local
     and Colab paths are fine as-is.
  2. Patch xopat's Node entrypoint to drop the upfront
     `decodeURIComponent(rawBody)` and rely on `querystring.parse`
     alone (single decode). Requires re-shipping the xopat binary
     and breaks any current consumer that relies on the 2-decode
     contract — riskier than option 1.
  3. Base64-encode the JSON into a `visualization_b64` field.
     URL-safe base64 is invariant under any number of percent-
     encode/decode passes. Needs a tiny server-side decode hook in
     xopat to map `visualization_b64` → `visualization`.

Until then: the workaround is to deploy JupyterHub without an
ingress that decodes request bodies, or to use the GET-by-slide-id
path (`display(server, "slide.tiff")`) which doesn't go through this
POST chain at all.
"""

import html
import json
from urllib.parse import quote as _urlquote


def session_form_inputs(session):
    """Render a session dict as a single hidden <input name="visualization">
    whose value is the JSON-encoded session. xopat reads the POST body
    as `{visualization: <session>}` — see the module docstring."""
    if not isinstance(session, dict):
        raise TypeError("session must be a dict")
    json_str = json.dumps(session, ensure_ascii=False)
    encoded = _urlquote(json_str, safe="")
    return f'<input type="hidden" name="visualization" value="{encoded}">'


def attr(value):
    """HTML-escape a string for use inside a double-quoted attribute."""
    return html.escape(str(value), quote=True)


def iframe_style(width, height, cap_height):
    """CSS `style` string for embedded viewer iframes.

    When `cap_height` is True (the caller used display()'s default height),
    the height is `min({height}px, 70vh)` so the viewer never exceeds 70 %
    of the browser viewport — important on laptops where 800 px crowds
    out the rest of the notebook. When False, the caller's explicit
    height is honored as-is, even on short windows (their override wins).

    Width is passed through unchanged: it's already a CSS value
    ("100%", "800px", …)."""
    if cap_height:
        return (f"width:{width};height:min({int(height)}px, 70vh);"
                f"max-height:70vh;border:1px solid #ccc;")
    return f"width:{width};height:{height}px;border:1px solid #ccc;"


# Number of viewer iframes in the notebook DOM at which the toolbar starts
# warning about accumulation. Shared with the Colab backend.
ACCUMULATION_WARN_AT = 6


STALL_HINT_HTML = (
    '<div style="margin:4px 0 10px 0;font-family:sans-serif;font-size:12px;'
    'color:#6b7280;line-height:1.45;max-width:720px;">'
    'Viewer blank or unresponsive? Click <strong>Reload viewer</strong>, '
    'or <strong>Open in new tab</strong> if reload doesn\'t help. '
    'Running multiple viewers in one notebook keeps several WebGL contexts '
    'alive and can stall rendering — if neither helps, clear older cell '
    'outputs (Cell &rarr; All Output &rarr; Clear).'
    '</div>'
)


def reload_toolbar(uid, open_url, reload_mode, open_form=False):
    """Render a Reload / Open-in-new-tab toolbar below a viewer iframe.

    Used by the JupyterHub and local-Jupyter display backends. Both run
    same-origin with the iframe document, so reload is either a plain
    `src` re-assignment or a re-submit of the companion POST form — no
    Colab postMessage-bridge node-recreation dance needed.

    The toolbar also carries a hint about white/blank viewports and an
    accumulation warning: rendering the WSI viewer multiple times in the
    same notebook tab keeps multiple WebGL contexts alive, which is a
    common cause of stalls on top of plain memory pressure. The warning
    only fires from ACCUMULATION_WARN_AT iframes up — the DOM count
    includes dead nodes, so a small number means nothing.

    Args:
        uid: matches the iframe id `xopat-frame-<uid>` (and, for
             `reload_mode="form"`, the form id `xopat-form-<uid>`).
        open_url: URL for "Open in new tab" as a plain link. Used by the
                  GET-by-slide-id paths, where the whole viewer state
                  lives in the URL.
        reload_mode: 'src' to re-assign the iframe src; 'form' to
                     re-submit `xopat-form-<uid>`.
        open_form: POST-session variant of the same button. The session
                   lives in the request body, not in a URL, so there is
                   nothing to put in an href — instead the button clones
                   `xopat-form-<uid>` and re-submits the clone with
                   `target="_blank"`. Ignored when `open_url` is set.
    """
    open_script = ""
    if open_url:
        open_link = (
            f'<a id="xopat-open-{uid}" href="{attr(open_url)}" target="_blank" '
            f'rel="noopener" style="padding:4px 10px;border:1px solid #d1d5db;'
            f'background:#f9fafb;border-radius:4px;color:#374151;'
            f'text-decoration:none;">Open in new tab</a>'
        )
    elif open_form:
        open_link = (
            f'<button id="xopat-open-{uid}" type="button" '
            f'style="padding:4px 10px;border:1px solid #d1d5db;'
            f'background:#f9fafb;border-radius:4px;color:#374151;'
            f'cursor:pointer;font:inherit;">Open in new tab</button>'
        )
        # A POST session has no URL to link to, so the new tab has to be
        # opened by re-submitting the form. Two details matter:
        #  * submit from inside the click handler — the user gesture is
        #    what keeps popup blockers from swallowing the new tab;
        #  * submit a *clone*, not the original: flipping the original's
        #    target to _blank would leave it pointed away from the
        #    embedded iframe and break the Reload button next to us.
        open_script = f"""
    document.getElementById('xopat-open-{uid}').addEventListener('click', function() {{
        const form = document.getElementById('xopat-form-{uid}');
        if (!form) {{ status.textContent = 'Form not found.'; return; }}
        const clone = form.cloneNode(true);
        clone.id = 'xopat-form-{uid}-tab';
        clone.target = '_blank';
        clone.rel = 'noopener';
        document.body.appendChild(clone);
        clone.submit();
        setTimeout(function() {{ clone.remove(); }}, 0);
    }});
"""
    else:
        open_link = ""

    if reload_mode == "form":
        reload_action = (
            f"const form = document.getElementById('xopat-form-{uid}');"
            f"if (!form) {{ status.textContent = 'Form not found.'; return; }}"
            f"status.textContent = 'Reloading…';"
            f"form.submit();"
        )
    else:
        reload_action = (
            f"const f = document.getElementById('xopat-frame-{uid}');"
            f"if (!f) {{ status.textContent = 'Iframe not found.'; return; }}"
            f"status.textContent = 'Reloading…';"
            # Same-origin: re-assigning src is enough. No need for the
            # destroy-and-recreate dance the Colab backend uses to defeat
            # the parent-frame postMessage bridge.
            f"f.src = f.src;"
        )

    return f"""
<div id="xopat-bar-{uid}" style="display:flex;align-items:center;gap:8px;
     margin:6px 0;font-family:sans-serif;font-size:13px;color:#374151;">
  <button id="xopat-reload-{uid}" type="button"
          style="padding:4px 10px;border:1px solid #d1d5db;background:#f9fafb;
                 border-radius:4px;cursor:pointer;">Reload viewer</button>
  {open_link}
  <span id="xopat-status-{uid}" style="margin-left:6px;color:#6b7280;"></span>
</div>
{STALL_HINT_HTML}
<script>
(function() {{
    const status = document.getElementById('xopat-status-{uid}');
    function updateAccumulationWarning() {{
        const all = document.querySelectorAll('iframe[id^="xopat-frame-"]');
        // Threshold, not `> 1`: the selector also matches dead nodes —
        // stale outputs scrolled out of view and iframe shells restored
        // from a saved .ipynb (their <script> never re-runs, so they host
        // no viewer). A couple of those are normal and harmless; only a
        // real pile-up is worth warning about.
        if (all.length >= {ACCUMULATION_WARN_AT}) {{
            status.textContent = all.length + ' viewers open in this notebook — '
                + 'rendering may stall. Clear older outputs.';
            status.style.color = '#a16207';
        }} else {{
            status.textContent = '';
            status.style.color = '#6b7280';
        }}
    }}
    updateAccumulationWarning();
    document.getElementById('xopat-reload-{uid}').addEventListener('click', function() {{
        {reload_action}
        setTimeout(updateAccumulationWarning, 500);
    }});
{open_script}
}})();
</script>
"""
