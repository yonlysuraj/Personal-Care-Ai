"""
Centralized configuration using pydantic-settings.
Automatically reads from .env file.
Selects the correct database URL based on ENVIRONMENT variable.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
	# LLM
	groq_api_key: str

	# Databases
	local_database_url: str = ""
	neon_database_url: str = ""
	environment: str = "development"

	# App
	support_phone: str = "+91-1800-266-1234"
	allowed_origins: str = "http://localhost:8501"

	@property
	def database_url(self) -> str:
		"""
		Returns the correct DB URL based on environment.
		In production (Vercel), ENVIRONMENT is set to "production"
		via Vercel's environment variable dashboard.
		"""
		if self.environment == "production":
			if not self.neon_database_url:
				raise ValueError("NEON_DATABASE_URL must be set in production")
			return self.neon_database_url
		return self.local_database_url

	@property
	def origins_list(self) -> list[str]:
		return [origin.strip() for origin in self.allowed_origins.split(",")]

	class Config:
		env_file = ".env"
		env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
	"""
	Cached settings instance.
	lru_cache means .env is only read once per process - efficient.
	"""
	return Settings()
