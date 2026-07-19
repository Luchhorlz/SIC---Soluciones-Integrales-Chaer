"""Convert the owner-approved Markdown taxonomy into the canonical JSON seed."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path

CATEGORY_PATTERN = re.compile(r"^# (\d+)\. (.+)$")
SUBCATEGORY_PATTERN = re.compile(r"^## (\d+)\.(\d+)\. (.+)$")


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", ascii_text)).strip("-")


def unique_slug(value: str, used: set[str], *, prefix: str = "", maximum: int = 160, fallback: str) -> str:
    base = slugify(value) or fallback.lower().replace("_", "-")
    candidates = [base, slugify(f"{prefix}-{base}") if prefix else base, slugify(f"{prefix}-{base}-{fallback}")]
    for candidate in candidates:
        candidate = candidate[:maximum].rstrip("-")
        if candidate and candidate not in used:
            used.add(candidate)
            return candidate
    raise ValueError(f"Unable to create a unique slug for {value!r}")


def build_seed(markdown: str) -> dict[str, object]:
    categories: list[dict[str, object]] = []
    category: dict[str, object] | None = None
    subcategory: dict[str, object] | None = None
    category_slugs: set[str] = set()
    subcategory_slugs: set[str] = set()
    service_slugs: set[str] = set()

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        category_match = CATEGORY_PATTERN.match(line)
        if category_match:
            number = int(category_match.group(1))
            if number >= 30:
                break
            code = f"CAT_{number:02d}"
            category = {
                "code": code,
                "name": category_match.group(2),
                "slug": unique_slug(category_match.group(2), category_slugs, maximum=140, fallback=code),
                "description": None,
                "icon_key": f"category-{number:02d}",
                "position": number,
                "is_active": True,
                "subcategories": [],
            }
            categories.append(category)
            subcategory = None
            continue

        subcategory_match = SUBCATEGORY_PATTERN.match(line)
        if subcategory_match and category is not None:
            category_number = int(subcategory_match.group(1))
            subcategory_number = int(subcategory_match.group(2))
            code = f"CAT_{category_number:02d}_SUB_{subcategory_number:02d}"
            subcategory = {
                "code": code,
                "name": subcategory_match.group(3),
                "slug": unique_slug(subcategory_match.group(3), subcategory_slugs, maximum=140, fallback=code),
                "description": None,
                "icon_key": f"subcategory-{category_number:02d}-{subcategory_number:02d}",
                "position": subcategory_number,
                "is_active": True,
                "services": [],
            }
            category["subcategories"].append(subcategory)  # type: ignore[union-attr]
            continue

        if line.startswith("* ") and subcategory is not None:
            services = subcategory["services"]
            assert isinstance(services, list)
            index = len(services) + 1
            code = f"{subcategory['code']}_SVC_{index:03d}"
            name = line[2:].strip()
            services.append({
                "code": code,
                "name": name,
                "slug": unique_slug(name, service_slugs, prefix=str(subcategory["slug"]), fallback=code),
                "description": None,
                "icon_key": "catalog-service",
                "is_active": True,
                "allows_fixed_price": False,
                "allows_quote": True,
                "allows_urgent": False,
            })
            continue

        if line and line != "---" and not line.startswith("#") and category is not None:
            current = category.get("description")
            category["description"] = f"{current} {line}".strip() if current else line

    if len(categories) != 29:
        raise ValueError(f"Expected 29 canonical categories, found {len(categories)}")
    for item in categories:
        subcategories = item["subcategories"]
        if not isinstance(subcategories, list) or not subcategories:
            raise ValueError(f"Category without subcategories: {item['name']}")
        for child in subcategories:
            services = child["services"]
            if not services:
                raise ValueError(f"Subcategory without services: {child['name']}")
    return {"version": 1, "categories": categories}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--seed", type=Path, default=Path("seeds/taxonomy.json"))
    parser.add_argument("--documentation", type=Path, default=Path("docs/taxonomy.md"))
    parser.add_argument("--manifest", type=Path, default=Path("apps/web/src/data/taxonomy-manifest.json"))
    parser.add_argument("--web-catalog", type=Path, default=Path("apps/web/src/data/taxonomy.json"))
    args = parser.parse_args()
    markdown = args.source.read_text(encoding="utf-8")
    seed = build_seed(markdown)
    args.seed.parent.mkdir(parents=True, exist_ok=True)
    args.documentation.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.web_catalog.parent.mkdir(parents=True, exist_ok=True)
    seed_text = json.dumps(seed, ensure_ascii=False, indent=2) + "\n"
    args.seed.write_text(seed_text, encoding="utf-8")
    args.documentation.write_text(markdown.rstrip() + "\n", encoding="utf-8")
    subcategories = sum(len(category["subcategories"]) for category in seed["categories"])
    services = sum(len(subcategory["services"]) for category in seed["categories"] for subcategory in category["subcategories"])
    manifest = {"version": seed["version"], "categories": len(seed["categories"]), "subcategories": subcategories, "services": services, "seed_sha256": hashlib.sha256(seed_text.encode("utf-8")).hexdigest()}
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    # Next keeps this canonical snapshot as a read-only fallback when the local
    # API/database is not running (for example, during a visual preview).
    args.web_catalog.write_text(seed_text, encoding="utf-8")
    print(f"Generated {len(seed['categories'])} categories, {subcategories} subcategories and {services} services")


if __name__ == "__main__":
    main()
