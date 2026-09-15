from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.db.database import get_db
from app.models.cart import CartItem
from app.models.product import Product

router = APIRouter(tags=["Cart"])
templates = Jinja2Templates(directory="app/templates")


def current_user_id(request: Request) -> int:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Please login first")
    return int(user_id)


def cart_items_for_user(db: Session, user_id: int):
    return (
        db.query(CartItem)
        .options(joinedload(CartItem.product))
        .filter(CartItem.user_id == user_id)
        .order_by(CartItem.id.desc())
        .all()
    )


@router.get("/cart", include_in_schema=False)
def cart_page(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/login?next=/cart", status_code=303)

    items = cart_items_for_user(db, int(user_id))
    total = sum(item.quantity * item.product.price for item in items)

    return templates.TemplateResponse(
        request=request,
        name="cart.html",
        context={"title": "Your Cart", "items": items, "total": total},
    )


@router.post("/cart/add/{product_id}", include_in_schema=False)
def add_to_cart(
    request: Request,
    product_id: int,
    quantity: int = 1,
    db: Session = Depends(get_db),
):
    user_id = current_user_id(request)
    quantity = max(1, int(quantity))

    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.stock <= 0:
        raise HTTPException(status_code=400, detail="Product is out of stock")

    item = (
        db.query(CartItem)
        .filter(CartItem.user_id == user_id, CartItem.product_id == product_id)
        .first()
    )

    if item:
        item.quantity = min(item.quantity + quantity, product.stock)
    else:
        item = CartItem(
            user_id=user_id,
            product_id=product_id,
            quantity=min(quantity, product.stock),
        )
        db.add(item)

    db.commit()
    return RedirectResponse("/cart", status_code=303)


@router.post("/cart/update/{item_id}", include_in_schema=False)
def update_cart_item(
    request: Request,
    item_id: int,
    quantity: int = Form(...),
    db: Session = Depends(get_db),
):
    user_id = current_user_id(request)
    item = (
        db.query(CartItem)
        .filter(CartItem.id == item_id, CartItem.user_id == user_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    if quantity <= 0:
        db.delete(item)
    else:
        item.quantity = min(quantity, item.product.stock)

    db.commit()
    return RedirectResponse("/cart", status_code=303)


@router.post("/cart/remove/{item_id}", include_in_schema=False)
def remove_cart_item(request: Request, item_id: int, db: Session = Depends(get_db)):
    user_id = current_user_id(request)
    item = (
        db.query(CartItem)
        .filter(CartItem.id == item_id, CartItem.user_id == user_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    db.delete(item)
    db.commit()
    return RedirectResponse("/cart", status_code=303)


@router.get("/api/cart/count")
def cart_count(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return {"count": 0}

    items = db.query(CartItem).filter(CartItem.user_id == int(user_id)).all()
    return {"count": sum(item.quantity for item in items)}