from datetime import date, datetime
from decimal import Decimal
from select_demo import run_all_queries


def normalize_rows(rows):
    """Normalize Decimal -> float and date -> ISO str for cross-database comparison."""
    norm = []
    for r in rows:
        item = {}
        for k, v in r.items():
            if isinstance(v, Decimal):
                item[k] = round(float(v), 2)
            elif isinstance(v, (date, datetime)):
                item[k] = v.isoformat()
            elif isinstance(v, float):
                item[k] = round(v, 2)
            else:
                item[k] = v
        norm.append(tuple(sorted(item.items())))
    return sorted(norm)


def compare_databases(dbs=("sqlite", "mysql")):
    all_res = {db: run_all_queries(db, show_output=False) for db in dbs}
    base_db = dbs[0]
    titles = list(all_res[base_db].keys())

    print("=== Cross-Database Query Equivalence Report ===")
    for title in titles:
        base_norm = normalize_rows(all_res[base_db][title])
        diffs = []
        for other in dbs[1:]:
            other_norm = normalize_rows(all_res[other][title])
            if other_norm != base_norm:
                diffs.append(f"{other} differs (base={len(base_norm)} vs {other}={len(other_norm)})")
        status = "IDENTICAL" if not diffs else "DIFF: " + "; ".join(diffs)
        print(f"  {title:<55} | rows={len(base_norm):<3} | {status}")


if __name__ == "__main__":
    compare_databases()

