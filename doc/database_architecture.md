# Database Architecture

## Business Context

A technology equipment sales company wants to implement a discount logic for the first 500 products sold through the online application:

- A **10% discount** is applied to online sales (`metodo_pago = 'Online'`) for the first 500 orders placed through the platform.
- Only the first sale per date is counted toward the 500-order threshold — duplicate `(fecha, id_cliente)` combinations are excluded before the count is computed.

This logic is implemented in the ETL pipeline via two derived columns in the `ventas` staging table:
- `count_pagos_by_tipo` — counts total orders per payment method after deduplication.
- `descuento` — applies 10% when `metodo_pago = 'Online'` AND `count_pagos_by_tipo < 500`; 0 otherwise.

---

## Requirements

| Package | Purpose |
|---|---|
| `sqlalchemy` | Database engine and connection management |
| `psycopg2` | PostgreSQL driver for SQLAlchemy (`psycopg2-binary` on some systems) |
| `pandas` | DataFrame operations and staging table load via `to_sql` |
| `kagglehub` | Dataset download |
| `openpyxl` | Reading the `.xlsx` source file |

Install with:

```bash
pip install -r requirements.txt
```

---

## Schema Initialization

All tables are defined in [`init_db.sql`](../init_db.sql) at the project root. Run it once before executing the ETL notebook:

```bash
psql -U postgres -d ecomerce -f init_db.sql
```

All `CREATE TABLE` statements use `IF NOT EXISTS`, so the script is safe to re-run.

---

## Overview

The database (`ecomerce`) follows a **star schema** pattern. Raw/transformed data lands in a staging table (`ventas`), then gets promoted into dimension and fact tables.

```
ventas (staging)
     │
     ├──► dim_cliente  ──┐
     │                   ├──► fact_ventas
     └──► dim_producto ──┘
```

---

## Staging Table

### `ventas`

Holds the full transformed dataset loaded from the notebook. Replaced on each ETL run (`if_exists="replace"`).

| Column | Type | Description |
|---|---|---|
| `order_id` | VARCHAR(20) PK | Unique order identifier |
| `fecha` | DATE | Order date |
| `id_cliente` | VARCHAR(20) | Customer identifier |
| `producto` | VARCHAR(100) | Product name |
| `cantidad` | INT | Units ordered |
| `precio_unitario` | NUMERIC(10,2) | Price per unit |
| `direccion_envio` | VARCHAR(255) | Shipping address |
| `metodo_pago` | VARCHAR(50) | Payment method (e.g. Online, Credit Card, Debit Card) |
| `estado_pedido` | VARCHAR(50) | Order status (e.g. Shipped, Delivered, Cancelled, Returned) |
| `numero_seguimiento` | VARCHAR(50) | Tracking number |
| `articulos_en_carrito` | INT | Items in cart at time of order |
| `codigo_cupon` | VARCHAR(50) | Coupon code applied |
| `fuente_referencia` | VARCHAR(50) | Referral source (e.g. Instagram, Email, Facebook) |
| `precio_total` | NUMERIC(12,2) | Raw total before discount |
| `count_pagos_by_tipo` | INT | Count of orders sharing the same payment method (window aggregate) |
| `descuento` | NUMERIC(12,3) | Discount applied (10% if Online and count < 500, else 0) |
| `final_total` | NUMERIC(12,3) | `precio_total - descuento` |

---

## Dimension Tables

### `dim_cliente`

| Column | Type | Description |
|---|---|---|
| `sk_cliente` | SERIAL PK | Surrogate key |
| `id_cliente` | VARCHAR(20) UNIQUE NOT NULL | Natural customer key |

### `dim_producto`

| Column | Type | Description |
|---|---|---|
| `sk_producto` | SERIAL PK | Surrogate key |
| `producto` | VARCHAR(100) UNIQUE NOT NULL | Product name (natural key) |

---

## Fact Table

### `fact_ventas`

| Column | Type | Description |
|---|---|---|
| `sk_venta` | SERIAL PK | Surrogate key |
| `order_id` | VARCHAR(20) UNIQUE NOT NULL | Natural order key |
| `fecha` | DATE | Order date |
| `sk_cliente` | INT FK → `dim_cliente.sk_cliente` | Customer dimension reference |
| `sk_producto` | INT FK → `dim_producto.sk_producto` | Product dimension reference |
| `cantidad` | INT | Units ordered |
| `final_total` | NUMERIC(12,3) | Final amount after discount |

---

## Load Strategy

All inserts into dimension and fact tables use `ON CONFLICT DO NOTHING`, making each ETL run idempotent. New orders are appended; existing `order_id` values are skipped.

```
ventas  →  dim_cliente   (DISTINCT id_cliente,  ON CONFLICT DO NOTHING)
ventas  →  dim_producto  (DISTINCT producto,    ON CONFLICT DO NOTHING)
ventas  →  fact_ventas   (JOIN both dims,        ON CONFLICT (order_id) DO NOTHING)
```
