"""JWT Bearer authentication dependency"""

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from app.auth.jwt_handler import verify_token
from app.config import settings


class JWTBearer(HTTPBearer):
    """JWT Bearer authentication"""
    
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
    
    async def __call__(self, request: Request) -> Optional[str]:
        """Validate JWT token from Authorization header"""
        
        # Skip auth if not required
        if not settings.require_auth:
            return None
        
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid authentication scheme"
                )
            
            if not self.verify_jwt(credentials.credentials):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid or expired token"
                )
            
            return credentials.credentials
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid authorization code"
            )
    
    def verify_jwt(self, token: str) -> bool:
        """Verify JWT token validity"""
        try:
            payload = verify_token(token)
            return payload is not None
        except Exception:
            return False


# Global JWT bearer dependency
jwt_bearer = JWTBearer()
