-- Initialize the ecomerce database schema — Medallion Architecture
-- Run this once before executing the ETL notebook:
--   psql -U postgres -d ecomerce -f init_db_v2.sql
--
-- Layers:
--   Bronze  → raw_ventas      : deduped data, no derived metrics
--   Silver  → silver_ventas   : bronze + descuento + final_total
--   Gold    → dim_cliente, dim_producto, fact_ventas (star schema)
--
-- NOTE: IF NOT EXISTS is safe to re-run, but constraint changes only apply
-- to freshly created tables. Drop existing tables to apply schema changes.

DROP TABLE IF EXISTS ventas;

-- Drop gold tables in dependency order to allow schema changes
DROP TABLE IF EXISTS fact_ventas;
DROP TABLE IF EXISTS dim_fecha;
DROP TABLE IF EXISTS dim_cliente;
DROP TABLE IF EXISTS dim_producto;

-- Bronze: deduped raw data, no transformation metrics applied
CREATE TABLE IF NOT EXISTS raw_ventas (
    order_id             VARCHAR(20) PRIMARY KEY,
    fecha                DATE,
    id_cliente           VARCHAR(20),
    producto             VARCHAR(100),
    cantidad             INT,
    precio_unitario      NUMERIC(10,2),
    direccion_envio      VARCHAR(255),
    metodo_pago          VARCHAR(50),
    estado_pedido        VARCHAR(50),
    numero_seguimiento   VARCHAR(50),
    articulos_en_carrito INT,
    codigo_cupon         VARCHAR(50),
    fuente_referencia    VARCHAR(50),
    precio_total         NUMERIC(12,2)
);

-- Silver: enriched with discount logic (online_rank <= 500 → 10% off)
CREATE TABLE IF NOT EXISTS silver_ventas (
    order_id             VARCHAR(20) PRIMARY KEY,
    fecha                DATE,
    id_cliente           VARCHAR(20),
    producto             VARCHAR(100),
    cantidad             INT,
    precio_unitario      NUMERIC(10,2),
    direccion_envio      VARCHAR(255),
    metodo_pago          VARCHAR(50),
    estado_pedido        VARCHAR(50),
    numero_seguimiento   VARCHAR(50),
    articulos_en_carrito INT,
    codigo_cupon         VARCHAR(50),
    fuente_referencia    VARCHAR(50),
    precio_total         NUMERIC(12,2),
    descuento            NUMERIC(12,3),
    final_total          NUMERIC(12,3)
);

-- Gold: dimension tables
CREATE TABLE IF NOT EXISTS dim_fecha (
    sk_fecha        SERIAL PRIMARY KEY,
    fecha           DATE UNIQUE NOT NULL,
    anio            INT NOT NULL,
    trimestre       INT NOT NULL,
    mes             INT NOT NULL,
    nombre_mes      VARCHAR(20) NOT NULL,
    semana_anio     INT NOT NULL,
    dia             INT NOT NULL,
    dia_semana      INT NOT NULL,    -- ISO: 1=Lunes ... 7=Domingo
    nombre_dia      VARCHAR(20) NOT NULL,
    es_fin_semana   BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_cliente (
    sk_cliente  SERIAL PRIMARY KEY,
    id_cliente  VARCHAR(20) UNIQUE NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dim_producto (
    sk_producto SERIAL PRIMARY KEY,
    producto    VARCHAR(100) UNIQUE NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Gold: fact table — reads from silver_ventas
CREATE TABLE IF NOT EXISTS fact_ventas (
    sk_venta    SERIAL PRIMARY KEY,
    order_id    VARCHAR(20) UNIQUE NOT NULL,
    fecha       DATE,
    sk_fecha    INT NOT NULL,
    sk_cliente  INT NOT NULL,
    sk_producto INT NOT NULL,
    cantidad    INT NOT NULL,
    final_total NUMERIC(12,3) NOT NULL,

    CONSTRAINT fk_fecha
        FOREIGN KEY (sk_fecha)
        REFERENCES dim_fecha(sk_fecha),

    CONSTRAINT fk_cliente
        FOREIGN KEY (sk_cliente)
        REFERENCES dim_cliente(sk_cliente),

    CONSTRAINT fk_producto
        FOREIGN KEY (sk_producto)
        REFERENCES dim_producto(sk_producto)
);
