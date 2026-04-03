from fastapi import APIRouter

from chatbot.product_kb import get_catalog_stats, load_products

router = APIRouter(prefix="/api", tags=["products"])


@router.get("/products")
async def get_products(limit: int = 20, brand: str | None = None):
	df = load_products()
	if df.empty:
		return {"products": [], "total": 0}

	if brand:
		df = df[df["brand"].str.lower().str.contains(brand.lower(), na=False)]

	records = df.head(limit).to_dict(orient="records")
	return {"products": records, "total": len(df)}


@router.get("/products/stats")
async def get_stats():
	return get_catalog_stats()


@router.get("/health")
async def health_check():
	from database.connection import check_connection

	return {
		"status": "ok",
		"db_connected": check_connection(),
	}
