# Documentation

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
