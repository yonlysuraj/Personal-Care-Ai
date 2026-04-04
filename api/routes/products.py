from pathlib import Path

from fastapi import APIRouter

from chatbot.product_kb import ALL_CSVS_TOKEN, get_active_csv, get_catalog_stats, load_products, reload_products
from config.logging_setup import get_logger

router = APIRouter(prefix="/api", tags=["products"])
logger = get_logger("api.routes.products", app_name="api")
DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def _list_available_datasets() -> list[str]:
	if not DATA_DIR.exists():
		return []
	return sorted(path.name for path in DATA_DIR.glob("*.csv"))


@router.get("/products")
async def get_products(limit: int = 20, brand: str | None = None):
	logger.info("Products request received limit=%s brand=%s active_csv=%s", limit, brand, get_active_csv())
	df = load_products(get_active_csv())
	if df.empty:
		logger.info("Products request returned empty dataset active_csv=%s", get_active_csv())
		return {"products": [], "total": 0}

	if brand:
		df = df[df["brand"].str.lower().str.contains(brand.lower(), na=False)]

	records = df.head(limit).to_dict(orient="records")
	logger.info("Products request served count=%s total_after_filter=%s", len(records), len(df))
	return {"products": records, "total": len(df)}


@router.get("/products/stats")
async def get_stats():
	logger.info("Stats request received active_csv=%s", get_active_csv())
	stats = get_catalog_stats()
	source_mode = "all" if get_active_csv() == ALL_CSVS_TOKEN else "single"
	if not stats:
		return {"active_csv": get_active_csv(), "source_mode": source_mode}
	return {"active_csv": get_active_csv(), "source_mode": source_mode, **stats}


@router.get("/products/datasets")
async def get_datasets():
	"""Return selectable dataset files and current source mode."""
	active = get_active_csv()
	files = _list_available_datasets()
	active_dataset = Path(active).name if active != ALL_CSVS_TOKEN else ALL_CSVS_TOKEN
	if active_dataset not in (ALL_CSVS_TOKEN, *files):
		files.insert(0, active_dataset)
	return {
		"datasets": files,
		"active_dataset": active_dataset,
		"active_csv": active,
		"source_mode": "all" if active == ALL_CSVS_TOKEN else "single",
	}


@router.post("/products/reload")
async def reload_products_data(csv_path: str | None = None, use_all: bool = True):
	target = ALL_CSVS_TOKEN if use_all else csv_path
	logger.info("Reload request received use_all=%s target=%s", use_all, target)
	loaded = reload_products(target)
	logger.info(
		"Reload completed active_csv=%s source_mode=%s loaded=%s",
		get_active_csv(),
		"all" if get_active_csv() == ALL_CSVS_TOKEN else "single",
		loaded,
	)
	return {
		"status": "ok",
		"active_csv": get_active_csv(),
		"source_mode": "all" if get_active_csv() == ALL_CSVS_TOKEN else "single",
		"loaded": loaded,
	}


@router.get("/health")
async def health_check():
	from database.connection import check_connection

	return {
		"status": "ok",
		"db_connected": check_connection(),
	}
