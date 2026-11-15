import re

members = [
    {"code": "M001", "full_name": "Arjun Mehta", "email": "arjun.mehta@meridian.edu", "joined_on": "2025-07-15", "status": "ACTIVE"},
    {"code": "M002", "full_name": "Sneha O'Brien", "email": "sneha.obrien@meridian.edu", "joined_on": "15/07/2025", "status": "active"},
    {"code": "M003", "full_name": "Karthik R", "email": "karthik.r@meridian.edu", "joined_on": "2025-08-01", "status": "ACTIVE"},
    {"code": "M004", "full_name": "Divya Nair", "email": "arjun.mehta@meridian.edu", "joined_on": "2025-08-03", "status": "ACTIVE"},
    {"code": "M005", "full_name": "", "email": "neha.k@meridian.edu", "joined_on": "2025-09-10", "status": "ACTIVE"},
    {"code": "M006", "full_name": "Imran Khan", "email": "imran.k@meridian", "joined_on": "2025-09-12", "status": "ACTIVE"},
]
books = [
    {"isbn": "978-0132350884", "title": "Clean Code", "author": "Robert C. Martin", "category": "Programming", "year": 2008, "total": 4, "available": 3},
    {"isbn": "978-0262033848", "title": "Introduction to Algorithms", "author": "Cormen et al.", "category": "Algorithms", "year": 2009, "total": 5, "available": 5},
    {"isbn": "978-0134685991", "title": "Effective Java", "author": "Joshua Bloch", "category": "Programming", "year": 2018, "total": 3, "available": 3},
    {"isbn": "978-0132350884", "title": "Clean Code (reprint)", "author": "Robert C. Martin", "category": "Programming", "year": 2008, "total": 2, "available": 2},
    {"isbn": "978-1491946008", "title": "Fluent Python", "author": "Luciano Ramalho", "category": "Programming", "year": 2015, "total": 2, "available": -1},
    {"isbn": "978-0596517748", "title": "JavaScript: The Good Parts", "author": "Douglas Crockford", "category": "Web", "year": 2008, "total": 1, "available": 0},
]
loans = [
    {"loan_id": 1, "member": "M001", "isbn": "978-0132350884", "issued_on": "2026-10-01", "due_on": "2026-10-15", "returned_on": None},
    {"loan_id": 2, "member": "M003", "isbn": "978-0262033848", "issued_on": "2026-10-03", "due_on": "2026-10-17", "returned_on": "2026-10-16"},
    {"loan_id": 3, "member": "M009", "isbn": "978-0134685991", "issued_on": "2026-10-05", "due_on": "2026-10-19", "returned_on": None},
    {"loan_id": 4, "member": "M001", "isbn": "978-0262033848", "issued_on": "2026-10-20", "due_on": "2026-10-10", "returned_on": None},
    {"loan_id": 5, "member": "M003", "isbn": "978-0596517748", "issued_on": "31-10-2026", "due_on": "14-11-2026", "returned_on": None},
]

seen_emails, seen_isbns, valid_codes = set(), set(), {m["code"] for m in members}
for m in members:
    if not m["full_name"].strip():
        print(f"[VIOLATION] Empty member name: {m}")
    if not re.fullmatch(r"[^@\s]+@meridian\.edu", m["email"].lower()):
        print(f"[VIOLATION BR2] Invalid institutional email: {m}")
    if m["email"].lower() in seen_emails:
        print(f"[VIOLATION BR2] Duplicate email: {m}")
    seen_emails.add(m["email"].lower())

for b in books:
    if b["isbn"] in seen_isbns:
        print(f"[VIOLATION BR1] Duplicate ISBN: {b}")
    seen_isbns.add(b["isbn"])
    if not (0 <= b["available"] <= b["total"]):
        print(f"[VIOLATION BR4] Invalid copies_available: {b}")

for ln in loans:
    if ln["member"] not in valid_codes:
        print(f"[VIOLATION BR6] Loan references unknown member: {ln}")
    if ln["issued_on"][4] == "-" and ln["due_on"][4] == "-" and ln["due_on"] < ln["issued_on"]:
        print(f"[VIOLATION BR5] Due date precedes issued date: {ln}")

