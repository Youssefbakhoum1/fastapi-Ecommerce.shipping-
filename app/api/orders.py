import os
import stripe

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.db.database import get_db
from app.models.cart import CartItem
from app.models.order import Order, OrderItem
from app.models.user import User  # adjust import path if your User model lives elsewhere
from app.sms import send_order_sms

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

router = APIRouter(tags=["Orders"])
templates = Jinja2Templates(directory="app/templates")

# change this to your real domain when you deploy
BASE_URL = "http://127.0.0.1:8000"


def require_user(request: Request) -> int:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Please login first")
    return int(user_id)


def create_order_from_cart(db: Session, user_id: int) -> Order:
    """Creates the Order + OrderItems, decrements stock, clears the cart.
    Called only after payment is confirmed."""
    items = (
        db.query(CartItem)
        .options(joinedload(CartItem.product))
        .filter(CartItem.user_id == user_id)
        .all()
    )
    if not items:
        return None

    total = sum(item.quantity * item.product.price for item in items)
    order = Order(user_id=user_id, total_price=total, status="confirmed")
    db.add(order)
    db.flush()

    for item in items:
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.product.price,
            )
        )
        item.product.stock -= item.quantity
        db.delete(item)

    db.commit()
    db.refresh(order)
    return order


@router.get("/checkout", include_in_schema=False)
def checkout(request: Request, db: Session = Depends(get_db)):
    user_id = require_user(request)
    items = (
        db.query(CartItem)
        .options(joinedload(CartItem.product))
        .filter(CartItem.user_id == user_id)
        .all()
    )
    if not items:
        return RedirectResponse("/cart", status_code=303)

    total = sum(item.quantity * item.product.price for item in items)
    return templates.TemplateResponse(
        request=request,
        name="checkout.html",
        context={"title": "Checkout", "items": items, "total": total},
    )


@router.post("/checkout", include_in_schema=False)
def start_payment(request: Request, db: Session = Depends(get_db)):
    """Creates a Stripe Checkout Session and redirects the customer to Stripe's
    hosted payment page. The order itself is NOT created yet."""
    user_id = require_user(request)
    items = (
        db.query(CartItem)
        .options(joinedload(CartItem.product))
        .filter(CartItem.user_id == user_id)
        .all()
    )
    if not items:
        return RedirectResponse("/cart", status_code=303)

    for item in items:
        if item.quantity > item.product.stock:
            raise HTTPException(status_code=400, detail=f"Not enough stock for {item.product.name}")

    line_items = [
        {
            "price_data": {
                "currency": "usd",
                "product_data": {"name": item.product.name},
                "unit_amount": int(item.product.price * 100),  # Stripe uses cents
            },
            "quantity": item.quantity,
        }
        for item in items
    ]

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=line_items,
        mode="payment",
        success_url=f"{BASE_URL}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{BASE_URL}/checkout",
        client_reference_id=str(user_id),
    )

    return RedirectResponse(session.url, status_code=303)


@router.get("/checkout/success", include_in_schema=False)
def payment_success(request: Request, session_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Stripe redirects here after successful payment. We verify the payment
    actually succeeded before creating the order."""
    user_id = require_user(request)

    session = stripe.checkout.Session.retrieve(session_id)

    if session.payment_status != "paid":
        raise HTTPException(status_code=400, detail="Payment was not completed.")

    if session.client_reference_id != str(user_id):
        raise HTTPException(status_code=403, detail="Session does not match this user.")

    order = create_order_from_cart(db, user_id)
    if not order:
        return RedirectResponse("/cart", status_code=303)

    user = db.query(User).filter(User.id == user_id).first()
    if user and user.phone:
        background_tasks.add_task(
            send_order_sms,
            order.id,
            user.phone,
            order.total_price,
        )

    return RedirectResponse(f"/orders/{order.id}", status_code=303)


@router.get("/orders", include_in_schema=False)
def orders_page(request: Request, db: Session = Depends(get_db)):
    user_id = require_user(request)
    orders = (
        db.query(Order)
        .filter(Order.user_id == user_id)
        .order_by(Order.id.desc())
        .all()
    )
    return templates.TemplateResponse(
        request=request,
        name="orders.html",
        context={"title": "My Orders", "orders": orders},
    )


@router.get("/orders/{order_id}", include_in_schema=False)
def order_detail(request: Request, order_id: int, db: Session = Depends(get_db)):
    user_id = require_user(request)
    order = (
        db.query(Order)
        .options(joinedload(Order.items).joinedload(OrderItem.product))
        .filter(Order.id == order_id, Order.user_id == user_id)
        .first()
    )
    if not order:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={"title": "Order not found", "message": "This order does not exist."},
            status_code=404,
        )

    return templates.TemplateResponse(
        request=request,
        name="order_detail.html",
        context={"title": f"Order #{order.id}", "order": order},
    )