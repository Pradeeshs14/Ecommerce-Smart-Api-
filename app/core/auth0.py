# ============================================================
# AUTH0 CONFIGURATION
# ============================================================

import os
import requests  # type: ignore

import jwt  # type: ignore
from dotenv import load_dotenv  # type: ignore
from fastapi import Depends, HTTPException, status  # type: ignore
from fastapi.security import ( # type: ignore
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from jwt import PyJWKClient  # type: ignore


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# AUTH0 SETTINGS
# ============================================================

AUTH0_DOMAIN = os.getenv(
    "AUTH0_DOMAIN",
    "dev-vsr4r7clluu1xuxk.us.auth0.com"
)

AUTH0_AUDIENCE = os.getenv(
    "AUTH0_AUDIENCE",
    "https://ecommerce-fastapi-api"
)

AUTH0_ISSUER = os.getenv(
    "AUTH0_ISSUER",
    f"https://{AUTH0_DOMAIN}/"
)

AUTH0_USERINFO_URL = (
    f"https://{AUTH0_DOMAIN}/userinfo"
)


# ============================================================
# AUTHENTICATION SCHEME
# ============================================================

bearer_scheme = HTTPBearer()


# ============================================================
# AUTH0 JWKS CLIENT
# ============================================================

jwks_client = PyJWKClient(
    f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
)


# ============================================================
# AUTH0 TOKEN VALIDATION
# ============================================================

def get_auth0_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        bearer_scheme
    )
):
    """
    Validate an Auth0 access token.

    If email/name are not present in the access token,
    retrieve them from Auth0 /userinfo endpoint.
    """

    token = credentials.credentials

    try:

        # ----------------------------------------------------
        # Get Auth0 public signing key
        # ----------------------------------------------------

        signing_key = jwks_client.get_signing_key_from_jwt(
            token
        )

        # ----------------------------------------------------
        # Validate and decode access token
        # ----------------------------------------------------

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=AUTH0_AUDIENCE,
            issuer=AUTH0_ISSUER
        )

        # ----------------------------------------------------
        # Get user information from Auth0 /userinfo
        # ----------------------------------------------------

        if not payload.get("email"):

            response = requests.get(
                AUTH0_USERINFO_URL,
                headers={
                    "Authorization": f"Bearer {token}"
                },
                timeout=10
            )

            if response.status_code != 200:

                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unable to retrieve Auth0 user information"
                )

            user_info = response.json()

            # Add Auth0 user information to payload
            payload.update(user_info)

        return payload

    except jwt.ExpiredSignatureError:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Auth0 token has expired"
        )

    except jwt.InvalidAudienceError:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Auth0 audience"
        )

    except jwt.InvalidIssuerError:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Auth0 issuer"
        )

    except jwt.InvalidTokenError:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Auth0 access token"
        )

    except HTTPException:

        raise

    except Exception:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to validate Auth0 token"
        )


# ============================================================
# AUTH0 PERMISSION CHECK
# ============================================================

def require_permission(
    required_permission: str
):

    def permission_checker(
        user=Depends(get_auth0_user)
    ):

        permissions = user.get(
            "permissions",
            []
        )

        if required_permission not in permissions:

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )

        return user

    return permission_checker