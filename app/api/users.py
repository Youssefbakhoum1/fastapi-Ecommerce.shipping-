from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.database import get_db
from app.models.user import User

router = APIRouter(tags=["Users"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/users", include_in_schema=False)
def users_page(request: Request, db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.id.desc()).all()
    return templates.TemplateResponse(request=request, name="users.html", context={"title": "Users", "users": users})


@router.get("/users/add", include_in_schema=False)
def add_user_page(request: Request):
    return templates.TemplateResponse(request=request, name="add_user.html", context={"title": "Add User"})


@router.post("/users/add", include_in_schema=False)
def add_user(request: Request, username: str = Form(...), email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    existing = db.query(User).filter(or_(User.email == email, User.username == username)).first()
    if existing:
        return templates.TemplateResponse(request=request, name="add_user.html", context={"title": "Add User", "error": "Email or username already exists."}, status_code=400)
    user = User(username=username, email=email, password=hash_password(password))
    db.add(user)
    db.commit()
    return RedirectResponse("/users", status_code=303)
