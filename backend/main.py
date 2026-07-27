"""Entry point.

Local dev:  python main.py          (reload on by default)
Production: RELOAD=false python main.py  (or just run inside Docker - see Dockerfile)
"""
import os

import uvicorn

_reload = os.getenv("RELOAD", "false").lower() == "true"

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=_reload,
        reload_dirs=["app"] if _reload else None,
    )
