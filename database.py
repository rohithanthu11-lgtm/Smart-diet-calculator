"""SQLite persistence for saved meals, meal history, and daily totals."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterator

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "nutrition_history.sqlite3"
DB_PATH = Path(os.environ.get("DIET_CALCULATOR_DB", DEFAULT_DB_PATH))
NUTRIENTS = ("calories", "carbohydrates", "protein", "fat", "fiber")


def _connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def _database(db_path: Path) -> Iterator[sqlite3.Connection]:
    connection = _connect(db_path)
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_database(db_path: Path = DB_PATH) -> None:
    """Create the meal tables if they do not exist."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _database(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS meals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                consumed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS meal_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meal_id INTEGER NOT NULL REFERENCES meals(id) ON DELETE CASCADE,
                food_id TEXT NOT NULL,
                food_name TEXT NOT NULL,
                preparation TEXT NOT NULL,
                weight_g REAL NOT NULL CHECK (weight_g > 0),
                calories REAL NOT NULL,
                carbohydrates REAL NOT NULL,
                protein REAL NOT NULL,
                fat REAL NOT NULL,
                fiber REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_meals_consumed_at ON meals(consumed_at);
            """
        )


def save_meal(
    name: str, items: list[dict[str, Any]], db_path: Path = DB_PATH
) -> int:
    """Persist one complete meal and all its calculated items atomically."""
    if not name.strip():
        raise ValueError("Enter a name for this meal.")
    if not items:
        raise ValueError("Add at least one food before saving a meal.")
    consumed_at = datetime.now().astimezone().isoformat(timespec="seconds")
    with _database(db_path) as connection:
        cursor = connection.execute(
            "INSERT INTO meals (name, consumed_at) VALUES (?, ?)",
            (name.strip(), consumed_at),
        )
        meal_id = int(cursor.lastrowid)
        for item in items:
            nutrition = item["nutrition"]
            connection.execute(
                """
                INSERT INTO meal_items (
                    meal_id, food_id, food_name, preparation, weight_g,
                    calories, carbohydrates, protein, fat, fiber
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    meal_id,
                    item["food_id"],
                    item["name"],
                    item["preparation"],
                    item["weight_g"],
                    *(nutrition[nutrient] for nutrient in NUTRIENTS),
                ),
            )
    return meal_id


def get_daily_totals(
    for_date: date | None = None, db_path: Path = DB_PATH
) -> dict[str, float]:
    """Return saved nutrition totals for a local calendar date."""
    target_date = (for_date or date.today()).isoformat()
    with _database(db_path) as connection:
        row = connection.execute(
            """
            SELECT
                COALESCE(SUM(i.calories), 0) AS calories,
                COALESCE(SUM(i.carbohydrates), 0) AS carbohydrates,
                COALESCE(SUM(i.protein), 0) AS protein,
                COALESCE(SUM(i.fat), 0) AS fat,
                COALESCE(SUM(i.fiber), 0) AS fiber
            FROM meals m
            JOIN meal_items i ON i.meal_id = m.id
            WHERE substr(m.consumed_at, 1, 10) = ?
            """,
            (target_date,),
        ).fetchone()
    return {nutrient: float(row[nutrient]) for nutrient in NUTRIENTS}


def get_meal_history(limit: int = 20, db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    """Return recent saved meals with their items and calculated totals."""
    if limit <= 0:
        raise ValueError("History limit must be positive.")
    with _database(db_path) as connection:
        meals = connection.execute(
            """
            SELECT m.id, m.name, m.consumed_at,
                COALESCE(SUM(i.calories), 0) AS calories,
                COALESCE(SUM(i.carbohydrates), 0) AS carbohydrates,
                COALESCE(SUM(i.protein), 0) AS protein,
                COALESCE(SUM(i.fat), 0) AS fat,
                COALESCE(SUM(i.fiber), 0) AS fiber
            FROM meals m
            LEFT JOIN meal_items i ON i.meal_id = m.id
            GROUP BY m.id
            ORDER BY m.consumed_at DESC, m.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        results: list[dict[str, Any]] = []
        for meal in meals:
            items = connection.execute(
                """
                SELECT food_name, preparation, weight_g, calories,
                    carbohydrates, protein, fat, fiber
                FROM meal_items
                WHERE meal_id = ?
                ORDER BY id
                """,
                (meal["id"],),
            ).fetchall()
            result = dict(meal)
            result["items"] = [dict(item) for item in items]
            results.append(result)
    return results


def export_csv_rows(items: list[dict[str, Any]]) -> str:
    """Serialize meal items to a portable CSV string."""
    import csv
    import io

    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        [
            "Food",
            "Preparation",
            "Weight (g)",
            "Calories (kcal)",
            "Carbohydrates (g)",
            "Protein (g)",
            "Fat (g)",
            "Fiber (g)",
        ]
    )
    for item in items:
        nutrition = item["nutrition"]
        writer.writerow(
            [
                item["name"],
                item["preparation"],
                item["weight_g"],
                *(nutrition[nutrient] for nutrient in NUTRIENTS),
            ]
        )
    return output.getvalue()
