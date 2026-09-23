# Professional Expense Tracker

A menu-driven expense tracker built in Python.
It stores expenses in a SQLite database and turns them into charts and simple trend analysis.
It runs in Google Colab or in a terminal.

## Features

| Menu option | What it does |
|---|---|
| 1. Add New Expense | Adds an expense with date, category, description and amount |
| 2. View / Sort Expenses | Shows all records, sorted by date, category or amount |
| 3. Edit Existing Expense | Updates a record by its ID |
| 4. Delete an Expense | Deletes a record by its ID, after confirmation |
| 5. Visual Report | Bar chart and pie chart of spending by category (Matplotlib) |
| 6. SQL Stats Report | SUM, AVG, MAX, MIN and COUNT with SQL aggregate queries |
| 7. Seaborn Charts | Histogram, box plot and scatter plot of expense amounts |
| 8. Linear Regression | Fits a trend line (scikit-learn) and shows if spending goes up or down |
| 9. Import from File | Bulk import from a CSV or Excel file (Google Colab) |

## Tools

Python, SQLite, pandas, NumPy, Matplotlib, Seaborn, scikit-learn

## Technical highlights

- Parameterised SQL queries (`?` placeholders) to prevent SQL injection
- Input validation for dates (YYYY-MM-DD), amounts and IDs
- Fast bulk insert with `executemany()` for file imports
- Data cleaning with pandas: invalid amounts and empty Excel columns are removed
- Colab-friendly chart display, so the menu does not freeze after a chart

## How to run

**Google Colab**
1. Open a new notebook and paste the code from `expense_tracker.py`.
2. Run the cell and choose options from the menu.
3. To test with data, choose option 9 and upload `sample_expenses.csv`.

**Locally**
```bash
pip install -r requirements.txt
python expense_tracker.py
```
The database is saved as `expenses.db` in the same folder.
File import (option 9) works only in Google Colab.

## Import file format

The first four columns must be in this order:

```
date,category,amount,description
2026-01-03,Groceries,42.50,Weekly shop
```

`sample_expenses.csv` is an example file with made-up data.

## Author

Ege Erenler
