# Smart Diet Calculator

A local Streamlit application that scales per-100-gram food nutrition to the
weight you enter, builds meals, tracks saved meals by day in SQLite, and exports
the current meal as CSV.

## Nutrition data and accuracy

The bundled `data/food_nutrition.csv` is a small, editable local reference, not a
laboratory analysis or a substitute for a product label. Basic generic foods
are attributed to USDA FoodData Central SR Legacy and values are rounded.
Chapati, roti, idli, dosa, paneer, and plain curd are marked as approximate
recipe/product references because their values depend on ingredients, water,
brand, and cooking fat. Check the `basis` and `source` fields in the catalog
and the in-app notice before relying on a value. The underlying USDA reference
is available at [FoodData Central](https://fdc.nal.usda.gov/).

Raw and cooked rice are separate entries, as are other foods whose preparation
materially changes their nutrition. The app does not use an AI model to create
nutrition values; calculations use the documented catalog and the deterministic
formula `(value per 100 g × entered grams) / 100`.

## Windows setup (VS Code)

1. Install Python 3.10 or newer and open this project folder in VS Code.
2. In the VS Code terminal, create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell prevents activation, run `.\.venv\Scripts\python.exe` instead
   of activating the environment.
3. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

4. Start the application:

   ```powershell
   python -m streamlit run app.py
   ```

5. Open the local URL printed in the terminal (normally
   `http://localhost:8501`).

In VS Code, choose the `.venv` interpreter with **Python: Select Interpreter**.
The SQLite history is stored in `nutrition_history.sqlite3` beside the app by
default. To store it elsewhere, set `DIET_CALCULATOR_DB` to a full Windows path
before starting Streamlit.

## Tests

Run the calculation, catalog, and SQLite tests from the project folder:

```powershell
python -m unittest discover -s tests -v
```
