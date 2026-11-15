import os
import sqlite3
import tempfile
from pathlib import Path
import mysql.connector
import psycopg2
from db_config import get_db_params
from safe_connect import is_transient_error, sanitize_message


def run_scenarios():
    records = []

    def add_record(db, scenario, exc):
        code = getattr(exc, "errno", None) or getattr(exc, "pgcode", None) or getattr(exc, "sqlite_errorcode", "N/A")
        kind = "Transient" if is_transient_error(db.lower(), exc) else "Permanent"
        records.append((db, scenario, type(exc).__name__, str(code), kind, sanitize_message(exc)[:85]))

    # --- SQLite (4 scenarios) ---
    # 1. Path in non-existent directory
    try:
        sqlite3.connect(str(Path(tempfile.gettempdir()) / "no_such_dir_xyz" / "test.db"))
    except sqlite3.Error as e:
        add_record("sqlite", "Non-existent folder path", e)

    with tempfile.TemporaryDirectory() as tmp:
        tdir = Path(tmp)
        # 2. Read-only file write
        ro_file = tdir / "ro.db"
        c = sqlite3.connect(ro_file)
        c.execute("CREATE TABLE t(x INT)")
        c.commit()
        c.close()
        os.chmod(ro_file, 0o444)
        c2 = None
        try:
            c2 = sqlite3.connect(ro_file)
            c2.execute("INSERT INTO t VALUES (1)")
        except sqlite3.Error as e:
            add_record("sqlite", "Write to read-only DB file", e)
        finally:
            if c2 is not None:
                c2.close()
            os.chmod(ro_file, 0o666)

        # 3. Non-database text file
        bad_file = tdir / "not_a_db.txt"
        bad_file.write_text("This is plain text, not SQLite", encoding="utf-8")
        try:
            c3 = sqlite3.connect(bad_file)
            c3.execute("SELECT * FROM sqlite_master")
        except sqlite3.Error as e:
            add_record("sqlite", "Open non-database text file", e)
        finally:
            c3.close()

        # 4. Locked database
        lock_file = tdir / "locked.db"
        c_hold = sqlite3.connect(lock_file)
        c_hold.execute("CREATE TABLE t(x INT)")
        c_hold.execute("BEGIN EXCLUSIVE")
        c_wait = sqlite3.connect(lock_file, timeout=0.05)
        try:
            c_wait.execute("INSERT INTO t VALUES (1)")
        except sqlite3.Error as e:
            add_record("sqlite", "Locked database write timeout", e)
        finally:
            c_wait.close()
            c_hold.rollback()
            c_hold.close()

    # --- MySQL (5 scenarios) ---
    mysql_params = get_db_params("mysql")

    # 5. Wrong password (synthetic invalid credentials)
    try:
        p = dict(mysql_params, user="bad_test_user", password="wrong_test_value_123")
        mysql.connector.connect(**p)
    except mysql.connector.Error as e:
        add_record("mysql", "Wrong credentials / password", e)

    # 6. Wrong closed port (3399)
    try:
        p = dict(mysql_params, port=3399, connection_timeout=1)
        mysql.connector.connect(**p)
    except mysql.connector.Error as e:
        add_record("mysql", "Closed / wrong port (3399)", e)

    # 7. Unknown host
    try:
        p = dict(mysql_params, host="nonexistent.invalid.local", connection_timeout=1)
        mysql.connector.connect(**p)
    except mysql.connector.Error as e:
        add_record("mysql", "Unknown hostname", e)

    # 8. Non-existent database
    try:
        p = dict(mysql_params, database="no_such_db_meridian")
        mysql.connector.connect(**p)
    except mysql.connector.Error as e:
        add_record("mysql", "Non-existent database", e)

    # 9. Insufficient privileges on restricted app user
    try:
        conn_priv = mysql.connector.connect(**mysql_params)
        conn_priv.cursor().execute("SELECT user FROM mysql.user")
        conn_priv.close()
    except mysql.connector.Error as e:
        add_record("mysql", "Insufficient privilege (mysql.user)", e)

    # --- PostgreSQL (2 driver scenarios) ---
    pg_params = get_db_params("postgres")

    # 10. Server unreachable / closed port 5432
    try:
        p = dict(pg_params, connect_timeout=1)
        psycopg2.connect(**p)
    except psycopg2.Error as e:
        add_record("postgres", "Server stopped / unreachable port", e)

    # 11. Unknown hostname in PostgreSQL
    try:
        p = dict(pg_params, host="nonexistent.pg.local", connect_timeout=1)
        psycopg2.connect(**p)
    except psycopg2.Error as e:
        add_record("postgres", "Unknown PostgreSQL host", e)

    print(f"{'#':<2} | {'DB':<8} | {'Scenario':<34} | {'Exception':<17} | {'Code':<6} | {'Class':<9} | {'Message'}")
    print("-" * 125)
    for idx, (db, scen, exc, code, kind, msg) in enumerate(records, start=1):
        print(f"{idx:<2} | {db:<8} | {scen:<34} | {exc:<17} | {code:<6} | {kind:<9} | {msg}")


if __name__ == "__main__":
    run_scenarios()
