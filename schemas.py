"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List

# Documentation app schemas

class Section(BaseModel):
    """
    Documentation sections (e.g., "Introducción", "Gestión de Procesos")
    Collection name: "section"
    """
    title: str = Field(..., description="Section title")
    description: Optional[str] = Field(None, description="Short description of the section")
    order: Optional[int] = Field(None, ge=0, description="Optional sort order")

class Doc(BaseModel):
    """
    Individual documentation entries inside a section
    Collection name: "doc"
    """
    section_id: str = Field(..., description="ID of the parent section")
    title: str = Field(..., description="Document title")
    content: str = Field("", description="Markdown content of the document")
    tags: Optional[List[str]] = Field(default=None, description="Tags for filtering/search")
    cover_image: Optional[str] = Field(default=None, description="Optional cover image URL")

# Example schemas kept for reference
class User(BaseModel):
    name: str
    email: str
    address: str
    age: Optional[int] = None
    is_active: bool = True

class Product(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: str
    in_stock: bool = True
