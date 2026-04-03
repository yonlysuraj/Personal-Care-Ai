"""
Loads products.csv into memory and performs keyword search to find
relevant products for a given user query.
Results are formatted as context for the LLM system prompt.
"""
from functools import lru_cache
from pathlib import Path

import pandas as pd


@lru_cache(maxsize=1)
def load_products(csv_path: str = "data/products.csv") -> pd.DataFrame:
	"""
	lru_cache means the CSV is read ONCE per process.
	On Vercel, each cold start re-reads it - acceptable for a small CSV.
	"""
	path = Path(csv_path)
	if not path.exists():
		return pd.DataFrame()
	return pd.read_csv(path)


def search_products(query: str, max_results: int = 6) -> list[dict]:
	"""Basic keyword search across brand and product_name columns."""
	df = load_products()
	if df.empty:
		return []

	keywords = query.lower().split()
	mask = pd.Series([False] * len(df))
	for keyword in keywords:
		mask |= (
			df.get("brand", pd.Series(dtype=str)).astype(str).str.lower().str.contains(keyword, na=False)
			| df.get("product_name", pd.Series(dtype=str))
			.astype(str)
			.str.lower()
			.str.contains(keyword, na=False)
		)

	results = df[mask] if mask.any() else df
	if "rating" in results.columns:
		results = results.sort_values("rating", ascending=False)

	return results.head(max_results).to_dict(orient="records")


def format_products_for_prompt(products: list[dict]) -> str:
	"""Converts product dicts to a readable string for the LLM system prompt."""
	if not products:
		return "No specific products found. Use your general knowledge."

	lines = []
	for product in products:
		lines.append(
			f"- {product.get('brand', '?')} - {product.get('product_name', '?')} | "
			f"Price: {product.get('discounted_price', 'N/A')} | "
			f"Rating: {product.get('rating', 'N/A')} stars | "
			f"URL: {product.get('product_url', 'N/A')}"
		)
	return "\n".join(lines)


def get_catalog_stats() -> dict:
	df = load_products()
	if df.empty:
		return {}
	return {
		"total": len(df),
		"brands": int(df["brand"].nunique()) if "brand" in df else 0,
		"avg_price": float(df["price_numeric"].mean()) if "price_numeric" in df else 0,
		"avg_rating": float(df["rating"].mean()) if "rating" in df else 0,
	}
