# E-Commerce Orders ETL Pipeline

ETL pipeline for a technology equipment sales company. Extracts e-commerce order data from Kaggle, transforms it with pandas, and loads it into a PostgreSQL star-schema database.

## Overview

```
Kaggle (.xlsx)  →  Transform (pandas)  →  PostgreSQL (Neon, star schema)
```

| Stage | Description |
|---|---|
| Extract | Downloads dataset via `kagglehub` and copies it to `data/` |
| Transform | Renames columns, casts types, deduplicates on `(fecha, id_cliente)`, applies discount logic |
| Load | Bronze (`raw_ventas`) → Silver (`silver_ventas`) → Gold (`dim_fecha`, `dim_cliente`, `dim_producto`, `fact_ventas`) |
| Analysis | Star schema queries: sales by customer, product, day, and weekend |
| Visualizations | `matplotlib` charts saved to `doc/` |

## Business Rule

A **10% discount** applies to online orders (`metodo_pago = 'Online'`) for the first 500 orders placed through the platform. Only the first order per `(fecha, id_cliente)` pair counts toward the threshold.

## Database Schema

```
silver_ventas (staging)
      │
      ├──► dim_fecha    ──┐
      ├──► dim_cliente  ──┼──► fact_ventas
      └──► dim_producto ──┘
```

- **`dim_fecha`** — 912 continuous dates (2023-01-01 to 2025-06-30) with attributes: `anio`, `trimestre`, `mes`, `dia_semana`, `es_fin_semana`, and more. Column names are read from `init_db.sql` at runtime.
- **`dim_cliente`** / **`dim_producto`** — conformed dimensions with surrogate keys.
- **`fact_ventas`** — one row per order; FKs to all three dimensions (`sk_fecha`, `sk_cliente`, `sk_producto`).

See [`doc/database_architecture.md`](doc/database_architecture.md) for the full ER diagram and table definitions.

## Setup

**Requirements:** Python 3.x, Neon Postgres credentials, Kaggle credentials.

```bash
pip install -r requirements.txt
```

Initialize the database schema (run once, or let cell 4.2 do it automatically):

```bash
python init_db.py
```

## Running the Pipeline

```bash
jupyter notebook data_extraction.ipynb
```

Run cells top to bottom. The notebook is self-contained and re-runnable — all gold inserts use `ON CONFLICT DO NOTHING`. Cell 4.2 drops and recreates gold tables on each run to apply schema changes cleanly.

## Running the Tests

```bash
.venv\Scripts\python.exe -m pytest test_data_extraction.py -v
```

**43 unit tests** with no DB or Kaggle connection required:

| Class | Tests | Coverage |
|---|---|---|
| `TestRename` | 2 | Column rename mapping |
| `TestTypeCasting` | 5 | Date/numeric casting, NaN on invalid input |
| `TestDeduplication` | 5 | `(fecha, id_cliente)` dedup logic |
| `TestDiscountLogic` | 8 | 10% discount rule, thresholds, payment methods |
| `TestDimFecha` | 20 | Row count, no gaps, `es_fin_semana`, ISO day numbers, trimestre, leap year |
| `TestWeekendSalesFilter` | 4 | Weekend filter correctness, `total_gastado` sums |

## Repository Structure

```
data_extraction.ipynb           # Main ETL notebook
init_db.sql                     # PostgreSQL schema — Bronze, Silver, Gold (incl. dim_fecha)
init_db.py                      # Python alternative for schema init
test_data_extraction.py         # 43 unit tests for transform logic
requirements.txt
doc/
  README.md
  database_architecture.md          # ER diagram (Mermaid) + full table definitions
  Challenge1.pdf                    # Project requirements
  sales_charts_by_customer.png      # Top 15 customers by total sales
  sales_charts_by_date.png          # Daily sales trend
  sales_charts_by_product.png       # Total sales by product
  sales_charts_weekend.png          # Weekend sales (Saturday vs Sunday)
```
