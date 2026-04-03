"""
SQLAlchemy engine setup.
- Local: standard connection pool (5 connections)
- Neon: NullPool (CRITICAL for serverless - explained below)
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config.settings import get_settings

settings = get_settings()


def get_engine():
	"""
	Neon (serverless) REQUIRES NullPool.

	Why: Vercel functions spin up and die with each request. A persistent
	connection pool keeps connections open between requests - but Vercel kills
	the process, leaving those connections dangling on Neon's side. Neon then
	refuses new connections ("too many clients"). NullPool opens a fresh
	connection per request and closes it immediately. Slightly slower but reliable.

	Local PostgreSQL uses the default pool - faster for development.
	"""
	if settings.environment == "production":
		from sqlalchemy.pool import NullPool

		return create_engine(
			settings.database_url,
			poolclass=NullPool,
			connect_args={"sslmode": "require"},
		)
	return create_engine(
		settings.database_url,
		pool_size=5,
		max_overflow=10,
		pool_pre_ping=True,
	)


engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
	pass


def get_db():
	"""FastAPI dependency - yields a DB session, closes it after the request."""
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()


def check_connection():
	"""Health check - returns True if DB is reachable."""
	try:
		with engine.connect() as conn:
			conn.execute(text("SELECT 1"))
		return True
	except Exception as e:
		print(f"DB connection failed: {e}")
		return False


def create_tables():
	"""Create all database tables defined in SQLAlchemy models."""
	from database.models import Base as ModelsBase

	ModelsBase.metadata.create_all(bind=engine)


if __name__ == "__main__":
	create_tables()
	print("Tables created successfully.")
