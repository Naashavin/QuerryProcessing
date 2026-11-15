from contextlib import closing
from db_config import get_connection


def main():
    with closing(get_connection("mysql")) as conn:
        cur = conn.cursor()
        cur.execute("SELECT VERSION()")
        version = cur.fetchone()[0]
        print(f"Connected to MySQL successfully! Version: {version}")
        cur.close()


if __name__ == "__main__":
    main()

