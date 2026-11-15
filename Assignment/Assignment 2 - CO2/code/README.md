# MeridianLib — Multi-Database Library Management System (DSA0501 Assignment 2 - CO2)

**Student:** Avinaash A (`192324260`)

## Security & Configuration Setup

No credentials, hostnames, or tokens are stored in source code or this archive.
1. Copy `.env.example` to `.env.local` (or export environment variables in your shell):
   - `MLIB_SQLITE_PATH=meridianlib.db`
   - `MLIB_MYSQL_HOST`, `MLIB_MYSQL_PORT`, `MLIB_MYSQL_USER`, `MLIB_MYSQL_PASSWORD`, `MLIB_MYSQL_DB`
   - `MLIB_PG_HOST`, `MLIB_PG_PORT`, `MLIB_PG_USER`, `MLIB_PG_PASSWORD`, `MLIB_PG_DB`
2. Install required drivers: `pip install mysql-connector-python psycopg2-binary` (`sqlite3` is in Python standard library).

## Execution Order

Run commands from inside the `code/` folder:

1. `python requirements_check.py` — Validates Task 1 business rules on spreadsheet seed data (<= 50 lines).
2. `python env_check.py` — Verifies installed DB-API 2.0 drivers (`sqlite3`, `mysql.connector`, `psycopg2`) and attributes.
3. `python connect_sqlite.py` / `connect_mysql.py` / `connect_postgres.py` — Tests connections and `with conn:` semantics.
4. `python safe_connect.py` & `python errors_demo.py` — Demonstrates transient vs permanent error retries and 11 failure scenarios.
5. `python create_schema.py sqlite` (and `mysql` / `postgres`) — Creates 3NF tables and inspects system catalog.
6. `python seed_data.py` & `python insert_demo.py` — Seeds pilot data (6 categories, 60 books, 30 members, 80 loans, 12 fines) and demonstrates SQL injection prevention, 6 invalid inserts, insert-ignore, and transaction rollback.
7. `python select_demo.py` & `python compare_results.py` — Runs 10 operational queries and compares equivalence across backends.
8. `python update_demo.py` — Runs 6 conditional/bulk updates, same-value rowcount test, missing-WHERE rollback, and atomic return.
9. `python delete_demo.py` — Runs 4 conditional deletes, FK policy matrix (`RESTRICT`/`CASCADE`/`SET NULL`), `safe_delete_member()`, and soft delete.
10. `python meridianlib.py --db sqlite|mysql|postgres <command>` — Unified layered CLI (`add-member`, `add-book`, `search-books`, `issue-book`, `return-book`, `renew-loan`, `safe-delete-member`, `overdue-report`, `ddl-tx-demo`, `separation-check`).
11. `python -m unittest test_crud.py -v` — Runs 22 automated CRUD/constraint/transaction tests per available backend.
12. `python benchmark.py` — Measures 5 CRUD & index operations (3 repetitions each).
13. Day-4 scripts: `python dedup_members.py`, `python migrate_sqlite_to_pg.py --target postgres|mysql`, `python day4_eval_concurrency.py`, `python -m unittest test_day4.py -v`.

