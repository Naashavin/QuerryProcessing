from contextlib import closing
from db_config import get_connection


def main():
    with closing(get_connection("sqlite")) as conn:
        cur = conn.cursor()
        cur.execute("SELECT sqlite_version()")
        version = cur.fetchone()[0]
        print(f"Connected to SQLite successfully! Version: {version}")
        cur.close()


def demonstrate_context_manager():
    """Show that `with conn:` in sqlite3 manages transaction commit/rollback, NOT connection closing."""
    conn = get_connection("sqlite")
    with conn:
        conn.execute("CREATE TABLE IF NOT EXISTS _ctx_demo (id INTEGER)")
        conn.execute("INSERT INTO _ctx_demo VALUES (1)")
    # Connection is STILL open after exiting `with conn:`!
    still_open_count = conn.execute("SELECT COUNT(*) FROM _ctx_demo").fetchone()[0]
    print(f"After `with conn:` exited, connection remained OPEN (rows={still_open_count})")

    # Demonstrate rollback on exception inside `with conn:`
    try:
        with conn:
            conn.execute("INSERT INTO _ctx_demo VALUES (2)")
            raise RuntimeError("Simulated mid-transaction failure")
    except RuntimeError:
        pass
    after_rollback = conn.execute("SELECT COUNT(*) FROM _ctx_demo").fetchone()[0]
    print(f"After exception inside `with conn:`, row 2 rolled back (rows={after_rollback})")
    conn.execute("DROP TABLE IF EXISTS _ctx_demo")
    conn.commit()
    conn.close()
    print("Connection explicitly closed via conn.close() (or use contextlib.closing).")


if __name__ == "__main__":
    main()
    print("\n--- sqlite3 `with conn:` Experiment ---")
    demonstrate_context_manager()

