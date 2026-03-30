"""
Utility condivise MRS backend.
"""
import math


def calcola_lotti(
    qty_target: int,
    tipo_produzione: str,
    multipli_taglio: int | None,
    mm_materiale: int | None,
    lunghezza_barra: int | None,
) -> tuple[int, int, int]:
    """
    Calcola (nr_lotti, pezzi_per_lotto, qty_suggerita) dato un target di produzione.

    PEZZO/SPECIALE: lotto = multipli_taglio pezzi
    BARRA/FASCI:    lotto = floor(lunghezza_barra / mm_materiale) * multipli_taglio pezzi
    """
    if qty_target <= 0:
        return (0, 0, 0)
    mult = multipli_taglio or 1
    if (
        tipo_produzione in ('BARRA', 'FASCI')
        and mm_materiale and mm_materiale > 0
        and lunghezza_barra and lunghezza_barra > 0
    ):
        pezzi_per_barra = lunghezza_barra // mm_materiale
        pezzi_per_lotto = max(1, pezzi_per_barra * mult)
    else:
        pezzi_per_lotto = max(1, mult)
    nr_lotti = math.ceil(qty_target / pezzi_per_lotto)
    return (nr_lotti, pezzi_per_lotto, nr_lotti * pezzi_per_lotto)


def codice_sort_key(codice: str) -> tuple:
    """
    Chiave di ordinamento articoli per codice dimensionale tipo NxNxN.

    Ordine:
      1. Articoli che iniziano con cifra  (es. 8X7X40, 40X22X100)
      2. Articoli che iniziano con X+cifra (es. X5X5X60)
      3. Tutto il resto (es. REGGISPINTA) — in fondo, alfabetico

    All'interno dei gruppi 1 e 2 ordina numericamente per:
      - primo numero, secondo numero, terzo numero
    """
    c = codice.upper().replace('.', 'X')

    if c and c[0].isdigit():
        group = 0
        strip = c
    elif len(c) > 1 and c[0] == 'X' and c[1].isdigit():
        group = 1
        strip = c[1:]
    else:
        return (2, 0, 0, 0, c)

    parts = strip.split('X')

    def _int(s: str) -> int:
        try:
            return int(s)
        except ValueError:
            return 9999

    n1 = _int(parts[0]) if len(parts) > 0 else 9999
    n2 = _int(parts[1]) if len(parts) > 1 else 9999
    n3 = _int(parts[2]) if len(parts) > 2 else 9999
    return (group, n1, n2, n3, c)
