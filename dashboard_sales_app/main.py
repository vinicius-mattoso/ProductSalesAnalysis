from functools import lru_cache
import os
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
DATA_PATH = PROJECT_ROOT / "data" / "raw" / "product_sales_dataset.csv"

app = FastAPI(title="Product Sales Dashboard", version="0.1.0")
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=APP_DIR / "templates")


@lru_cache(maxsize=1)
def load_sales_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df["Order_Date"] = pd.to_datetime(df["Order_Date"], errors="coerce")
    df["Price_USD"] = pd.to_numeric(df["Price_USD"], errors="coerce")
    df["Quantity_Sold"] = pd.to_numeric(df["Quantity_Sold"], errors="coerce")
    df["Total_Sales_USD"] = pd.to_numeric(df["Total_Sales_USD"], errors="coerce")
    df = df.dropna(subset=["Order_Date", "Price_USD", "Quantity_Sold", "Total_Sales_USD"])
    df["Year_Month"] = df["Order_Date"].dt.to_period("M").dt.to_timestamp()
    df["Month_Label"] = df["Year_Month"].dt.strftime("%b/%Y")
    df["Quarter"] = df["Order_Date"].dt.to_period("Q").astype(str)
    df["Day_Of_Week"] = df["Order_Date"].dt.day_name()
    return df


def apply_filters(
    df: pd.DataFrame,
    category: str | None = None,
    city: str | None = None,
    product: str | None = None,
) -> pd.DataFrame:
    filtered = df.copy()
    if category and category != "all":
        filtered = filtered[filtered["Category"] == category]
    if city and city != "all":
        filtered = filtered[filtered["Customer_City"] == city]
    if product and product != "all":
        filtered = filtered[filtered["Product_Name"] == product]
    return filtered


def pct_change(current: float, previous: float) -> float:
    if previous == 0 or pd.isna(previous):
        return 0.0
    return ((current - previous) / previous) * 100


def trend_label(value: float) -> str:
    if value > 2:
        return "up"
    if value < -2:
        return "down"
    return "flat"


def money(value: float) -> str:
    return f"${value:,.0f}"


def compact_number(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{value:,.0f}"


def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    monthly = (
        df.groupby("Year_Month", as_index=False)
        .agg(
            revenue=("Total_Sales_USD", "sum"),
            units=("Quantity_Sold", "sum"),
            orders=("Product_ID", "count"),
            avg_ticket=("Total_Sales_USD", "mean"),
        )
        .sort_values("Year_Month")
    )
    monthly["label"] = monthly["Year_Month"].dt.strftime("%b/%Y")
    monthly["revenue_mom_pct"] = monthly["revenue"].pct_change().replace([np.inf, -np.inf], 0).fillna(0) * 100
    monthly["moving_avg_3m"] = monthly["revenue"].rolling(3, min_periods=1).mean()
    return monthly


def dimension_summary(df: pd.DataFrame, dimension: str, limit: int | None = None) -> pd.DataFrame:
    summary = (
        df.groupby(dimension, as_index=False)
        .agg(
            revenue=("Total_Sales_USD", "sum"),
            units=("Quantity_Sold", "sum"),
            orders=("Product_ID", "count"),
            avg_price=("Price_USD", "mean"),
            avg_ticket=("Total_Sales_USD", "mean"),
        )
        .sort_values("revenue", ascending=False)
    )
    total = summary["revenue"].sum()
    summary["share_pct"] = np.where(total > 0, summary["revenue"] / total * 100, 0)
    if limit:
        return summary.head(limit)
    return summary


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    df = load_sales_data()
    context = {
        "request": request,
        "categories": sorted(df["Category"].dropna().unique().tolist()),
        "cities": sorted(df["Customer_City"].dropna().unique().tolist()),
        "products": sorted(df["Product_Name"].dropna().unique().tolist()),
        "date_min": df["Order_Date"].min().strftime("%Y-%m-%d"),
        "date_max": df["Order_Date"].max().strftime("%Y-%m-%d"),
    }
    return templates.TemplateResponse(request, "index.html", context)


@app.get("/api/dashboard")
async def dashboard_data(
    category: str = Query("all"),
    city: str = Query("all"),
    product: str = Query("all"),
):
    df = apply_filters(load_sales_data(), category, city, product)
    if df.empty:
        return {"empty": True}

    monthly = monthly_summary(df)
    current_month = monthly.iloc[-1]
    previous_month = monthly.iloc[-2] if len(monthly) > 1 else current_month

    revenue = float(df["Total_Sales_USD"].sum())
    units = int(df["Quantity_Sold"].sum())
    orders = int(len(df))
    avg_ticket = revenue / orders if orders else 0
    avg_price = revenue / units if units else 0
    revenue_delta = pct_change(float(current_month["revenue"]), float(previous_month["revenue"]))
    units_delta = pct_change(float(current_month["units"]), float(previous_month["units"]))
    orders_delta = pct_change(float(current_month["orders"]), float(previous_month["orders"]))
    ticket_delta = pct_change(float(current_month["avg_ticket"]), float(previous_month["avg_ticket"]))

    top_products = dimension_summary(df, "Product_Name", 8)
    categories = dimension_summary(df, "Category")
    cities = dimension_summary(df, "Customer_City")

    product_table = top_products.copy()
    product_table["revenue_fmt"] = product_table["revenue"].map(money)
    product_table["units_fmt"] = product_table["units"].map(compact_number)
    product_table["avg_ticket_fmt"] = product_table["avg_ticket"].map(lambda x: f"${x:,.0f}")
    product_table["share_fmt"] = product_table["share_pct"].map(lambda x: f"{x:.1f}%")

    category_city = (
        df.groupby(["Category", "Customer_City"], as_index=False)["Total_Sales_USD"]
        .sum()
        .rename(columns={"Total_Sales_USD": "revenue"})
    )

    leaders = {
        "product": str(top_products.iloc[0]["Product_Name"]),
        "category": str(categories.iloc[0]["Category"]),
        "city": str(cities.iloc[0]["Customer_City"]),
    }

    return {
        "empty": False,
        "period": {
            "start": df["Order_Date"].min().strftime("%d %b %Y"),
            "end": df["Order_Date"].max().strftime("%d %b %Y"),
            "orders": orders,
        },
        "kpis": [
            {"label": "Receita total", "value": money(revenue), "delta": revenue_delta, "trend": trend_label(revenue_delta)},
            {"label": "Unidades vendidas", "value": compact_number(units), "delta": units_delta, "trend": trend_label(units_delta)},
            {"label": "Pedidos", "value": compact_number(orders), "delta": orders_delta, "trend": trend_label(orders_delta)},
            {"label": "Ticket medio", "value": f"${avg_ticket:,.0f}", "delta": ticket_delta, "trend": trend_label(ticket_delta)},
            {"label": "Preco medio realizado", "value": f"${avg_price:,.0f}", "delta": 0, "trend": "flat"},
        ],
        "leaders": leaders,
        "monthly": {
            "labels": monthly["label"].tolist(),
            "revenue": monthly["revenue"].round(2).tolist(),
            "units": monthly["units"].astype(int).tolist(),
            "orders": monthly["orders"].astype(int).tolist(),
            "moving_avg": monthly["moving_avg_3m"].round(2).tolist(),
            "mom": monthly["revenue_mom_pct"].round(2).tolist(),
        },
        "categories": {
            "labels": categories["Category"].tolist(),
            "revenue": categories["revenue"].round(2).tolist(),
            "units": categories["units"].astype(int).tolist(),
            "share": categories["share_pct"].round(2).tolist(),
        },
        "cities": {
            "labels": cities["Customer_City"].tolist(),
            "revenue": cities["revenue"].round(2).tolist(),
            "ticket": cities["avg_ticket"].round(2).tolist(),
        },
        "top_products": product_table[
            ["Product_Name", "revenue_fmt", "units_fmt", "avg_ticket_fmt", "share_fmt", "share_pct"]
        ].to_dict(orient="records"),
        "category_city": category_city.to_dict(orient="records"),
    }


@app.get("/api/options")
async def options():
    df = load_sales_data()
    return {
        "categories": sorted(df["Category"].dropna().unique().tolist()),
        "cities": sorted(df["Customer_City"].dropna().unique().tolist()),
        "products": sorted(df["Product_Name"].dropna().unique().tolist()),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=os.getenv("DASHBOARD_HOST", "127.0.0.1"),
        port=int(os.getenv("DASHBOARD_PORT", "8001")),
    )
