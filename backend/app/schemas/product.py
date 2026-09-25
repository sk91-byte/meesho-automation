from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, ConfigDict, Field


class ProductVariantBase(BaseModel):
    type: str
    value: str
    available: bool = True


class ProductVariantCreate(ProductVariantBase):
    pass


class ProductVariantRead(ProductVariantBase):
    variant_id: str
    product_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductFAQBase(BaseModel):
    question: str
    answer: str
    verified_by_owner: bool = True


class ProductFAQCreate(ProductFAQBase):
    pass


class ProductFAQRead(ProductFAQBase):
    faq_id: str
    product_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductBase(BaseModel):
    sku: str
    product_name: str
    description: str = ""
    actual_price: float = Field(..., description="Meesho cost price")
    selling_price: float = Field(..., description="Instagram selling price")
    currency: str = "INR"
    meesho_url: Optional[str] = None
    images: List[str] = []
    videos: List[str] = []
    category: Optional[str] = None
    brand: Optional[str] = None
    material: Optional[str] = None
    dimensions: Optional[str] = None
    weight: Optional[str] = None
    stock_information: Dict[str, Any] = {"total_stock": 100, "in_stock": True}
    delivery_information: str = "5-7 business days"
    return_policy: str = "7 days return/replacement policy"
    cod_available: bool = True
    active: bool = True


class ProductCreate(ProductBase):
    variants: List[ProductVariantCreate] = []
    faqs: List[ProductFAQCreate] = []


class ProductUpdate(BaseModel):
    product_name: Optional[str] = None
    description: Optional[str] = None
    actual_price: Optional[float] = None
    selling_price: Optional[float] = None
    meesho_url: Optional[str] = None
    images: Optional[List[str]] = None
    videos: Optional[List[str]] = None
    category: Optional[str] = None
    material: Optional[str] = None
    dimensions: Optional[str] = None
    stock_information: Optional[Dict[str, Any]] = None
    delivery_information: Optional[str] = None
    return_policy: Optional[str] = None
    cod_available: Optional[bool] = None
    active: Optional[bool] = None


class ProductRead(ProductBase):
    product_id: str
    created_at: datetime
    updated_at: datetime
    variants: List[ProductVariantRead] = []
    faqs: List[ProductFAQRead] = []

    model_config = ConfigDict(from_attributes=True)
