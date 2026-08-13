from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status  # type: ignore
from fastapi.security import (  # type: ignore
    HTTPAuthorizationCredentials,
    HTTPBearer
)

from jose import JWTError, jwt  # type: ignore
from pwdlib import PasswordHash  # type: ignore

from app.core.config import (
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS
)


# ============================================================
# SECURITY CONFIGURATION
# ============================================================

bearer_scheme = HTTPBearer()

password_hash = PasswordHash.recommended()


# ============================================================
# PASSWORD HASHING
# ============================================================

def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    return password_hash.verify(
        plain_password,
        hashed_password
    )


# ============================================================
# ACCESS TOKEN
# ============================================================

def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None
) -> str:

    to_encode = data.copy()

    if expires_delta:
        expire = (
            datetime.now(timezone.utc)
            + expires_delta
        )
    else:
        expire = (
            datetime.now(timezone.utc)
            + timedelta(
                minutes=ACCESS_TOKEN_EXPIRE_MINUTES
            )
        )

    to_encode.update({
        "exp": expire,
        "type": "access"
    })

    return jwt.encode(
        to_encode,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM
    )


# ============================================================
# REFRESH TOKEN
# ============================================================

def create_refresh_token(data: dict) -> str:

    to_encode = data.copy()

    expire = (
        datetime.now(timezone.utc)
        + timedelta(
            days=REFRESH_TOKEN_EXPIRE_DAYS
        )
    )

    to_encode.update({
        "exp": expire,
        "type": "refresh"
    })

    return jwt.encode(
        to_encode,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM
    )


# ============================================================
# DECODE TOKEN
# ============================================================

def decode_token(token: str):

    try:

        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )

        return payload

    except JWTError:
        return None


# ============================================================
# CURRENT USER
# ============================================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        bearer_scheme
    )
):

    token = credentials.credentials

    payload = decode_token(token)

    if not payload:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token"
        )

    # Make sure this is an ACCESS token
    if payload.get("type") != "access":

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token required"
        )

    user_id = payload.get("sub")

    if not user_id:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token"
        )

    return user_id


# ============================================================
# ROLE-BASED ACCESS CONTROL
# ============================================================

def require_role(required_role: str):

    def role_checker(
        credentials: HTTPAuthorizationCredentials = Depends(
            bearer_scheme
        )
    ):

        token = credentials.credentials

        payload = decode_token(token)

        if not payload:

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired access token"
            )

        # Only access tokens can access protected routes
        if payload.get("type") != "access":

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Access token required"
            )

        user_role = payload.get("role")

        if not user_role:

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Role not found"
            )

        if user_role != required_role:

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )

        return payload

    return role_checker