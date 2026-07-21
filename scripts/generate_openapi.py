import json
import os
import sys

# Add project root and cmd/api to sys.path to enable imports without built-in cmd collision
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../cmd/api")))

import main

app = main.app


def generate_openapi() -> None:
    # Ensure target docs directory exists
    os.makedirs("docs", exist_ok=True)

    # Extract the OpenAPI schema dictionary
    openapi_schema = app.openapi()

    # Save as JSON
    output_path = "docs/openapi.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2)

    print(f"Successfully exported OpenAPI schema to {output_path}")


if __name__ == "__main__":
    generate_openapi()
