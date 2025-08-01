# main.py

import uvicorn
import os

# TODO: Add a `--cli` flag to allow `main.py` be entry point for both rest and cli

if __name__ == "__main__":
    port = int(os.environ.get("BUDGET_MGR_PORT", 8000))
    uvicorn.run("amount_partition.rest_api:app", host="0.0.0.0", port=port)

