import sys
from contextlib import closing
from pathlib import Path
from db_config import BASE_DIR, get_connection


SQL_FILES = {
    "sqlite": BASE_DIR / "schema_sqlite.sql",
    "mysql": BASE_DIR / "schema_mysql.sql",
    "postgres": BASE_DIR / "schema_postgres.sql",
}


def execute_schema(db_type):
    db_type = db_type.lower()
    if db_type not in SQL_FILES:
        raise ValueError("Usage: create_schema.py <sqlite|mysql|postgres>")

    sql_text = SQL_FILES[db_type].read_text(encoding="utf-8")

    with closing(get_connection(db_type)) as conn:
        cur = conn.cursor()
        if db_type == "sqlite":
            conn.executescript(sql_text)
        elif db_type == "mysql":
            for stmt in [s.strip() for s in sql_text.split(";") if s.strip()]:
                cur.execute(stmt)
            conn.commit()
        elif db_type == "postgres":
            cur.execute(sql_text)
            conn.commit()
        cur.close()
    print(f"[{db_type.upper()}] Schema created successfully from {SQL_FILES[db_type].name}")


def verify_catalogue(db_type):
    db_type = db_type.lower()
    with closing(get_connection(db_type)) as conn:
        cur = conn.cursor()
        print(f"\n--- Catalogue Verification ({db_type.upper()}) ---")
        if db_type == "sqlite":
            tables = [
                r[0]
                for r in cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                ).fetchall()
            ]
            for tbl in tables:
                cols = cur.execute(f"PRAGMA table_info({tbl})").fetchall()
                col_summary = [(c[1], c[2], "NOT NULL" if c[3] else "NULL") for c in cols]
                print(f"  {tbl:<12}: {col_summary}")
        elif db_type == "mysql":
            cur.execute(
                """
                SELECT table_name, column_name, column_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = DATABASE()
                ORDER BY table_name, ordinal_position
                """
            )
            by_tbl = {}
            for tbl, col, ctype, is_null in cur.fetchall():
                by_tbl.setdefault(tbl, []).append((col, ctype, "NULL" if is_null == "YES" else "NOT NULL"))
            for tbl, cols in by_tbl.items():
                print(f"  {tbl:<12}: {cols}")
        elif db_type == "postgres":
            cur.execute(
                """
                SELECT table_name, column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position
                """
            )
            by_tbl = {}
            for tbl, col, dtype, is_null in cur.fetchall():
                by_tbl.setdefault(tbl, []).append((col, dtype, "NULL" if is_null == "YES" else "NOT NULL"))
            for tbl, cols in by_tbl.items():
                print(f"  {tbl:<12}: {cols}")
        cur.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python create_schema.py <sqlite|mysql|postgres>")
        sys.exit(1)
    target = sys.argv[1].lower()
    execute_schema(target)
    verify_catalogue(target)

