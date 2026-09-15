# MyShop

A complete e-commerce web application built with FastAPI, SQLAlchemy, PostgreSQL and Jinja2 templates.

## Storefront
- Modern home page
- Shop/products grid
- Product details
- Login / register
- Dark / light mode
- Cart
- Checkout
- Orders and order details
- Responsive Bootstrap navigation and footer

## Backend
- PostgreSQL database
- SQLAlchemy models and relationships
- Password hashing with bcrypt
- Product CRUD API
- User management
- Cart and order workflow
- Swagger available at `/docs`

## Run
1. Create `.env` from `.env.example`.
2. Put your PostgreSQL connection string in `DATABASE_URL`.
3. Activate your venv.
4. Install requirements: `pip install -r requirements.txt`
5. Run: `uvicorn app.main:app --reload`
6. Open `http://127.0.0.1:8000/`
