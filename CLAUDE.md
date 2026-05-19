# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Jupyter Notebook ETL pipeline that extracts e-commerce order data from Kaggle, transforms it with pandas, and loads it into a PostgreSQL star-schema database.

## Environment Setup

```bash
# Install dependencies (virtual environment already exists at .venv)
pip install -r requirements.txt

# requirements: kagglehub, pandas, openpyxl, sqlalchemy, psycopg2
```

## Running the Notebook

Open and run `data_extraction.ipynb` cell by cell in Jupyter. The notebook is self-contained — no separate build or test commands exist.

```bash
jupyter notebook data_extraction.ipynb
```

## Repository Structure

```
data_extraction.ipynb   # Main ETL notebook
init_db.sql             # Run once to create all tables before the notebook
requirements.txt
doc/
  README.md
  database_architecture.md  # Table definitions and star schema diagram
```

## Database

- **Engine**: PostgreSQL, local instance
- **Connection string**: `postgresql+psycopg2://postgres:admin@localhost:5432/ecomerce`
- Before the first notebook run, initialize the schema:

```bash
psql -U postgres -d ecomerce -f init_db.sql
```

The notebook also runs `init_db.sql` automatically in cell **4.2** via `engine.exec_driver_sql()`, so manual execution is only needed if running outside the notebook.

## ETL Architecture (`data_extraction.ipynb`)

The notebook implements a single-file ETL in four logical stages:

1. **Extract** — Downloads dataset via `kagglehub` (`hammadansari7/e-commerce-orders-and-customer`). Dataset is a single `.xlsx` file cached at `~/.cache/kagglehub/`.

2. **Transform** — Renames columns to Spanish, casts types, deduplicates on `(fecha, id_cliente)`, adds a `count_pagos_by_tipo` window aggregate, then computes a 10% `descuento` for Online payments (when that payment method has fewer than 500 orders) and derives `final_total`.

3. **Stage** — Writes the cleaned DataFrame to a `ventas` staging table in Postgres using `to_sql(..., if_exists="replace")`.

4. **Load (star schema)** — A single transaction:
   - `dim_cliente` — populated from distinct `id_cliente` values; PK `sk_cliente`
   - `dim_producto` — populated from distinct `producto` values; PK `sk_producto`
   - `fact_ventas` — joins staging table with both dims; PK/unique on `order_id`

   All inserts use `ON CONFLICT DO NOTHING` for idempotency.

## Key Data Notes

- Source dataset: ~1,200+ rows after dedup (raw has ~1,200 unique `(fecha, id_cliente)` pairs from a larger set with 880 duplicate dates).
- `final_total` is the column loaded into `fact_ventas`, not the raw `precio_total`.
- The discount logic is intentionally narrow: only `metodo_pago = 'Online'` AND `count_pagos_by_tipo < 500`.
