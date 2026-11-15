from contextlib import closing
from db_config import get_connection
from safe_connect import sanitize_message


def main():
    try:
        with closing(get_connection("postgres")) as conn:
            cur = conn.cursor()
            cur.execute("SELECT version()")
            version = cur.fetchone()[0]
            print(f"Connected to PostgreSQL successfully! Version: {version}")
            cur.close()
    except Exception as err:
        print(f"PostgreSQL connection attempt failed ({type(err).__name__}): {sanitize_message(err)}")


if __name__ == "__main__":
    main()
