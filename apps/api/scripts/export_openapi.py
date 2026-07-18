"""Export FastAPI's canonical OpenAPI document for the generated web types."""
from __future__ import annotations

import json
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = Path(__file__).resolve().parents[2] / "web"
sys.path.insert(0, str(API_ROOT / "src"))

from sic_api.main import app  # noqa: E402


def main() -> None:
    destination = WEB_ROOT / "openapi.json"
    destination.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"OpenAPI exported to {destination}")


if __name__ == "__main__":
    main()
