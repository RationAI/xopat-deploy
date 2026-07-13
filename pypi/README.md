<h1 align="center">xopat</h1>
<p align="center">
  <sup>Launch the <a href="https://xopat.org"><b>xOpat</b></a> whole-slide image viewer and its
  <a href="https://github.com/RationAI/WSI-Service">WSI-Service</a> backend straight from a
  Jupyter, Google&nbsp;Colab, or JupyterHub notebook — in two lines.</sup>
</p>

<p align="center">
  <img alt="The xOpat Viewer" src="https://raw.githubusercontent.com/RationAI/xopat/master/docs/assets/xopat-banner-v3.png" width="820" />
</p>

<p align="center">
  <a href="https://pypi.org/project/xopat/"><img alt="PyPI" src="https://img.shields.io/pypi/v/xopat.svg"></a>
  <a href="https://pypi.org/project/xopat/"><img alt="Python versions" src="https://img.shields.io/pypi/pyversions/xopat.svg"></a>
  <a href="https://github.com/RationAI/xopat-deploy/blob/main/LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
</p>

---

## The viewer

[**xOpat**](https://xopat.org) — the e**X**plainable **O**pen **P**athology **A**nalysis **T**ool —
is a browser-based **whole-slide imaging framework** for digital pathology. Whole-slide images
(WSIs) are digitized microscopy slides: gigapixel, multi-gigabyte, pyramid-structured pictures that
no ordinary image viewer can open. xOpat streams them tile-by-tile, like an enhanced
[OpenSeadragon](https://openseadragon.github.io/), and adds the layer of interpretation that
pathology and AI research actually need on top of the raw pixels.

Crucially, **xOpat is not a viewer bolted to one platform — it is a *viewing framework*.** It has
**no hardwired image backend**: you point it at whatever WSI server can read your slides (the
RationAI [WSI-Service](https://github.com/RationAI/WSI-Service) is the reference server this package
ships, but any protocol xOpat can resolve works, and you can add a new one with a single file). That
keeps you out of the platform lock-in that usually comes with picking a slide viewer.

**What the viewer gives you:**

- 🔬 **Gigapixel WSI streaming** — smooth deep-zoom over multi-gigabyte pyramidal slides, only the
  visible tiles are fetched.
- 🗂️ **Raster *and* vector overlays** — Photoshop-style **visualization layers** (WebGL shaders:
  heatmaps, colormaps, edges…) and versatile annotations drawn over the same slide, so AI outputs,
  segmentations, and derived data sit registered on the tissue.
- 🪟 **Multiple synchronized viewports** — several slides/contexts side by side in a grid, each with
  its own background and visualization stack.
- 🧩 **Plugins & modules** — annotations, tutorials, OIDC auth, AI chat assistants, storytelling,
  ICC profiles, and more — load only what a deployment needs.
- ⚙️ **Deep configuration** — shape everything from a static `env.json` down to a per-session URL or
  POST body (the [session config](#displaying-slides) this package sends).

## What this package does

This `xopat` PyPI package is the **notebook launcher** for that viewer. It exists so you can go from
a folder of slides to a live, interactive viewer inside a notebook cell — with **no Docker, no
server to stand up, and no configuration**. It downloads self-contained xOpat and WSI-Service
binaries, starts them as local subprocesses, and embeds the running viewer as an iframe:

```python
!pip install xopat

import xopat
from xopat import run_server

server = run_server(data_dir="/path/to/slides")   # downloads binaries on first run, then starts them
xopat.display(server, "slide.tiff")               # embed the interactive viewer on a slide
```

`run_server()` **auto-detects** its host (local Jupyter, Google Colab, or JupyterHub) and wires up
the right proxy and cross-origin setup for each — so the same two lines work whether you are on a
laptop, on Colab, or on a shared hub. Typical uses: **inspecting slides next to your analysis code**,
**overlaying model predictions on the tissue they came from**, and **sharing a reproducible viewer
session** in a notebook others can rerun.

> **Note — a convenience launcher, not a deployment.** This package deliberately hardwires one
> server setup (WSI-Service + a fixed xOpat config) tuned for notebooks and local/desktop viewing.
> That is exactly what makes it two lines. To **host xOpat for real** — connect your own image
> servers, enable auth, run Node / PHP / server-less — do a proper deployment instead; see the
> [full documentation](https://xopat.org).

---

## Requirements

- **Python ≥ 3.9**, running inside a Jupyter-like host (Jupyter, JupyterLab, Google Colab, or
  JupyterHub). `IPython.display` is used for embedding and already ships with every such host.
- **Linux or Windows** — the launcher downloads a matching prebuilt binary for your platform.
- No pip dependencies are installed: the package deliberately declares none so it can't disturb a
  host's pinned `ipython` (this previously broke Colab's runtime).

Binaries are fetched from [GitHub Releases](https://github.com/RationAI/xopat-deploy/releases) on
first use and cached under `~/.xopat` (or `/content/.xopat` on Colab, so they survive a kernel
restart).

---

## Quick start by host

`run_server()` detects the host automatically. You only need an explicit setup call on JupyterHub.

### Local Jupyter

Just works.

```python
import xopat
from xopat import run_server

server = run_server(data_dir="/path/to/slides")
xopat.display(server, "slide.tiff")
...
server.stop()
```

### Google Colab

Just works. The viewer is served through Colab's `serve_kernel_port_as_iframe` helper so the
iframe is same-origin with the notebook output — which keeps Safari (ITP) and Firefox (ETP) happy
alongside Chrome.

```python
!pip install xopat
import xopat
from xopat import run_server

server = run_server()                  # defaults to /content on Colab
xopat.display(server, "slide.tiff")
```

> **Known limitation — private / incognito windows.** Colab's kernel-port proxy needs browser
> storage that private windows strip, so the iframe 404s even though `run_server()` succeeds.
> `display()` shows a heads-up when it detects this; open the notebook in a normal window.

### JupyterHub

**Call `setup_jupyterhub(<hub_url>)` before `run_server()`.** Without it, the xopat binary boots
its built-in localhost config and every asset URL resolves to `http://localhost:9001` —
unreachable through the hub proxy. `run_server()` raises a clear `RuntimeError` if you skip it.

```python
import xopat
from xopat import setup_jupyterhub, run_server

setup_jupyterhub("https://hub.example.com")   # MUST come first
server = run_server()
xopat.display(server, "slide.tiff")
```

> **Admin requirement:** [`jupyter-server-proxy`](https://github.com/jupyterhub/jupyter-server-proxy)
> must be installed in the **single-user server environment** (not the notebook kernel) so the
> `/proxy/<port>/...` routes exist. An in-notebook `pip install` is too late; bake it into the
> user-server image.

---

## Displaying slides

`xopat.display()` is your window into the viewer from Python. It accepts either a **slide id** (the
quick path) or a full **session config** (the powerful path — the same dynamic configuration the
viewer accepts as a URL/POST, letting you script exactly what the viewer opens with).

```python
# 1. A single slide by id — quick look, opened via GET ?slides=<id>
xopat.display(server, "slide.tiff")

# 2. A full viewer session (POSTed into the viewer). `data` is the list of
#    slides; backgrounds and visualization layers reference them by index
#    (dataReference), so one data list feeds many layers.
xopat.display(server, {
    "data": ["slide.tiff", "prediction_heatmap.tiff"],
    "background": [{"dataReference": 0}],                 # the tissue slide underneath
    "visualizations": [{                                  # WebGL overlay stack on top
        "name": "Model output",
        "shaders": {
            "heatmap": {"type": "heatmap", "dataReferences": [1]},
        },
    }],
})

# Sizing: height defaults to 800px, capped at 70% of the window.
# Pass an explicit height to opt out of the cap.
xopat.display(server, "slide.tiff", width="100%", height=1200)
```

> **Sessions are how you overlay AI results.** A **background** is the raster slide shown underneath
> (usually the WSI itself); a **visualization** is a Photoshop-style stack of WebGL **shader** layers
> drawn over it (`heatmap`, `colormap`, `edge`, …). Point a shader's `dataReferences` at a
> prediction/heatmap slide in `data` and it renders registered on the tissue — this is the core
> "explainable pathology" workflow the viewer is built for. See
> [Viewer Configuration](https://xopat.org) for the full session schema (visualizations, plugins,
> params, annotations).

> **Use `xopat.display(...)`, not a bare `display(...)`.** Jupyter and Colab auto-inject
> `display` from `IPython.display` into the notebook namespace, which reliably shadows
> `from xopat import display` on Colab. Going through the module avoids the footgun.

Open a viewer page in a new browser tab (the escape hatch when an in-notebook iframe wedges, and
the only surface for non-embeddable pages like `dev_setup`):

```python
xopat.display_link(server, "dev_setup")        # renders a clickable button
```

---

## API reference

### Top-level functions

| Function | Description |
|---|---|
| `run_server(data_dir=None)` | Download (if needed) and start WSI-Service + xOpat. Auto-detects and configures the host. `data_dir` defaults to the CWD (or `/content` on Colab). Returns a `Server`. |
| `display(server, slide, width="100%", height=None)` | Embed a slide (`str`) or a session (`dict`) as an iframe in the current cell. |
| `display_link(server, path, label=None)` | Render a button that opens the viewer at `path` in a new tab. |
| `setup_jupyterhub(jupyterhub_host)` | Configure xOpat for JupyterHub. **Call before `run_server()`** on a hub. |
| `setup_colab()` | Configure xOpat for Colab. Called automatically by `run_server()`; rarely needed directly. |
| `clear_binary_cache()` | Delete cached binaries so the next `run_server()` re-downloads them (config files are left intact). |

### The `Server` object

`run_server()` returns a `Server` exposing `wsi_url`, `xopat_url`, and:

| Method | Description |
|---|---|
| `stop()` | Stop both the xOpat and WSI-Service subprocesses. |
| `logs(name=None, n=50, full=False)` | Print captured process output (prefers the persistent per-process log file over the in-memory ring buffer). `name` is `"xopat"`, `"wsi"`, or `None` for both. |
| `log_path(name="wsi")` | Filesystem path of a process's log file (handy for `!tail -f` / `!grep`). |
| `diagnose(slide=None)` | Probe both backends and print each status code + response body — turns a blank 500 iframe into a readable traceback. Pass `slide` to also probe the real `/v3/slides/info` request. |
| `health()` | Snapshot each process: liveness, RSS memory, open FDs, and the open-file limit (memory/FD data needs `/proc`, i.e. Linux/Colab). |
| `monitor(seconds=60, interval=2, slide=None, stop_on_error=True)` | Poll the viewer while sampling memory and FD counts, one line per tick — pins down EMFILE-vs-ENOMEM style failures with evidence. |

---

## Troubleshooting

**The iframe is blank or shows a 500.** Probe the backends from Python — both servers write the
failing exception into the response body:

```python
server.diagnose("slide.tiff")     # prints status + body for the viewer and the WSI slide request
server.logs("wsi", n=100)         # tail the WSI-Service log
```

**Suspect a resource leak with several viewers open** (climbing memory or file descriptors):

```python
server.monitor(seconds=120, slide="slide.tiff")   # then open a few viewers and watch what climbs
```

**A binary looks stale** (e.g. a release was re-uploaded under the same tag):

```python
import xopat
xopat.clear_binary_cache()        # next run_server() re-downloads
```

---

## Links

- **Documentation:** <https://xopat.org>
- **xOpat viewer:** <https://github.com/RationAI/xopat>
- **WSI-Service backend:** <https://github.com/RationAI/WSI-Service>
- **This launcher & binaries:** <https://github.com/RationAI/xopat-deploy>
- **Demo notebooks:** [`notebooks/`](https://github.com/RationAI/xopat-deploy/tree/main/notebooks)
  (`demo_local_jupyter.ipynb`, `demo_jupyterhub.ipynb`)

## License

MIT © [RationAI Research Group](https://rationai.fi.muni.cz). See
[LICENSE](https://github.com/RationAI/xopat-deploy/blob/main/LICENSE).
