from pathlib import Path

import pandas as pd


def export_to_csv(products: list[dict], path: str = "data/products.csv") -> None:
	if not products:
		print("No products to export.")
		return

	Path(path).parent.mkdir(parents=True, exist_ok=True)
	df = pd.DataFrame(products)
	df.drop_duplicates(subset=["product_url"], keep="first", inplace=True)

	# Numeric price column for downstream filtering and stats
	cleaned_prices = (
		df["discounted_price"]
		.astype(str)
		.str.replace(",", "", regex=False)
		.str.replace(r"[^\d.]", "", regex=True)
		.str.strip(".")
		.replace("", "0")
	)
	df["price_numeric"] = pd.to_numeric(cleaned_prices, errors="coerce").fillna(0.0)
	df.to_csv(path, index=False, encoding="utf-8-sig")

	print(f"Exported {len(df)} products -> {path}")
	print(f"Brands: {df['brand'].nunique()}")
	print(f"Price range: Rs.{df['price_numeric'].min():.0f} - Rs.{df['price_numeric'].max():.0f}")
