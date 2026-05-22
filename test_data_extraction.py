"""
Unit tests for the transform logic in data_extraction.ipynb.

Each helper below mirrors the corresponding notebook cell exactly so tests
stay in sync with the notebook without requiring a live Kaggle or DB connection.
"""

import datetime
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


def build_dim_fecha(start: str, end: str) -> pd.DataFrame:
    """Mirrors the dim_fecha population logic in notebook cell 4.6."""
    dates = pd.date_range(start=start, end=end, freq="D")
    return pd.DataFrame({
        "fecha":         dates.date,
        "anio":          dates.year,
        "trimestre":     dates.quarter,
        "mes":           dates.month,
        "nombre_mes":    dates.strftime("%B"),
        "semana_anio":   dates.isocalendar().week.astype(int).values,
        "dia":           dates.day,
        "dia_semana":    dates.isocalendar().day.astype(int).values,
        "nombre_dia":    dates.strftime("%A"),
        "es_fin_semana": dates.isocalendar().day.astype(int).values >= 6,
    })


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


# ---------------------------------------------------------------------------
# dim_fecha generation
# ---------------------------------------------------------------------------

class TestDimFecha:
    def test_row_count_matches_date_range(self):
        df = build_dim_fecha("2023-01-01", "2023-01-31")
        assert len(df) == 31

    def test_single_day_range_produces_one_row(self):
        df = build_dim_fecha("2024-06-15", "2024-06-15")
        assert len(df) == 1

    def test_no_date_gaps(self):
        df = build_dim_fecha("2023-01-01", "2023-03-31")
        dates = pd.to_datetime(df["fecha"])
        diffs = dates.diff().dropna()
        assert (diffs == pd.Timedelta("1 day")).all()

    def test_all_required_columns_present(self):
        df = build_dim_fecha("2023-01-01", "2023-01-07")
        expected = {
            "fecha", "anio", "trimestre", "mes", "nombre_mes",
            "semana_anio", "dia", "dia_semana", "nombre_dia", "es_fin_semana",
        }
        assert expected.issubset(df.columns)

    def test_sunday_is_fin_semana(self):
        # 2023-01-01 is a Sunday
        df = build_dim_fecha("2023-01-01", "2023-01-01")
        assert df.iloc[0]["es_fin_semana"] == True

    def test_saturday_is_fin_semana(self):
        # 2023-01-07 is a Saturday
        df = build_dim_fecha("2023-01-07", "2023-01-07")
        assert df.iloc[0]["es_fin_semana"] == True

    def test_monday_is_not_fin_semana(self):
        # 2023-01-02 is a Monday
        df = build_dim_fecha("2023-01-02", "2023-01-02")
        assert df.iloc[0]["es_fin_semana"] == False

    def test_friday_is_not_fin_semana(self):
        # 2023-01-06 is a Friday
        df = build_dim_fecha("2023-01-06", "2023-01-06")
        assert df.iloc[0]["es_fin_semana"] == False

    def test_dia_semana_saturday_is_6(self):
        df = build_dim_fecha("2023-01-07", "2023-01-07")
        assert df.iloc[0]["dia_semana"] == 6

    def test_dia_semana_sunday_is_7(self):
        df = build_dim_fecha("2023-01-01", "2023-01-01")
        assert df.iloc[0]["dia_semana"] == 7

    def test_date_attributes_extracted_correctly(self):
        df = build_dim_fecha("2024-06-15", "2024-06-15")
        row = df.iloc[0]
        assert row["anio"] == 2024
        assert row["mes"] == 6
        assert row["dia"] == 15

    @pytest.mark.parametrize("date,expected_q", [
        ("2023-03-31", 1),
        ("2023-04-01", 2),
        ("2023-07-01", 3),
        ("2023-10-01", 4),
    ])
    def test_trimestre_boundaries(self, date, expected_q):
        df = build_dim_fecha(date, date)
        assert df.iloc[0]["trimestre"] == expected_q

    def test_weekend_count_in_full_week(self):
        # 2023-01-02 Mon → 2023-01-08 Sun: exactly 2 weekend days
        df = build_dim_fecha("2023-01-02", "2023-01-08")
        assert df["es_fin_semana"].sum() == 2

    def test_leap_day_included(self):
        # 2024 is a leap year
        df = build_dim_fecha("2024-02-01", "2024-02-29")
        assert len(df) == 29
        assert datetime.date(2024, 2, 29) in df["fecha"].values

    def test_full_year_has_365_days(self):
        df = build_dim_fecha("2023-01-01", "2023-12-31")
        assert len(df) == 365

    def test_nombre_dia_and_nombre_mes_are_nonempty_strings(self):
        df = build_dim_fecha("2023-06-15", "2023-06-15")
        assert isinstance(df.iloc[0]["nombre_dia"], str) and len(df.iloc[0]["nombre_dia"]) > 0
        assert isinstance(df.iloc[0]["nombre_mes"], str) and len(df.iloc[0]["nombre_mes"]) > 0


# ---------------------------------------------------------------------------
# Weekend sales filter
# ---------------------------------------------------------------------------

class TestWeekendSalesFilter:
    def _make_week_with_sales(self):
        """One order per day for Mon 2023-01-02 through Sun 2023-01-08."""
        dim = build_dim_fecha("2023-01-02", "2023-01-08")
        sales = pd.DataFrame({
            "fecha":       dim["fecha"],
            "final_total": [100.0] * 7,
        })
        return pd.merge(sales, dim, on="fecha")

    def test_weekend_filter_returns_only_saturday_and_sunday(self):
        merged = self._make_week_with_sales()
        weekend = merged[merged["es_fin_semana"]]
        assert set(weekend["nombre_dia"].unique()) == {"Saturday", "Sunday"}

    def test_weekend_filter_excludes_all_weekdays(self):
        merged = self._make_week_with_sales()
        weekend = merged[merged["es_fin_semana"]]
        weekdays = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday"}
        assert weekdays.isdisjoint(set(weekend["nombre_dia"].unique()))

    def test_weekend_total_gastado_is_correct(self):
        merged = self._make_week_with_sales()
        total = merged[merged["es_fin_semana"]]["final_total"].sum()
        assert total == 200.0  # 2 weekend days × $100

    def test_weekday_total_gastado_is_correct(self):
        merged = self._make_week_with_sales()
        total = merged[~merged["es_fin_semana"]]["final_total"].sum()
        assert total == 500.0  # 5 weekdays × $100
