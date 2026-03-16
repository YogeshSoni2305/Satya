"""
Entry point for the Satya API server.

Usage:
    python -m backend.main
    # or
    uvicorn backend.api.app:app --reload --port 8000
"""

import uvicorn


def main():
    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
