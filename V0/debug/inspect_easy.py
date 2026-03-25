"""
Ispezione schema tabelle Easy — eseguire dalla root V0/:
    python -m debug.inspect_easy

Aggiungere i nomi delle tabelle da ispezionare in TABLES_TO_INSPECT.
I risultati vengono salvati in debug/easy_schema/<tablename>.json
"""

import json
from pathlib import Path
from datetime import datetime
from sqlalchemy import text
from sync.easy.connector import get_easy_engine

# ── Configurazione ────────────────────────────────────────────────────────────

TABLES_TO_INSPECT = [
    # "ANACLI", # anagrafica clienti
    # "V_TORDCLI", #righe ordini clienti attivi
    # "POT_DESTDIV", # destinazioni clienti
    # "MAG_REALE", #movimenti carico scarico magazzino
    # "DPRE_PROD", #produzioni attive 
    "ANAART", # anagrafica articoli 
]

SAMPLE_ROWS = 3  # quante righe di esempio mostrare / salvare per tabella

OUTPUT_DIR = Path(__file__).parent / "easy_schema"

# ─────────────────────────────────────────────────────────────────────────────


def inspect_table(engine, table_name: str) -> dict:
    print(f"\n{'─' * 60}")
    print(f"  Tabella: {table_name}")
    print(f"{'─' * 60}")

    result = {
        "table": table_name,
        "inspected_at": datetime.now().isoformat(),
        "columns": [],
        "primary_key": [],
        "sample_rows": [],
    }

    with engine.connect() as conn:
        # Colonne via INFORMATION_SCHEMA (evita bug driver ODBC legacy con NUMERIC(38,0))
        try:
            rows = conn.execute(text("""
                SELECT
                    COLUMN_NAME,
                    DATA_TYPE,
                    CHARACTER_MAXIMUM_LENGTH,
                    NUMERIC_PRECISION,
                    NUMERIC_SCALE,
                    IS_NULLABLE,
                    COLUMN_DEFAULT
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = :table
                ORDER BY ORDINAL_POSITION
            """), {"table": table_name}).fetchall()

            if not rows:
                print("  Tabella non trovata o senza colonne.")
                result["error"] = "table not found"
                return result

            print(f"  Colonne ({len(rows)}):")
            for r in rows:
                type_str = r[1]
                if r[2]:
                    type_str += f"({r[2]})"
                elif r[3] is not None:
                    type_str += f"({r[3]},{r[4]})" if r[4] else f"({r[3]})"
                nullable = "NULL" if r[5] == "YES" else "NOT NULL"
                print(f"    {r[0]:<30} {type_str:<20} {nullable}")
                result["columns"].append({
                    "name": r[0],
                    "type": type_str,
                    "nullable": r[5] == "YES",
                    "default": r[6],
                })
        except Exception as e:
            print(f"  ERRORE lettura colonne: {e}")
            result["error"] = str(e)
            return result

        # Primary key
        try:
            pk_rows = conn.execute(text("""
                SELECT kcu.COLUMN_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
                JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
                    ON kcu.CONSTRAINT_NAME = tc.CONSTRAINT_NAME
                WHERE tc.TABLE_NAME = :table
                  AND tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
                ORDER BY kcu.ORDINAL_POSITION
            """), {"table": table_name}).fetchall()
            pk = [r[0] for r in pk_rows]
            if pk:
                result["primary_key"] = pk
                print(f"\n  Primary key: {pk}")
        except Exception:
            pass

        # Righe di esempio
        if SAMPLE_ROWS > 0:
            print(f"\n  Esempio ({SAMPLE_ROWS} righe):")
            try:
                col_names = [c["name"] for c in result["columns"]]
                sample = conn.execute(
                    text(f"SELECT TOP {SAMPLE_ROWS} * FROM {table_name}")
                ).fetchall()
                if sample:
                    for row in sample:
                        row_dict = {col_names[i]: v for i, v in enumerate(row)}
                        result["sample_rows"].append(row_dict)
                        print("    " + " | ".join(
                            f"{k}={str(v)[:30]}" for k, v in row_dict.items()
                        ))
                else:
                    print("    (tabella vuota)")
            except Exception as e:
                print(f"    ERRORE lettura righe: {e}")
                result["sample_error"] = str(e)

    return result


def save_result(table_name: str, data: dict):
    OUTPUT_DIR.mkdir(exist_ok=True)
    out_file = OUTPUT_DIR / f"{table_name}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str, ensure_ascii=False)
    print(f"  Salvato: {out_file}")


def main():
    if not TABLES_TO_INSPECT:
        print("Nessuna tabella configurata in TABLES_TO_INSPECT.")
        print("Aggiungere i nomi tabella e rieseguire.")
        return

    engine = get_easy_engine()

    print(f"Ispezione di {len(TABLES_TO_INSPECT)} tabella/e su Easy DB")
    print(f"Output: {OUTPUT_DIR.resolve()}")

    for table in TABLES_TO_INSPECT:
        data = inspect_table(engine, table)
        save_result(table, data)

    print(f"\n{'─' * 60}")
    print("Fine ispezione.")


if __name__ == "__main__":
    main()
