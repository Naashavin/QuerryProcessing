import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _load_env_file():
    """Load key=value settings from local .env.local (excluded from submission ZIP)."""
    env_file = BASE_DIR / ".env.local"
    if not env_file.exists():
        return
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, val = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())


_load_env_file()


def get_db_params(db_type):
    """Return connection parameters for 'sqlite', 'mysql', or 'postgres' from env vars."""
    db_type = db_type.strip().lower()
    timeout = int(os.environ.get("MLIB_TIMEOUT", "3"))

    if db_type == "sqlite":
        db_name = os.environ.get("MLIB_SQLITE_PATH", "meridianlib.db")
        db_path = Path(db_name)
        if not db_path.is_absolute():
            db_path = BASE_DIR / db_path
        return {"database": str(db_path), "timeout": float(timeout)}

    if db_type == "mysql":
        required = ["MLIB_MYSQL_HOST", "MLIB_MYSQL_USER", "MLIB_MYSQL_PASSWORD", "MLIB_MYSQL_DB"]
        missing = [k for k in required if not os.environ.get(k)]
        if missing:
            raise RuntimeError(f"Missing MySQL configuration environment variables: {', '.join(missing)}")
        return {
            "host": os.environ["MLIB_MYSQL_HOST"],
            "port": int(os.environ.get("MLIB_MYSQL_PORT", "3306")),
            "user": os.environ["MLIB_MYSQL_USER"],
            "password": os.environ["MLIB_MYSQL_PASSWORD"],
            "database": os.environ["MLIB_MYSQL_DB"],
            "connection_timeout": timeout,
        }

    if db_type in ("postgres", "postgresql"):
        required = ["MLIB_PG_HOST", "MLIB_PG_USER", "MLIB_PG_PASSWORD", "MLIB_PG_DB"]
        missing = [k for k in required if not os.environ.get(k)]
        if missing:
            raise RuntimeError(f"Missing PostgreSQL configuration environment variables: {', '.join(missing)}")
        return {
            "host": os.environ["MLIB_PG_HOST"],
            "port": int(os.environ.get("MLIB_PG_PORT", "5432")),
            "user": os.environ["MLIB_PG_USER"],
            "password": os.environ["MLIB_PG_PASSWORD"],
            "dbname": os.environ["MLIB_PG_DB"],
            "connect_timeout": timeout,
        }

    raise ValueError(f"Unsupported db_type: {db_type}")


def mask_params(params):
    """Return a copy of connection parameters safe for logs and screenshots."""
    masked = dict(params)
    for secret_key in ("password", "host", "user"):
        if secret_key in masked:
            masked[secret_key] = "********" if secret_key == "password" else f"<{secret_key}_configured>"
    return masked


def get_connection(db_type, dict_cursor=False):
    """Connection factory returning a DB-API connection for sqlite, mysql, or postgres."""
    db_type = db_type.strip().lower()
    params = get_db_params(db_type)

    if db_type == "sqlite":
        conn = sqlite3.connect(params["database"], timeout=params["timeout"])
        conn.execute("PRAGMA foreign_keys = ON;")
        if dict_cursor:
            conn.row_factory = sqlite3.Row
        return conn

    if db_type == "mysql":
        import mysql.connector

        conn = mysql.connector.connect(**params)
        conn.autocommit = False
        return conn

    if db_type in ("postgres", "postgresql"):
        import psycopg2

        conn = psycopg2.connect(**params)
        conn.autocommit = False
        return conn

    raise ValueError(f"Unsupported db_type: {db_type}")


if __name__ == "__main__":
    for dbt in ("sqlite", "mysql", "postgres"):
        try:
            print(f"{dbt:<10}:", mask_params(get_db_params(dbt)))
        except RuntimeError as e:
            print(f"{dbt:<10}: {e}")

