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
