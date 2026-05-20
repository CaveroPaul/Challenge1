# E-Commerce Orders ETL Pipeline

ETL pipeline for a technology equipment sales company. Extracts e-commerce order data from Kaggle, transforms it with pandas, and loads it into a PostgreSQL star-schema database.

## Overview

```
Kaggle (.xlsx)  →  Transform (pandas)  →  PostgreSQL (star schema)
```

| Stage | Description |
|---|---|
| Extract | Downloads dataset via `kagglehub` and copies it to `data/` |
| Transform | Renames columns, casts types, deduplicates on `(fecha, id_cliente)`, applies discount logic |
| Load | Writes to bronze (`raw_ventas`) → silver (`silver_ventas`) → gold (`dim_cliente`, `dim_producto`, `fact_ventas`) |

## Business Rule

A **10% discount** applies to online orders (`metodo_pago = 'Online'`) for the first 500 orders placed through the platform. Only the first order per `(fecha, id_cliente)` pair counts toward the threshold.

## Database Schema

```
silver_ventas (staging)
      │
      ├──► dim_cliente  ──┐
      │                   ├──► fact_ventas
      └──► dim_producto ──┘
```

See [`doc/database_architecture.md`](doc/database_architecture.md) for full table definitions.

## Setup

**Requirements:** Python 3.x, PostgreSQL running locally, Kaggle credentials configured.

```bash
pip install -r requirements.txt
```

Initialize the database schema (run once):

```bash
psql -U postgres -d ecomerce -f init_db.sql
```

Or use the Python alternative:

```bash
python init_db.py
```

## Running the Pipeline

```bash
jupyter notebook data_extraction.ipynb
```

Run cells top to bottom. The notebook is self-contained and re-runnable — all inserts use `ON CONFLICT DO NOTHING`.

## Running the Tests

```bash
.venv\Scripts\python.exe -m pytest test_data_extraction.py -v
```

20 unit tests cover the transform logic (rename, type casting, deduplication, discount) with no DB or Kaggle connection required.

## Repository Structure

```
data_extraction.ipynb       # Main ETL notebook
init_db.sql                 # PostgreSQL schema (CREATE TABLE IF NOT EXISTS)
init_db.py                  # Python alternative to psql for schema init
test_data_extraction.py     # Unit tests for transform logic
requirements.txt
doc/
  README.md
  database_architecture.md
```
