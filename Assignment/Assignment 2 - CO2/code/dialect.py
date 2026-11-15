import sqlite3
import mysql.connector
import psycopg2
import psycopg2.extras


class Dialect:
    """Encapsulates all SQL and driver-specific syntax for SQLite, MySQL, and PostgreSQL."""

    def __init__(self, db_type):
        self.db_type = db_type.strip().lower()
        if self.db_type == "postgresql":
            self.db_type = "postgres"
        if self.db_type not in ("sqlite", "mysql", "postgres"):
            raise ValueError(f"Unsupported db_type: {db_type}")

    @property
    def placeholder(self):
        return "?" if self.db_type == "sqlite" else "%s"

    def sql(self, template):
        """Replace {ph} tokens with the driver's native parameter placeholder."""
        return template.replace("{ph}", self.placeholder)

    def cursor(self, conn, as_dict=False):
        if not as_dict:
            return conn.cursor()
        if self.db_type == "sqlite":
            conn.row_factory = sqlite3.Row
            return conn.cursor()
        if self.db_type == "mysql":
            return conn.cursor(dictionary=True)
        return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def fetch_dicts(self, cur):
        rows = cur.fetchall()
        return [dict(r) for r in rows]

    def fetch_one_dict(self, cur):
        row = cur.fetchone()
        return dict(row) if row is not None else None

    def bool_val(self, flag):
        if self.db_type == "postgres":
            return bool(flag)
        return 1 if flag else 0

    def insert_ignore_sql(self, table, cols, conflict_col):
        col_list = ", ".join(cols)
        phs = ", ".join([self.placeholder] * len(cols))
        if self.db_type == "sqlite":
            return f"INSERT OR IGNORE INTO {table} ({col_list}) VALUES ({phs})"
        if self.db_type == "mysql":
            return f"INSERT IGNORE INTO {table} ({col_list}) VALUES ({phs})"
        return f"INSERT INTO {table} ({col_list}) VALUES ({phs}) ON CONFLICT ({conflict_col}) DO NOTHING"

    def insert_returning_id(self, cur, sql_template, params, pk_col):
        stmt = self.sql(sql_template)
        if self.db_type == "postgres":
            stmt = f"{stmt} RETURNING {pk_col}"
            cur.execute(stmt, params)
            return cur.fetchone()[0]
        cur.execute(stmt, params)
        return cur.lastrowid

    def ilike(self, column):
        if self.db_type == "postgres":
            return f"{column} ILIKE {self.placeholder}"
        return f"LOWER({column}) LIKE LOWER({self.placeholder})"

    def add_days_expr(self, date_col, days):
        if self.db_type == "sqlite":
            return f"DATE({date_col}, '+{int(days)} days')"
        if self.db_type == "mysql":
            return f"DATE_ADD({date_col}, INTERVAL {int(days)} DAY)"
        return f"({date_col}::date + INTERVAL '{int(days)} days')::date"

    def today_expr(self):
        return "DATE('now')" if self.db_type == "sqlite" else "CURRENT_DATE"

    def for_update(self):
        return "" if self.db_type == "sqlite" else " FOR UPDATE"

    def begin_tx(self, cur):
        if self.db_type == "mysql":
            cur.execute("START TRANSACTION")
        else:
            cur.execute("BEGIN")

    def integrity_exceptions(self):
        return (
            sqlite3.IntegrityError,
            mysql.connector.IntegrityError,
            mysql.connector.DatabaseError,
            psycopg2.IntegrityError,
        )
