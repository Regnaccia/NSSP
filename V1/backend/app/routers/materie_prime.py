"""
Router materie prime — configurazione lunghezze barre.

GET   /api/materie-prime          — lista materie prime
PATCH /api/materie-prime/{id}     — aggiorna lunghezza_mm (unico campo MRS-owned)
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.materia_prima import MateriaPrima
from app.schemas.produzione import MateriaPrimaResponse, MateriaPrimaPatchRequest
from app.utils import codice_sort_key

router = APIRouter(
    prefix="/api/materie-prime",
    tags=["materie_prime"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[MateriaPrimaResponse])
def list_materie_prime(
    q: Optional[str] = Query(None),
    solo_con_lunghezza: Optional[bool] = Query(None),
    session: Session = Depends(get_db),
):
    qs = session.query(MateriaPrima)
    if q:
        qs = qs.filter(MateriaPrima.codice_upper.like(f"{q.upper()}%"))
    if solo_con_lunghezza is True:
        qs = qs.filter(MateriaPrima.lunghezza_mm.isnot(None))
    elif solo_con_lunghezza is False:
        qs = qs.filter(MateriaPrima.lunghezza_mm.is_(None))
    result = [MateriaPrimaResponse.model_validate(m) for m in qs.all()]
    result.sort(key=lambda r: codice_sort_key(r.codice))
    return result


@router.patch("/{materia_prima_id}", response_model=MateriaPrimaResponse)
def patch_materia_prima(
    materia_prima_id: str,
    body: MateriaPrimaPatchRequest,
    session: Session = Depends(get_db),
):
    mp = session.get(MateriaPrima, materia_prima_id)
    if not mp:
        raise HTTPException(status_code=404, detail="Materia prima non trovata")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(mp, field, value)
    session.commit()
    session.refresh(mp)
    return MateriaPrimaResponse.model_validate(mp)
