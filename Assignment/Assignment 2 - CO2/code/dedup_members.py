import random
import re
from datetime import date, timedelta


STATUS_MAP = {
    "A": "ACTIVE",
    "ACTIVE": "ACTIVE",
    "ACT": "ACTIVE",
    "S": "SUSPENDED",
    "SUSPENDED": "SUSPENDED",
    "SUSP": "SUSPENDED",
    "E": "EXPIRED",
    "EXPIRED": "EXPIRED",
}


def normalise_status(raw_status):
    s = (raw_status or "").strip().upper()
    return STATUS_MAP.get(s, "ACTIVE")


def normalise_name(raw_name):
    return re.sub(r"\s+", " ", (raw_name or "").strip()).title()


def normalise_email(raw_email):
    return (raw_email or "").strip().lower()


def generate_merged_branch_dataset(num_unique_members=20000, num_loans=100000, seed=42):
    """Generate 20,000+ members with >=5% duplicates, 3+ status spellings, 100k loans, and >=50 orphan loans."""
    rng = random.Random(seed)
    members_raw = []
    firsts = ["Priya", "Arjun", "Sneha", "Karthik", "Divya", "Neha", "Imran", "Rohan", "Vikram", "Kavitha"]
    lasts = ["Sharma", "Mehta", "Nair", "Khan", "Reddy", "Menon", "Verma", "Iyer", "Patel", "Das"]
    branches = ["A", "B", "C"]
    status_variants = ["ACTIVE", "Active", "A", "SUSPENDED", "S", "EXPIRED"]

    for i in range(1, num_unique_members + 1):
        br = branches[i % 3]
        code = f"{br}-{i:05d}"
        name = f"{firsts[i % len(firsts)]} {lasts[(i // 10) % len(lasts)]}"
        email = f"user{i:05d}@meridian.edu"
        st = rng.choice(["ACTIVE", "Active", "A"]) if i % 10 != 0 else rng.choice(status_variants)
        members_raw.append((code, name, email, "2025-07-15", st))

    # Inject >=5% duplicate members (e.g. 1,150 duplicates = ~5.4% of raw, >5% of 20k)
    dup_count = max(int(num_unique_members * 0.0575), 50)
    for j in range(1, dup_count + 1):
        idx = (j * 18) % num_unique_members
        _, orig_name, orig_email, joined, _ = members_raw[idx]
        br = branches[(j + 1) % 3]
        dup_code = f"{br}-DUP{j:04d}"
        parts = orig_name.split(" ")
        dup_name = f"{parts[0]}  {parts[1]}" if j % 2 == 0 else f"{parts[0][0]}. {parts[1]}"
        dup_email = f" {orig_email.title()} " if j % 2 == 0 else orig_email.upper()
        dup_status = rng.choice(["Active", "A", "ACTIVE"])
        members_raw.append((dup_code, dup_name, dup_email, joined, dup_status))

    # Generate 100,000 loans + 60 orphan loans
    valid_codes = [m[0] for m in members_raw[:num_unique_members]]
    loans_raw = []
    start_d = date(2026, 1, 1)
    for k in range(1, num_loans + 1):
        mcode = valid_codes[k % num_unique_members]
        bid = (k % 60) + 1
        iss = start_d + timedelta(days=k % 300)
        due = iss + timedelta(days=14)
        ret = (due + timedelta(days=rng.randint(-3, 5))).isoformat() if k % 3 != 0 else None
        loans_raw.append((k, mcode, bid, iss.isoformat(), due.isoformat(), ret))

    # Inject 60 orphan loans referencing unknown branch member codes
    for o in range(1, 61):
        loans_raw.append((num_loans + o, f"C-ORPHAN-{o}", 1, "2026-11-02", "2026-11-16", None))

    return members_raw, loans_raw


def deduplicate_and_reconcile(members_raw, loans_raw):
    """Merge duplicate members by canonical email, map old codes -> canonical code, quarantine orphan loans."""
    canonical_by_email = {}
    code_remap = {}
    clean_members = []
    duplicates_merged = 0

    for code, name, email, joined, status in members_raw:
        canon_email = normalise_email(email)
        canon_name = normalise_name(name)
        canon_status = normalise_status(status)

        if canon_email in canonical_by_email:
            duplicates_merged += 1
            canon_code = canonical_by_email[canon_email]
            code_remap[code] = canon_code
        else:
            canonical_by_email[canon_email] = code
            code_remap[code] = code
            clean_members.append((code, canon_name, canon_email, joined, canon_status))

    clean_loans = []
    orphan_loans = []
    known_codes = {m[0] for m in clean_members}

    for lid, mcode, bid, iss, due, ret in loans_raw:
        mapped_code = code_remap.get(mcode)
        if mapped_code is None or mapped_code not in known_codes:
            orphan_loans.append((lid, mcode, bid, iss, "UNKNOWN_MEMBER_CODE"))
        else:
            clean_loans.append((lid, mapped_code, bid, iss, due, ret))

    return {
        "raw_members": len(members_raw),
        "clean_members": clean_members,
        "duplicates_merged": duplicates_merged,
        "raw_loans": len(loans_raw),
        "clean_loans": clean_loans,
        "orphan_loans": orphan_loans,
    }


if __name__ == "__main__":
    m_raw, l_raw = generate_merged_branch_dataset()
    res = deduplicate_and_reconcile(m_raw, l_raw)
    print("=== Day-4 Branch Merge & Deduplication Summary ===")
    print(f"  Raw members       : {res['raw_members']}")
    print(f"  Duplicates merged : {res['duplicates_merged']} ({res['duplicates_merged']/res['raw_members']*100:.2f}%)")
    print(f"  Clean members     : {len(res['clean_members'])}")
    print(f"  Raw loans         : {res['raw_loans']}")
    print(f"  Clean loans       : {len(res['clean_loans'])}")
    print(f"  Orphan loans      : {len(res['orphan_loans'])} (quarantined)")
