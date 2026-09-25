from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_current_user, require_roles
from app.models.user import User, RoleEnum
from app.models.product import Product, ProductVariant, ProductFAQ
from app.schemas.product import (
    ProductRead,
    ProductCreate,
    ProductUpdate,
    ProductVariantRead,
    ProductVariantCreate,
    ProductFAQRead,
    ProductFAQCreate
)

router = APIRouter(prefix="/products", tags=["Product Management"])


@router.get("/", response_model=List[ProductRead])
async def list_products(
    active_only: bool = Query(True, description="Filter active products only"),
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search term in product name or SKU"),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Product).options(
        selectinload(Product.variants),
        selectinload(Product.faqs)
    )
    if active_only:
        stmt = stmt.where(Product.active == True)
    if category:
        stmt = stmt.where(Product.category == category)
    if search:
        stmt = stmt.where(
            (Product.product_name.ilike(f"%{search}%")) | (Product.sku.ilike(f"%{search}%"))
        )
    
    stmt = stmt.order_by(Product.created_at.desc())
    result = await db.execute(stmt)
    products = result.scalars().all()
    return products


@router.post("/", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_in: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([RoleEnum.OWNER, RoleEnum.ADMIN]))
):
    # Check duplicate SKU
    sku_result = await db.execute(select(Product).where(Product.sku == product_in.sku))
    if sku_result.scalars().first():
        raise HTTPException(
            status_code=400,
            detail=f"Product with SKU '{product_in.sku}' already exists"
        )
    
    product_dict = product_in.model_dump(exclude={"variants", "faqs"})
    product = Product(**product_dict)
    
    for v_in in product_in.variants:
        variant = ProductVariant(**v_in.model_dump())
        product.variants.append(variant)
        
    for f_in in product_in.faqs:
        faq = ProductFAQ(**f_in.model_dump())
        product.faqs.append(faq)

    db.add(product)
    await db.commit()
    
    # Reload with relationships
    stmt = select(Product).options(
        selectinload(Product.variants),
        selectinload(Product.faqs)
    ).where(Product.product_id == product.product_id)
    refreshed_result = await db.execute(stmt)
    return refreshed_result.scalars().first()


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: str,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Product).options(
        selectinload(Product.variants),
        selectinload(Product.faqs)
    ).where(Product.product_id == product_id)
    result = await db.execute(stmt)
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: str,
    product_in: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([RoleEnum.OWNER, RoleEnum.ADMIN]))
):
    stmt = select(Product).options(
        selectinload(Product.variants),
        selectinload(Product.faqs)
    ).where(Product.product_id == product_id)
    result = await db.execute(stmt)
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = product_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_product(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([RoleEnum.OWNER, RoleEnum.ADMIN]))
):
    stmt = select(Product).where(Product.product_id == product_id)
    result = await db.execute(stmt)
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product.active = False
    await db.commit()
    return None


# Variant endpoints
@router.post("/{product_id}/variants", response_model=ProductVariantRead, status_code=status.HTTP_201_CREATED)
async def add_product_variant(
    product_id: str,
    variant_in: ProductVariantCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([RoleEnum.OWNER, RoleEnum.ADMIN]))
):
    stmt = select(Product).where(Product.product_id == product_id)
    result = await db.execute(stmt)
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    variant = ProductVariant(product_id=product_id, **variant_in.model_dump())
    db.add(variant)
    await db.commit()
    await db.refresh(variant)
    return variant


@router.put("/{product_id}/variants/{variant_id}", response_model=ProductVariantRead)
async def update_product_variant(
    product_id: str,
    variant_id: str,
    available: bool = Query(..., description="Variant availability flag"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([RoleEnum.OWNER, RoleEnum.ADMIN]))
):
    stmt = select(ProductVariant).where(
        ProductVariant.variant_id == variant_id,
        ProductVariant.product_id == product_id
    )
    result = await db.execute(stmt)
    variant = result.scalars().first()
    if not variant:
        raise HTTPException(status_code=404, detail="Product variant not found")

    variant.available = available
    await db.commit()
    await db.refresh(variant)
    return variant


# FAQ endpoints
@router.post("/{product_id}/faqs", response_model=ProductFAQRead, status_code=status.HTTP_201_CREATED)
async def add_product_faq(
    product_id: str,
    faq_in: ProductFAQCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([RoleEnum.OWNER, RoleEnum.ADMIN]))
):
    stmt = select(Product).where(Product.product_id == product_id)
    result = await db.execute(stmt)
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    faq = ProductFAQ(product_id=product_id, **faq_in.model_dump())
    db.add(faq)
    await db.commit()
    await db.refresh(faq)
    return faq
