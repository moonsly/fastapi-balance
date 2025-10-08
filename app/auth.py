import base64
from typing import Optional
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.crud import user_crud
from models.models import User

security = HTTPBasic()


async def get_current_user(credentials: HTTPBasicCredentials = Depends(security)) -> User:
    """
    Получает текущего аутентифицированного пользователя через Basic Auth
    """
    user = await user_crud.authenticate_user(credentials.username, credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверные учетные данные",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return user


def decode_basic_auth(authorization: str) -> tuple[str, str]:
    """
    Декодирует Basic Auth заголовок
    """
    try:
        if not authorization.startswith("Basic "):
            raise ValueError("Invalid authorization header")
        
        encoded_credentials = authorization.split(" ", 1)[1]
        decoded_credentials = base64.b64decode(encoded_credentials).decode("utf-8")
        username, password = decoded_credentials.split(":", 1)
        
        return username, password
    except (ValueError, IndexError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный формат авторизации",
            headers={"WWW-Authenticate": "Basic"},
        ) from e


async def authenticate_user_by_header(authorization: Optional[str]) -> User:
    """
    Аутентифицирует пользователя по заголовку Authorization
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    username, password = decode_basic_auth(authorization)
    user = await user_crud.authenticate_user(username, password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверные учетные данные",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return user
