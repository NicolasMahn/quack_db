"""Run Quack API with Uvicorn."""
import os

import uvicorn


def main():
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8001"))
    uvicorn.run("api.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()

