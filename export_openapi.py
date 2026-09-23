import json
import sys
from pathlib import Path

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app

def export_schema() -> None:
    output_file = backend_dir / "openapi.json"
    openapi_schema = app.openapi()
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2)
        
    print(f"OpenAPI schema successfully exported to {output_file}")

if __name__ == "__main__":
    export_schema()
