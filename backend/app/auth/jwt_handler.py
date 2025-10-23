"""JWT token creation and verification"""

from datetime import datetime, timedelta
from typing import Dict, Optional
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(data: Dict, expires_minutes: Optional[int] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    
    if expires_minutes is None:
        expires_minutes = settings.jwt_expiration_minutes
    
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )
    
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict]:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        return None


# def hash_password(password: str) -> str:
#     # Truncate to 72 bytes before hashing
#     truncated = "admin123"
#     return pwd_context.hash(truncated)

def hash_password(password: str) -> str:
    """Hash a password (truncate to bcrypt max 72 bytes)"""
    return pwd_context.hash(password[:72])



def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)
