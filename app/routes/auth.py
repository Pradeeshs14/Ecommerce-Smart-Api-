from fastapi import APIRouter, Depends, HTTPException, status  # type: ignore
from sqlalchemy.orm import Session  # type: ignore
from app.core.auth0 import get_auth0_user

from app.core.database import get_db
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    require_role
)
from app.models.user import User
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    RefreshTokenRequest
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED
)
def register_user(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):

    existing_user = (
        db.query(User)
        .filter(User.email == user_data.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    hashed_password = hash_password(
        user_data.password
    )

    new_user = User(
        name=user_data.name,
        email=user_data.email,
        password=hashed_password,
        role="customer"
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "User registered successfully",
        "user": {
            "id": new_user.id,
            "name": new_user.name,
            "email": new_user.email,
            "role": new_user.role
        }
    }


@router.post("/login")
def login_user(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    

    user = (
        db.query(User)
        .filter(User.email == user_data.email)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not verify_password(
        user_data.password,
        user.password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    access_token = create_access_token({
        "sub": str(user.id),
        "role": user.role
    })

    refresh_token = create_refresh_token({
        "sub": str(user.id)
    })

    return {
        "message": "Login successful",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh")
def refresh_access_token(
    token_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):

    payload = decode_token(
        token_data.refresh_token
    )

    if not payload:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    # Make sure this is a refresh token
    if payload.get("type") != "refresh":

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    user_id = payload.get("sub")

    if not user_id:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    user = (
        db.query(User)
        .filter(User.id == int(user_id))
        .first()
    )

    if not user:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    new_access_token = create_access_token({
        "sub": str(user.id),
        "role": user.role
    })

    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }


@router.get("/me")
def get_me(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    user = (
        db.query(User)
        .filter(User.id == int(user_id))
        .first()
    )

    if not user:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role
    }

# ============================================================
# ADMIN TEST
# ============================================================

@router.get("/admin-test")
def admin_test(
    current_user=Depends(require_role("admin"))
):
    return {
        "message": "Welcome Admin!",
        "role": current_user.get("role")
    }

    # ============================================================
# STAFF TEST
# ============================================================

@router.get("/staff-test")
def staff_test(
    current_user=Depends(require_role("staff"))
):
    return {
        "message": "Welcome Staff!",
        "role": current_user.get("role")
    }

# ============================================================
# AUTH0 SOCIAL LOGIN
# ============================================================

@router.post("/auth0/login")
def auth0_login(
    current_user=Depends(get_auth0_user),
    db: Session = Depends(get_db)
):
   

    # --------------------------------------------------------
    # Get Auth0 user information
    # --------------------------------------------------------

    auth0_user_id = current_user.get("sub")
    email = current_user.get("email")
    name = current_user.get("name")

    # Some Auth0 social connections may provide
    # a nickname instead of name.
    if not name:
        name = current_user.get("nickname")

    # Email is required because our local User model
    # uses email as the unique identifier.
    if not email:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not provided by Auth0"
        )

    # --------------------------------------------------------
    # Find existing local user
    # --------------------------------------------------------

    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    # --------------------------------------------------------
    # Create local user if not found
    # --------------------------------------------------------

    if not user:

        # Social-login users do not have a local password.
        # We store a random unusable value rather than
        # allowing a blank password.
        import secrets

        random_password = secrets.token_urlsafe(32)

        user = User(
            name=name or "Auth0 User",
            email=email,
            password=hash_password(random_password),
            role="customer"
        )

        db.add(user)
        db.commit()
        db.refresh(user)

    # --------------------------------------------------------
    # Generate our application's JWT tokens
    # --------------------------------------------------------

    access_token = create_access_token({
        "sub": str(user.id),
        "role": user.role
    })

    refresh_token = create_refresh_token({
        "sub": str(user.id)
    })

    # --------------------------------------------------------
    # Return application authentication response
    # --------------------------------------------------------

    return {
        "message": "Auth0 login successful",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role
        }
    }