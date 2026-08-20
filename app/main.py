from fastapi import FastAPI  # type: ignore

from app.core.database import Base, engine

from app.models.user import User
from app.models.product import Product
from app.models.cart import Cart
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.payment import Payment

from app.routes.auth import router as auth_router
from app.routes.product import router as product_router
from app.routes.cart import router as cart_router
from app.routes.order import router as order_router
from app.routes.payment import router as payment_router


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Smart E-Commerce API",
    version="1.0.0"
)


app.include_router(auth_router)
app.include_router(product_router)
app.include_router(cart_router)
app.include_router(order_router)
app.include_router(payment_router)


@app.get("/")
def home():
    return {
        "message": "Smart E-Commerce API is running"
    }