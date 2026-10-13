"""Load and search the bundled local food nutrition reference."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

DATA_FILE = Path(__file__).resolve().parent / "data" / "food_nutrition.csv"
NUMERIC_FIELDS = ("calories", "carbohydrates", "protein", "fat", "fiber")


def load_foods(path: Path = DATA_FILE) -> list[dict[str, Any]]:
    """Read the documented CSV catalog and validate its required fields."""
    foods: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        for row_number, row in enumerate(csv.DictReader(source), start=2):
            try:
                if not row["food_id"] or not row["name"] or not row["preparation"]:
                    raise ValueError("food_id, name, and preparation are required")
                food: dict[str, Any] = dict(row)
                for field in NUMERIC_FIELDS:
                    food[field] = float(row[field])
                    if food[field] < 0:
                        raise ValueError(f"{field} cannot be negative")
                foods.append(food)
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"Invalid food data at {path}:{row_number}: {exc}") from exc
    if not foods:
        raise ValueError(f"No food data found in {path}")
    if len({food["food_id"] for food in foods}) != len(foods):
        raise ValueError(f"Food IDs must be unique in {path}")
    return foods


def search_foods(foods: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    """Find foods by name, preparation, or category, case-insensitively."""
    terms = query.strip().casefold().split()
    if not terms:
        return foods
    return [
        food
        for food in foods
        if all(
            term in " ".join(
                str(food[field]) for field in ("name", "preparation", "category")
            ).casefold()
            for term in terms
        )
    ]
