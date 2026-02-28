import os
from pathlib import Path

here = Path(__file__).resolve().parent

# This file runs from external/wsi-service/
repo_root = (here / ".." / "..").resolve()
libs = (repo_root / "libs" / "windows").resolve()

if libs.exists():
    os.add_dll_directory(str(libs))

import uvicorn
from wsi_service.app import app

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)