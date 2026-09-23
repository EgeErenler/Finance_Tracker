"""
Professional Expense Tracker
============================

A menu-driven expense tracker that runs in Google Colab or a terminal.

Features:
  - SQLite database for storing expenses (add, view, sort, edit, delete)
  - Bar and pie charts of spending by category (Matplotlib)
  - SQL summary report (SUM, AVG, MAX, MIN, COUNT)
  - Seaborn charts: histogram, box plot and scatter plot
  - Linear regression trend analysis (scikit-learn)
  - Bulk import from CSV or Excel files (Google Colab)
"""

# =====================================================================
# ── Core libraries ───────────────────────────────────────────
# sqlite3: Built-in library to manage the local SQL database file.
import sqlite3
# matplotlib: The base library for creating static, animated, and interactive visualizations.
import matplotlib.pyplot as plt
# mpatches: Used for creating custom legend handles (shapes/colors) in charts.
import matplotlib.patches as mpatches
# datetime: Essential for parsing and validating date strings (YYYY-MM-DD).
from datetime import datetime
# time: Used here to manage the output buffer, specifically to prevent Google Colab input freezes.
import time

# ── Data & ML libraries ─────────────────────────────────────
# numpy: Used for numerical operations, specifically for handling arrays in Linear Regression.
import numpy as np
# pandas: Powerful data manipulation tool used to convert SQL rows into easy-to-read DataFrames.
import pandas as pd
# seaborn: High-level interface built on Matplotlib for more attractive statistical graphics.
import seaborn as sns
# LinearRegression: From Scikit-Learn; used to calculate the spending trend line (y = mx + c).
from sklearn.linear_model import LinearRegression

# ── Google Colab file upload helper ─────────────────────────
# This block detects if the code is running in a Colab environment to enable file picking features.
try:
    from google.colab import files
    IN_COLAB = True
except ImportError:
    # If running locally (not in Colab), file upload is disabled gracefully
    IN_COLAB = False


# ============================================================
# DATABASE LAYER
# Handles all interactions with the SQLite database.
# ============================================================

class ExpenseDB:
    """Manages the SQLite database for expense records."""

    def __init__(self, db_name: str = "expenses.db"):
        """
        Initialize the database connection and create the
        expenses table if it does not already exist.
        """
        # Connect to the SQLite file (creates it if it doesn't exist).
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self._create_table()

    def _create_table(self):
        """Create the expenses table (runs only on first launch)."""
        # Define the schema: ID (Auto-increment), Date, Category, Description, and Amount.
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT    NOT NULL,
                category    TEXT    NOT NULL,
                description TEXT,
                amount      REAL    NOT NULL
            )
        """)
        self.conn.commit()

    # --- CRUD Operations (Create, Read, Update, Delete) ---

    def add_expense(self, date: str, category: str, description: str, amount: float):
        """Insert a new expense record into the database."""
        self.cursor.execute(
            "INSERT INTO expenses (date, category, description, amount) VALUES (?, ?, ?, ?)",
            (date, category, description, amount)
        )
        self.conn.commit()

    def bulk_insert(self, rows: list):
        """
        Insert multiple expense records at once.
        rows: list of (date, category, description, amount) tuples.
        Used by the CSV/Excel import feature for speed.
        """
        self.cursor.executemany(
            "INSERT INTO expenses (date, category, description, amount) VALUES (?, ?, ?, ?)",
            rows
        )
        self.conn.commit()

    def get_all_expenses(self, sort_by: str = "date") -> list:
        """
        Fetch all expense records.
        sort_by: column name — 'date', 'category', or 'amount'
        """
        # NOTE: sort_by is validated before this call, so f-string is safe here.
        self.cursor.execute(
            f"SELECT id, date, category, description, amount FROM expenses ORDER BY {sort_by}"
        )
        return self.cursor.fetchall()

    def get_expense_by_id(self, exp_id: int):
        """Fetch a single expense record by its ID for editing or deletion."""
        self.cursor.execute("SELECT * FROM expenses WHERE id = ?", (exp_id,))
        return self.cursor.fetchone()

    def update_expense(self, exp_id: int, date: str, category: str,
                       description: str, amount: float):
        """Update all fields of an existing expense record by its primary key ID."""
        self.cursor.execute(
            "UPDATE expenses SET date=?, category=?, description=?, amount=? WHERE id=?",
            (date, category, description, amount, exp_id)
        )
        self.conn.commit()

    def delete_expense(self, exp_id: int):
        """Remove an expense record from the database by ID."""
        self.cursor.execute("DELETE FROM expenses WHERE id=?", (exp_id,))
        self.conn.commit()

    def get_category_totals(self) -> list:
        """
        Aggregate total spending per category.
        Returns a list of (category, total_amount) tuples used for Pie/Bar charts.
        """
        self.cursor.execute(
            "SELECT category, SUM(amount) FROM expenses GROUP BY category ORDER BY SUM(amount) DESC"
        )
        return self.cursor.fetchall()

    def get_total_spent(self) -> float:
        """Return the sum of all expense amounts in the database."""
        self.cursor.execute("SELECT SUM(amount) FROM expenses")
        result = self.cursor.fetchone()[0]
        return result if result else 0.0

    def get_as_dataframe(self) -> pd.DataFrame:
        """
        Load all expenses from DB into a pandas DataFrame.
        Used by Seaborn charts and Linear Regression for advanced analysis.
        """
        self.cursor.execute(
            "SELECT id, date, category, description, amount FROM expenses ORDER BY id"
        )
        rows = self.cursor.fetchall()
        if not rows:
            return pd.DataFrame(columns=["id", "date", "category", "description", "amount"])

        df = pd.DataFrame(rows, columns=["id", "date", "category", "description", "amount"])
        # Ensure the amount column is numeric for calculations.
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        df = df.dropna(subset=["amount"])
        return df

    def get_sql_stats(self) -> dict:
        """
        Run SQL aggregate queries (SUM, AVG, MAX, MIN, COUNT).
        Returns a dictionary: { "SUM": float, "AVG": float, ... }
        """
        stats = {}
        # Loop through standard SQL math functions to get a quick summary.
        for func in ("SUM", "AVG", "MAX", "MIN"):
            self.cursor.execute(f"SELECT {func}(amount) FROM expenses")
            result = self.cursor.fetchone()[0]
            stats[func] = round(result, 2) if result is not None else 0.0

        # COUNT uses * (not amount) to count every row regardless of content.
        self.cursor.execute("SELECT COUNT(*) FROM expenses")
        stats["COUNT"] = self.cursor.fetchone()[0]
        return stats

    def close(self):
        """Close the database connection gracefully when the app exits."""
        self.conn.close()


# ============================================================
# VALIDATION HELPERS
# Ensures that user input is clean and in the correct format.
# ============================================================

def validate_date(date_str: str) -> bool:
    """Return True if date_str matches the YYYY-MM-DD format."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def prompt_date(prompt_text: str = "Enter date (YYYY-MM-DD): ") -> str:
    """Repeatedly prompt the user until a valid date is entered."""
    date = input(prompt_text).strip()
    while not validate_date(date):
        print("  ⚠  Invalid format. Please use YYYY-MM-DD (e.g. 2024-03-15).")
        date = input(prompt_text).strip()
    return date


def prompt_amount(prompt_text: str = "Enter amount: ") -> float:
    """Repeatedly prompt the user until a valid positive number is entered."""
    while True:
        try:
            amount = float(input(prompt_text).strip())
            if amount <= 0:
                print("  ⚠  Amount must be greater than zero.")
                continue
            return amount
        except ValueError:
            print("  ⚠  Invalid number. Please enter a numeric value (e.g. 25.50).")


def prompt_id(prompt_text: str = "Enter expense ID: ") -> int:
    """Repeatedly prompt until a valid integer ID is entered."""
    while True:
        try:
            return int(input(prompt_text).strip())
        except ValueError:
            print("  ⚠  Please enter a valid integer ID.")


# ============================================================
# DISPLAY HELPERS
# Formatting for the terminal user interface.
# ============================================================

DIVIDER_WIDE  = "-" * 65
DIVIDER_SHORT = "=" * 35

def print_header():
    """Print the main application header."""
    print(f"\n{DIVIDER_SHORT}")
    print("   PROFESSIONAL EXPENSE TRACKER")
    print(DIVIDER_SHORT)


def print_menu():
    """Display the main menu options."""
    print_header()
    print("  1.  Add New Expense")
    print("  2.  View / Sort Expenses")
    print("  3.  Edit Existing Expense")
    print("  4.  Delete an Expense")
    print("  5.  Visual Report       (Bar + Pie Chart)")
    print("  6.  SQL Stats Report    (SUM, AVG, MAX, MIN)")
    print("  7.  Seaborn Charts      (Histogram, Box, Scatter)")
    print("  8.  Linear Regression   (Trend Analysis)")
    print("  9.  Import from File    (CSV / Excel)")
    print("  10. Exit")
    print(DIVIDER_SHORT)


def print_expense_table(expenses: list):
    """Render a formatted table of expense records."""
    if not expenses:
        print("  No expenses found.")
        return

    print(f"\n{DIVIDER_WIDE}")
    print(f"  {'ID':<5} {'Date':<13} {'Category':<16} {'Amount':>10}   {'Description'}")
    print(DIVIDER_WIDE)
    for exp in expenses:
        # Unpack the tuple returned from SQL
        exp_id, date, category, description, amount = exp
        print(f"  {exp_id:<5} {date:<13} {category:<16} {amount:>10.2f}   {description}")
    print(DIVIDER_WIDE)


def _show_and_wait(chart_name: str = ""):
    """
    Render the current matplotlib figure, then close it.
    This is specifically optimized for Google Colab environments.
    """
    plt.tight_layout()
    plt.show()
    time.sleep(0.5)   # Wait for output buffer to sync
    plt.close("all")  # Release memory and unblock input calls
    if chart_name:
        print(f"  ✔  '{chart_name}' displayed.")


# ============================================================
# CHART / VISUALISATION  (matplotlib — original)
# ============================================================

# A curated colour palette used across all charts for consistency.
CHART_COLORS = [
    "#4E79A7", "#F28E2B", "#E15759", "#76B7B2",
    "#59A14F", "#EDC948", "#B07AA1", "#FF9DA7",
    "#9C755F", "#BAB0AC"
]


def generate_visual_report(db: ExpenseDB):
    """
    Generate a side-by-side Bar Chart and Pie Chart showing
    total spending broken down by category.
    """
    data = db.get_category_totals()

    if not data:
        print("  ⚠  No data available to generate a report.")
        return

    categories = [row[0] for row in data]
    totals     = [row[1] for row in data]
    colors     = CHART_COLORS[:len(categories)]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle("Expense Report by Category", fontsize=16, fontweight="bold", y=1.01)

    # --- Bar Chart (left) ---
    ax_bar = axes[0]
    bars = ax_bar.bar(categories, totals, color=colors, edgecolor="white", linewidth=0.8)
    ax_bar.set_title("Total Spent per Category", fontsize=13, pad=10)
    ax_bar.set_xlabel("Category", fontsize=11)
    ax_bar.set_ylabel("Total Amount (£)", fontsize=11)
    ax_bar.tick_params(axis="x", rotation=20)
    ax_bar.spines[["top", "right"]].set_visible(False)

    # Annotate each bar with its rounded value for immediate readability
    for bar, value in zip(bars, totals):
        ax_bar.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(totals) * 0.01,
            f"{value:.2f}",
            ha="center", va="bottom", fontsize=9, color="#333333"
        )

    # --- Pie Chart (right) ---
    ax_pie = axes[1]
    wedges, texts, autotexts = ax_pie.pie(
        totals,
        labels=None,
        colors=colors,
        autopct="%1.1f%%",
        startangle=140,
        pctdistance=0.82,
        wedgeprops={"edgecolor": "white", "linewidth": 1.5}
    )

    # Style the percentage labels inside the wedges
    for autotext in autotexts:
        autotext.set_fontsize(9)
        autotext.set_color("white")
        autotext.set_fontweight("bold")

    ax_pie.set_title("Spending Distribution", fontsize=13, pad=10)

    # Build a clean legend with category names and totals
    legend_patches = [
        mpatches.Patch(color=colors[i], label=f"{categories[i]}  (£{totals[i]:,.2f})")
        for i in range(len(categories))
    ]
    ax_pie.legend(
        handles=legend_patches,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.18),
        ncol=2,
        fontsize=9,
        frameon=False
    )

    _show_and_wait("Bar + Pie Chart")
    input("  Press ENTER to return to the menu...")


# ============================================================
# SQL ARITHMETIC REPORT  (option 6)
# ============================================================

def show_sql_stats(db: ExpenseDB):
    """
    Run SQL aggregate functions directly on the expenses table
    and display a formatted summary report.
    """
    stats = db.get_sql_stats()

    print(f"\n  {'─' * 40}")
    print(f"  {'SQL ARITHMETIC REPORT':^40}")
    print(f"  {'─' * 40}")
    print(f"  {'Metric':<24} {'Value':>12}")
    print(f"  {'─' * 40}")
    print(f"  {'Total Spent  (SUM)':<24} £{stats['SUM']:>10,.2f}")
    print(f"  {'Average      (AVG)':<24} £{stats['AVG']:>10,.2f}")
    print(f"  {'Highest      (MAX)':<24} £{stats['MAX']:>10,.2f}")
    print(f"  {'Lowest       (MIN)':<24} £{stats['MIN']:>10,.2f}")
    print(f"  {'No. of Records (COUNT)':<24}  {int(stats['COUNT']):>10}")
    print(f"  {'─' * 40}\n")


# ============================================================
# SEABORN CHARTS  (option 7)
# ============================================================

def generate_seaborn_charts(db: ExpenseDB):
    """
    Display three Seaborn charts to analyze data distribution and spikes.
    """
    df = db.get_as_dataframe()

    if df.empty:
        print("  ⚠  No data available for Seaborn charts.")
        return

    amounts = df["amount"]
    sns.set_theme(style="whitegrid")  # Apply aesthetic global style

    # ── 1. Histogram ────────────────────────────────────────
    # Shows the density of spending (e.g., do you have many small expenses or few large ones?)
    plt.figure(figsize=(8, 5))
    sns.histplot(amounts, bins=10, color="#4E79A7", edgecolor="white")
    plt.title("Distribution of Expense Amounts", fontsize=14, fontweight="bold")
    plt.xlabel("Amount (£)", fontsize=11)
    plt.ylabel("Frequency", fontsize=11)
    _show_and_wait("Histogram")

    # ── 2. Box Plot ──────────────────────────────────────────
    # Useful for spotting outliers (extreme spending) and identifying the median.
    plt.figure(figsize=(8, 4))
    sns.boxplot(
        x=amounts, color="#76B7B2",
        flierprops={"marker": "o", "markerfacecolor": "#E15759", "markersize": 6}
    )
    plt.title("Box Plot of Expenses", fontsize=14, fontweight="bold")
    plt.xlabel("Amount (£)", fontsize=11)
    _show_and_wait("Box Plot")

    # ── 3. Scatter Plot ──────────────────────────────────────
    # Plots each transaction in order to see if spending is rising or falling over time.
    unique_cats = df["category"].unique()
    palette     = CHART_COLORS[:len(unique_cats)]

    plt.figure(figsize=(10, 5))
    sns.scatterplot(
        data=df, x=df.index, y="amount",
        hue="category", palette=palette, s=80, edgecolor="white"
    )
    plt.title("Expense Amounts by Transaction Order", fontsize=14, fontweight="bold")
    plt.xlabel("Transaction Order", fontsize=11)
    plt.ylabel("Amount (£)", fontsize=11)
    plt.legend(title="Category", bbox_to_anchor=(1.02, 1), loc="upper left",
               fontsize=8, frameon=False)
    _show_and_wait("Scatter Plot")

    print("  ✔  All 3 Seaborn charts displayed.")
    input("  Press ENTER to return to the menu...")


# ============================================================
# LINEAR REGRESSION  (option 8)
# ============================================================

def generate_regression_analysis(db: ExpenseDB):
    """
    Fit a Linear Regression model to visualize the spending trajectory.
    """
    df = db.get_as_dataframe()

    if df.empty or len(df) < 2:
        print("  ⚠  Need at least 2 expense records for regression analysis.")
        return

    # Prepare features (X) and target (Y). X is reshaped to 2D for scikit-learn.
    X = np.arange(len(df)).reshape(-1, 1)
    Y = df["amount"].values

    # Train the model
    model = LinearRegression()
    model.fit(X, Y)

    # Predict values to draw the "trend line"
    predictions = model.predict(X)

    # Get coefficients for the equation y = mx + c
    m = round(float(model.coef_[0]), 4)   # Slope
    c = round(float(model.intercept_), 2) # Intercept
    equation = f"y = {m}x + {c}"

    # Determine trend based on the slope (m)
    if m > 0.01:
        trend = f"📈 Upward trend  — spending increases by ~£{abs(m):.2f} per transaction."
    elif m < -0.01:
        trend = f"📉 Downward trend — spending decreases by ~£{abs(m):.2f} per transaction."
    else:
        trend = "➡  Stable — no significant upward or downward trend detected."

    # ── Plotting the Results ────────────────────────────────
    unique_cats = df["category"].unique()
    palette     = CHART_COLORS[:len(unique_cats)]

    plt.figure(figsize=(10, 5))

    # Actual spending points
    sns.scatterplot(
        data=df, x=X.flatten(), y="amount",
        hue="category", palette=palette, s=80, edgecolor="white"
    )

    # The mathematical trend line
    plt.plot(X, predictions, color="#E15759", linewidth=2,
             linestyle="--", label=f"Best-fit: {equation}")

    # Display the equation on the chart
    plt.text(
        0.02, 0.95, equation,
        transform=plt.gca().transAxes,
        fontsize=10, color="#E15759", verticalalignment="top",
        bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "edgecolor": "#E15759"}
    )

    plt.title("Linear Regression — Expense Trend Over Time",
              fontsize=14, fontweight="bold")
    plt.xlabel("Transaction Order", fontsize=11)
    plt.ylabel("Amount (£)", fontsize=11)
    plt.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8, frameon=False)

    _show_and_wait("Linear Regression")

    # Output stats to console
    print(f"\n  Regression Equation : {equation}")
    print(f"  Slope (m)           : {m}  →  change in amount per transaction")
    print(f"  Intercept (c)       : {c}  →  estimated starting value")
    print(f"  Trend               : {trend}")
    input("\n  Press ENTER to return to the menu...")


# ============================================================
# CSV / EXCEL FILE IMPORT  (option 9)
# ============================================================

def import_from_file(db: ExpenseDB):
    """
    Allow users to upload and bulk-insert data from external files.
    """
    if not IN_COLAB:
        print("  ⚠  File upload requires Google Colab.")
        print("     Running locally? Use pd.read_csv() / pd.read_excel() manually.")
        input("  Press ENTER to return to the menu...")
        return

    print("\n  [ Import from CSV / Excel ]")
    print("  A file picker will appear — select your .csv or .xlsx file.\n")

    # Trigger Colab's file upload UI
    uploaded = files.upload()

    if not uploaded:
        print("  ⚠  No file was selected.")
        input("  Press ENTER to return to the menu...")
        return

    file_name = list(uploaded.keys())[0]

    # Process file based on extension using Pandas
    try:
        if file_name.endswith(".csv"):
            df = pd.read_csv(file_name)
        elif file_name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file_name)
        else:
            print(f"  ⚠  Unsupported file type: '{file_name}'")
            print("     Please upload a .csv or .xlsx file.")
            input("  Press ENTER to return to the menu...")
            return
    except Exception as e:
        print(f"  ⚠  Error reading file: {e}")
        input("  Press ENTER to return to the menu...")
        return

    # Clean up empty columns (like those often exported by Excel)
    df = df.loc[:, ~df.columns.str.contains("^Unnamed")]

    # Force the first 4 columns to be the expected fields
    df = df.iloc[:, :4]
    df.columns = ["date", "category", "amount", "description"]

    # Data Cleaning: ensure Amount is numeric, drop rows that aren't
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    invalid_count = int(df["amount"].isna().sum())
    df = df.dropna(subset=["amount"])

    if df.empty:
        print("  ⚠  No valid rows found in the file after cleaning.")
        input("  Press ENTER to return to the menu...")
        return

    df["description"] = df["description"].fillna("").astype(str)

    # Convert DataFrame rows into a list of tuples for the database
    rows = [
        (str(row["date"]), str(row["category"]),
         str(row["description"]), float(row["amount"]))
        for _, row in df.iterrows()
    ]

    # Efficient database entry
    db.bulk_insert(rows)

    print(f"\n  ✔  Import complete!")
    print(f"     Rows imported  : {len(rows)}")
    if invalid_count > 0:
        print(f"     Rows skipped   : {invalid_count}  (invalid amount values)")
    print(f"\n  Preview (first 5 rows):")
    print(df.head().to_string(index=False))
    input("\n  Press ENTER to return to the menu...")


# ============================================================
# MAIN APPLICATION LOOP
# ============================================================

def main():
    """
    Entry point for the Expense Tracker.
    Runs an interactive menu loop in the Colab cell / terminal.
    """
    db = ExpenseDB()
    print("\n  Welcome to the Professional Expense Tracker!")
    print("  Data is stored locally in 'expenses.db'.\n")

    while True:
        print_menu()
        choice = input("  Enter your choice (1-10): ").strip()

        # ── 1. ADD EXPENSE ────────────────────────────────────
        if choice == "1":
            print("\n  [ Add New Expense ]")
            date        = prompt_date()
            category    = input("  Category (e.g. Food, Rent, Transport): ").strip()
            description = input("  Brief description: ").strip()
            amount      = prompt_amount("  Amount: ")

            db.add_expense(date, category, description, amount)
            print(f"  ✔  Expense of £{amount:.2f} added under '{category}'.")

        # ── 2. VIEW / SORT EXPENSES ───────────────────────────
        elif choice == "2":
            print("\n  [ View Expenses ]")
            sort_opt = input(
                "  Sort by (date / category / amount) [default: date]: "
            ).strip().lower()
            if sort_opt not in ("date", "category", "amount"):
                sort_opt = "date"

            expenses = db.get_all_expenses(sort_opt)
            print(f"  Showing {len(expenses)} record(s), sorted by '{sort_opt}':")
            print_expense_table(expenses)

        # ── 3. EDIT EXPENSE ───────────────────────────────────
        elif choice == "3":
            print("\n  [ Edit Expense ]")
            exp_id = prompt_id("  Enter the ID of the expense to edit: ")

            existing = db.get_expense_by_id(exp_id)
            if not existing:
                print(f"  ⚠  No expense found with ID {exp_id}.")
                continue

            print(f"  Current record: {existing}")
            date        = prompt_date("  New date (YYYY-MM-DD): ")
            category    = input("  New category: ").strip()
            description = input("  New description: ").strip()
            amount      = prompt_amount("  New amount: ")

            db.update_expense(exp_id, date, category, description, amount)
            print(f"  ✔  Expense ID {exp_id} updated successfully.")

        # ── 4. DELETE EXPENSE ─────────────────────────────────
        elif choice == "4":
            print("\n  [ Delete Expense ]")
            exp_id = prompt_id("  Enter the ID of the expense to delete: ")

            existing = db.get_expense_by_id(exp_id)
            if not existing:
                print(f"  ⚠  No expense found with ID {exp_id}.")
                continue

            confirm = input(
                f"  Delete '{existing[3]}' (£{existing[4]:.2f})? (y/n): "
            ).strip().lower()
            if confirm == "y":
                db.delete_expense(exp_id)
                print(f"  ✔  Expense ID {exp_id} deleted.")
            else:
                print("  Deletion cancelled.")

        # ── 5. VISUAL REPORT (Bar + Pie) ──────────────────────
        elif choice == "5":
            print("\n  [ Generating Visual Report (Bar + Pie Chart)... ]")
            generate_visual_report(db)

        # ── 6. SQL ARITHMETIC REPORT ──────────────────────────
        elif choice == "6":
            print("\n  [ SQL Arithmetic Report ]")
            show_sql_stats(db)
            input("  Press ENTER to return to the menu...")

        # ── 7. SEABORN CHARTS ─────────────────────────────────
        elif choice == "7":
            print("\n  [ Seaborn Charts: Histogram → Box Plot → Scatter ]")
            generate_seaborn_charts(db)

        # ── 8. LINEAR REGRESSION ──────────────────────────────
        elif choice == "8":
            print("\n  [ Linear Regression — Trend Analysis ]")
            generate_regression_analysis(db)

        # ── 9. IMPORT FROM FILE ───────────────────────────────
        elif choice == "9":
            import_from_file(db)

        # ── 10. EXIT ──────────────────────────────────────────
        elif choice == "10":
            # Close the connection and break the loop
            db.close()
            print("\n  Goodbye! Your expenses have been saved.\n")
            break

        else:
            print("  ⚠  Invalid selection. Please enter a number between 1 and 10.")


# ── Run the application ──────────────────────────────────────
# Standard Python boilerplate to ensure the app starts only when the script is run directly.
if __name__ == "__main__":
    main()