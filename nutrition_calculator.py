"""Deterministic weight-based nutrition calculations."""

from __future__ import annotations

from math import isfinite
from typing import Any

NUTRIENTS = ("calories", "carbohydrates", "protein", "fat", "fiber")


def calculate_nutrition(food: dict[str, Any], weight_g: float) -> dict[str, float]:
    """Scale a food's per-100-gram nutrient values to the requested weight."""
    if isinstance(weight_g, bool) or not isinstance(weight_g, (int, float)):
        raise TypeError("Weight must be a number of grams.")
    if not isfinite(weight_g) or weight_g <= 0:
        raise ValueError("Weight must be a positive, finite number of grams.")

    result: dict[str, float] = {}
    for nutrient in NUTRIENTS:
        value = float(food[nutrient])
        if not isfinite(value) or value < 0:
            raise ValueError(f"{nutrient} must be a non-negative finite value.")
        result[nutrient] = value * weight_g / 100
    return result
