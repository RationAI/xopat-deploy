"""Shared helpers for POST-iframe session opening.

xOpat v3's `responseViewer` reads the request body twice for the
urlencoded content-type path: once via `decodeURIComponent` over the
whole body, then once via `querystring.parse` per pair. Each parsed
value is then fed through `readPostDataItem` which tries `JSON.parse`.

We therefore encode the session as one form field per top-level key,
where each value is the JSON-stringified content URL-encoded once. The
browser adds the second encoding layer on submit, matching xOpat's
double-decode.
"""

import html
import json
from urllib.parse import quote as _urlquote


def session_form_inputs(session):
    """Render a session dict as hidden <input> tags suitable for a
    form posting to xOpat's main page with the default urlencoded
    enctype. Each top-level key becomes one input."""
    if not isinstance(session, dict):
        raise TypeError("session must be a dict")
    parts = []
    for k, v in session.items():
        json_str = json.dumps(v, ensure_ascii=False)
        encoded = _urlquote(json_str, safe="")
        parts.append(
            f'<input type="hidden" name="{html.escape(str(k), quote=True)}" value="{encoded}">'
        )
    return "\n".join(parts)


def attr(value):
    """HTML-escape a string for use inside a double-quoted attribute."""
    return html.escape(str(value), quote=True)
