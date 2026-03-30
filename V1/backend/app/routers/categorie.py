"""
Router categorie articolo — mapping categoria EasyJob → famiglia MRS.

GET   /api/categorie                 — lista con conteggi articoli per categoria
PATCH /api/categorie/{codice}        — assegna famiglia ('standard'|'speciali'|'barre'|null)
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.deps import get_current_user

router = APIRouter(
    prefix="/api/categorie",
    tags=["categorie"],
    dependencies=[Depends(get_current_user)],
)

FAMIGLIE_VALIDE = {'standard', 'speciali', 'barre'}


class CategoriaResponse(BaseModel):
    codice: str
    descrizione: Optional[str]
    famiglia: Optional[str]
    nr_articoli: int


class CategoriaPatchRequest(BaseModel):
    famiglia: Optional[str] = None   # None = escludi dai lanci


@router.get("", response_model=list[CategoriaResponse])
def list_categorie(session: Session = Depends(get_db)):
    """Lista categorie con conteggio articoli e famiglia assegnata."""
    rows = session.execute(text("""
        SELECT ca.codice, ca.descrizione, ca.famiglia,
               COUNT(a.id) AS nr_articoli
        FROM categorie_articolo ca
        LEFT JOIN articoli a ON a.categoria = ca.codice
        GROUP BY ca.codice, ca.descrizione, ca.famiglia
        ORDER BY ca.codice
    """)).mappings().all()
    return [CategoriaResponse(**dict(r)) for r in rows]


@router.patch("/{codice}", response_model=CategoriaResponse)
def patch_categoria(
    codice: str,
    body: CategoriaPatchRequest,
    session: Session = Depends(get_db),
):
    """Assegna o rimuove la famiglia di una categoria."""
    if body.famiglia is not None and body.famiglia not in FAMIGLIE_VALIDE:
        raise HTTPException(
            status_code=422,
            detail=f"famiglia deve essere uno di: {', '.join(sorted(FAMIGLIE_VALIDE))} oppure null",
        )
    existing = session.execute(
        text("SELECT codice FROM categorie_articolo WHERE codice = :c"),
        {"c": codice},
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Categoria non trovata")

    session.execute(
        text("UPDATE categorie_articolo SET famiglia = :f WHERE codice = :c"),
        {"f": body.famiglia, "c": codice},
    )
    session.commit()

    row = session.execute(text("""
        SELECT ca.codice, ca.descrizione, ca.famiglia,
               COUNT(a.id) AS nr_articoli
        FROM categorie_articolo ca
        LEFT JOIN articoli a ON a.categoria = ca.codice
        WHERE ca.codice = :c
        GROUP BY ca.codice, ca.descrizione, ca.famiglia
    """), {"c": codice}).mappings().fetchone()
    return CategoriaResponse(**dict(row))
