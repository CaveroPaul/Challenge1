# Documentation

## Data Source

Dataset: **[E-Commerce Orders and Customer — hammadansari7](https://www.kaggle.com/datasets/hammadansari7/e-commerce-orders-and-customer/data)**
Downloaded via `kagglehub` and cached locally at runtime.

---

## Feature Phases

**Phase 1 — Extract**
Download the e-commerce dataset from Kaggle using kagglehub and cache it locally.

**Phase 2 — Transform**
Rename columns, cast types, deduplicate by `(date, customer)`, and apply the 10% discount logic for the first 500 online orders.

**Phase 3 — Load**
Write data through a medallion architecture:
- Bronze: raw deduplicated data (`raw_ventas`)
- Silver: enriched with discount columns (`silver_ventas`)
- Gold: star schema (`dim_cliente`, `dim_produto`, `fact_ventas`)

**Phase 4 — Analysis**
Query the star schema on Neon for business metrics: sales by customer, by product, and by day.

---

## [`database_architecture.md`](database_architecture.md)

Full reference for the `ecomerce` PostgreSQL database.

### What's covered

- **Business context** — the 10% discount rule for the first 500 online orders and how it maps to derived columns (`count_pagos_by_tipo`, `descuento`, `final_total`).
- **Medallion architecture** — three-layer pipeline:
  - **Bronze** (`raw_ventas`) — deduped source data, no derived metrics.
  - **Silver** (`silver_ventas`) — bronze + discount columns; this is what the star schema reads from.
  - **Gold** (`dim_cliente`, `dim_produto`, `fact_ventas`) — star schema for analytics queries.
- **Table definitions** — column names, types, and constraints for every table.
- **Load strategy** — idempotent inserts using `ON CONFLICT DO NOTHING`.
- **Schema initialization** — how to run `init_db.sql` or `init_db.py` before the first ETL run.
