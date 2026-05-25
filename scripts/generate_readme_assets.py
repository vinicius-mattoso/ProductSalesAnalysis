from pathlib import Path
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from sklearn.cluster import KMeans
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX


warnings.filterwarnings("ignore")
sns.set_theme(style="whitegrid", context="notebook")
plt.rcParams["figure.figsize"] = (13, 5)
plt.rcParams["axes.titleweight"] = "bold"

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "raw" / "product_sales_dataset.csv"
OUT_DIR = ROOT / "docs" / "assets"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def money_axis(ax):
    ax.get_yaxis().set_major_formatter(lambda x, _: f"${x/1000:.0f}K")


def mape(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = y_true != 0
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100


def regression_metrics(y_true, y_pred):
    return {
        "MAE": mean_absolute_error(y_true, y_pred),
        "RMSE": np.sqrt(mean_squared_error(y_true, y_pred)),
        "MAPE_%": mape(y_true, y_pred),
    }


def recursive_baseline_forecast(history, horizon, method="naive", window=3):
    values = list(history)
    preds = []
    for _ in range(horizon):
        if method == "naive":
            pred = values[-1]
        elif method == "moving_average":
            pred = np.mean(values[-window:])
        else:
            raise ValueError(method)
        preds.append(float(pred))
        values.append(float(pred))
    return np.array(preds)


def fit_forecast_ets(train_series, horizon):
    model = ExponentialSmoothing(
        train_series,
        trend=None,
        seasonal=None,
        initialization_method="estimated",
    ).fit(optimized=True)
    return np.asarray(model.forecast(horizon), dtype=float)


def fit_forecast_sarimax_drift(train_series, horizon):
    model = SARIMAX(
        train_series,
        order=(0, 1, 0),
        seasonal_order=(0, 0, 0, 0),
        trend="c",
        enforce_stationarity=False,
        enforce_invertibility=False,
    ).fit(disp=False)
    return np.asarray(model.forecast(horizon), dtype=float)


def fit_forecast_arima_grid(train_series, horizon):
    candidate_orders = [
        (0, 0, 0), (1, 0, 0), (0, 0, 1), (1, 0, 1),
        (0, 1, 0), (1, 1, 0), (0, 1, 1), (1, 1, 1),
        (2, 1, 0), (0, 1, 2), (2, 1, 1),
    ]
    candidates = []
    for order in candidate_orders:
        trend_options = ["c"] if order[1] == 0 else ["n", "c"]
        for trend in trend_options:
            try:
                model = SARIMAX(
                    train_series,
                    order=order,
                    seasonal_order=(0, 0, 0, 0),
                    trend=trend,
                    enforce_stationarity=False,
                    enforce_invertibility=False,
                ).fit(disp=False)
                candidates.append((model.aic, model))
            except Exception:
                continue
    best = min(candidates, key=lambda item: item[0])[1]
    return np.asarray(best.forecast(horizon), dtype=float)


def add_time_features(data):
    out = data.copy().sort_values("month")
    out["month_num"] = out["month"].dt.month
    out["quarter"] = out["month"].dt.quarter
    out["time_idx"] = np.arange(len(out))
    out["lag_1"] = out["total_sales"].shift(1)
    out["lag_2"] = out["total_sales"].shift(2)
    out["lag_3"] = out["total_sales"].shift(3)
    out["rolling_mean_3"] = out["total_sales"].shift(1).rolling(3).mean()
    out["rolling_std_3"] = out["total_sales"].shift(1).rolling(3).std()
    out["rolling_mean_6"] = out["total_sales"].shift(1).rolling(6).mean()
    out["pct_change_1"] = out["total_sales"].pct_change(1).shift(1)
    out["pct_change_3"] = out["total_sales"].pct_change(3).shift(1)
    return out


def build_next_feature_row(history, next_month, feature_cols):
    values = history["total_sales"].tolist()
    row = {
        "month_num": next_month.month,
        "quarter": next_month.quarter,
        "time_idx": len(history),
        "lag_1": values[-1],
        "lag_2": values[-2],
        "lag_3": values[-3],
        "rolling_mean_3": np.mean(values[-3:]),
        "rolling_std_3": np.std(values[-3:], ddof=1),
        "rolling_mean_6": np.mean(values[-6:]),
        "pct_change_1": (values[-1] / values[-2]) - 1 if values[-2] != 0 else 0,
        "pct_change_3": (values[-1] / values[-4]) - 1 if len(values) >= 4 and values[-4] != 0 else 0,
    }
    return pd.DataFrame([row])[feature_cols]


def recursive_ml_forecast(model, history, feature_cols, horizon=3):
    history = history[["month", "total_sales"]].copy().sort_values("month")
    preds = []
    for _ in range(horizon):
        next_month = history["month"].max() + pd.DateOffset(months=1)
        pred = max(0, float(model.predict(build_next_feature_row(history, next_month, feature_cols))[0]))
        preds.append(pred)
        history = pd.concat(
            [history, pd.DataFrame({"month": [next_month], "total_sales": [pred]})],
            ignore_index=True,
        )
    return np.array(preds)


df = pd.read_csv(DATA_PATH)
df["Order_Date"] = pd.to_datetime(df["Order_Date"], errors="coerce")
for col in ["Price_USD", "Quantity_Sold", "Total_Sales_USD"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")
df = df.dropna(subset=["Order_Date", "Price_USD", "Quantity_Sold", "Total_Sales_USD"])
df["Year_Month"] = df["Order_Date"].dt.to_period("M").dt.to_timestamp()


# 1. EDA monthly sales
monthly_all = (
    df.set_index("Order_Date")
    .resample("MS")
    .agg(total_sales=("Total_Sales_USD", "sum"), units=("Quantity_Sold", "sum"), orders=("Product_ID", "count"))
    .reset_index()
    .rename(columns={"Order_Date": "month"})
)
fig, ax = plt.subplots(figsize=(13, 5))
sns.lineplot(data=monthly_all, x="month", y="total_sales", marker="o", color="#2F6FED", ax=ax)
ax.set_title("Receita mensal observada")
ax.set_xlabel("")
ax.set_ylabel("Total Sales USD")
money_axis(ax)
plt.xticks(rotation=35)
plt.tight_layout()
plt.savefig(OUT_DIR / "eda_monthly_sales.png", dpi=160, bbox_inches="tight")
plt.close()


# 2. EDA category and city
category_summary = (
    df.groupby("Category", as_index=False)
    .agg(revenue=("Total_Sales_USD", "sum"), units=("Quantity_Sold", "sum"))
    .sort_values("revenue", ascending=False)
)
city_summary = (
    df.groupby("Customer_City", as_index=False)
    .agg(revenue=("Total_Sales_USD", "sum"), avg_ticket=("Total_Sales_USD", "mean"))
    .sort_values("revenue", ascending=False)
)
fig, axes = plt.subplots(1, 2, figsize=(15, 5))
sns.barplot(data=category_summary, y="Category", x="revenue", color="#2F6FED", ax=axes[0])
axes[0].set_title("Receita por categoria")
axes[0].set_xlabel("Total Sales USD")
axes[0].set_ylabel("")
sns.barplot(data=city_summary, y="Customer_City", x="revenue", color="#1D9A6C", ax=axes[1])
axes[1].set_title("Receita por cidade")
axes[1].set_xlabel("Total Sales USD")
axes[1].set_ylabel("")
plt.tight_layout()
plt.savefig(OUT_DIR / "eda_segments.png", dpi=160, bbox_inches="tight")
plt.close()


# 3. Forecasting model comparison
max_order_date = df["Order_Date"].max()
last_month_start = max_order_date.to_period("M").to_timestamp()
last_month_end = max_order_date.to_period("M").to_timestamp("M")
monthly = monthly_all[monthly_all["month"] < last_month_start].copy() if max_order_date.normalize() < last_month_end.normalize() else monthly_all.copy()
test_size = 3
train = monthly.iloc[:-test_size].copy()
test = monthly.iloc[-test_size:].copy()

baseline_predictions = {
    "baseline_naive_last_month": recursive_baseline_forecast(train["total_sales"], test_size, method="naive"),
    "baseline_moving_avg_3m": recursive_baseline_forecast(train["total_sales"], test_size, method="moving_average", window=3),
    "baseline_moving_avg_6m": recursive_baseline_forecast(train["total_sales"], test_size, method="moving_average", window=6),
}
train_series = train.set_index("month")["total_sales"].asfreq("MS")
test_series = test.set_index("month")["total_sales"].asfreq("MS")
ts_predictions = {
    "ts_sarimax_drift": fit_forecast_sarimax_drift(train_series, test_size),
    "ts_exponential_smoothing": fit_forecast_ets(train_series, test_size),
    "ts_arima_grid": fit_forecast_arima_grid(train_series, test_size),
}
feature_cols = [
    "month_num", "quarter", "time_idx", "lag_1", "lag_2", "lag_3",
    "rolling_mean_3", "rolling_std_3", "rolling_mean_6", "pct_change_1", "pct_change_3",
]
ml_dataset = add_time_features(monthly).dropna().reset_index(drop=True)
ml_train = ml_dataset[ml_dataset["month"].isin(train["month"])].copy()
ml_test = ml_dataset[ml_dataset["month"].isin(test["month"])].copy()
ml_models = {
    "ml_random_forest": RandomForestRegressor(random_state=42, n_estimators=300, max_depth=4, min_samples_leaf=2),
    "ml_gradient_boosting": GradientBoostingRegressor(random_state=42, n_estimators=80, learning_rate=0.05, max_depth=2),
}
ml_predictions = {}
for name, model in ml_models.items():
    model.fit(ml_train[feature_cols], ml_train["total_sales"])
    ml_predictions[name] = model.predict(ml_test[feature_cols])

all_eval = []
for source in [baseline_predictions, ts_predictions, ml_predictions]:
    for name, preds in source.items():
        all_eval.append({"model": name, **regression_metrics(test_series, preds)})
all_eval = pd.DataFrame(all_eval).sort_values("RMSE")

fig, ax = plt.subplots(figsize=(13, 5))
sns.barplot(data=all_eval, y="model", x="RMSE", color="#2F6FED", ax=ax)
ax.set_title("Comparacao de modelos de forecasting no backtest")
ax.set_xlabel("RMSE")
ax.set_ylabel("")
plt.tight_layout()
plt.savefig(OUT_DIR / "forecast_model_comparison.png", dpi=160, bbox_inches="tight")
plt.close()


# 4. Forecast selected and scenario band
full_series = monthly.set_index("month")["total_sales"].asfreq("MS")
future_months = pd.date_range(monthly["month"].max() + pd.DateOffset(months=1), periods=3, freq="MS")
candidate_forecasts = []
candidate_forecasts.append(pd.DataFrame({"month": future_months, "forecast": recursive_baseline_forecast(monthly["total_sales"], 3, method="naive"), "model": "baseline_naive_last_month"}))
candidate_forecasts.append(pd.DataFrame({"month": future_months, "forecast": fit_forecast_sarimax_drift(full_series, 3), "model": "ts_sarimax_drift"}))
candidate_forecasts.append(pd.DataFrame({"month": future_months, "forecast": fit_forecast_ets(full_series, 3), "model": "ts_exponential_smoothing"}))
candidate_forecasts.append(pd.DataFrame({"month": future_months, "forecast": fit_forecast_arima_grid(full_series, 3), "model": "ts_arima_grid"}))
final_ml_dataset = add_time_features(monthly).dropna().reset_index(drop=True)
best_ml_model = ml_models["ml_random_forest"]
best_ml_model.fit(final_ml_dataset[feature_cols], final_ml_dataset["total_sales"])
candidate_forecasts.append(pd.DataFrame({"month": future_months, "forecast": recursive_ml_forecast(best_ml_model, monthly, feature_cols, 3), "model": "ml_random_forest"}))
forecast_comparison = pd.concat(candidate_forecasts, ignore_index=True)
champion_model = all_eval.iloc[0]["model"]
champion = forecast_comparison[forecast_comparison["model"] == champion_model]
band = forecast_comparison.groupby("month", as_index=False).agg(scenario_min=("forecast", "min"), scenario_max=("forecast", "max"))
fig, ax = plt.subplots(figsize=(13, 5))
ax.plot(monthly["month"], monthly["total_sales"], marker="o", color="#2F6FED", label="Historico usado no treino")
ax.plot(champion["month"], champion["forecast"], marker="o", color="#1D9A6C", linewidth=2.5, label=f"Forecast selecionado: {champion_model}")
ax.fill_between(band["month"], band["scenario_min"], band["scenario_max"], color="#1D9A6C", alpha=0.12, label="Faixa dos cenarios testados")
ax.axvline(monthly["month"].max(), color="gray", linestyle="--", linewidth=1)
ax.set_title("Forecast trimestral selecionado com faixa de cenarios")
ax.set_xlabel("")
ax.set_ylabel("Total Sales USD")
money_axis(ax)
ax.legend(loc="best")
plt.xticks(rotation=35)
plt.tight_layout()
plt.savefig(OUT_DIR / "forecast_selected.png", dpi=160, bbox_inches="tight")
plt.close()


# 5. Product clustering / ABC
monthly_product = (
    df.groupby(["Product_Name", "Year_Month"], as_index=False)
    .agg(monthly_revenue=("Total_Sales_USD", "sum"), monthly_units=("Quantity_Sold", "sum"), monthly_orders=("Product_ID", "count"))
)
product_base = (
    df.groupby("Product_Name", as_index=False)
    .agg(
        category=("Category", lambda x: x.mode().iloc[0]),
        revenue=("Total_Sales_USD", "sum"),
        units=("Quantity_Sold", "sum"),
        orders=("Product_ID", "count"),
        avg_price=("Price_USD", "mean"),
        avg_ticket=("Total_Sales_USD", "mean"),
        cities=("Customer_City", "nunique"),
        first_sale=("Order_Date", "min"),
        last_sale=("Order_Date", "max"),
    )
)
monthly_stats = (
    monthly_product.groupby("Product_Name", as_index=False)
    .agg(
        active_months=("Year_Month", "nunique"),
        monthly_revenue_mean=("monthly_revenue", "mean"),
        monthly_revenue_std=("monthly_revenue", "std"),
        monthly_units_mean=("monthly_units", "mean"),
    )
)
last_month = df["Year_Month"].max()
recent_start = last_month - pd.DateOffset(months=2)
previous_start = recent_start - pd.DateOffset(months=3)
previous_end = recent_start - pd.DateOffset(months=1)
recent = monthly_product[monthly_product["Year_Month"].between(recent_start, last_month)].groupby("Product_Name", as_index=False)["monthly_revenue"].sum().rename(columns={"monthly_revenue": "revenue_last_3m"})
previous = monthly_product[monthly_product["Year_Month"].between(previous_start, previous_end)].groupby("Product_Name", as_index=False)["monthly_revenue"].sum().rename(columns={"monthly_revenue": "revenue_prev_3m"})
product_features = product_base.merge(monthly_stats, on="Product_Name", how="left").merge(recent, on="Product_Name", how="left").merge(previous, on="Product_Name", how="left")
product_features[["revenue_last_3m", "revenue_prev_3m", "monthly_revenue_std"]] = product_features[["revenue_last_3m", "revenue_prev_3m", "monthly_revenue_std"]].fillna(0)
product_features["demand_cv"] = np.where(product_features["monthly_revenue_mean"] > 0, product_features["monthly_revenue_std"] / product_features["monthly_revenue_mean"], 0)
product_features["recent_growth_pct"] = np.where(product_features["revenue_prev_3m"] > 0, (product_features["revenue_last_3m"] / product_features["revenue_prev_3m"] - 1) * 100, 0)
product_features["recency_days"] = (df["Order_Date"].max() - product_features["last_sale"]).dt.days
score_cols = ["revenue", "units", "orders", "cities", "recent_growth_pct"]
score_scaled = pd.DataFrame(MinMaxScaler().fit_transform(product_features[score_cols]), columns=[f"score_{col}" for col in score_cols], index=product_features.index)
volatility_scaled = MinMaxScaler().fit_transform(product_features[["demand_cv"]]).ravel()
product_scored = pd.concat([product_features, score_scaled], axis=1)
product_scored["potential_score"] = (
    0.40 * product_scored["score_revenue"]
    + 0.25 * product_scored["score_units"]
    + 0.15 * product_scored["score_orders"]
    + 0.10 * product_scored["score_cities"]
    + 0.10 * product_scored["score_recent_growth_pct"]
    - 0.10 * volatility_scaled
)
product_scored["potential_score"] = MinMaxScaler().fit_transform(product_scored[["potential_score"]]).ravel() * 100
cluster_features = ["revenue", "units", "orders", "avg_price", "avg_ticket", "cities", "active_months", "recent_growth_pct", "demand_cv", "recency_days"]
X_scaled = StandardScaler().fit_transform(product_scored[cluster_features].replace([np.inf, -np.inf], 0).fillna(0))
product_scored["cluster"] = KMeans(n_clusters=3, random_state=42, n_init=20).fit_predict(X_scaled)
final_ranking = product_scored.sort_values("potential_score", ascending=False).reset_index(drop=True)
final_ranking["rank"] = np.arange(1, len(final_ranking) + 1)
final_ranking["rank_pct"] = final_ranking["rank"] / len(final_ranking)
final_ranking["abc_potential_class"] = np.select([final_ranking["rank_pct"] <= 0.30, final_ranking["rank_pct"] <= 0.70], ["A", "B"], default="C")

fig, ax = plt.subplots(figsize=(13, 6))
sns.barplot(
    data=final_ranking.head(15),
    y="Product_Name",
    x="potential_score",
    hue="abc_potential_class",
    dodge=False,
    palette={"A": "#1D9A6C", "B": "#2F6FED", "C": "#D84B55"},
    ax=ax,
)
ax.set_title("Top 15 produtos por potencial comercial")
ax.set_xlabel("Potential Score")
ax.set_ylabel("")
ax.legend(title="Classe ABC")
plt.tight_layout()
plt.savefig(OUT_DIR / "cluster_top_products.png", dpi=160, bbox_inches="tight")
plt.close()

fig, ax = plt.subplots(figsize=(12, 6))
sns.scatterplot(
    data=final_ranking,
    x="units",
    y="revenue",
    hue="abc_potential_class",
    size="potential_score",
    sizes=(80, 450),
    palette={"A": "#1D9A6C", "B": "#2F6FED", "C": "#D84B55"},
    ax=ax,
)
for _, row in final_ranking.head(8).iterrows():
    ax.annotate(row["Product_Name"], (row["units"], row["revenue"]), fontsize=9, xytext=(5, 5), textcoords="offset points")
ax.set_title("Receita x unidades vendidas por classe ABC")
ax.set_xlabel("Units Sold")
ax.set_ylabel("Total Sales USD")
money_axis(ax)
plt.tight_layout()
plt.savefig(OUT_DIR / "cluster_revenue_units.png", dpi=160, bbox_inches="tight")
plt.close()

print(f"Assets generated in {OUT_DIR}")
