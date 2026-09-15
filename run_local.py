import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
os.environ.setdefault("THE_THREE_MAPS_ENV", "development")
os.environ.setdefault("THE_THREE_MAPS_DB_PATH", "the_three_maps_local.sqlite3")

import uvicorn

if __name__ == "__main__":
    uvicorn.run("three_maps.api.app:app", host="127.0.0.1", port=8000, reload=False)
