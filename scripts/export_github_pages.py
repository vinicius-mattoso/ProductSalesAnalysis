from __future__ import annotations

import argparse
import json
import re
import shutil
from html import escape
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "raw" / "product_sales_dataset.csv"
APP_DIR = ROOT / "dashboard_sales_app"
OUT_DIR = ROOT / "docs" / "demos" / "productsalesanalysis"


def option_tags(values: list[str]) -> str:
    return "\n".join(f'              <option value="{escape(value)}">{escape(value)}</option>' for value in values)


def replace_select_options(html: str, select_id: str, values: list[str], all_label: str) -> str:
    pattern = re.compile(
        rf'(<select id="{select_id}">\s*<option value="all">{all_label}</option>).*?(</select>)',
        re.DOTALL,
    )
    replacement = "\\1\n" + option_tags(values) + "\n            \\2"
    return pattern.sub(replacement, html)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the Product Sales dashboard as a static GitHub Pages bundle.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=OUT_DIR,
        help="Output folder. Default: docs/demos/productsalesanalysis",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = args.out.resolve()
    asset_dir = out_dir / "assets"

    df = pd.read_csv(DATA_PATH)
    df["Order_Date"] = pd.to_datetime(df["Order_Date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df = df.dropna(subset=["Order_Date", "Price_USD", "Quantity_Sold", "Total_Sales_USD"])

    categories = sorted(df["Category"].dropna().unique().tolist())
    cities = sorted(df["Customer_City"].dropna().unique().tolist())
    products = sorted(df["Product_Name"].dropna().unique().tolist())

    out_dir.mkdir(parents=True, exist_ok=True)
    asset_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(APP_DIR / "static" / "styles.css", asset_dir / "styles.css")
    shutil.copy2(APP_DIR / "static" / "app.js", asset_dir / "app.js")

    with (asset_dir / "sales-data.json").open("w", encoding="utf-8") as file:
        json.dump(df.to_dict(orient="records"), file, ensure_ascii=False)

    html = (APP_DIR / "templates" / "index.html").read_text(encoding="utf-8")
    html = html.replace('{{ url_for(\'static\', path=\'/styles.css\') }}', "assets/styles.css")
    html = html.replace('{{ url_for(\'static\', path=\'/app.js\') }}', "assets/app.js")
    html = html.replace("{{ date_min }}", str(df["Order_Date"].min()))
    html = html.replace("{{ date_max }}", str(df["Order_Date"].max()))
    html = replace_select_options(html, "categoryFilter", categories, "Todas")
    html = replace_select_options(html, "cityFilter", cities, "Todas")
    html = replace_select_options(html, "productFilter", products, "Todos")
    html = html.replace(
        '<script src="assets/app.js"></script>',
        '<script>window.STATIC_SALES_DATA_URL = "assets/sales-data.json";</script>\n    <script src="assets/app.js"></script>',
    )

    (out_dir / "index.html").write_text(html, encoding="utf-8")
    (out_dir / "README.md").write_text(
        "\n".join(
            [
                "# Product Sales Analysis - Static Page",
                "",
                "Pasta estatica pronta para GitHub Pages.",
                "",
                "Para publicar dentro do repositorio `home`, copie esta pasta para:",
                "",
                "```text",
                "home/demos/productsalesanalysis/",
                "```",
                "",
                "URL esperada:",
                "",
                "```text",
                "https://vinicius-mattoso.github.io/home/demos/productsalesanalysis/",
                "```",
                "",
                "Arquivos principais:",
                "",
                "- `index.html`: pagina do dashboard.",
                "- `assets/app.js`: logica de filtros, KPIs e graficos.",
                "- `assets/styles.css`: estilos da pagina.",
                "- `assets/sales-data.json`: dados pre-processados a partir do CSV.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Static dashboard exported to {out_dir}")


if __name__ == "__main__":
    main()
