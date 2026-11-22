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

## Releases

Publishing a release `X.Y.Z` in [RationAI/xopat](https://github.com/RationAI/xopat)
starts `.github/workflows/release.yml` here (through a `repository_dispatch`
sent by xopat's `deploy-dispatch.yml`). One run produces one release
**`vX.Y.Z`**:

| Asset | |
|---|---|
| `xopat_linux_vX.Y.Z.zip`, `xopat_windows_vX.Y.Z.zip` | Standalone server binaries, built from the xOpat tag `X.Y.Z` |
| `xOpat-Installer-Linux-X.Y.Z` | Linux installer |
| `xOpat-Installer-Windows-X.Y.Z.exe` | Windows installer, signed through SignPath |
| `*.sha256` | Checksum of each file |

It then publishes the pip package and writes a "Desktop installers and pip"
block into the xOpat release notes. The pip package keeps its own version
line (`0.1.N`, bumped by one per release) and is pinned to the binaries of
exactly this release; the mapping is recorded in the release notes here.
WSI-Service keeps its independent `wsi-v*` releases; the newest is bundled.

A deploy-only fix for an already released version is a manual run with
`revision: 2` — it publishes `vX.Y.Z-deploy.2` and moves the link in the
xOpat release. A published release is never rebuilt in place.

Manual runs default to `dry_run`: everything is built and signed with the
test certificate, and the release is left as a **draft**.

### Code signing

- The installer is built, uploaded and submitted to SignPath within one job
  of `release.yml`. SignPath verifies the artifact's origin against that
  run, so those steps must stay together, in that workflow, in this
  repository, on GitHub-hosted runners.
- The signing policy is the repository variable `SIGNPATH_SIGNING_POLICY`
  (default `test-signing`). Pre-releases and dry runs always use
  `test-signing`.
- **Which release is really signed is decided per release, in GitHub.** Any
  policy other than `test-signing` pauses the run at the job *Approve
  production signature* until a reviewer of the environment
  `production-signing` approves it (no runner is held; GitHub waits up to
  30 days). Approve = the production signature is requested. Reject = the
  run stops and nothing is published; to ship that version with the test
  certificate instead, start the workflow by hand with
  `signing_policy: test-signing`. The run refuses to start with a
  production policy if that environment has no required reviewers.
- **Recognising the request in SignPath.** Only approved runs reach the
  production policy, so every request waiting there is a release someone
  approved here; tests, dry runs and pre-releases arrive under
  `test-signing`. The Windows job additionally prints a notice and a summary
  table *before* submitting: file name (it carries the version), SHA-256 of
  the unsigned installer, commit, and the run link — compare them with the
  origin data SignPath shows on the request.
- The release stays a draft until the signed installer came back and its
  signature was checked. There is no unsigned fallback.
- If the SignPath policy itself needs approval, the job waits for it, up to
  about 5.5 hours. If the wait runs out, use **Re-run failed jobs**: only
  the Windows installer is rebuilt and a new request is submitted, without
  asking for the GitHub approval again. SignPath evaluates a limited number
  of re-runs and a project can forbid them (`disallow_reruns`); in that case
  start a fresh run.

### Setup

| Where | Name | Purpose |
|---|---|---|
| xopat, secret | `XOPAT_DEPLOY_TOKEN` | Contents: write on xopat-deploy — sends the dispatch |
| xopat-deploy, secret | `XOPAT_RELEASE_TOKEN` | Contents: write on xopat — writes the link block |
| xopat-deploy, secret | `SIGNPATH_API_TOKEN` | SignPath submitter token |
| xopat-deploy, variable | `SIGNPATH_SIGNING_POLICY` | Optional, e.g. `release-signing` |
| xopat-deploy, environment | `production-signing` | Required reviewers = who may approve a production signature. Needed as soon as the variable above is set |

The `build-*` and `pypi-publish` workflows remain for building a single
piece by hand.
