"""
Unit tests for the transform logic in data_extraction.ipynb.

Each helper below mirrors the corresponding notebook cell exactly so tests
stay in sync with the notebook without requiring a live Kaggle or DB connection.
"""

import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Helpers mirroring notebook transform cells
# ---------------------------------------------------------------------------

RENAME_MAP = {
    "OrderID": "order_id",
    "Date": "fecha",
    "CustomerID": "id_cliente",
    "Product": "producto",
    "Quantity": "cantidad",
    "UnitPrice": "precio_unitario",
    "ShippingAddress": "direccion_envio",
    "PaymentMethod": "metodo_pago",
    "OrderStatus": "estado_pedido",
    "TrackingNumber": "numero_seguimiento",
    "ItemsInCart": "articulos_en_carrito",
    "CouponCode": "codigo_cupon",
    "ReferralSource": "fuente_referencia",
    "TotalPrice": "precio_total",
}


def apply_rename(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns=RENAME_MAP)


def apply_cast(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    for col in ["cantidad", "precio_unitario", "precio_total", "articulos_en_carrito"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def apply_dedup(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["fecha", "id_cliente", "order_id"]).reset_index(drop=True)
    return df.drop_duplicates(subset=["fecha", "id_cliente"], keep="first")


def apply_discount(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["count_pagos_by_tipo"] = df.groupby("metodo_pago")["order_id"].transform("count")
    df["descuento"] = np.where(
        (df["count_pagos_by_tipo"] < 500) & (df["metodo_pago"] == "Online"),
        df["precio_total"] * 0.10,
        0,
    )
    df["final_total"] = df["precio_total"] - df["descuento"]
    return df


# ---------------------------------------------------------------------------
# Fixture factory
# ---------------------------------------------------------------------------

def make_row(**overrides):
    defaults = {
        "OrderID": "ORD000001",
        "Date": "2023-01-01",
        "CustomerID": "C00001",
        "Product": "Laptop",
        "Quantity": 1,
        "UnitPrice": 100.0,
        "ShippingAddress": "123 Main St",
        "PaymentMethod": "Online",
        "OrderStatus": "Shipped",
        "TrackingNumber": "TRK001",
        "ItemsInCart": 1,
        "CouponCode": "SAVE10",
        "ReferralSource": "Google",
        "TotalPrice": 100.0,
    }
    return {**defaults, **overrides}


def make_df(rows) -> pd.DataFrame:
    return apply_cast(apply_rename(pd.DataFrame(rows)))


# ---------------------------------------------------------------------------
# Rename
# ---------------------------------------------------------------------------

class TestRename:
    def test_all_columns_renamed(self):
        result = apply_rename(pd.DataFrame([make_row()]))
        assert set(RENAME_MAP.values()).issubset(result.columns)

    def test_no_original_names_remain(self):
        result = apply_rename(pd.DataFrame([make_row()]))
        for original in RENAME_MAP:
            assert original not in result.columns


# ---------------------------------------------------------------------------
# Type casting
# ---------------------------------------------------------------------------

class TestTypeCasting:
    def test_fecha_becomes_datetime(self):
        result = make_df([make_row(Date="2023-06-15")])
        assert pd.api.types.is_datetime64_any_dtype(result["fecha"])

    def test_numeric_columns_have_numeric_dtype(self):
        result = make_df([make_row()])
        for col in ["cantidad", "precio_unitario", "precio_total", "articulos_en_carrito"]:
            assert pd.api.types.is_numeric_dtype(result[col]), f"{col} not numeric"

    def test_invalid_date_becomes_nat(self):
        result = make_df([make_row(Date="not-a-date")])
        assert pd.isna(result["fecha"].iloc[0])

    def test_invalid_numeric_becomes_nan(self):
        result = make_df([make_row(Quantity="abc")])
        assert pd.isna(result["cantidad"].iloc[0])

    def test_valid_data_has_no_nans(self):
        result = make_df([make_row()])
        for col in ["cantidad", "precio_unitario", "precio_total", "articulos_en_carrito"]:
            assert result[col].isna().sum() == 0


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

class TestDeduplication:
    def test_duplicate_date_customer_pair_removed(self):
        rows = [
            make_row(OrderID="ORD000001", Date="2023-01-01", CustomerID="C00001"),
            make_row(OrderID="ORD000002", Date="2023-01-01", CustomerID="C00001"),
        ]
        result = apply_dedup(make_df(rows))
        assert len(result) == 1

    def test_keeps_earliest_order_id(self):
        rows = [
            make_row(OrderID="ORD000002", Date="2023-01-01", CustomerID="C00001"),
            make_row(OrderID="ORD000001", Date="2023-01-01", CustomerID="C00001"),
        ]
        result = apply_dedup(make_df(rows))
        assert result.iloc[0]["order_id"] == "ORD000001"

    def test_different_customers_same_date_both_kept(self):
        rows = [
            make_row(OrderID="ORD000001", Date="2023-01-01", CustomerID="C00001"),
            make_row(OrderID="ORD000002", Date="2023-01-01", CustomerID="C00002"),
        ]
        result = apply_dedup(make_df(rows))
        assert len(result) == 2

    def test_same_customer_different_dates_both_kept(self):
        rows = [
            make_row(OrderID="ORD000001", Date="2023-01-01", CustomerID="C00001"),
            make_row(OrderID="ORD000002", Date="2023-01-02", CustomerID="C00001"),
        ]
        result = apply_dedup(make_df(rows))
        assert len(result) == 2

    def test_no_duplicates_remain(self):
        rows = [
            make_row(OrderID="ORD000001", Date="2023-01-01", CustomerID="C00001"),
            make_row(OrderID="ORD000002", Date="2023-01-01", CustomerID="C00001"),
            make_row(OrderID="ORD000003", Date="2023-01-02", CustomerID="C00001"),
        ]
        result = apply_dedup(make_df(rows))
        assert result.duplicated(subset=["fecha", "id_cliente"]).sum() == 0


# ---------------------------------------------------------------------------
# Discount logic
# ---------------------------------------------------------------------------

class TestDiscountLogic:
    def test_online_under_500_receives_10_percent_discount(self):
        rows = [make_row(OrderID=f"ORD{i:06d}", TotalPrice=200.0) for i in range(2)]
        result = apply_discount(make_df(rows))
        assert all(result["descuento"] == 20.0)

    def test_online_at_500_receives_no_discount(self):
        rows = [
            make_row(OrderID=f"ORD{i:06d}", CustomerID=f"C{i:05d}", TotalPrice=100.0)
            for i in range(500)
        ]
        result = apply_discount(make_df(rows))
        assert all(result["descuento"] == 0)

    @pytest.mark.parametrize("method", ["Credit Card", "Debit Card", "Cash"])
    def test_non_online_payment_receives_no_discount(self, method):
        rows = [make_row(OrderID="ORD000001", PaymentMethod=method, TotalPrice=100.0)]
        result = apply_discount(make_df(rows))
        assert result.iloc[0]["descuento"] == 0

    def test_final_total_equals_precio_total_minus_descuento(self):
        rows = [make_row(OrderID=f"ORD{i:06d}", TotalPrice=200.0) for i in range(2)]
        result = apply_discount(make_df(rows))
        pd.testing.assert_series_equal(
            result["final_total"],
            result["precio_total"] - result["descuento"],
            check_names=False,
        )

    def test_non_online_final_total_equals_precio_total(self):
        rows = [make_row(OrderID="ORD000001", PaymentMethod="Cash", TotalPrice=150.0)]
        result = apply_discount(make_df(rows))
        assert result.iloc[0]["final_total"] == 150.0

    def test_discount_amount_is_exactly_10_percent(self):
        rows = [make_row(OrderID=f"ORD{i:06d}", TotalPrice=300.0) for i in range(3)]
        result = apply_discount(make_df(rows))
        assert np.allclose(result["descuento"].to_numpy(), 30.0)
