"""Shared helpers for POST-iframe session opening.

xopat's POST entry point parses the urlencoded request body into a
key-value map, then JSON-parses each value. It looks up the session
under a single top-level `visualization` key. We therefore emit a
single form field named `visualization` whose value is the
JSON-stringified session, URL-encoded once (the browser adds the
second encoding layer on submit, matching the server's decode).
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


def reload_toolbar(uid, open_url, reload_mode):
    """Render a Reload / Open-in-new-tab toolbar below a viewer iframe.

    Used by the JupyterHub and local-Jupyter display backends. Both run
    same-origin with the iframe document, so reload is either a plain
    `src` re-assignment or a re-submit of the companion POST form — no
    Colab postMessage-bridge node-recreation dance needed.

    The toolbar also carries a hint about white/blank viewports and an
    accumulation warning: rendering the WSI viewer multiple times in the
    same notebook tab keeps multiple WebGL contexts alive, which is a
    common cause of stalls on top of plain memory pressure.

    Args:
        uid: matches the iframe id `xopat-frame-<uid>` (and, for
             `reload_mode="form"`, the form id `xopat-form-<uid>`).
        open_url: URL for "Open in new tab". Pass None/"" to hide
                  the link (POST sessions can't be re-opened by URL alone).
        reload_mode: 'src' to re-assign the iframe src; 'form' to
                     re-submit `xopat-form-<uid>`.
    """
    if open_url:
        open_link = (
            f'<a id="xopat-open-{uid}" href="{attr(open_url)}" target="_blank" '
            f'rel="noopener" style="padding:4px 10px;border:1px solid #d1d5db;'
            f'background:#f9fafb;border-radius:4px;color:#374151;'
            f'text-decoration:none;">Open in new tab</a>'
        )
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
        if (all.length > 1) {{
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
}})();
</script>
"""
