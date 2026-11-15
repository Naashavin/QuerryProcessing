import importlib


def check_driver(module_name, display_name):
    try:
        mod = importlib.import_module(module_name)
        ver = getattr(mod, "__version__", getattr(mod, "sqlite_version", "N/A"))
        apilevel = getattr(mod, "apilevel", "N/A")
        threadsafety = getattr(mod, "threadsafety", "N/A")
        paramstyle = getattr(mod, "paramstyle", "N/A")
        print(
            f"[OK] {display_name:<24} | version={ver:<10} | apilevel={apilevel} "
            f"| threadsafety={threadsafety} | paramstyle={paramstyle}"
        )
    except ImportError as err:
        print(f"[MISSING] {display_name:<24} -> {err}. Install via pip before running.")


if __name__ == "__main__":
    print("=== DB-API 2.0 Driver Environment Check ===")
    check_driver("sqlite3", "sqlite3 (stdlib)")
    check_driver("mysql.connector", "mysql-connector-python")
    check_driver("psycopg2", "psycopg2-binary")

