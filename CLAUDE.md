# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Jupyter Notebook ETL pipeline for a technology equipment sales company. It extracts e-commerce order data from Kaggle, transforms it with pandas (including a discount logic for online sales), and loads it into a PostgreSQL star-schema database.

**Business rule:** A 10% discount applies to online orders (`metodo_pago = 'Online'`) for the first 500 sales placed through the platform. Only the first sale per `(fecha, id_cliente)` pair counts toward the 500-order threshold.

## Environment Setup

```bash
# Install dependencies (virtual environment already exists at .venv)
pip install -r requirements.txt

# requirements: kagglehub, pandas, openpyxl, sqlalchemy, psycopg2, matplotlib, pytest
# Note: psycopg2 may require the binary build on some systems: pip install psycopg2-binary
```

## Running the Notebook

Open and run `data_extraction.ipynb` cell by cell in Jupyter. The notebook is self-contained — no separate build or test commands exist.

```bash
jupyter notebook data_extraction.ipynb
```

## Repository Structure

```
data_extraction.ipynb       # Main ETL notebook
init_db.sql                 # PostgreSQL schema (CREATE TABLE IF NOT EXISTS)
init_db.py                  # Python alternative to psql for schema init
test_data_extraction.py     # 20 unit tests for transform logic (no DB required)
requirements.txt
doc/
  README.md
  database_architecture.md      # Table definitions and star schema diagram
  sales_charts_by_customer.png  # Top 15 customers by total sales
  sales_charts_by_date.png      # Daily sales trend
  sales_charts_by_product.png   # Total sales by product
```

## Database

- **Engine**: PostgreSQL via [Neon](https://neon.tech) (serverless)
- **Connection string**: set in cell 4.1 as a `postgresql+psycopg2://` URL pointing to the Neon pooler endpoint (`?sslmode=require`)
- Before the first notebook run, initialize the schema (or let cell 4.2 do it automatically):

```bash
python init_db.py
```

Cell **4.2** runs `init_db.sql` automatically via `engine.begin()`, so manual execution is only needed if running outside the notebook.

## ETL Architecture (`data_extraction.ipynb`)

The notebook implements a single-file ETL pipeline in six sections:

1. **Setup** — Imports (`kagglehub`, `pandas`, `numpy`, `sqlalchemy`, `matplotlib`).

2. **Extract** — Downloads dataset via `kagglehub` (`hammadansari7/e-commerce-orders-and-customer`). Dataset is a single `.xlsx` file cached at `~/.cache/kagglehub/` and copied to `data/`.

3. **Transform** — Renames columns to Spanish, casts types, deduplicates on `(fecha, id_cliente)`, adds `count_pagos_by_tipo` (groupby count per payment method), then computes a 10% `descuento` for Online payments when `count_pagos_by_tipo < 500` and derives `final_total`.

4. **Load** — Medallion architecture, all written to Neon:
   - **Bronze** (`raw_ventas`) — deduped source data, no discount columns; replaced each run.
   - **Silver** (`silver_ventas`) — bronze + `count_pagos_by_tipo`, `descuento`, `final_total`; replaced each run.
   - **Gold** — single transaction reading from `silver_ventas`:
     - `dim_cliente` — distinct `id_cliente` values; PK `sk_cliente`
     - `dim_producto` — distinct `producto` values; PK `sk_producto`
     - `fact_ventas` — joins both dims; unique on `order_id`
   - All gold inserts use `ON CONFLICT DO NOTHING` for idempotency.

5. **Analysis** — Star schema queries: top customers, top products, daily sales trend.

6. **Visualizations** — `matplotlib` bar/line charts saved to `doc/`.

## Key Data Notes

- Source dataset: 1,200 rows with no `(fecha, id_cliente)` duplicates (529 date-only duplicates exist but no same-day same-customer pairs).
- `final_total` is the column loaded into `fact_ventas`, not the raw `precio_total`.
- The discount logic: `metodo_pago = 'Online'` AND `count_pagos_by_tipo < 500`. Because the dataset has 258 online orders (< 500), every online order receives the 10% discount.
- `count_pagos_by_tipo` is a per-payment-method order count (not a sequential rank), so all online orders share the same value (258).
