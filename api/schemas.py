from datetime import datetime

from pydantic import BaseModel


class ChatRequest(BaseModel):
	message: str
	session_id: str


class MessageOut(BaseModel):
	role: str
	content: str
	is_handoff: bool
	created_at: datetime

	class Config:
		from_attributes = True


class ChatResponse(BaseModel):
	reply: str
	session_id: str
	is_handoff: bool
	intent: str | None = None


class ProductOut(BaseModel):
	product_id: str
	brand: str
	product_name: str
	discounted_price: str
	rating: float | None
	product_url: str

	class Config:
		from_attributes = True
