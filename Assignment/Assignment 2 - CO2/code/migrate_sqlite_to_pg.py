import argparse
import hashlib
from contextlib import closing
from create_schema import execute_schema
from db_config import get_connection
from dialect import Dialect
from safe_connect import sanitize_message


TABLES_IN_ORDER = [
    ("category", ["category_id", "name"], "category_id"),
    ("book", ["book_id", "isbn", "title", "author", "category_id", "publication_year", "copies_total", "copies_available"], "book_id"),
    ("member", ["member_id", "member_code", "full_name", "email", "joined_on", "status"], "member_id"),
    ("loan", ["loan_id", "member_id", "book_id", "issued_on", "due_on", "returned_on", "renew_count"], "loan_id"),
    ("fine", ["fine_id", "loan_id", "amount", "assessed_on", "paid"], "fine_id"),
    ("audit_log", ["log_id", "table_name", "record_key", "action", "details", "logged_at"], "log_id"),
]


def compute_table_checksum(cur, table, pk_col):
    cur.execute(f"SELECT {pk_col} FROM {table} ORDER BY {pk_col}")
    keys = [str(r[0]) for r in cur.fetchall()]
    digest = hashlib.sha256(",".join(keys).encode("utf-8")).hexdigest()[:16]
    return len(keys), digest


def migrate(target_db="postgres"):
    """Copy all rows from SQLite to target (PostgreSQL or MySQL verification target) & verify checksums."""
    d_target = Dialect(target_db)
    execute_schema(target_db)

    with closing(get_connection("sqlite")) as src_conn, closing(get_connection(target_db)) as dst_conn:
        src_cur = src_conn.cursor()
        dst_cur = dst_conn.cursor()

        reconciliation = []
        for table, cols, pk_col in TABLES_IN_ORDER:
            col_list = ", ".join(cols)
            src_cur.execute(f"SELECT {col_list} FROM {table} ORDER BY {pk_col}")
            rows = src_cur.fetchall()

            # Convert SQLite integer booleans (0/1) to native boolean for PostgreSQL fine.paid
            if table == "fine":
                converted = []
                for r in rows:
                    row_l = list(r)
                    row_l[4] = d_target.bool_val(bool(row_l[4]))
                    converted.append(tuple(row_l))
                rows = converted

            if rows:
                phs = ", ".join([d_target.placeholder] * len(cols))
                ins_sql = f"INSERT INTO {table} ({col_list}) VALUES ({phs})"
                dst_cur.executemany(ins_sql, rows)

            # Reset PostgreSQL SERIAL sequence after explicit PK load
            if target_db == "postgres" and rows:
                dst_cur.execute(
                    f"SELECT setval(pg_get_serial_sequence('{table}', '{pk_col}'), COALESCE(MAX({pk_col}), 1)) FROM {table}"
                )

            src_cnt, src_hash = compute_table_checksum(src_cur, table, pk_col)
            dst_cnt, dst_hash = compute_table_checksum(dst_cur, table, pk_col)
            match = (src_cnt == dst_cnt) and (src_hash == dst_hash)
            reconciliation.append((table, src_cnt, dst_cnt, src_hash, dst_hash, match))

        dst_conn.commit()
        src_cur.close()
        dst_cur.close()

    print(f"=== Migration Reconciliation Report (SQLite -> {target_db.upper()}) ===")
    print(f"  {'Table':<12} | {'Src Rows':<8} | {'Dst Rows':<8} | {'Src SHA256':<16} | {'Dst SHA256':<16} | {'Match'}")
    print("  " + "-" * 80)
    for tbl, sc, dc, sh, dh, ok in reconciliation:
        print(f"  {tbl:<12} | {sc:<8} | {dc:<8} | {sh:<16} | {dh:<16} | {ok}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate MeridianLib SQLite data to PostgreSQL (or verify via MySQL).")
    parser.add_argument("--target", default="postgres", choices=["postgres", "mysql"])
    args = parser.parse_args()
    try:
        migrate(args.target)
    except Exception as err:
        print(f"Migration to {args.target} stopped ({type(err).__name__}): {sanitize_message(err)}")
