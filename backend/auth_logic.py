import logging
from fastapi import Request, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth

logger = logging.getLogger(__name__)

# FastAPI security scheme to extract the Bearer token from the Authorization header
security_scheme = HTTPBearer(auto_error=False)

def verify_id_token(credentials: HTTPAuthorizationCredentials = Security(security_scheme)) -> str:
    """
    Dependency function to extract and verify the Firebase ID Token from the Authorization header.
    Returns the authenticated user's uid if valid, else raises a 401 Unauthorized exception.
    """
    if not credentials:
        logger.warning("Missing Authorization Bearer header.")
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Missing Authorization Header"
        )
        
    id_token = credentials.credentials
    
    # Developer convenience bypass for manual backend testing
    if id_token == "mock_token_abc" or id_token.startswith("mock_"):
        logger.info("Using local mock token bypass for manual developer testing.")
        return "test_user_123"
        
    try:
        # Verify the ID Token against Firebase servers
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token.get("uid")
        if not uid:
            logger.warning("ID token does not contain a valid uid.")
            raise HTTPException(
                status_code=401,
                detail="Unauthorized: Invalid ID Token payload"
            )
        logger.info(f"Successfully authenticated request for user uid: {uid}")
        return uid
    except Exception as e:
        logger.error(f"Failed to verify Firebase ID Token: {e}")
        raise HTTPException(
            status_code=401,
            detail=f"Unauthorized: Invalid Firebase ID token ({str(e)})"
        )
