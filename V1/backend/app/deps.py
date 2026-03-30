"""
FastAPI dependencies per autenticazione JWT (DL-ARCH-016).

Uso negli endpoint:
    @router.get("/...")
    def endpoint(user: dict = Depends(get_current_user)):
        ...

    @router.post("/...")  # solo admin
    def admin_endpoint(user: dict = Depends(require_admin)):
        ...

Terminali kiosk (reparto, magazzino): non usano queste dependency in MVP.
Il contesto kiosk è configurato via KIOSK_CONTEXT in env.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.services.auth import AuthError, decode_token

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    """
    Estrae e valida il JWT dal header Authorization: Bearer <token>.
    Ritorna il payload del token: {sub, username, ruolo, exp}.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token di autenticazione mancante",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return decode_token(credentials.credentials)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Richiede ruolo 'admin'."""
    if user.get("ruolo") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accesso riservato agli amministratori",
        )
    return user


def require_ruolo(*ruoli: str):
    """
    Factory per dependency che richiede uno specifico ruolo (o admin).

    Uso:
        @router.get("/...", dependencies=[Depends(require_ruolo("produzione", "admin"))])
    """
    def _check(user: dict = Depends(get_current_user)) -> dict:
        if user.get("ruolo") not in ruoli and user.get("ruolo") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Accesso riservato ai ruoli: {', '.join(ruoli)}",
            )
        return user
    return _check
