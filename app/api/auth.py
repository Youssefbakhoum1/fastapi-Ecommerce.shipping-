from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.db.database import get_db
from app.models.user import User

router = APIRouter(tags=["Authentication"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", include_in_schema=False)
def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={"title": "Login"})


@router.post("/login", include_in_schema=False)
def login_user(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return templates.TemplateResponse(request=request, name="login.html", context={"title": "Login", "error": "Email does not exist. Please register first."}, status_code=400)
    if not verify_password(password, user.password):
        return templates.TemplateResponse(request=request, name="login.html", context={"title": "Login", "error": "Incorrect password. Please try again."}, status_code=400)
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    return RedirectResponse("/", status_code=303)


@router.get("/register", include_in_schema=False)
def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="register.html", context={"title": "Register"})


@router.post("/register", include_in_schema=False)
def register_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    phone: str = Form(None),
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(or_(User.email == email, User.username == username)).first()
    if existing:
        message = "Email or username is already registered."
        return templates.TemplateResponse(request=request, name="register.html", context={"title": "Register", "error": message}, status_code=400)

    # basic E.164 check: must start with + and have 8-15 digits after it (required for SMS to work)
    if phone:
        phone = phone.strip()
        digits_only = phone[1:] if phone.startswith("+") else phone
        if not phone.startswith("+") or not digits_only.isdigit() or not (8 <= len(digits_only) <= 15):
            message = "Phone number must be in international format, e.g. +15551234567."
            return templates.TemplateResponse(request=request, name="register.html", context={"title": "Register", "error": message}, status_code=400)

    user = User(username=username, email=email, password=hash_password(password), phone=phone)
    db.add(user)
    db.commit()
    return RedirectResponse("/login", status_code=303)


@router.get("/logout", include_in_schema=False)
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)