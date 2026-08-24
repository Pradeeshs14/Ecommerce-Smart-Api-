import os
from dotenv import load_dotenv  # type: ignore

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "Smart E-Commerce API")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./ecommerce.db"
)

# ============================================================
# JWT CONFIGURATION
# ============================================================

JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "change-this-secret-key"
)

JWT_ALGORITHM = os.getenv(
    "JWT_ALGORITHM",
    "HS256"
)

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "30"
    )
)

REFRESH_TOKEN_EXPIRE_DAYS = int(
    os.getenv(
        "REFRESH_TOKEN_EXPIRE_DAYS",
        "7"
    )
)

# ============================================================
# STRIPE CONFIGURATION
# ============================================================

STRIPE_SECRET_KEY = os.getenv(
    "STRIPE_SECRET_KEY",
    ""
)

STRIPE_PUBLISHABLE_KEY = os.getenv(
    "STRIPE_PUBLISHABLE_KEY",
    ""
)
STRIPE_WEBHOOK_SECRET = os.getenv(
    "STRIPE_WEBHOOK_SECRET",
    ""
)

# ============================================================
# EMAIL CONFIGURATION
# ============================================================

MAIL_USERNAME = os.getenv(
    "MAIL_USERNAME",
    ""
)

MAIL_PASSWORD = os.getenv(
    "MAIL_PASSWORD",
    ""
)

MAIL_FROM = os.getenv(
    "MAIL_FROM",
    ""
)

MAIL_PORT = int(
    os.getenv(
        "MAIL_PORT",
        "587"
    )
)

MAIL_SERVER = os.getenv(
    "MAIL_SERVER",
    "smtp.gmail.com"
)

MAIL_FROM_NAME = os.getenv(
    "MAIL_FROM_NAME",
    "Smart E-Commerce"
)

MAIL_STARTTLS = os.getenv(
    "MAIL_STARTTLS",
    "True"
).lower() == "true"

MAIL_SSL_TLS = os.getenv(
    "MAIL_SSL_TLS",
    "False"
).lower() == "true"

MAIL_USE_CREDENTIALS = os.getenv(
    "MAIL_USE_CREDENTIALS",
    "True"
).lower() == "true"

MAIL_VALIDATE_CERTS = os.getenv(
    "MAIL_VALIDATE_CERTS",
    "True"
).lower() == "true"