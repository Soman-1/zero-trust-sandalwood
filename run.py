"""Agroforestry Zero Trust Platform Launcher: Runs the FastAPI backend server."""

import sys
import uvicorn
from app.core.config import settings

def main():
    print("=" * 65)
    print(f"  {settings.APP_NAME} v{settings.APP_VERSION}")
    print("  Zero Trust Agroforestry & Sandalwood AI Platform")
    print("=" * 65)
    print("  Backend API:      http://127.0.0.1:8000")
    print("  Interactive Docs: http://127.0.0.1:8000/docs")
    print("  Frontend UI:      http://127.0.0.1:3000")
    print("=" * 65)

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )

if __name__ == "__main__":
    main()
