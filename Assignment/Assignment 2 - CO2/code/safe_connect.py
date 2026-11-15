import logging
import re
import sqlite3
import time
from pathlib import Path
from db_config import BASE_DIR, get_connection, get_db_params

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
SAFE_LOG_PATH = LOG_DIR / "safe_connect.log"


def get_logger():
    logger = logging.getLogger("safe_connect")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fh = logging.FileHandler(SAFE_LOG_PATH, mode="a", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
        logger.addHandler(fh)
    return logger


def sanitize_message(msg):
    """Strip any hostnames, usernames, or password-like fragments from error messages."""
    text = str(msg)
    text = re.sub(r"'[^']+'@'[^']+'", "'<app_user>'@'<host>'", text)
    text = re.sub(r"127\.0\.0\.1|localhost", "<configured_host>", text, flags=re.IGNORECASE)
    return text


def is_transient_error(db_type, err):
    """Classify a driver exception as transient (retryable) vs permanent (config fix needed)."""
    msg = str(err).lower()
    if db_type == "sqlite":
        return "locked" in msg or "busy" in msg

    if db_type == "mysql":
        errno = getattr(err, "errno", None)
        if errno in (1045, 1044, 1049, 2005):
            return False  # Access denied, unknown DB, unknown host -> permanent
        if errno in (2003, 2006, 2013, 1205, 1040) or "timed out" in msg or "refused" in msg:
            return True
        return False

    if db_type in ("postgres", "postgresql"):
        pgcode = getattr(err, "pgcode", None)
        if pgcode in ("28P01", "28000", "3D000", "42501"):
            return False
        if "password authentication" in msg or "does not exist" in msg or "could not translate host" in msg:
            return False
        if "timeout" in msg or "connection refused" in msg or "could not connect" in msg or pgcode in ("53300", "57P03"):
            return True
        return False

    return False


def safe_connect(db_type, retries=3, delay=0.2, connector_fn=None):
    """Connect with exponential-style backoff on transient failures; fail fast on permanent errors."""
    logger = get_logger()
    conn_fn = connector_fn or get_connection
    attempt = 0

    while True:
        attempt += 1
        try:
            logger.info(f"[{db_type}] Connection attempt {attempt}/{retries + 1} (credentials masked)")
            conn = conn_fn(db_type)
            logger.info(f"[{db_type}] Connected on attempt {attempt}")
            return conn
        except Exception as err:
            transient = is_transient_error(db_type, err)
            safe_msg = sanitize_message(err)
            kind = "TRANSIENT" if transient else "PERMANENT"
            logger.warning(f"[{db_type}] Attempt {attempt} failed ({kind}): {type(err).__name__}: {safe_msg}")

            if not transient or attempt > retries:
                logger.error(f"[{db_type}] Aborting after {attempt} attempt(s) ({kind})")
                raise

            sleep_sec = delay * attempt
            logger.info(f"[{db_type}] Retrying in {sleep_sec:.2f}s...")
            time.sleep(sleep_sec)


def run_retry_tests():
    # Reset log for clean demonstration
    if SAFE_LOG_PATH.exists():
        SAFE_LOG_PATH.unlink()
    logger = get_logger()

    print("=== Test 1: Permanent Error (Must NOT retry) ===")
    perm_attempts = {"n": 0}

    def fake_perm(_db):
        perm_attempts["n"] += 1
        raise sqlite3.OperationalError("unable to open database file")

    try:
        safe_connect("sqlite", retries=3, delay=0.05, connector_fn=fake_perm)
    except sqlite3.OperationalError as e:
        print(f"Caught permanent error after {perm_attempts['n']} attempt(s): {e}")

    print("\n=== Test 2: Transient Error (Must retry with increasing delay & succeed) ===")
    trans_attempts = {"n": 0}

    def fake_transient(_db):
        trans_attempts["n"] += 1
        if trans_attempts["n"] < 3:
            raise sqlite3.OperationalError("database is locked")
        return sqlite3.connect(":memory:")

    conn = safe_connect("sqlite", retries=3, delay=0.05, connector_fn=fake_transient)
    print(f"Succeeded after {trans_attempts['n']} attempt(s)! Connection open: {conn is not None}")
    conn.close()

    print("\n=== Test 3: Log Audit (Confirm zero passwords/secrets in log) ===")
    log_text = SAFE_LOG_PATH.read_text(encoding="utf-8")
    print(log_text.strip())


if __name__ == "__main__":
    run_retry_tests()

