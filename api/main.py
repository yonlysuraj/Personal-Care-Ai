"""
FastAPI app entry point.

IMPORTANT for serverless deployment:
  - The handler variable at the bottom wraps the app with Mangum.
	- Mangum translates serverless requests into ASGI.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from api.routes import chat, products
from config.logging_setup import get_logger, silence_console_logging
from config.settings import get_settings
from database.connection import engine
from database.models import Base

settings = get_settings()
silence_console_logging(["uvicorn", "uvicorn.error", "uvicorn.access"])
logger = get_logger("api.main", app_name="api")

app = FastAPI(
	title="Personal Care AI Chatbot API",
	version="1.0.0",
	docs_url="/api/docs",
	redoc_url=None,
)

app.add_middleware(
	CORSMiddleware,
	allow_origins=settings.origins_list,
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(products.router)


@app.on_event("startup")
async def startup():
	"""Create DB tables on startup if they do not exist."""
	Base.metadata.create_all(bind=engine)
	logger.info("Database tables ready.")


handler = Mangum(app, lifespan="off")
