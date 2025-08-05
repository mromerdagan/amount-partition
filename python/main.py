# main.py

import uvicorn
import os


if __name__ == "__main__":
    port = int(os.environ.get("BUDGET_MGR_PORT", 8000))
    debug = os.environ.get("BUDGET_MGR_DEBUG", "false").lower() == "true"
    if debug:
        print(f"Starting server in debug mode on port {port}")
    else:
        print(f"Starting server on port {port}")
    
    uvicorn.run("amount_partition.rest_api:app", host="0.0.0", port=port, reload=debug)

