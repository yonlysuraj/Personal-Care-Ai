"""
SQLAlchemy ORM models.
Two tables: Conversation (session container) + Message (each chat turn).
"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database.connection import Base


class Conversation(Base):
	__tablename__ = "conversations"

	id = Column(Integer, primary_key=True, index=True)
	session_id = Column(String(64), unique=True, index=True, nullable=False)
	created_at = Column(DateTime, default=datetime.utcnow)
	updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

	messages = relationship(
		"Message",
		back_populates="conversation",
		cascade="all, delete-orphan",
		order_by="Message.id",
	)


class Message(Base):
	__tablename__ = "messages"

	id = Column(Integer, primary_key=True, index=True)
	conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
	role = Column(String(20), nullable=False)
	content = Column(Text, nullable=False)
	is_handoff = Column(Boolean, default=False)
	intent = Column(String(50), nullable=True)
	created_at = Column(DateTime, default=datetime.utcnow)

	conversation = relationship("Conversation", back_populates="messages")


class Product(Base):
	__tablename__ = "products"

	id = Column(Integer, primary_key=True, index=True)
	product_id = Column(String(30), unique=True, index=True)
	brand = Column(String(100))
	product_name = Column(String(300))
	shade = Column(String(100))
	discounted_price = Column(String(20))
	price_numeric = Column(Float)
	original_price = Column(String(20))
	discount_percentage = Column(String(20))
	rating = Column(Float)
	reviews_count = Column(Integer)
	product_url = Column(Text)
	image_url = Column(Text)
	breadcrumbs = Column(String(200), default="Home/Personal Care/Lipstick")
	in_stock = Column(Boolean, default=True)
	created_at = Column(DateTime, default=datetime.utcnow)
