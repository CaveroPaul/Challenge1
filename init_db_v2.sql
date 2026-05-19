-- Initialize the ecomerce database schema
-- Run this once before executing the ETL notebook:
--   psql -U postgres -d ecomerce -f init_db_v2.sql
--
-- NOTE: IF NOT EXISTS means this is safe to re-run, but schema changes
-- (e.g. new NOT NULL constraints) only apply to freshly created tables.
-- Drop existing tables first if you need to apply constraint changes.

-- Staging table: receives the transformed DataFrame on each ETL run.
-- Transient columns (online_rank, descuento) are dropped before writing here.
CREATE TABLE IF NOT EXISTS ventas (
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
    final_total          NUMERIC(12,3)
);

-- Dimension: customers
CREATE TABLE IF NOT EXISTS dim_cliente (
    sk_cliente  SERIAL PRIMARY KEY,
    id_cliente  VARCHAR(20) UNIQUE NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Dimension: products
CREATE TABLE IF NOT EXISTS dim_producto (
    sk_producto SERIAL PRIMARY KEY,
    producto    VARCHAR(100) UNIQUE NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fact table: one row per order
CREATE TABLE IF NOT EXISTS fact_ventas (
    sk_venta    SERIAL PRIMARY KEY,
    order_id    VARCHAR(20) UNIQUE NOT NULL,
    fecha       DATE,
    sk_cliente  INT NOT NULL,
    sk_producto INT NOT NULL,
    cantidad    INT NOT NULL,
    final_total NUMERIC(12,3) NOT NULL,

    CONSTRAINT fk_cliente
        FOREIGN KEY (sk_cliente)
        REFERENCES dim_cliente(sk_cliente),

    CONSTRAINT fk_producto
        FOREIGN KEY (sk_producto)
        REFERENCES dim_producto(sk_producto)
);
