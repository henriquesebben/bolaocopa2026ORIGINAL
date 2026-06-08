import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import bcrypt
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .database import get_db
from . import models

ENVIRONMENT = os.getenv("ENV", "development").lower()
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-troque-em-producao")
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 7

if ENVIRONMENT == "production" and SECRET_KEY == "dev-secret-troque-em-producao":
    raise RuntimeError("SECRET_KEY environment variable is required in production")

if SECRET_KEY == "dev-secret-troque-em-producao":
    import warnings
    warnings.warn(
        "Using default SECRET_KEY. Set SECRET_KEY environment variable for production.",
        UserWarning,
    )

bearer_scheme = HTTPBearer()


def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()


def verificar_senha(senha: str, hash_: str) -> bool:
    return bcrypt.checkpw(senha.encode(), hash_.encode())


def criar_token(jogador_id: int, nome: str, is_admin: bool) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(jogador_id),
        "nome": nome,
        "is_admin": is_admin,
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _decodificar_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_jogador_atual(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.Jogador:
    payload = _decodificar_token(credentials.credentials)
    jogador = db.query(models.Jogador).filter(models.Jogador.id == int(payload["sub"])).first()
    if not jogador:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jogador não encontrado")
    return jogador


def get_admin_atual(jogador: models.Jogador = Depends(get_jogador_atual)) -> models.Jogador:
    if not jogador.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito ao admin")
    return jogador


def exigir_dono_ou_admin(
    jogador_id: int,
    atual: models.Jogador = Depends(get_jogador_atual),
) -> models.Jogador:
    if not atual.is_admin and atual.id != jogador_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
    return atual
