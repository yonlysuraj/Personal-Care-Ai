"""
Loads products CSV into memory and performs keyword search to find
relevant products for a given user query.
Results are formatted as context for the LLM system prompt.
"""
from functools import lru_cache
from pathlib import Path
import re

import pandas as pd

# Tracks which CSV the chatbot is currently using
ALL_CSVS_TOKEN = "__ALL__"
_active_csv: str = ALL_CSVS_TOKEN
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
STOPWORDS = {
	"a",
	"an",
	"and",
	"are",
	"best",
	"for",
	"from",
	"give",
	"i",
	"in",
	"is",
	"me",
	"my",
	"of",
	"on",
	"please",
	"show",
	"the",
	"to",
	"under",
	"with",
	"you",
}

CATEGORY_ALIASES = {
	"lipstick": ["lipstick", "lipsticks"],
	"perfume": ["perfume", "perfumes", "fragrance", "fragrances"],
	"nail polish": ["nail polish", "nail polishes", "nailpolish", "nail", "polish"],
	"beard serum": ["beard serum", "beard serums", "beard oil", "beard oils", "beard growth"],
	"shower gel": ["shower gel", "shower gels", "body wash", "body washes", "shower"],
	"massage oils": ["massage oil", "massage oils", "body oil", "body oils"],
	"body lotion": ["body lotion", "body lotions", "lotion", "lotions", "body cream", "body creams"],
}
GENERIC_CATEGORY_WORDS = {"and", "or", "care", "personal", "set", "with", "for", "the"}


def _normalize_keywords(query: str) -> list[str]:
	raw_tokens = re.findall(r"[a-zA-Z0-9]+", query.lower())
	keywords: list[str] = []
	for token in raw_tokens:
		if len(token) < 3 or token in STOPWORDS:
			continue
		keywords.append(token)
		# naive singularization for words like lipsticks/perfumes/polishes
		if token.endswith("s") and len(token) > 4:
			keywords.append(token[:-1])

	# Preserve order while removing duplicates.
	seen: set[str] = set()
	normalized: list[str] = []
	for keyword in keywords:
		if keyword not in seen:
			seen.add(keyword)
			normalized.append(keyword)
	return normalized


def _detect_requested_categories(query: str, available_categories: list[str] | None = None) -> list[str]:
	query_lower = query.lower()
	requested: list[str] = []
	for canonical, aliases in CATEGORY_ALIASES.items():
		if any(alias in query_lower for alias in aliases):
			requested.append(canonical)

	# Dynamic category detection: auto-detect new categories present in scraped CSVs.
	if available_categories:
		query_tokens = set(_normalize_keywords(query))
		for category_name in available_categories:
			cat_tokens = {
				t
				for t in re.findall(r"[a-zA-Z0-9]+", category_name.lower())
				if len(t) >= 3 and t not in STOPWORDS and t not in GENERIC_CATEGORY_WORDS
			}
			if not cat_tokens:
				continue
			# If at least one meaningful token overlaps, treat this category as requested.
			if query_tokens.intersection(cat_tokens):
				requested.append(category_name.lower())

	# Preserve order while de-duplicating.
	seen: set[str] = set()
	ordered: list[str] = []
	for category in requested:
		if category not in seen:
			seen.add(category)
			ordered.append(category)
	return ordered


def _category_match_mask(category_series: pd.Series, category_name: str) -> pd.Series:
	if category_name == "lipstick":
		return category_series.str.contains("lipstick", na=False)
	if category_name == "perfume":
		return category_series.str.contains("perfume|fragrance", regex=True, na=False)
	if category_name == "nail polish":
		return category_series.str.contains(r"nail\s*polish", regex=True, na=False)
	if category_name == "beard serum":
		return category_series.str.contains("beard|serum|oil", regex=True, na=False)
	if category_name == "shower gel":
		return category_series.str.contains("shower gel|body wash|shower", regex=True, na=False)
	if category_name == "massage oils":
		return category_series.str.contains("massage|body oil", regex=True, na=False)
	if category_name == "body lotion":
		return category_series.str.contains("body cream|body lotion|lotion", regex=True, na=False)

	# Fallback for new categories scraped in the future (no code change needed).
	tokens = [
		re.escape(t)
		for t in re.findall(r"[a-zA-Z0-9]+", category_name.lower())
		if len(t) >= 3 and t not in STOPWORDS and t not in GENERIC_CATEGORY_WORDS
	]
	if tokens:
		pattern = "|".join(tokens)
		return category_series.str.contains(pattern, regex=True, na=False)
	return pd.Series([False] * len(category_series), index=category_series.index)


@lru_cache(maxsize=1)
def load_products(csv_path: str = "") -> pd.DataFrame:
	"""
	lru_cache means the CSV is read ONCE per process.
	On each cold start, it is re-read once per process - acceptable for a small CSV.
	"""
	path = Path(csv_path)
	if not path.exists():
		return pd.DataFrame()
	return pd.read_csv(path)


@lru_cache(maxsize=1)
def load_all_products() -> pd.DataFrame:
	"""Load and merge all products_*.csv files from the data folder."""
	if not DATA_DIR.exists():
		return pd.DataFrame()

	frames: list[pd.DataFrame] = []
	for csv_file in sorted(DATA_DIR.glob("products_*.csv")):
		try:
			frames.append(pd.read_csv(csv_file))
		except Exception:
			continue

	if not frames:
		return pd.DataFrame()

	merged = pd.concat(frames, ignore_index=True)
	if "product_url" in merged.columns:
		merged = merged.drop_duplicates(subset=["product_url"], keep="first")
	return merged


def get_active_products() -> pd.DataFrame:
	if _active_csv == ALL_CSVS_TOKEN:
		return load_all_products()
	return load_products(_active_csv)


def reload_products(csv_path: str | None = None) -> int:
	"""
	Clears the product cache and reloads from the given CSV.
	Returns the number of products loaded.
	"""
	global _active_csv
	if csv_path:
		_active_csv = csv_path
	load_products.cache_clear()
	load_all_products.cache_clear()
	df = get_active_products()
	return len(df)


def get_active_csv() -> str:
	return _active_csv


def search_products(query: str, max_results: int = 6) -> list[dict]:
	"""Basic keyword search across brand and product_name columns."""
	df = get_active_products()
	if df.empty:
		return []

	keywords = _normalize_keywords(query)
	if not keywords:
		keywords = ["lipstick", "perfume", "nail", "polish"]

	brand_col = df.get("brand", pd.Series(dtype=str)).astype(str).str.lower()
	name_col = df.get("product_name", pd.Series(dtype=str)).astype(str).str.lower()
	category_col = df.get("category", pd.Series(dtype=str)).astype(str).str.lower()
	breadcrumbs_col = df.get("breadcrumbs", pd.Series(dtype=str)).astype(str).str.lower()

	mask = pd.Series([False] * len(df))
	for keyword in keywords:
		mask |= (
			brand_col.str.contains(keyword, na=False)
			| name_col.str.contains(keyword, na=False)
			| category_col.str.contains(keyword, na=False)
			| breadcrumbs_col.str.contains(keyword, na=False)
		)

	results = df[mask] if mask.any() else df
	if "rating" in results.columns and "reviews_count" in results.columns:
		results = results.sort_values(["rating", "reviews_count"], ascending=[False, False])
	elif "rating" in results.columns:
		results = results.sort_values("rating", ascending=False)

	available_categories = []
	if "category" in results.columns:
		available_categories = (
			results["category"].dropna().astype(str).str.lower().drop_duplicates().tolist()
		)

	requested_categories = _detect_requested_categories(query, available_categories=available_categories)
	if requested_categories and "category" in results.columns and len(results) > 0:
		cat_series = results["category"].astype(str).str.lower()
		selected_idx: list[int] = []
		per_category = max(1, max_results // max(1, len(requested_categories)))

		for category_name in requested_categories:
			cat_rows = results[_category_match_mask(cat_series, category_name)]
			selected_idx.extend(cat_rows.head(per_category).index.tolist())

		# Fill remaining slots with the top-ranked rows not yet selected.
		selected_idx = list(dict.fromkeys(selected_idx))
		if len(selected_idx) < max_results:
			for idx in results.index.tolist():
				if idx not in selected_idx:
					selected_idx.append(idx)
				if len(selected_idx) >= max_results:
					break

		results = results.loc[selected_idx]

	return results.head(max_results).to_dict(orient="records")


def format_products_for_prompt(products: list[dict]) -> str:
	"""Converts product dicts to a readable string for the LLM system prompt."""
	if not products:
		return "No specific products found. Use your general knowledge."

	lines = []
	for product in products:
		category = product.get("category", "N/A")
		lines.append(
			f"- Category: {category} | {product.get('brand', '?')} - {product.get('product_name', '?')} | "
			f"Price: {product.get('discounted_price', 'N/A')} | "
			f"Rating: {product.get('rating', 'N/A')} stars | "
			f"URL: {product.get('product_url', 'N/A')}"
		)
	return "\n".join(lines)


def get_catalog_stats() -> dict:
	df = get_active_products()
	if df.empty:
		return {}
	return {
		"total": len(df),
		"brands": int(df["brand"].nunique()) if "brand" in df else 0,
		"avg_price": float(df["price_numeric"].mean()) if "price_numeric" in df else 0,
		"avg_rating": float(df["rating"].mean()) if "rating" in df else 0,
	}
