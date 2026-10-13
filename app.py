"""Streamlit interface for the Smart Diet Calculator."""

from __future__ import annotations

import sqlite3
from uuid import uuid4

import pandas as pd
import plotly.express as px
import streamlit as st

from database import (
    export_csv_rows,
    get_daily_totals,
    get_meal_history,
    initialize_database,
    save_meal,
)
from food_database import load_foods, search_foods
from nutrition_calculator import NUTRIENTS, calculate_nutrition

st.set_page_config(
    page_title="Smart Diet Calculator",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp { background: #f6f8f5; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }
    h1, h2, h3 { font-family: ui-sans-serif, system-ui, sans-serif; color: #173c30; }
    .hero {
        background: linear-gradient(115deg, #123f32 0%, #237456 100%);
        padding: 2rem 2.25rem; border-radius: 20px; color: white;
        margin: .25rem 0 1.6rem; box-shadow: 0 12px 35px #1a57451a;
    }
    .hero h1 { color: white; margin: 0 0 .4rem; font-size: 2.15rem; }
    .hero p { color: #d3e9dd; margin: 0; font-size: 1rem; }
    .stButton > button[kind="primary"] {
        background: #21825b; border: 0; border-radius: 10px;
        font-weight: 700; min-height: 2.7rem;
    }
    [data-testid="stMetric"] {
        background: white; padding: 1rem 1.1rem; border-radius: 14px;
        border: 1px solid #e5ece6; box-shadow: 0 3px 12px #173c3008;
    }
    [data-testid="stMetricLabel"] { color: #597166; }
    div[data-testid="stExpander"] { border-color: #e5ece6; border-radius: 12px; }
    </style>
    """,
    unsafe_allow_html=True,
)

try:
    foods = load_foods()
    initialize_database()
except (OSError, ValueError, sqlite3.Error) as exc:
    st.error(f"Could not load the food catalog or initialize meal history: {exc}")
    st.stop()

if "meal_items" not in st.session_state:
    st.session_state.meal_items = []

st.markdown(
    """
    <div class="hero">
      <h1>🥗 Smart Diet Calculator</h1>
      <p>Build a meal, see nutrition by weight, and keep track of your day.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption(
    "Reference values are per 100 g. Actual nutrition varies with brands, "
    "ingredients, water content, and preparation. Approximate catalog entries "
    "are identified in the food details."
)

try:
    daily_totals = get_daily_totals()
except sqlite3.Error as exc:
    st.error(f"Could not load today's saved nutrition: {exc}")
    st.stop()
st.subheader("Today's saved nutrition")
daily_columns = st.columns(5)
daily_labels = (
    ("calories", "Calories", "kcal", 0),
    ("carbohydrates", "Carbohydrates", "g", 1),
    ("protein", "Protein", "g", 1),
    ("fat", "Fat", "g", 1),
    ("fiber", "Fiber", "g", 1),
)
for column, (nutrient, label, unit, precision) in zip(daily_columns, daily_labels):
    column.metric(label, f"{daily_totals[nutrient]:.{precision}f} {unit}")
st.caption("Daily totals include meals saved in this app, not the current unsaved meal.")

st.divider()
st.subheader("Add food to your meal")
search_query = st.text_input(
    "Search foods",
    placeholder="Try rice cooked, chicken, banana, or idli",
    help="Search by food name, preparation, or category.",
)
matches = search_foods(foods, search_query)
if not matches:
    st.warning("No matching foods in the local catalog. Try a different search.")
else:
    options = {
        f"{food['name']} — {food['preparation']}": food for food in matches
    }
    selected_label = st.selectbox("Food and preparation", list(options))
    selected_food = options[selected_label]
    source_label = selected_food["source"]
    st.caption(
        f"Per 100 g: {selected_food['calories']:g} kcal · "
        f"{selected_food['carbohydrates']:g} g carbs · "
        f"{selected_food['protein']:g} g protein · "
        f"{selected_food['fat']:g} g fat · "
        f"{selected_food['fiber']:g} g fiber. "
        f"Source: {source_label}. {selected_food['basis']}."
    )
    with st.form("add_food_form"):
        weight_g = st.number_input(
            "Weight (grams)",
            min_value=0.1,
            value=100.0,
            step=10.0,
            format="%.1f",
            help="Enter a positive weight in grams.",
        )
        add_food = st.form_submit_button(
            "Calculate Nutrition", type="primary", width="stretch"
        )
    if add_food:
        try:
            nutrition = calculate_nutrition(selected_food, weight_g)
            st.session_state.meal_items.append(
                {
                    "key": uuid4().hex,
                    "food_id": selected_food["food_id"],
                    "name": selected_food["name"],
                    "preparation": selected_food["preparation"],
                    "source": source_label,
                    "basis": selected_food["basis"],
                    "weight_g": float(weight_g),
                    "nutrition": nutrition,
                }
            )
            st.toast(f"Added {selected_food['name']} ({weight_g:g} g) to your meal.")
        except (TypeError, ValueError) as exc:
            st.error(str(exc))

st.divider()
st.subheader("Current meal")
if not st.session_state.meal_items:
    st.info("Your meal is empty. Search for a food above and calculate its nutrition.")
else:
    for item in list(st.session_state.meal_items):
        item_key = item["key"]
        title_column, weight_column, update_column, delete_column = st.columns(
            [4, 1.3, 1, 0.8], vertical_alignment="bottom"
        )
        title_column.markdown(
            f"**{item['name']}** · {item['preparation']}  \n"
            f"<small>{item['nutrition']['calories']:.0f} kcal · "
            f"{item['nutrition']['carbohydrates']:.1f} g carbs · "
            f"{item['nutrition']['protein']:.1f} g protein</small>",
            unsafe_allow_html=True,
        )
        weight_key = f"weight_{item_key}"
        if weight_key not in st.session_state:
            st.session_state[weight_key] = float(item["weight_g"])
        new_weight = weight_column.number_input(
            "Weight (g)",
            min_value=0.1,
            step=10.0,
            format="%.1f",
            key=weight_key,
        )
        if update_column.button("Update", key=f"update_{item_key}"):
            try:
                item["weight_g"] = float(new_weight)
                food_record = next(food for food in foods if food["food_id"] == item["food_id"])
                item["nutrition"] = calculate_nutrition(food_record, new_weight)
                st.rerun()
            except (StopIteration, TypeError, ValueError) as exc:
                st.error(f"Could not update {item['name']}: {exc}")
        if delete_column.button("Remove", key=f"remove_{item_key}"):
            st.session_state.meal_items = [
                current
                for current in st.session_state.meal_items
                if current["key"] != item_key
            ]
            st.rerun()
        with st.expander(f"{item['name']} nutrition details"):
            st.write(f"Data source: {item['source']}. {item['basis']}.")
            st.json(item["nutrition"])

    meal_totals = {
        nutrient: sum(item["nutrition"][nutrient] for item in st.session_state.meal_items)
        for nutrient in NUTRIENTS
    }
    st.markdown("#### Meal totals")
    meal_columns = st.columns(5)
    for column, (nutrient, label, unit, precision) in zip(meal_columns, daily_labels):
        column.metric(label, f"{meal_totals[nutrient]:.{precision}f} {unit}")

    chart_columns = st.columns([1, 1.5])
    macro_data = pd.DataFrame(
        [
            {"Nutrient": label, "Grams": meal_totals[nutrient]}
            for nutrient, label in (
                ("carbohydrates", "Carbohydrates"),
                ("protein", "Protein"),
                ("fat", "Fat"),
            )
        ]
    )
    macro_data = macro_data[macro_data["Grams"] > 0]
    if not macro_data.empty:
        chart = px.pie(
            macro_data,
            values="Grams",
            names="Nutrient",
            hole=0.58,
            color_discrete_sequence=["#4ca77a", "#e4a64b", "#dc765a"],
        )
        chart.update_layout(
            margin=dict(l=0, r=0, t=12, b=0),
            legend_title_text="Macro (g)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        chart_columns[0].plotly_chart(chart, width="stretch")
    summary_rows = [
        {
            "Food": item["name"],
            "Preparation": item["preparation"],
            "Weight (g)": item["weight_g"],
            "Calories (kcal)": round(item["nutrition"]["calories"]),
            "Carbs (g)": round(item["nutrition"]["carbohydrates"], 1),
            "Protein (g)": round(item["nutrition"]["protein"], 1),
            "Fat (g)": round(item["nutrition"]["fat"], 1),
            "Fiber (g)": round(item["nutrition"]["fiber"], 1),
        }
        for item in st.session_state.meal_items
    ]
    chart_columns[1].dataframe(
        pd.DataFrame(summary_rows), hide_index=True, width="stretch"
    )

    save_column, export_column, clear_column = st.columns([2, 1, 1])
    meal_name = save_column.text_input("Meal name", value="Meal")
    if save_column.button("Save meal to today's log", type="primary"):
        try:
            save_meal(meal_name, st.session_state.meal_items)
            st.session_state.meal_items = []
            st.success("Meal saved to your daily summary and history.")
            st.rerun()
        except (ValueError, sqlite3.Error) as exc:
            st.error(str(exc))
    export_column.download_button(
        "Download meal CSV",
        data=export_csv_rows(st.session_state.meal_items),
        file_name="meal_nutrition.csv",
        mime="text/csv",
        width="stretch",
    )
    if clear_column.button("Clear current meal", width="stretch"):
        st.session_state.meal_items = []
        st.rerun()

st.divider()
st.subheader("Calculation history")
try:
    history = get_meal_history()
except sqlite3.Error as exc:
    st.error(f"Could not load meal history: {exc}")
    st.stop()
if history:
    for saved_meal in history:
        timestamp = saved_meal["consumed_at"].replace("T", " ")
        with st.expander(
            f"{saved_meal['name']} · {timestamp} · {saved_meal['calories']:.0f} kcal"
        ):
            st.dataframe(
                pd.DataFrame(saved_meal["items"]),
                hide_index=True,
                width="stretch",
            )
else:
    st.caption("Saved meals will appear here.")

st.caption(
    "Nutrition values are reference estimates, not medical advice. "
    "Use package labels or a qualified professional for dietary decisions."
)
