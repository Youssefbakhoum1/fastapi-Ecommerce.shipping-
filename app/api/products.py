from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate

router = APIRouter(tags=["Products"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/products", include_in_schema=False)
def products_page(
    request: Request,
    db: Session = Depends(get_db),
    search: Optional[str] = None,
    category: Optional[str] = None,
    min_price: Optional[str] = None,
    max_price: Optional[str] = None,
    in_stock: Optional[bool] = None,
    sort: Optional[str] = "newest",
):
    # empty strings from unfilled form fields get sent as "" not omitted,
    # so we convert manually instead of letting FastAPI coerce straight to float
    min_price = float(min_price) if min_price not in (None, "") else None
    max_price = float(max_price) if max_price not in (None, "") else None

    query = db.query(Product)

    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))

    if category and category.lower() != "all":
        query = query.filter(Product.category == category)

    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)

    if in_stock:
        query = query.filter(Product.stock > 0)

    sort_map = {
        "price_asc": asc(Product.price),
        "price_desc": desc(Product.price),
        "newest": desc(Product.id),
        "oldest": asc(Product.id),
    }
    query = query.order_by(sort_map.get(sort, desc(Product.id)))

    products = query.all()

    categories = [row[0] for row in db.query(Product.category).distinct() if row[0]]

    return templates.TemplateResponse(
        request=request,
        name="products.html",
        context={
            "title": "Products",
            "products": products,
            "categories": categories,
            "filters": {
                "search": search or "",
                "category": category or "all",
                "min_price": min_price,
                "max_price": max_price,
                "in_stock": bool(in_stock),
                "sort": sort,
            },
        },
    )


@router.get("/products/{product_id}", include_in_schema=False)
def product_page(request: Request, product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        return templates.TemplateResponse(request=request, name="error.html", context={"title": "Product not found", "message": "This product does not exist."}, status_code=404)
    return templates.TemplateResponse(request=request, name="product_detail.html", context={"title": product.name, "product": product})


@router.get("/api/products", response_model=list[ProductResponse])
def get_products(db: Session = Depends(get_db)):
    return db.query(Product).order_by(Product.id.desc()).all()


@router.post("/api/products", response_model=ProductResponse, status_code=201)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("/api/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/api/products/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, payload: ProductUpdate, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/api/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return {"message": "Product deleted successfully"}