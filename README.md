# xopat-deploy

Deployment orchestration for the [xOpat viewer](https://github.com/RationAI/xopat).
xOpat is a zero-API-dependency whole-slide image viewer; this repo packages it
together with the [WSI-Service backend](https://github.com/RationAI/WSI-Service)
for standalone or isolated environments.

> **Not the recommended way to run xOpat.** This repo hardwires a specific
> server setup and configuration. Use it for desktop installs, local Jupyter,
> JupyterHub, and Google Colab notebooks — not for production.

## What's in here

| Path | Purpose |
|---|---|
| `pypi/` | The `xopat` Python package, published on PyPI. Used from notebooks. |
| `installer_linux/`, `installer_win/` | Standalone desktop installers. |
| `notebooks/` | Demo notebooks (`demo_local_jupyter.ipynb`, `demo_jupyterhub.ipynb`). |
| `scripts/` | Build scripts for the xOpat and WSI-Service binaries. |
| `external/` | Git submodules: the xOpat viewer and the WSI-Service backend. |

## Notebook usage

The `xopat` Python package launches WSI-Service and xOpat as local
subprocesses, then exposes them as an iframe in your notebook cell.

```python
!pip install xopat
import xopat
from xopat import run_server

# before running the server, setup proxy if needed (see JupyterHub)
server = run_server(data_dir="/path/to/slides")
xopat.display(server, "slide.tiff")
# or with a full viewer session:
xopat.display(server, {"data": ["slide.tiff"], "background": [{"dataReference": 0}]})
```

> **Use `xopat.display(...)`, not bare `display(...)`.** Jupyter / Colab
> auto-inject `display` from `IPython.display` into the notebook
> namespace; calling `from xopat import display` works on some hosts but
> is reliably shadowed on Colab. Going through the module avoids the
> footgun.

The package supports three notebook hosts. `run_server()` detects the host
automatically; you only need an explicit setup call on JupyterHub.

### Local Jupyter

Just works. See `notebooks/demo_local_jupyter.ipynb`.

### Google Colab

Just works. The viewer is loaded through Colab's `serve_kernel_port_as_iframe`
helper so the wrapper is same-origin to the notebook output, which keeps
Safari (ITP) and Firefox (ETP) happy alongside Chrome.

**Known limitation: private / incognito windows.** Colab's kernel-port
proxy needs browser storage that private windows strip, so the viewer
iframe returns 404 even though `run_server()` succeeds. `display()`
shows a heads-up notice when it detects this; the fix is to open the
notebook in a regular window.

### JupyterHub

**Call `setup_jupyterhub(<hub_url>)` before `run_server()`** —
without it, the xopat binary boots with its built-in localhost
client and every asset URL resolves to `http://localhost:9001`,
unreachable through the hub proxy. `run_server()` will raise a
clear `RuntimeError` if you skip the call.

```python
import xopat
from xopat import setup_jupyterhub, run_server
setup_jupyterhub("https://hub.example.com")   # MUST come first
server = run_server()
xopat.display(server, "slide.tiff")
```

**JupyterHub admin requirement**: `jupyter-server-proxy` must be installed
in the **single-user server environment** (not the notebook kernel) so the
`/proxy/<port>/...` URL routes exist. Without it the iframe will 404
regardless of any in-notebook `pip install`. Install on the user-server
image ahead of time.

See `notebooks/demo_jupyterhub.ipynb`.

## Desktop installers

Prebuilt installers for Linux and Windows live under `installer_linux/` and
`installer_win/`. They bundle xOpat, WSI-Service, and a tray app
(`xopat_tray.py`) that manages the local servers.

## Building from source

The xOpat viewer and WSI-Service backend are git submodules under `external/`.
Build them via the scripts in `scripts/linux/` (`build_wsi_service.sh`,
`build_xopat.sh`) or `scripts/windows/` (`build_wsi_service.ps1`,
`build_xopat.ps1`). CI workflows under `.github/workflows/` produce the
published binaries and the PyPI package.

```bash
git clone --recurse-submodules https://github.com/RationAI/xopat-deploy.git
```
