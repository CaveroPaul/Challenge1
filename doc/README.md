# Documentation

## Data Source

Dataset: **[E-Commerce Orders and Customer — hammadansari7](https://www.kaggle.com/datasets/hammadansari7/e-commerce-orders-and-customer/data)**
Downloaded via `kagglehub` and cached locally at runtime.

---

## Feature Phases

**Phase 1 — Extract**
Download the e-commerce dataset from Kaggle using kagglehub and cache it locally.

**Phase 2 — Transform**
Rename columns, cast types, deduplicate by `(fecha, id_cliente)`, and apply the 10% discount logic for the first 500 online orders.

**Phase 3 — Load**
Write data through a medallion architecture:
- Bronze: raw deduplicated data (`raw_ventas`)
- Silver: enriched with discount columns (`silver_ventas`)
- Gold: star schema with four tables:
  - `dim_fecha` — continuous date range (all days from min to max date); 10 date attributes including `anio`, `trimestre`, `mes`, `dia_semana`, and `es_fin_semana`
  - `dim_cliente` — unique customers
  - `dim_producto` — unique products
  - `fact_ventas` — one row per order; FKs to all three dimensions (`sk_fecha`, `sk_cliente`, `sk_producto`)

**Phase 4 — Analysis**
Query the star schema on Neon for business metrics:
- 5.1 Total sales by customer
- 5.2 Total sales by product
- 5.3 Daily sales trend
- 5.4 Weekend sales (`es_fin_semana = true`) — total revenue and order count for Saturday and Sunday, joined through `dim_fecha`

**Phase 5 — Visualizations**
Generate `matplotlib` charts from the analysis queries and save them to `doc/`:
- 6.1 Top 15 customers by total sales (`sales_charts_by_customer.png`)
- 6.2 Total sales by product (`sales_charts_by_product.png`)
- 6.3 Daily sales trend (`sales_charts_by_date.png`)
- 6.4 Weekend sales — revenue and order count by day (`sales_charts_weekend.png`)

---

## [`database_architecture.md`](database_architecture.md)

Full reference for the `ecomerce` PostgreSQL database.

### What's covered

- **Entity-Relationship Diagram** — Mermaid ER diagram showing all six tables (Bronze, Silver, Gold) with column types, PKs, UKs, FKs, and relationships.
- **Business context** — the 10% discount rule for the first 500 online orders and how it maps to derived columns (`count_pagos_by_tipo`, `descuento`, `final_total`).
- **Medallion architecture** — three-layer pipeline:
  - **Bronze** (`raw_ventas`) — deduped source data, no derived metrics.
  - **Silver** (`silver_ventas`) — bronze + discount columns; this is what the star schema reads from.
  - **Gold** — star schema for analytics queries:
    - `dim_fecha` — 912 continuous dates (2023-01-01 to 2025-06-30); columns parsed from `init_db.sql` at runtime.
    - `dim_cliente`, `dim_producto` — conformed dimensions.
    - `fact_ventas` — grain: one row per order; includes `sk_fecha` FK for time-based analysis.
- **Table definitions** — column names, types, and constraints for every table.
- **Load strategy** — idempotent inserts using `ON CONFLICT DO NOTHING`; gold tables are dropped and recreated on each `init_db.sql` run to allow schema migrations.
- **Schema initialization** — how to run `init_db.sql` or `init_db.py` before the first ETL run.

---

## Test Suite

`test_data_extraction.py` — **43 unit tests**, no DB or Kaggle connection required.

| Class | Tests | Coverage |
|---|---|---|
| `TestRename` | 2 | Column rename mapping |
| `TestTypeCasting` | 5 | Date/numeric casting, NaN on invalid input |
| `TestDeduplication` | 5 | `(fecha, id_cliente)` dedup logic |
| `TestDiscountLogic` | 8 | 10% discount rule, thresholds, payment methods |
| `TestDimFecha` | 20 | Row count, no gaps, `es_fin_semana`, ISO day numbers, trimestre boundaries, leap year, full year |
| `TestWeekendSalesFilter` | 4 | Weekend filter correctness, `total_gastado` sums |

Run with:
```bash
.venv\Scripts\python.exe -m pytest test_data_extraction.py -v
```

---

## Charts

| File | Description |
|---|---|
| `sales_charts_by_customer.png` | Top 15 customers by total sales |
| `sales_charts_by_date.png` | Daily sales trend |
| `sales_charts_by_product.png` | Total sales by product |
| `sales_charts_weekend.png` | Weekend sales — revenue and orders by day (Saturday vs Sunday) |
