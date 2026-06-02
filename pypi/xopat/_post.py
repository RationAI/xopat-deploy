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
